from app.storage.interface import ObjectStorage
from minio import Minio
from minio.error import S3Error
from minio.commonconfig import CopySource
from datetime import timedelta
from typing import List, Dict, Optional
import socket
import time
import urllib3
import json
import structlog
import os

logger = structlog.get_logger(__name__)

class MinIOStorage(ObjectStorage):
    def __init__(self, endpoint: str, access_key: str, secret_key: str, secure: bool = False):
        self.endpoint = endpoint
        self.secure = secure
        self._last_probe_time: float = 0.0
        self._is_online: bool = False

        # Aggressive sub-second timeouts caused upload finalize/hang failures
        # under load (complete_multipart / head_object / fget_object).
        http_client = urllib3.PoolManager(
            timeout=urllib3.Timeout(connect=10.0, read=120.0),
            retries=urllib3.Retry(
                total=3,
                connect=3,
                read=2,
                backoff_factor=0.5,
                status_forcelist=[500, 502, 503, 504],
            ),
        )
        self.client = Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=secure, http_client=http_client)
        self._ensure_buckets(["knowra-raw", "knowra-derived", "knowra-quarantine"])

    def is_available(self) -> bool:
        """Fast TCP probe (0.2s) to verify if the object storage port is listening.
        Caches offline state for 20s to prevent blocking HTTP request threads with urllib3 connection retries."""
        now = time.time()
        if not self._is_online and (now - self._last_probe_time < 20.0):
            return False

        self._last_probe_time = now
        try:
            parts = self.endpoint.split(":")
            host = parts[0]
            port = int(parts[1]) if len(parts) > 1 else (443 if self.secure else 9000)
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.2)
            res = sock.connect_ex((host, port))
            sock.close()
            self._is_online = (res == 0)
        except Exception:
            self._is_online = False

        return self._is_online

    def _ensure_buckets(self, buckets: List[str]):
        if not self.is_available():
            logger.info("Object storage is currently offline or unreachable; operating in database-first mode", endpoint=self.endpoint)
            return

        for bucket in buckets:
            try:
                if not self.client.bucket_exists(bucket):
                    self.client.make_bucket(bucket)
                    logger.info("Bucket created", bucket=bucket)
            except Exception as e:
                logger.warning("Bucket check/creation failed", error=str(e))
                break

    def initialize_multipart_upload(self, bucket: str, key: str, content_type: str) -> str:
        # MinIO Python SDK does not expose _create_multipart_upload publicly.
        # We access the private method to adhere to direct-to-S3 multi-part without boto3.
        try:
            upload_id = self.client._create_multipart_upload(bucket, key, headers={"Content-Type": content_type})
            return upload_id
        except Exception as e:
            logger.error("Init multipart failed", error=str(e))
            raise

    def generate_presigned_part_url(
        self,
        bucket: str,
        key: str,
        upload_id: str,
        part_number: int,
        expires: timedelta,
    ) -> str:
        try:
            url = self.client.get_presigned_url(
                method="PUT",
                bucket_name=bucket,
                object_name=key,
                expires=expires,
                extra_query_params={
                    "uploadId": upload_id,
                    "partNumber": str(part_number),
                },
            )
            return url
        except Exception as e:
            logger.error(
                "Generate presigned part failed",
                error=str(e),
                bucket=bucket,
                key=key,
                upload_id=upload_id,
                part_number=part_number,
            )
            raise

    def complete_multipart_upload(self, bucket: str, key: str, upload_id: str, parts: List[Dict[str, str]]) -> bool:
        try:
            # parts format expected by private method: [minio.datatypes.Part(part_number, etag)]
            from minio.datatypes import Part
            formatted_parts = [Part(int(p["part_number"]), p["etag"]) for p in parts]
            self.client._complete_multipart_upload(bucket, key, upload_id, formatted_parts)
            return True
        except Exception as e:
            logger.error("Complete multipart failed", error=str(e))
            raise

    def abort_multipart_upload(self, bucket: str, key: str, upload_id: str) -> bool:
        try:
            self.client._abort_multipart_upload(bucket, key, upload_id)
            return True
        except Exception as e:
            logger.error("Abort multipart failed", error=str(e))
            return False

    def head_object(self, bucket: str, key: str) -> Optional[Dict[str, any]]:
        if not self.is_available():
            return None
        try:
            obj = self.client.stat_object(bucket, key)
            return {"size": obj.size, "content_type": obj.content_type, "etag": obj.etag}
        except S3Error as e:
            if e.code == 'NoSuchKey':
                return None
            raise

    def move_object(self, source_bucket: str, source_key: str, dest_bucket: str, dest_key: str) -> bool:
        if not self.is_available():
            return False
        try:
            self.client.copy_object(dest_bucket, dest_key, CopySource(source_bucket, source_key))
            self.client.remove_object(source_bucket, source_key)
            return True
        except Exception as e:
            logger.error("Move object failed", error=str(e))
            return False

    def download_file(self, bucket: str, key: str, file_path: str) -> bool:
        if not self.is_available():
            logger.warning("Object storage is offline, skipping file download", bucket=bucket, key=key)
            return False
        try:
            self.client.fget_object(bucket, key, file_path)
            return True
        except Exception as e:
            logger.error("Download failed", error=str(e))
            return False

    def upload_file(self, bucket: str, key: str, file_path: str, content_type: str) -> bool:
        if not self.is_available():
            logger.info("Object storage is offline, skipping S3 upload (data preserved in database)", bucket=bucket, key=key)
            return False
        try:
            self.client.fput_object(bucket, key, file_path, content_type=content_type)
            return True
        except Exception as e:
            logger.error("Upload failed", error=str(e))
            return False
            
    def get_presigned_download_url(self, bucket: str, key: str, expires: timedelta, filename: Optional[str] = None) -> str:
        extra_query_params = None
        if filename:
            extra_query_params = {"response-content-disposition": f'attachment; filename="{filename}"'}
        return self.client.presigned_get_object(bucket, key, expires=expires, extra_query_params=extra_query_params)


# Global instance for injection
import os
MINIO_ENDPOINT = os.getenv("S3_ENDPOINT", "localhost:9000")
MINIO_ACCESS = os.getenv("S3_ACCESS_KEY", "minioadmin")
MINIO_SECRET = os.getenv("S3_SECRET_KEY", "minioadmin")
storage_client = MinIOStorage(MINIO_ENDPOINT, MINIO_ACCESS, MINIO_SECRET, secure=False)

def get_storage_client() -> ObjectStorage:
    return storage_client

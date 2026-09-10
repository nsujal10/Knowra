from app.storage.interface import ObjectStorage
from minio import Minio
from minio.error import S3Error
from minio.commonconfig import CopySource
from datetime import timedelta
from typing import List, Dict, Optional
import urllib3
import json
import structlog
import os

logger = structlog.get_logger(__name__)

class MinIOStorage(ObjectStorage):
    def __init__(self, endpoint: str, access_key: str, secret_key: str, secure: bool = False):
        self.client = Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=secure)
        self._ensure_buckets(["knowra-raw", "knowra-derived", "knowra-quarantine"])

    def _ensure_buckets(self, buckets: List[str]):
        for bucket in buckets:
            try:
                if not self.client.bucket_exists(bucket):
                    self.client.make_bucket(bucket)
                    logger.info("Bucket created", bucket=bucket)
            except S3Error as e:
                logger.error("Bucket creation failed", error=str(e))

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
        try:
            obj = self.client.stat_object(bucket, key)
            return {"size": obj.size, "content_type": obj.content_type, "etag": obj.etag}
        except S3Error as e:
            if e.code == 'NoSuchKey':
                return None
            raise

    def move_object(self, source_bucket: str, source_key: str, dest_bucket: str, dest_key: str) -> bool:
        try:
            self.client.copy_object(dest_bucket, dest_key, CopySource(source_bucket, source_key))
            self.client.remove_object(source_bucket, source_key)
            return True
        except Exception as e:
            logger.error("Move object failed", error=str(e))
            return False

    def download_file(self, bucket: str, key: str, file_path: str) -> bool:
        try:
            self.client.fget_object(bucket, key, file_path)
            return True
        except Exception as e:
            logger.error("Download failed", error=str(e))
            return False

    def upload_file(self, bucket: str, key: str, file_path: str, content_type: str) -> bool:
        try:
            self.client.fput_object(bucket, key, file_path, content_type=content_type)
            return True
        except Exception as e:
            logger.error("Upload failed", error=str(e))
            return False
            
    def get_presigned_download_url(self, bucket: str, key: str, expires: timedelta) -> str:
        return self.client.presigned_get_object(bucket, key, expires=expires)

# Global instance for injection
import os
MINIO_ENDPOINT = os.getenv("S3_ENDPOINT", "localhost:9000")
MINIO_ACCESS = os.getenv("S3_ACCESS_KEY", "minioadmin")
MINIO_SECRET = os.getenv("S3_SECRET_KEY", "minioadmin")
storage_client = MinIOStorage(MINIO_ENDPOINT, MINIO_ACCESS, MINIO_SECRET, secure=False)

def get_storage_client() -> ObjectStorage:
    return storage_client

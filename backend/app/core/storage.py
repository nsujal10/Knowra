from abc import ABC, abstractmethod
from minio import Minio
from minio.error import S3Error
import datetime
import structlog
import os

logger = structlog.get_logger(__name__)

class ObjectStorage(ABC):
    @abstractmethod
    def upload(self, bucket: str, object_name: str, file_path: str) -> bool:
        pass
    
    @abstractmethod
    def download(self, bucket: str, object_name: str, file_path: str) -> bool:
        pass
        
    @abstractmethod
    def delete(self, bucket: str, object_name: str) -> bool:
        pass
        
    @abstractmethod
    def exists(self, bucket: str, object_name: str) -> bool:
        pass
        
    @abstractmethod
    def generate_presigned_url(self, bucket: str, object_name: str, expires_in_sec: int = 3600) -> str:
        pass

class MinIOStorage(ObjectStorage):
    def __init__(self, endpoint: str, access_key: str, secret_key: str, secure: bool = False):
        self.client = Minio(
            endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure
        )
        logger.info("MinIO client initialized", endpoint=endpoint)

    def _ensure_bucket(self, bucket: str):
        try:
            if not self.client.bucket_exists(bucket):
                self.client.make_bucket(bucket)
                logger.info("Bucket created", bucket=bucket)
        except S3Error as e:
            logger.error("Bucket creation failed", error=str(e))
            raise

    def upload(self, bucket: str, object_name: str, file_path: str) -> bool:
        self._ensure_bucket(bucket)
        try:
            self.client.fput_object(bucket, object_name, file_path)
            logger.info("File uploaded", bucket=bucket, object_name=object_name)
            return True
        except Exception as e:
            logger.error("Upload failed", error=str(e))
            return False

    def download(self, bucket: str, object_name: str, file_path: str) -> bool:
        try:
            self.client.fget_object(bucket, object_name, file_path)
            logger.info("File downloaded", object_name=object_name, dest=file_path)
            return True
        except Exception as e:
            logger.error("Download failed", error=str(e))
            return False

    def delete(self, bucket: str, object_name: str) -> bool:
        try:
            self.client.remove_object(bucket, object_name)
            logger.info("File deleted", object_name=object_name)
            return True
        except Exception as e:
            logger.error("Delete failed", error=str(e))
            return False

    def exists(self, bucket: str, object_name: str) -> bool:
        try:
            self.client.stat_object(bucket, object_name)
            return True
        except S3Error as e:
            if e.code == 'NoSuchKey':
                return False
            raise

    def generate_presigned_url(self, bucket: str, object_name: str, expires_in_sec: int = 3600) -> str:
        try:
            url = self.client.presigned_get_object(
                bucket, object_name, expires=datetime.timedelta(seconds=expires_in_sec)
            )
            return url
        except Exception as e:
            logger.error("Failed to generate presigned URL", error=str(e))
            raise

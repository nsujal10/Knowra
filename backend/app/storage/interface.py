from typing import Protocol, List, Dict, Optional
from datetime import timedelta
import io

class ObjectStorage(Protocol):
    def initialize_multipart_upload(self, bucket: str, key: str, content_type: str) -> str:
        ...
        
    def generate_presigned_part_url(self, bucket: str, key: str, upload_id: str, part_number: int, expires: timedelta) -> str:
        ...
        
    def complete_multipart_upload(self, bucket: str, key: str, upload_id: str, parts: List[Dict[str, str]]) -> bool:
        ...
        
    def abort_multipart_upload(self, bucket: str, key: str, upload_id: str) -> bool:
        ...
        
    def head_object(self, bucket: str, key: str) -> Optional[Dict[str, any]]:
        ...
        
    def move_object(self, source_bucket: str, source_key: str, dest_bucket: str, dest_key: str) -> bool:
        ...
        
    def download_file(self, bucket: str, key: str, file_path: str) -> bool:
        ...
        
    def upload_file(self, bucket: str, key: str, file_path: str, content_type: str) -> bool:
        ...
        
    def get_presigned_download_url(self, bucket: str, key: str, expires: timedelta) -> str:
        ...

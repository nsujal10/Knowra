import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from app.core.storage import MinIOStorage

def test_storage():
    storage = MinIOStorage("localhost:9000", "minioadmin", "Sipl@12345", secure=False)
    bucket = "knowra"
    
    # Create a dummy file
    with open("dummy.txt", "w") as f:
        f.write("Hello MinIO")
        
    storage.upload(bucket, "test/dummy.txt", "dummy.txt")
    assert storage.exists(bucket, "test/dummy.txt")
    
    url = storage.generate_presigned_url(bucket, "test/dummy.txt")
    print(f"Presigned URL generated: {url}")
    
    storage.download(bucket, "test/dummy.txt", "dummy_downloaded.txt")
    assert os.path.exists("dummy_downloaded.txt")
    
    storage.delete(bucket, "test/dummy.txt")
    assert not storage.exists(bucket, "test/dummy.txt")
    
    os.remove("dummy.txt")
    os.remove("dummy_downloaded.txt")
    print("Storage Test Passed!")

if __name__ == "__main__":
    test_storage()

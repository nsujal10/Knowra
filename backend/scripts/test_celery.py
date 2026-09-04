import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from app.tasks.pipeline import validate_media_task
import time

def test_celery():
    print("Dispatching Celery Task...")
    result = validate_media_task.delay("s3://bucket/test.mp4")
    print(f"Task ID: {result.id}")
    while not result.ready():
        print("Waiting for task completion...")
        time.sleep(1)
    print(f"Task Output: {result.get()}")
    print("Celery Test Passed!")

if __name__ == "__main__":
    test_celery()

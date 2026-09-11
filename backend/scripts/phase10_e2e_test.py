import sys
import os
import time
import subprocess

sys.path.append(
    os.path.join(os.path.dirname(__file__), "..")
)

from app.core.database import engine, SessionLocal
from app.models.base import Base
from app.models.media_asset import MediaAsset
from app.models.media_artifact import MediaArtifact
from app.models.enums import MediaStatus


Base.metadata.create_all(bind=engine)

import scripts.seed_security

scripts.seed_security.seed()


def run_test():
    import requests

    BASE_URL = "http://localhost:8000/api/v1"

    print("\n--- 1. Provisioning & Setup ---")

    # Register test user.
    # Registration may return 401 in the current project because of
    # the existing registration/security behavior, so don't depend
    # on its response if the user already exists.
    requests.post(
        f"{BASE_URL}/auth/register",
        json={
            "email": "audio@tenant.com",
            "password": "Sipl@12345",
            "full_name": "Au",
            "organization_name": "Org Au",
        },
    )

    # Login
    login_res = requests.post(
        f"{BASE_URL}/auth/login",
        json={
            "email": "audio@tenant.com",
            "password": "Sipl@12345",
        },
    )

    login_res.raise_for_status()

    token = login_res.json()["access_token"]

    headers = {
        "Authorization": f"Bearer {token}"
    }

    # Create meeting
    meeting_res = requests.post(
        f"{BASE_URL}/meetings",
        headers=headers,
        json={
            "title": "Audio Pipeline Test"
        },
    )

    meeting_res.raise_for_status()

    meeting_id = meeting_res.json()["id"]

    # ---------------------------------------------------------
    # Generate synthetic MP4
    # ---------------------------------------------------------

    import tempfile

    test_media_path = tempfile.mktemp(
        suffix=".mp4"
    )

    print(
        "Generating synthetic 2-second MP4 "
        "with 1kHz tone using FFmpeg..."
    )

    subprocess.run(
        [
            "ffmpeg",
            "-f",
            "lavfi",
            "-i",
            "testsrc=duration=2:size=128x72:rate=10",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=1000:duration=2",
            "-c:v",
            "libx264",
            "-c:a",
            "aac",
            "-y",
            test_media_path,
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    size = os.path.getsize(
        test_media_path
    )

    # ---------------------------------------------------------
    # Upload
    # ---------------------------------------------------------

    print("\n--- 2. Uploading Media ---")

    upload_res = requests.post(
        f"{BASE_URL}/meetings/{meeting_id}/media",
        headers=headers,
        json={
            "filename": "test_video.mp4",
            "content_type": "video/mp4",
            "size_bytes": size,
            "parts_count": 1,
        },
    )

    upload_res.raise_for_status()

    media_data = upload_res.json()

    media_id = media_data["media_id"]
    upload_id = media_data["upload_id"]

    presigned_url = (
        media_data["parts"][0]["upload_url"]
    )

    # Client-side upload to MinIO
    with open(test_media_path, "rb") as f:
        put_res = requests.put(
            presigned_url,
            data=f,
        )

    put_res.raise_for_status()

    etag = put_res.headers.get(
        "ETag",
        put_res.headers.get("etag", ""),
    ).strip('"')

    # Complete multipart upload
    complete_res = requests.post(
        f"{BASE_URL}/media/{media_id}/complete",
        headers=headers,
        json={
            "upload_id": upload_id,
            "parts": [
                {
                    "part_number": 1,
                    "etag": etag,
                }
            ],
        },
    )

    complete_res.raise_for_status()

    print(
        f"Media uploaded successfully: {media_id}"
    )

    # ---------------------------------------------------------
    # Pipeline polling
    # ---------------------------------------------------------

    print(
        "\n--- 3. Polling Media Processing Pipeline ---"
    )

    db = SessionLocal()

    try:
        for attempt in range(30):

            db.expire_all()

            media = (
                db.query(MediaAsset)
                .filter(
                    MediaAsset.id == media_id
                )
                .first()
            )

            if not media:
                raise RuntimeError(
                    "Media asset not found"
                )

            print(
                f"Attempt {attempt + 1}/30 | "
                f"Media Status: {media.status}"
            )

            # -------------------------------------------------
            # SUCCESS
            # -------------------------------------------------

            if (
                media.status
                == MediaStatus.READY.value
            ):

                print(
                    "\n[PASS] Media pipeline "
                    "completed successfully."
                )

                artifact = (
                    db.query(MediaArtifact)
                    .filter(
                        MediaArtifact.media_asset_id
                        == media_id
                    )
                    .first()
                )

                if not artifact:
                    raise AssertionError(
                        "Normalized audio artifact "
                        "was not created"
                    )

                print(
                    f"Artifact Type: "
                    f"{artifact.artifact_type}"
                )

                print(
                    f"Artifact Storage Key: "
                    f"{artifact.storage_key}"
                )

                print(
                    f"Artifact Size: "
                    f"{artifact.byte_size} bytes"
                )

                print(
                    f"Artifact SHA256: "
                    f"{artifact.checksum_sha256}"
                )

                break

            # -------------------------------------------------
            # FAILURE
            # -------------------------------------------------

            if (
                media.status
                == MediaStatus.FAILED.value
            ):
                raise AssertionError(
                    "Media pipeline failed"
                )

            # -------------------------------------------------
            # QUARANTINE
            # -------------------------------------------------

            if (
                media.status
                == MediaStatus.QUARANTINED.value
            ):
                raise AssertionError(
                    "Media was quarantined"
                )

            time.sleep(2)

        else:
            raise AssertionError(
                "Media pipeline did not reach READY "
                "within 60 seconds"
            )

    finally:
        db.close()

        if os.path.exists(test_media_path):
            os.remove(test_media_path)


if __name__ == "__main__":
    run_test()
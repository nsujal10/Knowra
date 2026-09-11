import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import unittest
from uuid import uuid4
from app.core.database import SessionLocal, engine
from app.models.base import Base
from app.models.organization import Organization
from app.models.user import User
from app.models.meeting import Meeting
from app.models.speaker import Speaker
from app.models.media_asset import MediaAsset
from app.models.enums import MediaStatus
from app.services.diarization_service import DiarizationService
from app.ai.diarization.schemas import DiarizationResult, DiarizationSegment


class TestDiarizationIsolation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=engine)
        import scripts.seed_security
        scripts.seed_security.seed()

    def setUp(self):
        self.db = SessionLocal()

        # Provision Tenant A
        unique_a = uuid4().hex[:6]
        self.tenant_a = Organization(name=f"Org A {unique_a}", slug=f"org-a-{unique_a}")
        self.db.add(self.tenant_a)
        self.db.flush()

        self.user_a = User(
            email=f"user_a_{unique_a}@example.com",
            password_hash="hash",
            full_name="User A",
        )
        self.db.add(self.user_a)
        self.db.flush()

        self.meeting_a = Meeting(
            tenant_id=self.tenant_a.id,
            owner_id=self.user_a.id,
            title="Tenant A Strategy",
        )
        self.db.add(self.meeting_a)
        self.db.flush()

        self.speaker_a = Speaker(
            tenant_id=self.tenant_a.id,
            meeting_id=self.meeting_a.id,
            speaker_label="SPEAKER_00",
            display_name="CEO Alice",
        )
        self.db.add(self.speaker_a)

        # Provision Tenant B
        unique_b = uuid4().hex[:6]
        self.tenant_b = Organization(name=f"Org B {unique_b}", slug=f"org-b-{unique_b}")
        self.db.add(self.tenant_b)
        self.db.flush()

        self.user_b = User(
            email=f"user_b_{unique_b}@example.com",
            password_hash="hash",
            full_name="User B",
        )
        self.db.add(self.user_b)
        self.db.flush()

        self.meeting_b = Meeting(
            tenant_id=self.tenant_b.id,
            owner_id=self.user_b.id,
            title="Tenant B Strategy",
        )
        self.db.add(self.meeting_b)
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_tenant_cannot_read_other_tenant_speakers(self):
        """Tenant B query for Tenant A's meeting speakers returns empty list."""
        service_b = DiarizationService(self.db, self.tenant_b.id)
        speakers = service_b.get_speakers_for_meeting(self.meeting_a.id)
        self.assertEqual(speakers, [])

    def test_tenant_cannot_update_other_tenant_speaker(self):
        """Tenant B cannot update Tenant A's speaker display name."""
        service_b = DiarizationService(self.db, self.tenant_b.id)
        updated = service_b.update_speaker(
            speaker_id=self.speaker_a.id,
            display_name="Hacked Name",
        )
        self.assertIsNone(updated)

        # Verify Tenant A's speaker was NOT modified
        self.db.refresh(self.speaker_a)
        self.assertEqual(self.speaker_a.display_name, "CEO Alice")

    def test_tenant_cannot_save_diarization_for_other_meeting(self):
        """Diarization persistence preserves tenant boundary and creates speakers under caller's tenant."""
        service_b = DiarizationService(self.db, self.tenant_b.id)
        result = DiarizationResult(
            segments=[
                DiarizationSegment(speaker_label="SPEAKER_00", start_seconds=0.0, end_seconds=1.0),
            ],
            speakers=["SPEAKER_00"],
            model_name="mock",
            model_version="1.0",
        )

        # Service under tenant B cannot modify Tenant A's speakers
        speakers_a_before = (
            self.db.query(Speaker)
            .filter(Speaker.tenant_id == self.tenant_a.id)
            .count()
        )

        media_b = MediaAsset(
            tenant_id=self.tenant_b.id,
            meeting_id=self.meeting_b.id,
            filename="audio.wav",
            original_content_type="audio/wav",
            status=MediaStatus.READY,
        )
        self.db.add(media_b)
        self.db.commit()

        run = service_b.save_diarization(self.meeting_b.id, media_b.id, result)
        self.assertEqual(run.tenant_id, self.tenant_b.id)

        speakers_a_after = (
            self.db.query(Speaker)
            .filter(Speaker.tenant_id == self.tenant_a.id)
            .count()
        )
        self.assertEqual(speakers_a_before, speakers_a_after)


if __name__ == "__main__":
    unittest.main()

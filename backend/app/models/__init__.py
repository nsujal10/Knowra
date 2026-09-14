from app.models.audit_log import AuditLog
from app.models.membership import Membership
from app.models.organization import Organization
from app.models.permission import Permission
from app.models.refresh_session import RefreshSession
from app.models.role import Role
from app.models.role_permission import RolePermission
from app.models.user import User
from app.models.meeting import Meeting

from app.models.media_asset import MediaAsset
from app.models.upload_session import UploadSession
from app.models.processing_job import ProcessingJob
from app.models.media_artifact import MediaArtifact
from app.models.transcript import Transcript
from app.models.transcript_segment import TranscriptSegment
from app.models.transcript_word import TranscriptWord
from app.models.transcription_run import TranscriptionRun
from app.models.speaker import Speaker
from app.models.speaker_segment import SpeakerSegment
from app.models.diarization_run import DiarizationRun

# Phase 13 – Canonical Transcript Format
from app.models.transcript_version import TranscriptVersion

# Phase 14 – Speaker Identification
from app.models.speaker_identity import (
    SpeakerProfile,
    SpeakerIdentityAssignment,
    SpeakerIdentityHistory,
)

# Phase 15 – Meeting Intelligence
from app.intelligence.models import (
    IntelligenceRun,
    Topic,
    Decision,
    Risk,
    Question,
    Commitment,
)

# Phase 16 – Action Item Lifecycle
from app.actions.models import (
    ActionItem,
    ActionItemEvidence,
    ActionItemEvent,
    ActionItemComment,
)

__all__ = [
    "Transcript",
    "TranscriptSegment",
    "TranscriptWord",
    "TranscriptionRun",
    "TranscriptVersion",
    "Speaker",
    "SpeakerSegment",
    "DiarizationRun",
    "SpeakerProfile",
    "SpeakerIdentityAssignment",
    "SpeakerIdentityHistory",
    "IntelligenceRun",
    "Topic",
    "Decision",
    "Risk",
    "Question",
    "Commitment",
    "ActionItem",
    "ActionItemEvidence",
    "ActionItemEvent",
    "ActionItemComment",
]
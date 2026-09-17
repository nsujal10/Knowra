import re
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from uuid import UUID
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.speaker import Speaker


class TemporalResolver:
    """
    Parses conversational temporal expressions from meeting transcripts into concrete,
    timezone-aware UTC datetimes.
    """

    WEEKDAYS = {
        "monday": 0,
        "tuesday": 1,
        "wednesday": 2,
        "thursday": 3,
        "friday": 4,
        "saturday": 5,
        "sunday": 6,
    }

    @classmethod
    def resolve_expression(
        cls, expression: Optional[str], anchor_date: Optional[datetime] = None
    ) -> Optional[datetime]:
        if not expression or not expression.strip():
            return None

        clean_expr = expression.strip().lower()
        base = anchor_date or datetime.now(timezone.utc)
        if base.tzinfo is None:
            base = base.replace(tzinfo=timezone.utc)

        # 1. Standard ISO parsing attempt
        try:
            # e.g. 2026-09-20 or 2026-09-20T17:00:00Z
            parsed = datetime.fromisoformat(expression.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed
        except (ValueError, TypeError):
            pass

        # 2. "today" / "end of day"
        if "today" in clean_expr or "eod" in clean_expr or "end of day" in clean_expr:
            return base.replace(hour=18, minute=0, second=0, microsecond=0)

        # 3. "tomorrow"
        if "tomorrow" in clean_expr:
            target = base + timedelta(days=1)
            return target.replace(hour=18, minute=0, second=0, microsecond=0)

        # 4. "in X days / weeks"
        days_match = re.search(r"in\s+(\d+)\s+day", clean_expr)
        if days_match:
            days = int(days_match.group(1))
            return (base + timedelta(days=days)).replace(hour=18, minute=0, second=0, microsecond=0)

        weeks_match = re.search(r"in\s+(\d+)\s+week", clean_expr)
        if weeks_match:
            weeks = int(weeks_match.group(1))
            return (base + timedelta(weeks=weeks)).replace(hour=18, minute=0, second=0, microsecond=0)

        # 5. "end of week" / "eow" / "by friday"
        if "end of week" in clean_expr or "eow" in clean_expr:
            days_ahead = (4 - base.weekday()) % 7
            if days_ahead == 0:
                days_ahead = 7
            target = base + timedelta(days=days_ahead)
            return target.replace(hour=18, minute=0, second=0, microsecond=0)

        # 6. Specific day of week (e.g. "by next tuesday" or "by monday")
        for day_name, day_idx in cls.WEEKDAYS.items():
            if day_name in clean_expr:
                current_day = base.weekday()
                days_ahead = (day_idx - current_day) % 7
                if days_ahead <= 0 or "next" in clean_expr:
                    days_ahead += 7
                target = base + timedelta(days=days_ahead)
                return target.replace(hour=18, minute=0, second=0, microsecond=0)

        # 7. Next month
        if "next month" in clean_expr:
            # Approximate by adding 30 days
            return (base + timedelta(days=30)).replace(hour=18, minute=0, second=0, microsecond=0)

        return None


class OwnerCandidateResolver:
    """
    Maps speaker labels or extracted owner names to registered enterprise tenant users.
    Implements candidate scoring so humans can easily confirm assignments.
    """

    def __init__(self, db: Session, tenant_id: UUID):
        self.db = db
        self.tenant_id = tenant_id

    def resolve_candidate(
        self,
        owner_raw: Optional[str],
        meeting_id: UUID,
    ) -> Tuple[Optional[UUID], Optional[UUID], Optional[float]]:
        """
        Returns:
            (candidate_user_id, candidate_speaker_id, confidence_score)
        """
        if not owner_raw or not owner_raw.strip():
            return None, None, None

        query = owner_raw.strip().lower()

        # Step 1: Match against meeting speakers
        speakers = (
            self.db.query(Speaker)
            .filter(
                Speaker.tenant_id == self.tenant_id,
                Speaker.meeting_id == meeting_id,
            )
            .all()
        )

        for spk in speakers:
            # Match speaker label (e.g. "speaker_0", "SPEAKER_1")
            if spk.speaker_label.lower() == query or spk.speaker_label.lower().replace("_", " ") == query:
                user_id = spk.user_id
                confidence = 0.95 if user_id else 0.70
                return user_id, spk.id, confidence

            # Match display name (e.g. "David", "Zira")
            if spk.display_name and (spk.display_name.lower() in query or query in spk.display_name.lower()):
                user_id = spk.user_id
                confidence = 0.90 if user_id else 0.75
                return user_id, spk.id, confidence

        # Step 2: Match against tenant users (full name, email, or first name)
        from app.models.membership import Membership
        tenant_users = (
            self.db.query(User)
            .join(Membership, Membership.user_id == User.id)
            .filter(Membership.organization_id == self.tenant_id)
            .all()
        )

        for user in tenant_users:
            full_name = user.full_name.lower() if user.full_name else ""
            email = user.email.lower() if user.email else ""

            if query == email or query in email:
                return user.id, None, 0.95

            if query == full_name:
                return user.id, None, 0.90

            # First name match
            first_name = full_name.split()[0] if full_name else ""
            if first_name and (first_name == query or query in first_name):
                return user.id, None, 0.80

        return None, None, None

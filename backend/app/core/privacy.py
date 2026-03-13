"""Privacy Controls and User Preferences.

Manages:
1. Data retention policies
2. Processing boundaries (what's off-limits)
3. Intervention preferences
4. Export and deletion
"""

import logging
from datetime import datetime
from typing import List, Dict, Optional

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class PrivacyZone(BaseModel):
    """Topic or context that's off-limits for AI processing."""

    id: str
    name: str
    keywords: List[str]  # Keywords to detect this zone
    mode: str  # "reflection_only" or "no_storage"
    created_at: str


class InterventionPreferences(BaseModel):
    """User preferences for AI interventions."""

    enabled: bool = True
    pause_until: Optional[str] = None  # ISO timestamp
    quiet_hours_start: Optional[int] = None  # Hour (0-23)
    quiet_hours_end: Optional[int] = None  # Hour (0-23)
    max_per_day: int = 3
    priority_threshold: str = "medium"  # "low", "medium", "high"


class DataRetentionPolicy(BaseModel):
    """Data retention and deletion rules."""

    auto_delete_after_days: Optional[int] = None
    archive_after_days: Optional[int] = 365
    keep_insights_only: bool = False  # Delete raw data, keep patterns


class UserPrivacySettings(BaseModel):
    """Complete privacy settings for a user."""

    user_id: str
    privacy_zones: List[PrivacyZone] = []
    intervention_prefs: InterventionPreferences = InterventionPreferences()
    retention_policy: DataRetentionPolicy = DataRetentionPolicy()
    local_processing_only: bool = False
    allow_model_training: bool = False
    created_at: str
    updated_at: str


class PrivacyController:
    """Enforces privacy controls and user preferences."""

    def __init__(self):
        self.settings_cache = {}  # user_id -> UserPrivacySettings

    def check_privacy_zone(
        self,
        text: str,
        user_settings: UserPrivacySettings,
    ) -> Optional[PrivacyZone]:
        """Check if text contains privacy zone keywords.
        
        Returns:
            PrivacyZone if detected, None otherwise
        """
        text_lower = text.lower()

        for zone in user_settings.privacy_zones:
            if any(kw in text_lower for kw in zone.keywords):
                return zone

        return None

    def should_store_event(
        self,
        event: dict,
        user_settings: UserPrivacySettings,
    ) -> bool:
        """Determine if event should be stored."""
        # Check privacy zones
        zone = self.check_privacy_zone(
            event.get("text", ""),
            user_settings,
        )

        if zone:
            if zone.mode == "no_storage":
                logger.info(f"Event blocked by privacy zone: {zone.name}")
                return False
            elif zone.mode == "reflection_only":
                # Store but don't process with AI
                event["privacy_mode"] = "reflection_only"

        return True

    def should_send_intervention(
        self,
        priority: str,
        user_settings: UserPrivacySettings,
    ) -> bool:
        """Check if intervention should be sent based on preferences."""
        prefs = user_settings.intervention_prefs

        # Check if interventions are enabled
        if not prefs.enabled:
            return False

        # Check pause mode
        if prefs.pause_until:
            pause_until = datetime.fromisoformat(prefs.pause_until)
            if datetime.utcnow() < pause_until:
                logger.info("Interventions paused")
                return False

        # Check quiet hours
        if prefs.quiet_hours_start is not None and prefs.quiet_hours_end is not None:
            current_hour = datetime.utcnow().hour
            if prefs.quiet_hours_start <= current_hour < prefs.quiet_hours_end:
                logger.info("In quiet hours")
                return False

        # Check priority threshold
        priority_levels = {"low": 0, "medium": 1, "high": 2}
        if priority_levels.get(priority, 0) < priority_levels.get(prefs.priority_threshold, 1):
            return False

        # TODO: Check max_per_day from database

        return True

    def apply_retention_policy(
        self,
        events: List[dict],
        user_settings: UserPrivacySettings,
    ) -> List[dict]:
        """Apply retention policy to events.
        
        Returns:
            Events that should be kept
        """
        policy = user_settings.retention_policy
        now = datetime.utcnow()

        kept_events = []

        for event in events:
            created_at = datetime.fromisoformat(event.get("created_at", ""))
            age_days = (now - created_at).days

            # Auto-delete
            if policy.auto_delete_after_days:
                if age_days > policy.auto_delete_after_days:
                    logger.info(f"Auto-deleting event {event.get('id')} (age: {age_days} days)")
                    continue

            # Archive (mark for cold storage)
            if policy.archive_after_days:
                if age_days > policy.archive_after_days:
                    event["archived"] = True

            # Keep insights only
            if policy.keep_insights_only:
                if age_days > 90:  # Keep raw data for 90 days
                    # Strip raw text, keep only metadata
                    event["text"] = "[REDACTED - insights preserved]"

            kept_events.append(event)

        return kept_events

    def export_user_data(
        self,
        user_id: str,
        events: List[dict],
        insights: List[dict],
    ) -> dict:
        """Export all user data in portable format."""
        return {
            "user_id": user_id,
            "export_date": datetime.utcnow().isoformat(),
            "events": events,
            "insights": insights,
            "format_version": "1.0",
        }

    async def delete_user_data(
        self,
        user_id: str,
        db_session,
    ) -> dict:
        """Delete all user data (GDPR right to erasure).

        Deletes all rows belonging to the user across every table, then removes
        the user record itself. The User model has cascade="all, delete-orphan"
        on its relationships, but we also issue explicit DELETEs for safety and
        to capture accurate row counts.

        Returns:
            Deletion confirmation with per-table row counts.
        """
        from sqlalchemy import text as sa_text

        logger.warning(f"GDPR erasure: deleting all data for user {user_id}")

        counts: Dict[str, int] = {}

        # Delete event_patterns join table first (no user_id — join through founder_events)
        result = await db_session.execute(
            sa_text("""
                DELETE FROM seedlings.event_patterns
                WHERE event_id IN (
                    SELECT id FROM seedlings.founder_events WHERE user_id = :uid
                )
            """),
            {"uid": user_id},
        )
        counts["event_patterns_deleted"] = result.rowcount

        # Tables with a direct user_id FK (order matters — child tables before parents)
        ordered_tables = [
            "framework_applications",
            "interventions",
            "decision_outcomes",
            "patterns",
            "founder_events",
        ]

        for table in ordered_tables:
            result = await db_session.execute(
                sa_text(f"DELETE FROM seedlings.{table} WHERE user_id = :uid"),
                {"uid": user_id},
            )
            counts[f"{table}_deleted"] = result.rowcount

        # Delete knowledge_chunks that belong to this user — stored with no user_id
        # so we skip them (they are shared framework data, not personal).

        # Finally delete the user row itself
        result = await db_session.execute(
            sa_text("DELETE FROM seedlings.users WHERE id = :uid"),
            {"uid": user_id},
        )
        counts["user_deleted"] = result.rowcount

        # Purge privacy settings cache if present
        self.settings_cache.pop(user_id, None)

        await db_session.commit()
        logger.info(f"GDPR erasure complete for user {user_id}: {counts}")

        return {
            "user_id": user_id,
            "deleted_at": datetime.utcnow().isoformat(),
            **counts,
        }


class ConsentManager:
    """Manages user consent for different data processing activities."""

    def __init__(self):
        self.consent_records = {}  # user_id -> consent_data

    def record_consent(
        self,
        user_id: str,
        purpose: str,
        granted: bool,
        timestamp: str,
    ):
        """Record user consent for a specific purpose.
        
        Purposes:
        - "ai_processing": Allow AI analysis of data
        - "model_training": Allow data for model training
        - "third_party_integrations": Allow third-party integrations
        - "analytics": Allow usage analytics
        """
        if user_id not in self.consent_records:
            self.consent_records[user_id] = {}

        self.consent_records[user_id][purpose] = {
            "granted": granted,
            "timestamp": timestamp,
        }

        logger.info(f"Consent recorded: {user_id} -> {purpose} = {granted}")

    def has_consent(
        self,
        user_id: str,
        purpose: str,
    ) -> bool:
        """Check if user has granted consent for a purpose."""
        if user_id not in self.consent_records:
            return False

        consent = self.consent_records[user_id].get(purpose)
        if not consent:
            return False

        return consent.get("granted", False)


if __name__ == "__main__":
    # Example usage
    controller = PrivacyController()

    # Create privacy settings
    settings = UserPrivacySettings(
        user_id="founder-123",
        privacy_zones=[
            PrivacyZone(
                id="personal-health",
                name="Personal Health",
                keywords=["therapy", "medication", "mental health"],
                mode="no_storage",
                created_at=datetime.utcnow().isoformat(),
            ),
            PrivacyZone(
                id="family",
                name="Family Matters",
                keywords=["spouse", "kids", "family"],
                mode="reflection_only",
                created_at=datetime.utcnow().isoformat(),
            ),
        ],
        intervention_prefs=InterventionPreferences(
            quiet_hours_start=22,
            quiet_hours_end=8,
            max_per_day=2,
        ),
        created_at=datetime.utcnow().isoformat(),
        updated_at=datetime.utcnow().isoformat(),
    )

    # Test privacy zone detection
    event = {
        "text": "Had a therapy session today, feeling better about the fundraising stress.",
        "created_at": datetime.utcnow().isoformat(),
    }

    should_store = controller.should_store_event(event, settings)
    print(f"Should store event: {should_store}")

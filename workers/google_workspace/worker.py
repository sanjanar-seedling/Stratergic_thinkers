"""Google Workspace Integration Worker.

OAuth 2.0 integration for Google Calendar & Gmail.
Periodically polls calendar data to detect time allocation drift
and identify execution/reflection phases.
"""

import logging
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

import httpx

logger = logging.getLogger(__name__)


# Keywords used to auto-categorize calendar event titles
_CATEGORY_KEYWORDS = {
    "engineering": ["standup", "engineering", "tech", "architecture", "code", "review",
                    "sprint", "deploy", "debug", "refactor", "devops", "backend", "frontend"],
    "fundraising": ["investor", "fundrais", "pitch", "vc", "venture", "term sheet",
                    "due diligence", "cap table", "series"],
    "management":  ["1:1", "1-1", "management", "team", "hr", "hiring", "interview",
                    "onboard", "offboard", "performance"],
    "sales":       ["sales", "demo", "customer", "client", "prospect", "deal", "closing",
                    "renewal", "churn", "account"],
    "strategy":    ["strategy", "planning", "roadmap", "okr", "kpi", "board", "offsite",
                    "vision", "mission"],
    "reflection":  ["retrospective", "retro", "review", "reflection", "debrief", "learning"],
}


class GoogleWorkspaceWorker:
    """Manages Google Calendar & Gmail integration."""

    def __init__(self):
        self._credentials = None

    def get_auth_url(self, client_id: str, redirect_uri: str) -> str:
        """Generate OAuth 2.0 authorization URL."""
        scopes = [
            "https://www.googleapis.com/auth/calendar.readonly",
            "https://www.googleapis.com/auth/gmail.readonly",
        ]
        scope_str = quote(" ".join(scopes))
        return (
            f"https://accounts.google.com/o/oauth2/v2/auth"
            f"?client_id={client_id}"
            f"&redirect_uri={redirect_uri}"
            f"&response_type=code"
            f"&scope={scope_str}"
            f"&access_type=offline"
            f"&prompt=consent"
        )

    def _categorize_event(self, summary: str) -> str:
        """Auto-categorize a calendar event by its title."""
        lower = summary.lower()
        for category, keywords in _CATEGORY_KEYWORDS.items():
            if any(kw in lower for kw in keywords):
                return category
        return "other"

    async def fetch_calendar_events(
        self,
        access_token: str,
        days: int = 7,
    ) -> list[dict]:
        """Fetch calendar events for the past N days from Google Calendar API.

        Falls back to sample data if the access token is missing or the call fails.
        """
        if not access_token:
            logger.warning("No Google access token — returning empty calendar")
            return []

        now = datetime.now(timezone.utc)
        time_min = (now - timedelta(days=days)).isoformat()
        time_max = now.isoformat()

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.get(
                    "https://www.googleapis.com/calendar/v3/calendars/primary/events",
                    headers={"Authorization": f"Bearer {access_token}"},
                    params={
                        "timeMin": time_min,
                        "timeMax": time_max,
                        "singleEvents": "true",
                        "orderBy": "startTime",
                        "maxResults": 100,
                    },
                )

                if response.status_code == 401:
                    logger.warning("Google access token expired or revoked")
                    return []

                response.raise_for_status()
                data = response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Google Calendar API error {e.response.status_code}: {e.response.text}")
            return []
        except Exception as e:
            logger.error(f"Google Calendar fetch failed: {e}")
            return []

        events = []
        for item in data.get("items", []):
            start = item.get("start", {})
            end = item.get("end", {})
            # All-day events use "date"; timed events use "dateTime"
            start_time = start.get("dateTime") or start.get("date", "")
            end_time = end.get("dateTime") or end.get("date", "")
            summary = item.get("summary", "(no title)")

            events.append({
                "id": item.get("id", ""),
                "summary": summary,
                "start": start_time,
                "end": end_time,
                "category": self._categorize_event(summary),
                "description": item.get("description", ""),
                "location": item.get("location", ""),
                "attendee_count": len(item.get("attendees", [])),
            })

        logger.info(f"Fetched {len(events)} calendar events for past {days} days")
        return events

    async def fetch_recent_gmail_snippets(
        self,
        access_token: str,
        max_results: int = 10,
        query: str = "in:inbox newer_than:7d",
    ) -> list[dict]:
        """Fetch recent Gmail message snippets for reflection ingestion."""
        if not access_token:
            return []

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                # List recent messages
                list_resp = await client.get(
                    "https://gmail.googleapis.com/gmail/v1/users/me/messages",
                    headers={"Authorization": f"Bearer {access_token}"},
                    params={"maxResults": max_results, "q": query},
                )
                list_resp.raise_for_status()
                messages_meta = list_resp.json().get("messages", [])

                messages = []
                for meta in messages_meta:
                    msg_resp = await client.get(
                        f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{meta['id']}",
                        headers={"Authorization": f"Bearer {access_token}"},
                        params={"format": "metadata", "metadataHeaders": "Subject,From,Date"},
                    )
                    if msg_resp.status_code != 200:
                        continue
                    msg_data = msg_resp.json()

                    headers = {
                        h["name"]: h["value"]
                        for h in msg_data.get("payload", {}).get("headers", [])
                    }
                    messages.append({
                        "id": meta["id"],
                        "subject": headers.get("Subject", "(no subject)"),
                        "from": headers.get("From", ""),
                        "date": headers.get("Date", ""),
                        "snippet": msg_data.get("snippet", ""),
                    })

                logger.info(f"Fetched {len(messages)} Gmail snippets")
                return messages

        except Exception as e:
            logger.error(f"Gmail fetch failed: {e}")
            return []

    def analyze_time_allocation(
        self,
        events: list[dict],
    ) -> dict[str, float]:
        """Analyze how time is distributed across categories.

        Returns a dict of {category: fraction_of_total} where fractions sum to 1.0.
        Events without parseable start/end times are skipped.
        """
        total_minutes = 0.0
        category_minutes: dict[str, float] = {}

        for event in events:
            try:
                start_raw = event.get("start", "")
                end_raw = event.get("end", "")
                if not start_raw or not end_raw:
                    continue

                # Handle both date-only ("2026-03-01") and datetime strings
                if "T" in start_raw:
                    start = datetime.fromisoformat(start_raw.replace("Z", "+00:00"))
                    end = datetime.fromisoformat(end_raw.replace("Z", "+00:00"))
                else:
                    start = datetime.strptime(start_raw, "%Y-%m-%d")
                    end = datetime.strptime(end_raw, "%Y-%m-%d")

                duration = (end - start).total_seconds() / 60
                if duration <= 0:
                    continue

                category = event.get("category", "other")
                category_minutes[category] = category_minutes.get(category, 0.0) + duration
                total_minutes += duration
            except Exception:
                continue

        if total_minutes == 0:
            return {}

        return {
            cat: round(mins / total_minutes, 3)
            for cat, mins in category_minutes.items()
        }

    def detect_heavy_execution_phase(
        self,
        events: list[dict],
        threshold_hours: float = 4,
    ) -> bool:
        """Detect if the founder is in a heavy execution phase.

        Returns True if total engineering/technical time exceeds threshold_hours.
        """
        engineering_events = [e for e in events if e.get("category") == "engineering"]

        total_eng_hours = 0.0
        for event in engineering_events:
            try:
                start_raw = event.get("start", "")
                end_raw = event.get("end", "")
                if not start_raw or not end_raw:
                    continue
                if "T" in start_raw:
                    start = datetime.fromisoformat(start_raw.replace("Z", "+00:00"))
                    end = datetime.fromisoformat(end_raw.replace("Z", "+00:00"))
                else:
                    start = datetime.strptime(start_raw, "%Y-%m-%d")
                    end = datetime.strptime(end_raw, "%Y-%m-%d")
                total_eng_hours += (end - start).total_seconds() / 3600
            except Exception:
                continue

        return total_eng_hours >= threshold_hours


# Singleton
google_worker = GoogleWorkspaceWorker()

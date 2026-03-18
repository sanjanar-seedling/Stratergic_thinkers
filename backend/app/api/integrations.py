"""Integration OAuth Routes — Slack, Google Calendar, Gmail.

Each service follows the same pattern:
1. GET /integrations/{service}/auth-url → returns OAuth authorization URL
2. POST /integrations/{service}/callback → exchange code for tokens
3. GET /integrations/status → return which services are connected
4. DELETE /integrations/{service} → disconnect a service
"""

import logging
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from app.core.security import get_current_user
from app.core.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()

# ── In-memory integration store (replace with DB in production) ──
_integrations: list[dict] = []


# ── Schemas ──

class OAuthCallback(BaseModel):
    code: str


class IntegrationStatus(BaseModel):
    service: str
    connected: bool
    connected_at: str | None = None


# ── OAuth URL Generators ──

OAUTH_CONFIGS = {
    "slack": {
        "auth_url": "https://slack.com/oauth/v2/authorize",
        "token_url": "https://slack.com/api/oauth.v2.access",
        "scopes": "channels:history,chat:write,groups:history,im:history,channels:read,groups:read,im:read,mpim:read,users:read,team:read",
    },
    "google": {
        "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "scopes": "https://www.googleapis.com/auth/calendar.readonly",
    },
    "gmail": {
        "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "scopes": "https://www.googleapis.com/auth/gmail.readonly",
    },
}


def _get_client_id(service: str) -> str:
    """Get client ID for a service from config."""
    mapping = {
        "slack": settings.slack_client_id,
        "google": settings.google_client_id,
        "gmail": settings.google_client_id,
    }
    return mapping.get(service, "")


def _get_client_secret(service: str) -> str:
    """Get client secret for a service from config."""
    mapping = {
        "slack": settings.slack_client_secret,
        "google": settings.google_client_secret,
        "gmail": settings.google_client_secret,
    }
    return mapping.get(service, "")


def _get_redirect_uri(service: str) -> str:
    """Get redirect URI for a service from config."""
    mapping = {
        "slack": settings.slack_redirect_uri,
        "google": settings.google_redirect_uri,
        "gmail": settings.google_redirect_uri,
    }
    return mapping.get(service, "")


# ── Routes ──

@router.get("/status")
async def get_integration_status(
    current_user: dict = Depends(get_current_user),
):
    """Get connection status for all integrations."""
    user_integrations = [
        i for i in _integrations if i["user_id"] == current_user["id"]
    ]

    statuses = []
    for service_name in OAUTH_CONFIGS:
        integration = next(
            (i for i in user_integrations if i["service"] == service_name),
            None,
        )
        statuses.append(IntegrationStatus(
            service=service_name,
            connected=integration is not None,
            connected_at=integration["connected_at"] if integration else None,
        ))

    return statuses


@router.get("/{service}/auth-url")
async def get_auth_url(
    service: str,
    _current_user: dict = Depends(get_current_user),
):
    """Generate OAuth authorization URL for a service."""
    if service not in OAUTH_CONFIGS:
        raise HTTPException(status_code=400, detail=f"Unknown service: {service}")

    config = OAUTH_CONFIGS[service]
    client_id = _get_client_id(service)

    if not client_id:
        raise HTTPException(
            status_code=400,
            detail=f"{service} OAuth not configured. Set {service.upper()}_CLIENT_ID in .env",
        )

    params = {
        "client_id": client_id,
        "redirect_uri": _get_redirect_uri(service),
        "response_type": "code",
        "scope": config["scopes"],
        "state": service,  # Used by callback page to identify the service
    }

    # Google needs access_type=offline for refresh tokens
    if service in ("google", "gmail"):
        params["access_type"] = "offline"
        params["prompt"] = "consent"

    auth_url = f"{config['auth_url']}?{urlencode(params)}"
    return {"auth_url": auth_url}


@router.post("/{service}/callback")
async def oauth_callback(
    service: str,
    data: OAuthCallback,
    current_user: dict = Depends(get_current_user),
):
    """Exchange OAuth authorization code for access tokens."""
    if service not in OAUTH_CONFIGS:
        raise HTTPException(status_code=400, detail=f"Unknown service: {service}")

    config = OAUTH_CONFIGS[service]
    client_id = _get_client_id(service)
    client_secret = _get_client_secret(service)

    if not client_id or not client_secret:
        raise HTTPException(
            status_code=400,
            detail=f"{service} OAuth not fully configured in .env",
        )

    # Exchange code for tokens
    import httpx
    from datetime import datetime

    try:
        async with httpx.AsyncClient() as client:
            token_payload = {
                "client_id": client_id,
                "client_secret": client_secret,
                "code": data.code,
                "redirect_uri": _get_redirect_uri(service),
                "grant_type": "authorization_code",
            }
            headers = {
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded",
            }
            response = await client.post(
                config["token_url"],
                data=token_payload,
                headers=headers,
            )
            token_data = response.json()
            logger.info(f"OAuth {service} token response status={response.status_code} body={token_data}")

            if response.status_code >= 400:
                error_detail = token_data.get("error_description") or token_data.get("error") or str(token_data)
                raise HTTPException(status_code=400, detail=f"{service} token exchange failed: {error_detail}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OAuth token exchange failed for {service}: {e}")
        raise HTTPException(status_code=400, detail="Failed to exchange authorization code")

    logger.info(f"OAuth token response for {service}: {list(token_data.keys())}")

    # Slack returns {"ok": false, "error": "..."} with 200 status
    if service == "slack":
        if not token_data.get("ok"):
            error_msg = token_data.get("error", "unknown error")
            logger.error(f"Slack OAuth error: {error_msg}")
            raise HTTPException(status_code=400, detail=f"Slack authorization failed: {error_msg}")
        access_token = token_data.get("access_token") or token_data.get("authed_user", {}).get("access_token", "")
    else:
        access_token = token_data.get("access_token", "")

    # Validate we actually got a token
    if not access_token:
        logger.error(f"No access token received from {service}. Response keys: {list(token_data.keys())}")
        raise HTTPException(status_code=400, detail=f"No access token received from {service}. Authorization may have been denied.")

    # Store integration (replace existing if any)
    _integrations[:] = [
        i for i in _integrations
        if not (i["user_id"] == current_user["id"] and i["service"] == service)
    ]

    _integrations.append({
        "user_id": current_user["id"],
        "service": service,
        "access_token": access_token,
        "refresh_token": token_data.get("refresh_token", ""),
        "scopes": config["scopes"],
        "connected_at": datetime.utcnow().isoformat(),
    })

    logger.info(f"User {current_user['id']} connected {service} (token length: {len(access_token)})")
    return {"status": "connected", "service": service}


@router.delete("/{service}")
async def disconnect_integration(
    service: str,
    current_user: dict = Depends(get_current_user),
):
    """Disconnect an integration."""
    before = len(_integrations)
    _integrations[:] = [
        i for i in _integrations
        if not (i["user_id"] == current_user["id"] and i["service"] == service)
    ]

    if len(_integrations) == before:
        raise HTTPException(status_code=404, detail="Integration not found")

    logger.info(f"User {current_user['id']} disconnected {service}")
    return {"status": "disconnected", "service": service}


@router.post("/sync")
async def sync_integrations(
    current_user: dict = Depends(get_current_user),
):
    """Sync recent data from all connected integrations into the event pipeline.

    For each connected service, calls the real API using the stored access token,
    scrubs PII, and publishes events to Redis for processing.
    """
    import uuid
    from datetime import datetime

    from app.api.routes import _events
    from app.middleware.pii_stripper import full_scrub
    from app.core.redis_client import publish_event

    user_integrations = [
        i for i in _integrations if i["user_id"] == current_user["id"]
    ]

    if not user_integrations:
        return {"status": "no_integrations", "events_created": 0, "services_synced": []}

    events_created = 0
    services_synced = []
    errors = []

    for integration in user_integrations:
        service = integration["service"]
        access_token = integration.get("access_token", "")
        
        # For Slack: fallback to user token from .env if OAuth token is bot token
        if service == "slack" and access_token.startswith("xoxb-"):
            slack_user_token = getattr(settings, "slack_user_token", None)
            if slack_user_token:
                logger.info(f"Slack bot token detected, using user token from .env for better DM access")
                access_token = slack_user_token

        try:
            logger.info(f"Syncing {service} (token: {access_token[:20]}...)")
            texts = await _fetch_texts_from_service(service, access_token)
            logger.info(f"Sync {service}: got {len(texts)} texts")
        except Exception as e:
            logger.error(f"Sync failed for {service}: {e}")
            errors.append({"service": service, "error": str(e)})
            continue

        if not texts:
            services_synced.append(service)
            continue

        uid = current_user["id"]
        for text in texts:
            scrubbed_text = full_scrub(text)
            event_id = str(uuid.uuid4())
            new_event = {
                "id": event_id,
                "user_id": uid,
                "source": "google_calendar" if service == "google" else service,
                "event_type": "reflection",
                "scrubbed_text": scrubbed_text,
                "context": {"synced_from": service},
                "created_at": datetime.utcnow().isoformat(),
            }
            _events.setdefault(uid, []).insert(0, new_event)
            events_created += 1

            try:
                # Publish full event to Redis for event processor to consume
                import json
                await publish_event(
                    settings.redis_stream_name,
                    {
                        "payload": json.dumps({
                            "id": event_id,
                            "user_id": uid,
                            "source": new_event["source"],
                            "event_type": "reflection",
                            "text": text,  # Raw text before scrubbing
                            "context": new_event["context"],
                            "created_at": new_event["created_at"],
                        }),
                    }
                )
                logger.info(f"Published event {event_id} to Redis stream for processing")
            except Exception as e:
                logger.error(f"Failed to publish event {event_id} to Redis: {e}")
                # Non-critical - event is still stored in memory

        services_synced.append(service)

    return {
        "status": "success",
        "events_created": events_created,
        "services_synced": services_synced,
        "errors": errors,
    }


async def _fetch_texts_from_service(service: str, access_token: str) -> list[str]:
    """Call the real API for a service and return a list of text strings to ingest."""
    if not access_token:
        logger.warning(f"No access token for {service} — skipping")
        return []

    if service == "slack":
        return await _fetch_slack_messages(access_token)
    elif service == "gmail":
        return await _fetch_gmail_snippets(access_token)
    elif service == "google":
        return await _fetch_google_calendar_summaries(access_token)
    else:
        logger.warning(f"Unknown service for sync: {service}")
        return []


async def _fetch_slack_messages(access_token: str) -> list[str]:
    """Fetch recent messages from Slack (DMs, group DMs, and all channels the bot is a member of)."""
    import httpx

    texts = []
    headers = {"Authorization": f"Bearer {access_token}"}

    async with httpx.AsyncClient(timeout=15) as client:
        # Fetch from DM channels
        try:
            resp = await client.get(
                "https://slack.com/api/conversations.list",
                headers=headers,
                params={"types": "im,mpim", "limit": 5},
            )
            data = resp.json()
            logger.info(f"Slack conversations.list response (im/mpim): ok={data.get('ok')}, channels_count={len(data.get('channels', []))}")
            
            if data.get("ok"):
                channels = data.get("channels", [])[:3]
                logger.info(f"Slack: Processing {len(channels)} DM/Group DM channels")
                
                for channel in channels:
                    channel_id = channel["id"]
                    logger.info(f"Slack: Fetching history for DM {channel_id}")
                    
                    hist = await client.get(
                        "https://slack.com/api/conversations.history",
                        headers=headers,
                        params={"channel": channel_id, "limit": 50},
                    )
                    hist_data = hist.json()
                    
                    if not hist_data.get("ok"):
                        logger.warning(f"Slack history error for {channel_id}: {hist_data.get('error')}")
                        continue
                    
                    messages = hist_data.get("messages", [])
                    logger.info(f"Slack: DM {channel_id} has {len(messages)} messages")
                    
                    for msg in messages:
                        text = msg.get("text", "").strip()
                        if text and len(text) > 2:
                            texts.append(text)
        except Exception as e:
            logger.error(f"Slack IM fetch failed: {e}", exc_info=True)

        # ALWAYS also fetch from public channels (not just when DMs are empty)
        try:
            resp = await client.get(
                "https://slack.com/api/conversations.list",
                headers=headers,
                params={"types": "public_channel,private_channel", "limit": 10, "exclude_archived": True},
            )
            data = resp.json()
            logger.info(f"Slack conversations.list response (public/private): ok={data.get('ok')}, channels_count={len(data.get('channels', []))}")
            
            if data.get("ok"):
                channels = data.get("channels", [])[:5]
                logger.info(f"Slack: Processing {len(channels)} public/private channels")
                
                for channel in channels:
                    channel_name = channel.get("name", "unknown")
                    channel_id = channel["id"]
                    logger.info(f"Slack: Fetching history for channel #{channel_name} ({channel_id})")
                    
                    hist = await client.get(
                        "https://slack.com/api/conversations.history",
                        headers=headers,
                        params={"channel": channel_id, "limit": 50},
                    )
                    hist_data = hist.json()
                    if not hist_data.get("ok"):
                        logger.warning(f"Slack history error for {channel_id}: {hist_data.get('error')}")
                        continue
                    
                    messages = hist_data.get("messages", [])
                    logger.info(f"Slack: Channel #{channel_name} has {len(messages)} messages")
                    
                    for msg in messages:
                        text = msg.get("text", "").strip()
                        if text and len(text) > 2:
                            texts.append(text)
        except Exception as e:
            logger.error(f"Slack channel fetch failed: {e}", exc_info=True)

    logger.info(f"Slack sync: FINAL - fetched {len(texts)} messages total")
    if not texts:
        logger.warning("Slack sync returned 0 messages. Make sure the bot is added to channels with recent messages.")
    return texts


async def _fetch_gmail_snippets(access_token: str) -> list[str]:
    """Fetch recent inbox email snippets from Gmail."""
    import httpx

    texts = []
    headers = {"Authorization": f"Bearer {access_token}"}

    async with httpx.AsyncClient(timeout=15) as client:
        list_resp = await client.get(
            "https://gmail.googleapis.com/gmail/v1/users/me/messages",
            headers=headers,
            params={"maxResults": 10, "q": "in:inbox newer_than:7d"},
        )
        if list_resp.status_code != 200:
            logger.warning(f"Gmail messages.list error: {list_resp.status_code}")
            return []

        messages_meta = list_resp.json().get("messages", [])
        for meta in messages_meta[:10]:
            msg_resp = await client.get(
                f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{meta['id']}",
                headers=headers,
                params={"format": "metadata", "metadataHeaders": "Subject"},
            )
            if msg_resp.status_code != 200:
                continue
            msg_data = msg_resp.json()
            snippet = msg_data.get("snippet", "").strip()
            headers_list = msg_data.get("payload", {}).get("headers", [])
            subject = next((h["value"] for h in headers_list if h["name"] == "Subject"), "")
            combined = f"{subject}: {snippet}" if subject else snippet
            if combined.strip():
                texts.append(combined)

    logger.info(f"Gmail sync: fetched {len(texts)} snippets")
    return texts


async def _fetch_google_calendar_summaries(access_token: str) -> list[str]:
    """Fetch recent Google Calendar events and format as text summaries."""
    import sys
    import os
    # Allow importing the worker from the workers directory
    workers_path = os.path.join(os.path.dirname(__file__), "../../../../workers")
    if workers_path not in sys.path:
        sys.path.insert(0, workers_path)

    try:
        from google_workspace.worker import google_worker
        events = await google_worker.fetch_calendar_events(access_token, days=7)
    except ImportError:
        # Fallback: call the API directly
        import httpx
        from datetime import timezone, timedelta
        now = datetime.utcnow().replace(tzinfo=timezone.utc)
        time_min = (now - timedelta(days=7)).isoformat()
        time_max = now.isoformat()
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                "https://www.googleapis.com/calendar/v3/calendars/primary/events",
                headers={"Authorization": f"Bearer {access_token}"},
                params={"timeMin": time_min, "timeMax": time_max,
                        "singleEvents": "true", "maxResults": 20},
            )
            if resp.status_code != 200:
                return []
            events = resp.json().get("items", [])

    texts = []
    for event in events:
        summary = event.get("summary", "")
        if summary:
            texts.append(f"Calendar event: {summary}")

    logger.info(f"Google Calendar sync: fetched {len(texts)} events")
    return texts

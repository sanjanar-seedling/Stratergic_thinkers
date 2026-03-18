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
        "bot_scopes": "chat:write",  # What the bot/app can do
        "user_scopes": "channels:history,groups:history,im:history,mpim:history,channels:read,groups:read,im:read,mpim:read",  # What the user authorizes
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
    """Get connection status for all integrations (both in-memory and database)."""
    from sqlalchemy import select
    from app.core.database import async_session_factory
    from app.models import SlackInstallation
    
    user_integrations = [
        i for i in _integrations if i["user_id"] == current_user["id"]
    ]
    
    # Fetch Slack installations from database
    slack_installs = []
    try:
        async with async_session_factory() as session:
            slack_installations = await session.execute(
                select(SlackInstallation).where(
                    (SlackInstallation.user_id == current_user["id"]) &
                    (SlackInstallation.is_active == True)
                )
            )
            slack_installs = slack_installations.scalars().all()
    except Exception as e:
        logger.debug(f"Could not fetch Slack installations from database: {e}")
        slack_installs = []

    statuses = []
    
    # Determine Slack connection status
    slack_connected = False
    slack_connected_at = None
    
    # Check Slack installations from database
    if slack_installs:
        slack_connected = True
        slack_connected_at = slack_installs[0].installed_at.isoformat() if slack_installs[0].installed_at else None
    else:
        # Also check for legacy in-memory Slack tokens during transition
        legacy_slack = next((i for i in user_integrations if i["service"] == "slack"), None)
        if legacy_slack:
            slack_connected = True
            slack_connected_at = legacy_slack.get("connected_at")
    
    # Always add Slack status
    statuses.append(IntegrationStatus(
        service="slack",
        connected=slack_connected,
        connected_at=slack_connected_at,
    ))
    
    # Add other services from in-memory store (Google, etc)
    for service_name in ["google", "gmail"]:
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
        "state": service,  # Used by callback page to identify the service
    }
    
    # Slack uses separate bot and user scopes
    if service == "slack":
        params["scope"] = config["bot_scopes"]
        params["user_scope"] = config["user_scopes"]
        logger.info(f"Slack OAuth scopes - bot: {params['scope']}, user: {params['user_scope']}")
    else:
        params["scope"] = config["scopes"]

    # Google needs access_type=offline for refresh tokens
    if service in ("google", "gmail"):
        params["access_type"] = "offline"
        params["prompt"] = "consent"

    auth_url = f"{config['auth_url']}?{urlencode(params)}"
    logger.info(f"Generated OAuth URL for {service}: {auth_url}")
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
        
        # Debug: Log all token fields
        logger.info(f"Slack OAuth response keys: {list(token_data.keys())}")
        logger.info(f"Slack authed_user keys: {list(token_data.get('authed_user', {}).keys())}")
        logger.info(f"Top-level access_token (first 20 chars): {token_data.get('access_token', '')[:20]}...")
        logger.info(f"User scope from response: {token_data.get('authed_user', {}).get('scope', 'NONE')}")
        
        # Try to get tokens from both locations
        bot_token = token_data.get("access_token")
        user_token = token_data.get("authed_user", {}).get("access_token")
        
        logger.warning(f"Slack token types received: bot_token={'xoxb' if bot_token and bot_token.startswith('xoxb') else 'MISSING/WRONG'}, user_token={'xoxp' if user_token and user_token.startswith('xoxp') else 'MISSING'}")
        
        # Use whichever token we got
        access_token = user_token or bot_token
    else:
        access_token = token_data.get("access_token", "")

    # Validate we actually got a token
    if not access_token:
        logger.error(f"No access token received from {service}. Response keys: {list(token_data.keys())}")
        raise HTTPException(status_code=400, detail=f"No access token received from {service}. Authorization may have been denied.")

    # Handle Slack installations: encrypt and save to database
    if service == "slack":
        return await _save_slack_installation(
            user_id=current_user["id"],
            token_data=token_data,
            access_token=access_token,
        )
    
    # For other services (Google), keep in-memory for now
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


async def _save_slack_installation(user_id: str, token_data: dict, access_token: str) -> dict:
    """Save encrypted Slack installation to database."""
    from app.core.encryption import E2EEncryption
    from app.core.database import async_session_factory
    from app.models import SlackInstallation
    from sqlalchemy import delete
    import json
    
    # Extract Slack identifiers
    slack_user_id = token_data.get("authed_user", {}).get("id", "")
    slack_workspace_id = token_data.get("team", {}).get("id", "")
    slack_workspace_name = token_data.get("team", {}).get("name", "")
    
    # Check token types
    bot_token = token_data.get("access_token")  # Usually a bot token (xoxb-)
    user_token = token_data.get("authed_user", {}).get("access_token")  # User token (xoxp-), might not exist
    
    if not slack_user_id or not slack_workspace_id:
        logger.error(f"Missing Slack identifiers in token response: {token_data.keys()}")
        raise HTTPException(status_code=400, detail="Invalid Slack OAuth response - missing identifiers")
    
    # Determine which token is which
    if bot_token and bot_token.startswith("xoxb-"):
        logger.info(f"Got bot token (xoxb-) for user {slack_user_id}")
        has_bot_token = True
        has_user_token = False
    else:
        has_bot_token = False
    
    if user_token and user_token.startswith("xoxp-"):
        logger.info(f"Got user token (xoxp-) for user {slack_user_id}")
        has_user_token = True
    else:
        user_token = None
        logger.warning(f"No user token (xoxp-) received - DM access will be limited. Only bot token available.")
    
    # Encrypt tokens
    encryptor = E2EEncryption()
    encryption_key = encryptor.derive_key_from_string(settings.encryption_key) if settings.encryption_key else b"0" * 32
    
    # Encrypt user token (prefer user token, fallback to bot token for channel access)
    token_to_use = user_token or bot_token  # Use user token if available, else bot token
    
    if not token_to_use:
        raise HTTPException(status_code=400, detail="No Slack token received in OAuth response")
    
    encrypted_user_token_data = encryptor.encrypt_data(token_to_use, encryption_key)
    
    encrypted_bot_token_data = None
    if bot_token and bot_token != token_to_use:
        # Only save bot token separately if it's different from what we saved as user token
        encrypted_bot_token_data = encryptor.encrypt_data(bot_token, encryption_key)
    
    logger.info(
        f"Encrypted Slack tokens for user {user_id}, workspace {slack_workspace_id}: "
        f"user_token={bool(user_token)}, bot_token={bool(bot_token)}"
    )
    
    # Save to database
    from app.models import User
    from sqlalchemy import select
    
    # Step 1: Ensure user exists (create in separate transaction if needed)
    async with async_session_factory() as check_session:
        result = await check_session.execute(select(User).where(User.id == user_id))
        user_exists = result.scalars().first() is not None
    
    if not user_exists:
        logger.warning(f"User {user_id} not found in database. Creating minimal account for Slack integration.")
        from app.core.security import hash_password
        
        # Create user in its own transaction
        async with async_session_factory() as create_session:
            new_user = User(
                id=user_id,
                email=slack_user_id or f"slack_{slack_workspace_id}@slacked.local",
                hashed_password=hash_password("change_me_in_settings"),
                full_name=slack_user_id,
            )
            create_session.add(new_user)
            await create_session.commit()
            logger.info(f"Created user {user_id}")
    
    # Step 2: Save Slack installation in main transaction
    async with async_session_factory() as session:
        # Delete any existing installation for this user+workspace
        await session.execute(
            delete(SlackInstallation).where(
                (SlackInstallation.user_id == user_id) & 
                (SlackInstallation.slack_workspace_id == slack_workspace_id)
            )
        )
        
        # Create new installation record
        installation = SlackInstallation(
            user_id=user_id,
            slack_user_id=slack_user_id,
            slack_workspace_id=slack_workspace_id,
            slack_workspace_name=slack_workspace_name,
            encrypted_user_token=encrypted_user_token_data["ciphertext"],
            user_token_nonce=encrypted_user_token_data["nonce"],
            user_token_tag=encrypted_user_token_data["tag"],
            encrypted_bot_token=encrypted_bot_token_data["ciphertext"] if encrypted_bot_token_data else None,
            bot_token_nonce=encrypted_bot_token_data["nonce"] if encrypted_bot_token_data else None,
            bot_token_tag=encrypted_bot_token_data["tag"] if encrypted_bot_token_data else None,
            # Parse scopes - could be in root level or authed_user
            user_scopes=token_data.get("authed_user", {}).get("scope", "") or token_data.get("scope", ""),
            bot_scopes=token_data.get("scope", "") if bot_token and bot_token.startswith("xoxb-") else "",
            is_active=True,
        )
        
        session.add(installation)
        await session.commit()
        
        logger.info(f"Saved Slack installation for user {user_id} in workspace {slack_workspace_id}")
    
    return {
        "status": "connected",
        "service": "slack",
        "workspace": slack_workspace_name,
        "note": "DM access limited: user token not available, using bot token for channels only" if not user_token else None,
    }


@router.delete("/{service}")
async def disconnect_integration(
    service: str,
    current_user: dict = Depends(get_current_user),
):
    """Disconnect an integration."""
    if service == "slack":
        # Delete from database
        from sqlalchemy import delete
        from app.core.database import async_session_factory
        from app.models import SlackInstallation
        
        async with async_session_factory() as session:
            result = await session.execute(
                delete(SlackInstallation).where(
                    (SlackInstallation.user_id == current_user["id"]) &
                    (SlackInstallation.is_active == True)
                )
            )
            await session.commit()
            
            if result.rowcount == 0:
                raise HTTPException(status_code=404, detail="Slack integration not found")
            
            logger.info(f"User {current_user['id']} disconnected Slack ({result.rowcount} installations)")
    else:
        # Delete from in-memory store (Google, Gmail)
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
    from sqlalchemy import select

    from app.api.routes import _events
    from app.middleware.pii_stripper import full_scrub
    from app.core.redis_client import publish_event
    from app.core.database import async_session_factory
    from app.models import SlackInstallation
    from app.core.encryption import E2EEncryption

    events_created = 0
    services_synced = []
    errors = []

    # Fetch Slack installations from database
    installations = []
    try:
        async with async_session_factory() as session:
            slack_installations = await session.execute(
                select(SlackInstallation).where(
                    (SlackInstallation.user_id == current_user["id"]) &
                    (SlackInstallation.is_active == True)
                )
            )
            installations = slack_installations.scalars().all()
        logger.info(f"Fetched {len(installations)} Slack installations from database")
    except Exception as e:
        logger.warning(f"Could not fetch from database (table may not exist yet): {e}")
        installations = []
    
    # Fallback: Check for old in-memory Slack tokens (backwards compatibility during transition)
    if not installations:
        legacy_slack = [i for i in _integrations if i["user_id"] == current_user["id"] and i["service"] == "slack"]
        if legacy_slack:
            logger.info(f"Using legacy in-memory Slack token (migrate by re-authenticating)")
            # Use the legacy token directly
            for integration in legacy_slack:
                access_token = integration.get("access_token", "")
                try:
                    logger.info(f"Syncing Slack (legacy in-memory token, first 20 chars: {access_token[:20]}...)")
                    texts = await _fetch_slack_messages(access_token)
                    logger.info(f"Sync slack: got {len(texts)} texts")
                    
                    if texts:
                        uid = current_user["id"]
                        for text in texts:
                            scrubbed_text = full_scrub(text)
                            event_id = str(uuid.uuid4())
                            new_event = {
                                "id": event_id,
                                "user_id": uid,
                                "source": "slack",
                                "event_type": "reflection",
                                "scrubbed_text": scrubbed_text,
                                "context": {"synced_from": "slack", "legacy": True},
                                "created_at": datetime.utcnow().isoformat(),
                            }
                            _events.setdefault(uid, []).insert(0, new_event)
                            events_created += 1

                            try:
                                import json
                                await publish_event(
                                    settings.redis_stream_name,
                                    {
                                        "payload": json.dumps({
                                            "id": event_id,
                                            "user_id": uid,
                                            "source": "slack",
                                            "event_type": "reflection",
                                            "text": text,
                                            "context": new_event["context"],
                                            "created_at": new_event["created_at"],
                                        }),
                                    }
                                )
                                logger.info(f"Published event {event_id} to Redis")
                            except Exception as e:
                                logger.error(f"Failed to publish event: {e}")
                        
                        services_synced.append("slack")
                    
                except Exception as e:
                    logger.error(f"Sync failed for legacy Slack: {e}", exc_info=True)
                    errors.append({"service": "slack", "error": str(e)})
            
            return {
                "status": "success",
                "events_created": events_created,
                "services_synced": services_synced,
                "errors": errors if errors else None,
                "note": "Using legacy in-memory token. Please re-authenticate Slack to migrate to database storage.",
            }
        else:
            return {"status": "no_integrations", "events_created": 0, "services_synced": []}
    
    # Decrypt and process each Slack installation (new database-backed flow)
    encryptor = E2EEncryption()
    encryption_key = encryptor.derive_key_from_string(settings.encryption_key) if settings.encryption_key else b"0" * 32
    
    for installation in installations:
        try:
            # Decrypt the user token
            decrypted_token = encryptor.decrypt_data(
                {
                    "ciphertext": installation.encrypted_user_token,
                    "nonce": installation.user_token_nonce,
                    "tag": installation.user_token_tag,
                },
                encryption_key,
            )
            
            logger.info(f"Syncing Slack workspace {installation.slack_workspace_id}")
            texts = await _fetch_slack_messages(decrypted_token)
            logger.info(f"Sync slack: got {len(texts)} texts from workspace {installation.slack_workspace_id}")
            
        except Exception as e:
            logger.error(f"Sync failed for Slack workspace {installation.slack_workspace_id}: {e}", exc_info=True)
            errors.append({"service": "slack", "workspace": installation.slack_workspace_id, "error": str(e)})
            continue

        if not texts:
            services_synced.append("slack")
            continue

        uid = current_user["id"]
        for text in texts:
            scrubbed_text = full_scrub(text)
            event_id = str(uuid.uuid4())
            new_event = {
                "id": event_id,
                "user_id": uid,
                "source": "slack",
                "event_type": "reflection",
                "scrubbed_text": scrubbed_text,
                "context": {
                    "synced_from": "slack",
                    "workspace": installation.slack_workspace_name,
                    "workspace_id": installation.slack_workspace_id,
                },
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
                            "source": "slack",
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

        services_synced.append("slack")
        
        # Update last_accessed_at timestamp
        async with async_session_factory() as session:
            db_installation = await session.get(SlackInstallation, installation.id)
            if db_installation:
                db_installation.last_accessed_at = datetime.utcnow()
                await session.commit()

    return {
        "status": "success",
        "events_created": events_created,
        "services_synced": services_synced,
        "errors": errors if errors else None,
    }


# Legacy in-memory sync (for Google Calendar, Gmail)
# TODO: Migrate Google services to database-backed installations like Slack
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
    """Fetch recent messages from Slack (DMs, group DMs, and all channels the bot is a member of).
    
    Note: Bot tokens (xoxb-) cannot access DMs/MPIMs, only user tokens (xoxp-) can.
    """
    import httpx

    texts = []
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Check token type
    is_bot_token = access_token.startswith("xoxb-")
    is_user_token = access_token.startswith("xoxp-")
    
    logger.info(f"Slack token type: bot_token={is_bot_token}, user_token={is_user_token}")

    async with httpx.AsyncClient(timeout=15) as client:
        # Fetch from DM channels (only if we have a user token)
        if not is_bot_token:
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
        else:
            logger.warning("Bot token detected (xoxb-): DM access not available. Skipping DM/MPIM channels. Add a user token (xoxp-) for full access.")

        # ALWAYS also fetch from public/private channels (works with both bot and user tokens)
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
        logger.warning(f"Slack sync returned 0 messages. Make sure the bot/app is added to channels with recent messages.")
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

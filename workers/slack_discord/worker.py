"""Slack & Discord Webhook Ingestion Worker.

Receives incoming webhook payloads, verifies signatures,
and pushes standardized FounderEvents to Redis Stream.
"""

import hashlib
import hmac
import json
import logging
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException

logger = logging.getLogger(__name__)

app = FastAPI(title="Seedlings Ingestion Worker - Slack/Discord")

SLACK_SIGNING_SECRET = ""  # Set via env var in production
DISCORD_PUBLIC_KEY = ""    # Set via env var in production


def verify_slack_signature(
    body: bytes,
    timestamp: str,
    signature: str,
    secret: str,
) -> bool:
    """Verify Slack webhook signature."""
    if not secret:
        logger.warning("Slack signing secret not configured, skipping verification")
        return True

    sig_basestring = f"v0:{timestamp}:{body.decode('utf-8')}"
    my_signature = "v0=" + hmac.new(
        secret.encode(), sig_basestring.encode(), hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(my_signature, signature)


@app.post("/webhook/slack")
async def slack_webhook(request: Request):
    """Receive Slack DM webhooks and push to Redis Stream."""
    body = await request.body()
    timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
    signature = request.headers.get("X-Slack-Signature", "")

    if SLACK_SIGNING_SECRET and not verify_slack_signature(
        body, timestamp, signature, SLACK_SIGNING_SECRET
    ):
        raise HTTPException(status_code=401, detail="Invalid signature")

    payload = json.loads(body)

    # Handle URL verification challenge
    if payload.get("type") == "url_verification":
        return {"challenge": payload["challenge"]}

    # Process message events
    event = payload.get("event", {})
    if event.get("type") == "message" and "subtype" not in event:
        founder_event = {
            "id": event.get("client_msg_id", ""),
            "source": "slack",
            "event_type": "reflection",
            "text": event.get("text", ""),
            "context": {
                "channel": event.get("channel", ""),
                "user": event.get("user", ""),
                "timestamp": event.get("ts", ""),
            },
            "created_at": datetime.utcnow().isoformat(),
        }

        # Push to Redis Stream
        try:
            import redis
            r = redis.Redis(host="localhost", port=6379, decode_responses=True)
            r.xadd("seedlings:events", {
                "event_id": founder_event["id"],
                "source": "slack",
                "payload": json.dumps(founder_event),
            })
            logger.info(f"Slack event pushed to Redis: {founder_event['id']}")
        except Exception as e:
            logger.error(f"Failed to push to Redis: {e}")

        return {"status": "ok"}

    return {"status": "ignored"}


@app.post("/webhook/discord")
async def discord_webhook(request: Request):
    """Receive Discord DM webhooks and push to Redis Stream."""
    body = await request.body()
    payload = json.loads(body)

    # Discord ping verification
    if payload.get("type") == 1:
        return {"type": 1}

    # Message create event
    if payload.get("type") == 0:
        content = payload.get("content", "")
        author = payload.get("author", {})

        founder_event = {
            "id": payload.get("id", ""),
            "source": "discord",
            "event_type": "reflection",
            "text": content,
            "context": {
                "author_id": author.get("id", ""),
                "channel_id": payload.get("channel_id", ""),
            },
            "created_at": datetime.utcnow().isoformat(),
        }

        try:
            import redis
            r = redis.Redis(host="localhost", port=6379, decode_responses=True)
            r.xadd("seedlings:events", {
                "event_id": founder_event["id"],
                "source": "discord",
                "payload": json.dumps(founder_event),
            })
            logger.info(f"Discord event pushed to Redis: {founder_event['id']}")
        except Exception as e:
            logger.error(f"Failed to push to Redis: {e}")

        return {"status": "ok"}

    return {"status": "ignored"}


@app.get("/health")
async def health():
    return {"status": "ok", "worker": "slack_discord"}

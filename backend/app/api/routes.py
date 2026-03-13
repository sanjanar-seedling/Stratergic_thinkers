"""API Routes — All REST endpoints for the Seedlings application."""

import uuid
import logging
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends

from app.core.security import get_current_user

from app.schemas import (
    FounderEventCreate,
    FounderEventResponse,
    DecisionCreate,
    DecisionResponse,
    DecisionResolve,
    TranscriptionResponse,
    DashboardStats,
    SparringContinueRequest,
)
from app.middleware.pii_stripper import full_scrub
from app.core.redis_client import publish_event
from app.core.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()

# ── Per-user in-memory stores (keyed by user_id) ──

_events: dict[str, list[dict]] = {}
_decisions: dict[str, list[dict]] = {}
_biases: dict[str, list[dict]] = {}


# ── Health ──

@router.get("/health")
async def health_check():
    return {"status": "ok", "service": "seedlings-api", "version": "0.1.0"}


# ── Events ──

@router.post("/events", response_model=FounderEventResponse)
async def create_event(event: FounderEventCreate, current_user: dict = Depends(get_current_user)):
    """Create a new FounderEvent. Text is PII-scrubbed before storage."""
    uid = current_user["id"]
    scrubbed_text = full_scrub(event.text) if not event.encrypted else event.text

    event_record = {
        "id": str(uuid.uuid4()),
        "user_id": uid,
        "source": event.source.value,
        "event_type": event.event_type.value,
        "scrubbed_text": scrubbed_text,
        "context": event.context,
        "created_at": datetime.utcnow().isoformat(),
    }

    _events.setdefault(uid, []).insert(0, event_record)

    # Publish to Redis Stream
    try:
        await publish_event(
            settings.redis_stream_name,
            {"event_id": event_record["id"], "source": event.source.value, "type": event.event_type.value},
        )
    except Exception as e:
        logger.warning(f"Redis publish failed (non-critical): {e}")

    return FounderEventResponse(
        id=event_record["id"],
        source=event.source,
        event_type=event.event_type,
        scrubbed_text=scrubbed_text,
        context=event.context,
        created_at=datetime.utcnow(),
    )


@router.get("/events")
async def list_events(limit: int = 20, offset: int = 0, current_user: dict = Depends(get_current_user)):
    uid = current_user["id"]
    user_events = _events.get(uid, [])
    return user_events[offset:offset + limit]


# ── Decisions ──

@router.post("/decisions", response_model=DecisionResponse)
async def create_decision(decision: DecisionCreate, current_user: dict = Depends(get_current_user)):
    uid = current_user["id"]
    record = {
        "id": str(uuid.uuid4()),
        "user_id": uid,
        "title": decision.title,
        "rationale": full_scrub(decision.rationale),
        "expected_outcome": decision.expected_outcome,
        "expected_outcome_date": decision.expected_outcome_date,
        "confidence_score": decision.confidence_score,
        "alternatives": decision.alternatives,
        "status": "pending",
        "actual_outcome": None,
        "outcome_score": None,
        "created_at": datetime.utcnow().isoformat(),
    }
    _decisions.setdefault(uid, []).insert(0, record)
    return DecisionResponse(**{**record, "created_at": datetime.utcnow()})


@router.get("/decisions")
async def list_decisions(status: str = None, current_user: dict = Depends(get_current_user)):
    uid = current_user["id"]
    user_decisions = _decisions.get(uid, [])
    if status:
        return [d for d in user_decisions if d["status"] == status]
    return user_decisions


@router.put("/decisions/{decision_id}/resolve")
async def resolve_decision(decision_id: str, resolution: DecisionResolve, current_user: dict = Depends(get_current_user)):
    uid = current_user["id"]
    for d in _decisions.get(uid, []):
        if d["id"] == decision_id:
            d["actual_outcome"] = resolution.actual_outcome
            d["outcome_score"] = resolution.outcome_score
            d["status"] = "resolved"
            return d
    raise HTTPException(status_code=404, detail="Decision not found")


# ── Transcription ──

@router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio(audio: UploadFile = File(...), language: str = None):
    """Transcribe audio using Groq Whisper, OpenAI Whisper, or local fallback.

    Language parameter is optional — omit for auto-detection (language agnostic).
    """
    audio_bytes = await audio.read()
    size_mb = len(audio_bytes) / (1024 * 1024)
    logger.info(f"Received audio file: {audio.filename}, size: {size_mb:.2f}MB")

    import tempfile, os
    ext = audio.filename.rsplit(".", 1)[-1] if audio.filename and "." in audio.filename else "webm"
    with tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        # Try Groq Whisper first (fast, free tier available)
        if settings.groq_api_key:
            try:
                from openai import OpenAI
                client = OpenAI(
                    api_key=settings.groq_api_key,
                    base_url="https://api.groq.com/openai/v1",
                )
                kwargs = {
                    "model": settings.groq_whisper_model,
                    "file": open(tmp_path, "rb"),
                }
                if language:
                    kwargs["language"] = language

                transcript = client.audio.transcriptions.create(**kwargs)
                return TranscriptionResponse(
                    text=transcript.text,
                    duration_seconds=size_mb * 30,
                )
            except Exception as e:
                logger.error(f"Groq Whisper transcription failed: {e}")

        # Fallback to OpenAI Whisper
        if settings.openai_api_key:
            try:
                from openai import OpenAI
                client = OpenAI(api_key=settings.openai_api_key)
                kwargs = {"model": "whisper-1", "file": open(tmp_path, "rb")}
                if language:
                    kwargs["language"] = language

                transcript = client.audio.transcriptions.create(**kwargs)
                return TranscriptionResponse(
                    text=transcript.text,
                    duration_seconds=size_mb * 30,
                )
            except Exception as e:
                logger.error(f"OpenAI Whisper transcription failed: {e}")

        # No API key configured
        logger.warning("No transcription API key configured — returning stub")
        return TranscriptionResponse(
            text="[Transcription requires GROQ_API_KEY or OPENAI_API_KEY in .env] "
                 "Audio received successfully. Set your API key to enable real transcription.",
            duration_seconds=size_mb * 30,
        )
    finally:
        os.unlink(tmp_path)


# ── Sparring ──

@router.post("/sparring/{decision_id}")
async def trigger_sparring(decision_id: str, current_user: dict = Depends(get_current_user)):
    """Trigger adversarial sparring for a specific decision."""
    from app.services.adversarial_sparring import adversarial_sparring

    uid = current_user["id"]
    decision = next((d for d in _decisions.get(uid, []) if d["id"] == decision_id), None)
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")

    challenge = await adversarial_sparring.generate_challenge(decision)
    return {"decision_id": decision_id, "challenge": challenge}


@router.post("/sparring/{decision_id}/continue")
async def continue_sparring(decision_id: str, request: SparringContinueRequest, current_user: dict = Depends(get_current_user)):
    """Continue adversarial sparring for a specific decision."""
    from app.services.adversarial_sparring import adversarial_sparring

    uid = current_user["id"]
    decision = next((d for d in _decisions.get(uid, []) if d["id"] == decision_id), None)
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")

    # Format history into a string
    history_str = ""
    for msg in request.conversation_history:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        if role == "system":
            history_str += f"AI: {content}\n\n"
        elif role == "user":
            history_str += f"Founder: {content}\n\n"

    response = await adversarial_sparring.continue_sparring(
        history_str,
        request.user_message
    )
    return {"decision_id": decision_id, "response": response}


# ── Dashboard ──

@router.get("/dashboard/stats", response_model=DashboardStats)
async def get_dashboard_stats(current_user: dict = Depends(get_current_user)):
    uid = current_user["id"]
    user_decisions = _decisions.get(uid, [])
    resolved = [d for d in user_decisions if d["status"] == "resolved"]
    avg_accuracy = (
        sum(d.get("outcome_score", 0) for d in resolved) / len(resolved) * 100
        if resolved else 0
    )
    return DashboardStats(
        total_decisions=len(user_decisions),
        avg_accuracy=round(avg_accuracy, 1),
        biases_caught=len(_biases.get(uid, [])),
        open_decisions=sum(1 for d in user_decisions if d["status"] == "pending"),
    )


@router.get("/dashboard/biases")
async def get_bias_detections(current_user: dict = Depends(get_current_user)):
    return _biases.get(current_user["id"], [])


@router.get("/dashboard/growth")
async def get_growth_trajectory(current_user: dict = Depends(get_current_user)):
    uid = current_user["id"]
    user_decisions = _decisions.get(uid, [])
    user_events = _events.get(uid, [])

    # Build last 6 months of real data
    from collections import defaultdict
    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                   "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    now = datetime.utcnow()
    buckets: dict[str, dict] = {}
    for i in range(5, -1, -1):
        m = now.month - i
        y = now.year
        while m <= 0:
            m += 12
            y -= 1
        label = month_names[m - 1]
        buckets[f"{y}-{m:02d}"] = {"month": label, "confidence": 0, "accuracy": 0,
                                    "reflection_count": 0, "_conf_sum": 0, "_conf_n": 0,
                                    "_acc_sum": 0, "_acc_n": 0}

    for d in user_decisions:
        try:
            dt = datetime.fromisoformat(d["created_at"])
            key = f"{dt.year}-{dt.month:02d}"
            if key in buckets:
                buckets[key]["_conf_sum"] += d.get("confidence_score", 0) * 100
                buckets[key]["_conf_n"] += 1
                if d.get("outcome_score") is not None:
                    buckets[key]["_acc_sum"] += d["outcome_score"] * 100
                    buckets[key]["_acc_n"] += 1
        except Exception:
            pass

    for e in user_events:
        try:
            dt = datetime.fromisoformat(e["created_at"])
            key = f"{dt.year}-{dt.month:02d}"
            if key in buckets:
                buckets[key]["reflection_count"] += 1
        except Exception:
            pass

    result = []
    for b in buckets.values():
        result.append({
            "month": b["month"],
            "confidence": round(b["_conf_sum"] / b["_conf_n"]) if b["_conf_n"] else 0,
            "accuracy": round(b["_acc_sum"] / b["_acc_n"]) if b["_acc_n"] else 0,
            "reflection_count": b["reflection_count"],
        })
    return result


# ── Privacy / Data Management ──

@router.get("/privacy/export")
async def export_user_data(current_user: dict = Depends(get_current_user)):
    """Export all user data as JSON."""
    uid = current_user["id"]
    return {
        "user_id": uid,
        "exported_at": datetime.utcnow().isoformat(),
        "events": _events.get(uid, []),
        "decisions": _decisions.get(uid, []),
        "biases": _biases.get(uid, []),
    }


@router.delete("/privacy/data")
async def delete_user_data(current_user: dict = Depends(get_current_user)):
    """Delete all data for the current user."""
    uid = current_user["id"]
    _events.pop(uid, None)
    _decisions.pop(uid, None)
    _biases.pop(uid, None)
    return {"status": "deleted", "user_id": uid}

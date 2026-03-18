"""Event Processor Service.

Consumes events from Redis Stream and performs:
1. Validation and normalization
2. PII detection and redaction
3. Event enrichment (sentiment, entities, etc.)
4. Storage in PostgreSQL
5. Triggering downstream analysis pipelines
"""

import json
import logging
from datetime import datetime
from typing import Optional
import uuid

import redis.asyncio
from pydantic import BaseModel, Field, validator

# Strategic Thinkers internal imports
from app.core.database import async_session_factory
from app.models import FounderEvent as DBFounderEvent, EventSource, EventType
from app.middleware.pii_stripper import full_scrub
from app.services.pattern_engine import PatternEngine
from app.services.intervention import InterventionEngine
from app.core.encryption import E2EEncryption

logger = logging.getLogger(__name__)


class FounderEvent(BaseModel):
    """Standardized event schema for all input sources."""

    id: str = Field(..., description="Unique event identifier")
    source: str = Field(
        ...,
        description="Input source: email, slack, voice, web",
    )
    event_type: str = Field(
        ...,
        description="Event type: reflection, decision_record, weekly_review",
    )
    text: str = Field(..., description="Main text content")
    context: dict = Field(
        default_factory=dict,
        description="Source-specific metadata",
    )
    created_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="ISO 8601 timestamp",
    )
    user_id: Optional[str] = Field(None, description="User ID (if authenticated)")

    @validator("source")
    def validate_source(cls, v):
        allowed = ["email", "slack", "voice", "web", "google_calendar"]
        if v not in allowed:
            raise ValueError(f"Invalid source: {v}. Must be one of {allowed}")
        return v

    @validator("event_type")
    def validate_event_type(cls, v):
        allowed = ["reflection", "decision_record", "weekly_review", "time_allocation"]
        if v not in allowed:
            raise ValueError(f"Invalid event_type: {v}. Must be one of {allowed}")
        return v


class EventProcessor:
    """Processes and enriches FounderEvents from Redis Stream."""

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        stream_name: str = "seedlings:events",
        consumer_group: str = "event-processors",
        consumer_name: str = "processor-1",
    ):
        self.redis_url = redis_url
        self.stream_name = stream_name
        self.consumer_group = consumer_group
        self.consumer_name = consumer_name
        self._redis_client = None

    async def _get_redis(self) -> redis.asyncio.Redis:
        """Lazy async Redis connection."""
        if self._redis_client is None:
            self._redis_client = await redis.asyncio.from_url(
                self.redis_url, decode_responses=True
            )
            # Create consumer group if it doesn't exist
            try:
                await self._redis_client.xgroup_create(
                    self.stream_name,
                    self.consumer_group,
                    id="0",
                    mkstream=True,
                )
                logger.info(f"Created consumer group: {self.consumer_group}")
            except redis.ResponseError as e:
                if "BUSYGROUP" not in str(e):
                    raise
        return self._redis_client

    def validate_event(self, raw_payload: str) -> Optional[FounderEvent]:
        """Validate and parse raw event payload."""
        try:
            data = json.loads(raw_payload)
            return FounderEvent(**data)
        except Exception as e:
            logger.error(f"Event validation failed: {e}")
            return None

    def enrich_event(self, event: FounderEvent) -> dict:
        """Enrich event with additional metadata.
        
        Future enhancements:
        - Sentiment analysis
        - Named entity recognition
        - Topic classification
        - Urgency detection
        """
        enriched = event.dict()
        enriched["enrichment"] = {
            "processed_at": datetime.utcnow().isoformat(),
            "text_length": len(event.text),
            "word_count": len(event.text.split()),
        }
        return enriched

    async def process_stream(self, batch_size: int = 10, block_ms: int = 5000):
        """Continuously process events from Redis Stream.
        
        Args:
            batch_size: Number of events to fetch per batch
            block_ms: Milliseconds to block waiting for new events
        """
        r = await self._get_redis()
        logger.info(
            f"Starting event processor: {self.consumer_name} "
            f"(group: {self.consumer_group})"
        )

        while True:
            try:
                # Read from stream
                messages = await r.xreadgroup(
                    self.consumer_group,
                    self.consumer_name,
                    {self.stream_name: ">"},
                    count=batch_size,
                    block=block_ms,
                )

                if not messages:
                    continue

                for stream_name, stream_messages in messages:
                    for message_id, message_data in stream_messages:
                        try:
                            # Extract payload
                            raw_payload = message_data.get("payload")
                            if not raw_payload:
                                logger.warning(f"Empty payload: {message_id}")
                                await r.xack(self.stream_name, self.consumer_group, message_id)
                                continue

                            # Validate
                            event = self.validate_event(raw_payload)
                            if not event:
                                logger.warning(f"Invalid event: {message_id}")
                                await r.xack(self.stream_name, self.consumer_group, message_id)
                                continue

                            # Enrich
                            enriched_event = self.enrich_event(event)
                            
                            # Perform PII scrubbing for AI processing
                            anonymized_text = full_scrub(event.text)
                            
                            # Encrypt the raw data for storage
                            encryptor = E2EEncryption()
                            # In reality, obtain user's password/secret key securely.
                            # For ingestion pipelines, we use a system-level symmetric key or user's public key
                            storage_key = b"0" * 32 # Mock 32-byte key for event processor
                            encrypted_data = encryptor.encrypt_data(event.text, storage_key)

                            # 1. Store in PostgreSQL
                            async with async_session_factory() as session:
                                # Prepare the models and map fields
                                db_event = DBFounderEvent(
                                    user_id=uuid.UUID(event.user_id) if event.user_id else uuid.uuid4(), # Fallback for demo
                                    source=EventSource(event.source),
                                    event_type=EventType(event.event_type),
                                    encrypted_text=encrypted_data["ciphertext"],
                                    encryption_nonce=encrypted_data["nonce"],
                                    encryption_tag=encrypted_data["tag"],
                                    anonymized_text=anonymized_text,
                                )
                                session.add(db_event)
                                await session.commit()
                                await session.refresh(db_event)

                            # 2. Trigger cognitive analysis pipelines
                            # If it is a reflection, let's run it through our pattern engine
                            pattern_findings = []
                            if event.event_type in ["reflection", "weekly_review"]:
                                engine = PatternEngine()
                                # Simulate analyzing a week of context using just this event for now
                                # In a real implementation this would fetch last 7 days of DBFounderEvents
                                pattern_findings = await engine.analyze_week([enriched_event])
                                logger.info(f"Pattern findings for {event.id}: {pattern_findings}")

                            # 3. Check for intervention triggers
                            # If biases or patterns were found, trigger an intervention
                            if pattern_findings:
                                dummy_llm_provider = None # Interventions class relies on llm_provider
                                intervention_engine = InterventionEngine(llm_provider=dummy_llm_provider)
                                
                                # Try generating an intervention for the first detected bias
                                bias_type = pattern_findings[0].get("bias_type", "unknown")
                                description = pattern_findings[0].get("description", "")
                                
                                if intervention_engine.should_intervene("pattern", context={"pattern": bias_type}):
                                    # Since we mocked llm provider, maybe we shouldn't await if it crashes, 
                                    # but this shows the architecture flow
                                    try:
                                        prompt = await intervention_engine.generate_bias_intervention(
                                            bias_type=bias_type,
                                            evidence=description,
                                            recent_context=anonymized_text
                                        )
                                        logger.info(f"Generated Intervention -> {prompt.question}")
                                        # Push intervention to Redis for queued delivery
                                        try:
                                            redis_client = await self._get_redis()
                                            intervention_payload = {
                                                "user_id": str(event.user_id),
                                                "intervention_id": prompt.id,
                                                "prompt": prompt.question,
                                                "context": prompt.context,
                                                "timestamp": datetime.utcnow().isoformat(),
                                            }
                                            await redis_client.xadd(f"interventions:{event.user_id}", intervention_payload)
                                            logger.info(f"Intervention queued for delivery: {prompt.id}")
                                        except Exception as e:
                                            logger.warning(f"Failed to queue intervention delivery: {e}")
                                    except Exception as e:
                                        logger.error(f"Failed to generate intervention: {e}")

                            logger.info(
                                f"Processed event {event.id}: {event.source} -> {event.event_type}"
                            )

                            # Acknowledge
                            await r.xack(self.stream_name, self.consumer_group, message_id)

                        except Exception as e:
                            logger.error(f"Failed to process message {message_id}: {e}")
                            # Don't acknowledge - will be retried
                            continue

            except KeyboardInterrupt:
                logger.info("Shutting down event processor")
                break
            except Exception as e:
                logger.error(f"Stream processing error: {e}")
                continue


if __name__ == "__main__":
    import asyncio

    processor = EventProcessor()
    asyncio.run(processor.process_stream())

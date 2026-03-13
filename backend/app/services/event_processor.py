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

import redis
from pydantic import BaseModel, Field, validator

logger = logging.getLogger(__name__)


class FounderEvent(BaseModel):
    """Standardized event schema for all input sources."""

    id: str = Field(..., description="Unique event identifier")
    source: str = Field(
        ...,
        description="Input source: email, slack, discord, voice, web",
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
        allowed = ["email", "slack", "discord", "voice", "web", "google_calendar"]
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

    def _get_redis(self) -> redis.Redis:
        """Lazy Redis connection."""
        if self._redis_client is None:
            self._redis_client = redis.from_url(
                self.redis_url, decode_responses=True
            )
            # Create consumer group if it doesn't exist
            try:
                self._redis_client.xgroup_create(
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
        r = self._get_redis()
        logger.info(
            f"Starting event processor: {self.consumer_name} "
            f"(group: {self.consumer_group})"
        )

        while True:
            try:
                # Read from stream
                messages = r.xreadgroup(
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
                                r.xack(self.stream_name, self.consumer_group, message_id)
                                continue

                            # Validate
                            event = self.validate_event(raw_payload)
                            if not event:
                                logger.warning(f"Invalid event: {message_id}")
                                r.xack(self.stream_name, self.consumer_group, message_id)
                                continue

                            # Enrich
                            enriched_event = self.enrich_event(event)

                            # TODO: Store in PostgreSQL
                            # TODO: Trigger cognitive analysis pipelines
                            # TODO: Check for intervention triggers

                            logger.info(
                                f"Processed event {event.id}: {event.source} -> {event.event_type}"
                            )

                            # Acknowledge
                            r.xack(self.stream_name, self.consumer_group, message_id)

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

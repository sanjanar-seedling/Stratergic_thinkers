"""Voice Transcription Worker.

Transcribes voice memos using OpenAI Whisper API or local Whisper model.
Supports async voice note capture for frictionless reflection.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

import httpx
import redis

logger = logging.getLogger(__name__)


class VoiceTranscriptionWorker:
    """Transcribes audio files and converts to FounderEvents."""

    def __init__(
        self,
        provider: str = "groq",  # "groq", "openai", or "local"
        openai_api_key: Optional[str] = None,
        groq_api_key: Optional[str] = None,
        redis_url: str = "redis://localhost:6379",
        stream_name: str = "seedlings:events",
    ):
        self.provider = provider
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.groq_api_key = groq_api_key or os.getenv("GROQ_API_KEY")
        self.redis_url = redis_url
        self.stream_name = stream_name
        self._redis_client = None

    def _get_redis(self) -> redis.Redis:
        """Lazy Redis connection."""
        if self._redis_client is None:
            self._redis_client = redis.from_url(
                self.redis_url, decode_responses=True
            )
        return self._redis_client

    async def transcribe_groq(
        self,
        audio_file_path: str,
        language: Optional[str] = None,
    ) -> dict:
        """Transcribe audio using Groq Whisper API (OpenAI-compatible).

        Returns:
            {
                "text": "transcribed text",
                "language": "en",
                "duration": 45.2,
            }
        """
        if not self.groq_api_key:
            raise ValueError("Groq API key not configured")

        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                with open(audio_file_path, "rb") as audio_file:
                    files = {"file": audio_file}
                    data = {
                        "model": os.getenv("GROQ_WHISPER_MODEL", "whisper-large-v3-turbo"),
                        "response_format": "verbose_json",
                    }
                    if language:
                        data["language"] = language

                    response = await client.post(
                        "https://api.groq.com/openai/v1/audio/transcriptions",
                        headers={"Authorization": f"Bearer {self.groq_api_key}"},
                        files=files,
                        data=data,
                    )
                    response.raise_for_status()
                    result = response.json()

                    return {
                        "text": result.get("text", "").strip(),
                        "language": result.get("language", "unknown"),
                        "duration": result.get("duration", 0),
                    }

        except Exception as e:
            logger.error(f"Groq transcription failed: {e}")
            raise

    async def transcribe_openai(
        self,
        audio_file_path: str,
        language: Optional[str] = None,
    ) -> dict:
        """Transcribe audio using OpenAI Whisper API.
        
        Returns:
            {
                "text": "transcribed text",
                "language": "en",
                "duration": 45.2,
            }
        """
        if not self.openai_api_key:
            raise ValueError("OpenAI API key not configured")

        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                with open(audio_file_path, "rb") as audio_file:
                    files = {"file": audio_file}
                    data = {
                        "model": "whisper-1",
                        "response_format": "verbose_json",
                    }
                    if language:
                        data["language"] = language

                    response = await client.post(
                        "https://api.openai.com/v1/audio/transcriptions",
                        headers={"Authorization": f"Bearer {self.openai_api_key}"},
                        files=files,
                        data=data,
                    )
                    response.raise_for_status()
                    result = response.json()

                    return {
                        "text": result.get("text", "").strip(),
                        "language": result.get("language", "unknown"),
                        "duration": result.get("duration", 0),
                    }

        except Exception as e:
            logger.error(f"OpenAI transcription failed: {e}")
            raise

    async def transcribe_local(
        self,
        audio_file_path: str,
    ) -> dict:
        """Transcribe audio using local Whisper model.
        
        Requires: pip install openai-whisper
        
        Returns:
            {
                "text": "transcribed text",
                "language": "en",
                "duration": 45.2,
            }
        """
        try:
            import whisper

            model = whisper.load_model("base")  # or "small", "medium", "large"
            result = model.transcribe(audio_file_path)

            return {
                "text": result["text"].strip(),
                "language": result.get("language", "unknown"),
                "duration": 0,  # Local model doesn't return duration
            }

        except ImportError:
            logger.error(
                "Local Whisper not installed. Run: pip install openai-whisper"
            )
            raise
        except Exception as e:
            logger.error(f"Local transcription failed: {e}")
            raise

    async def process_audio_file(
        self,
        audio_file_path: str,
        user_id: str,
        metadata: Optional[dict] = None,
    ) -> str:
        """Process audio file and push to Redis Stream.
        
        Args:
            audio_file_path: Path to audio file (mp3, m4a, wav, etc.)
            user_id: User ID for attribution
            metadata: Optional metadata (tags, context, etc.)
        
        Returns:
            Event ID
        """
        # Transcribe
        if self.provider == "groq":
            transcription = await self.transcribe_groq(audio_file_path)
        elif self.provider == "openai":
            transcription = await self.transcribe_openai(audio_file_path)
        else:
            transcription = await self.transcribe_local(audio_file_path)

        # Detect event type from transcription
        event_type = self._detect_event_type(transcription["text"])

        # Create FounderEvent
        file_name = Path(audio_file_path).name
        founder_event = {
            "id": f"voice-{datetime.utcnow().timestamp()}",
            "source": "voice",
            "event_type": event_type,
            "text": transcription["text"],
            "context": {
                "file_name": file_name,
                "language": transcription["language"],
                "duration_seconds": transcription["duration"],
                "transcription_provider": self.provider,
                "user_id": user_id,
                **(metadata or {}),
            },
            "created_at": datetime.utcnow().isoformat(),
        }

        # Push to Redis Stream
        r = self._get_redis()
        r.xadd(
            self.stream_name,
            {
                "event_id": founder_event["id"],
                "source": "voice",
                "payload": json.dumps(founder_event),
            },
        )

        logger.info(
            f"Voice memo transcribed: {file_name} -> {event_type} "
            f"({len(transcription['text'])} chars)"
        )

        return founder_event["id"]

    def _detect_event_type(self, text: str) -> str:
        """Detect event type from transcription text."""
        text_lower = text.lower()

        # Decision indicators
        decision_keywords = [
            "i decided",
            "we're going with",
            "chose to",
            "decision:",
            "going to pivot",
        ]
        if any(kw in text_lower for kw in decision_keywords):
            return "decision_record"

        # Weekly review indicators
        review_keywords = [
            "weekly review",
            "this week",
            "last week",
            "looking back",
        ]
        if any(kw in text_lower for kw in review_keywords):
            return "weekly_review"

        return "reflection"


if __name__ == "__main__":
    import asyncio

    # Example usage
    worker = VoiceTranscriptionWorker(provider="groq")

    async def run():
        event_id = await worker.process_audio_file(
            audio_file_path="/path/to/voice_memo.m4a",
            user_id="founder-123",
            metadata={"tags": ["product", "strategy"]},
        )
        print(f"Created event: {event_id}")

    asyncio.run(run())

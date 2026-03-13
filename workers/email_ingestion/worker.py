"""Email Ingestion Worker.

Allows founders to forward emails or send journal entries directly via email.
Processes IMAP inbox and converts emails to standardized FounderEvents.
"""

import email
import imaplib
import json
import logging
import re
from datetime import datetime
from email.header import decode_header
from typing import Optional

import redis

logger = logging.getLogger(__name__)


class EmailIngestionWorker:
    """Processes incoming emails and converts them to FounderEvents."""

    def __init__(
        self,
        imap_server: str,
        email_address: str,
        password: str,
        redis_url: str = "redis://localhost:6379",
        stream_name: str = "seedlings:events",
    ):
        self.imap_server = imap_server
        self.email_address = email_address
        self.password = password
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

    def _decode_header_value(self, value: str) -> str:
        """Decode email header value."""
        decoded_parts = decode_header(value)
        result = ""
        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                result += part.decode(encoding or "utf-8", errors="ignore")
            else:
                result += part
        return result

    def _extract_text_from_email(self, msg: email.message.Message) -> str:
        """Extract plain text content from email message."""
        text_parts = []

        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == "text/plain":
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or "utf-8"
                        text_parts.append(
                            payload.decode(charset, errors="ignore")
                        )
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset() or "utf-8"
                text_parts.append(payload.decode(charset, errors="ignore"))

        return "\n\n".join(text_parts).strip()

    def _detect_event_type(self, subject: str, body: str) -> str:
        """Detect event type from email content.
        
        Patterns:
        - Subject starts with [DECISION]: decision_record
        - Subject starts with [WEEKLY]: weekly_review
        - Subject starts with [REFLECTION]: reflection
        - Default: reflection
        """
        subject_lower = subject.lower()
        
        if subject_lower.startswith("[decision]") or "decision:" in subject_lower:
            return "decision_record"
        elif subject_lower.startswith("[weekly]") or "weekly review" in subject_lower:
            return "weekly_review"
        elif subject_lower.startswith("[reflection]"):
            return "reflection"
        
        # Check body for decision keywords
        decision_keywords = ["decided to", "choosing", "going with", "opted for"]
        if any(kw in body.lower() for kw in decision_keywords):
            return "decision_record"
        
        return "reflection"

    def _extract_metadata(self, body: str) -> dict:
        """Extract structured metadata from email body.
        
        Supports patterns like:
        - Tags: #fundraising #product
        - Priority: [HIGH] or [URGENT]
        - Context: @context: board meeting
        """
        metadata = {}
        
        # Extract hashtags
        tags = re.findall(r'#(\w+)', body)
        if tags:
            metadata["tags"] = tags
        
        # Extract priority
        priority_match = re.search(r'\[(HIGH|URGENT|LOW)\]', body, re.IGNORECASE)
        if priority_match:
            metadata["priority"] = priority_match.group(1).upper()
        
        # Extract context
        context_match = re.search(r'@context:\s*(.+?)(?:\n|$)', body, re.IGNORECASE)
        if context_match:
            metadata["context"] = context_match.group(1).strip()
        
        return metadata

    async def process_inbox(self, mark_as_read: bool = True) -> int:
        """Process unread emails from inbox.
        
        Returns:
            Number of emails processed
        """
        processed_count = 0

        try:
            # Connect to IMAP server
            mail = imaplib.IMAP4_SSL(self.imap_server)
            mail.login(self.email_address, self.password)
            mail.select("INBOX")

            # Search for unread emails
            status, messages = mail.search(None, "UNSEEN")
            if status != "OK":
                logger.error("Failed to search inbox")
                return 0

            email_ids = messages[0].split()
            logger.info(f"Found {len(email_ids)} unread emails")

            for email_id in email_ids:
                try:
                    # Fetch email
                    status, msg_data = mail.fetch(email_id, "(RFC822)")
                    if status != "OK":
                        continue

                    # Parse email
                    raw_email = msg_data[0][1]
                    msg = email.message_from_bytes(raw_email)

                    # Extract fields
                    subject = self._decode_header_value(msg.get("Subject", ""))
                    from_addr = msg.get("From", "")
                    date_str = msg.get("Date", "")
                    body = self._extract_text_from_email(msg)

                    # Detect event type and extract metadata
                    event_type = self._detect_event_type(subject, body)
                    metadata = self._extract_metadata(body)

                    # Create FounderEvent
                    founder_event = {
                        "id": msg.get("Message-ID", f"email-{email_id.decode()}"),
                        "source": "email",
                        "event_type": event_type,
                        "text": body,
                        "context": {
                            "subject": subject,
                            "from": from_addr,
                            "date": date_str,
                            **metadata,
                        },
                        "created_at": datetime.utcnow().isoformat(),
                    }

                    # Push to Redis Stream
                    r = self._get_redis()
                    r.xadd(
                        self.stream_name,
                        {
                            "event_id": founder_event["id"],
                            "source": "email",
                            "payload": json.dumps(founder_event),
                        },
                    )

                    logger.info(
                        f"Email processed: {subject[:50]} -> {event_type}"
                    )
                    processed_count += 1

                    # Mark as read
                    if mark_as_read:
                        mail.store(email_id, "+FLAGS", "\\Seen")

                except Exception as e:
                    logger.error(f"Failed to process email {email_id}: {e}")
                    continue

            mail.close()
            mail.logout()

        except Exception as e:
            logger.error(f"IMAP connection failed: {e}")
            return 0

        return processed_count


if __name__ == "__main__":
    import asyncio
    import os

    # Example usage
    worker = EmailIngestionWorker(
        imap_server=os.getenv("IMAP_SERVER", "imap.gmail.com"),
        email_address=os.getenv("EMAIL_ADDRESS", ""),
        password=os.getenv("EMAIL_PASSWORD", ""),
    )

    async def run():
        count = await worker.process_inbox()
        print(f"Processed {count} emails")

    asyncio.run(run())

# 🌱 Workers — Seedlings

> Multi-modal ingestion workers that capture founder input and normalize it to the FounderEvent schema.

## 📖 Overview

The workers layer is responsible for ingesting founder signals from multiple channels — email, voice memos, chat platforms, calendar data, and uploaded documents. Each worker normalizes its input into a unified `FounderEvent` and pushes it to a Redis Stream (`seedlings:events`) for downstream processing by the backend.

## 📁 Directory Structure

```
workers/
├── email_ingestion/
│   └── worker.py          # IMAP email polling and parsing
├── voice_transcription/
│   └── worker.py          # Audio transcription via OpenAI Whisper
├── slack/
│   └── worker.py          # Slack webhook ingestion (FastAPI)
├── google_workspace/
│   └── worker.py          # Google Calendar & Gmail integration
├── ocr/
│   └── worker.py          # Document upload (S3/MinIO) and OCR extraction
└── README.md
```

## 🔑 Key Components

| Worker | Class | Key Functions | Input Source |
|---|---|---|---|
| Email Ingestion | `EmailIngestionWorker` | `process_inbox()`, `_detect_event_type()`, `_extract_metadata()` | IMAP inbox (unread emails) |
| Voice Transcription | `VoiceTranscriptionWorker` | `process_audio_file()`, `transcribe_openai()`, `transcribe_local()` | Audio files (mp3, m4a, wav) |
| Slack | FastAPI `app` | `slack_webhook()`, `verify_slack_signature()` | Slack webhook payloads |
| Google Workspace | `GoogleWorkspaceWorker` | `fetch_calendar_events()`, `fetch_recent_gmail_snippets()`, `analyze_time_allocation()`, `detect_heavy_execution_phase()` | Google Calendar & Gmail APIs |
| OCR | `OCRWorker` | `upload_file()`, `extract_text()`, `extract_text_from_bytes()` | Uploaded PDFs, images, text files (S3/MinIO) |

## 📋 FounderEvent Schema

All workers emit events in this normalized format:

```json
{
  "id": "email-42",
  "source": "email",
  "event_type": "reflection",
  "text": "Today I realized we need to rethink our onboarding flow...",
  "context": {
    "subject": "Weekly thoughts",
    "from": "founder@example.com",
    "tags": ["product"],
    "priority": "HIGH"
  },
  "created_at": "2026-03-13T10:30:00.000000"
}
```

Supported `source` values: `email`, `voice`, `slack`.
Supported `event_type` values: `reflection`, `decision_record`, `weekly_review`.

## ⚙️ Configuration

| Variable | Used By | Description |
|---|---|---|
| `IMAP_SERVER` | Email Ingestion | IMAP server hostname (default: `imap.gmail.com`) |
| `EMAIL_ADDRESS` | Email Ingestion | Email account to poll |
| `EMAIL_PASSWORD` | Email Ingestion | Email account password or app password |
| `OPENAI_API_KEY` | Voice Transcription | OpenAI API key for Whisper transcription |
| `SLACK_SIGNING_SECRET` | Slack | Slack app signing secret for webhook verification |
| `GOOGLE_CLIENT_ID` | Google Workspace | OAuth 2.0 client ID |
| `GOOGLE_CLIENT_SECRET` | Google Workspace | OAuth 2.0 client secret |
| `S3_ENDPOINT` | OCR | S3-compatible endpoint (default: `http://localhost:9000`) |
| `S3_ACCESS_KEY` | OCR | S3 access key (default: `seedlings`) |
| `S3_SECRET_KEY` | OCR | S3 secret key |
| `S3_BUCKET` | OCR | S3 bucket name (default: `seedlings-uploads`) |
| `REDIS_URL` | Email Ingestion, Voice Transcription | Redis connection URL (default: `redis://localhost:6379`) |

## 🚀 Running Workers

```bash
# Email Ingestion (async polling)
IMAP_SERVER=imap.gmail.com EMAIL_ADDRESS=you@example.com EMAIL_PASSWORD=secret \
  python -m workers.email_ingestion.worker

# Voice Transcription
OPENAI_API_KEY=sk-... python -m workers.voice_transcription.worker

# Slack (FastAPI server)
uvicorn workers.slack.worker:app --host 0.0.0.0 --port 8001

# Google Workspace (imported as a module by the backend)
# Usage: from workers.google_workspace.worker import google_worker

# OCR (imported as a module by the backend)
# Usage: from workers.ocr.worker import ocr_worker
```

## 📚 Related Documentation

- [Root README](../README.md) — Project overview and architecture
- [Backend README](../backend/README.md) — API server and downstream processing

"""OCR Worker — Document upload and text extraction.

Handles S3-compatible uploads (MinIO for local dev) and
runs OCR on uploaded images/documents.

Extraction priority:
1. PDF  → pypdf  (no external binary needed)
2. Image → Tesseract via pytesseract (if installed)
3. Image → PIL-based fallback (returns notice)
"""

import io
import logging
import os
import uuid
from typing import Optional

logger = logging.getLogger(__name__)

# MIME types considered images
_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/tiff", "image/bmp", "image/webp"}
_PDF_TYPES = {"application/pdf"}


class OCRWorker:
    """Processes uploaded documents and extracts text via OCR."""

    def __init__(self):
        self._s3_client = None
        self._s3_endpoint = os.getenv("S3_ENDPOINT", "http://localhost:9000")
        self._s3_access_key = os.getenv("S3_ACCESS_KEY", "seedlings")
        self._s3_secret_key = os.getenv("S3_SECRET_KEY", "seedlings_dev_2024")
        self._s3_bucket = os.getenv("S3_BUCKET", "seedlings-uploads")

    def _get_s3_client(self):
        if self._s3_client is None:
            try:
                import boto3
                self._s3_client = boto3.client(
                    "s3",
                    endpoint_url=self._s3_endpoint,
                    aws_access_key_id=self._s3_access_key,
                    aws_secret_access_key=self._s3_secret_key,
                )
            except Exception as e:
                logger.warning(f"S3 client not available: {e}")
        return self._s3_client

    async def upload_file(
        self,
        file_data: bytes,
        filename: str,
        content_type: str,
    ) -> Optional[str]:
        """Upload a file to S3-compatible storage. Returns object key if successful."""
        object_key = f"uploads/{uuid.uuid4()}/{filename}"

        client = self._get_s3_client()
        if client is None:
            logger.warning("S3 upload skipped — client not available")
            return object_key  # Return key anyway so extraction can proceed from bytes

        try:
            client.put_object(
                Bucket=self._s3_bucket,
                Key=object_key,
                Body=file_data,
                ContentType=content_type,
            )
            logger.info(f"Uploaded {filename} to {object_key}")
            return object_key
        except Exception as e:
            logger.error(f"Upload failed: {e}")
            return None

    async def extract_text_from_bytes(
        self,
        file_data: bytes,
        content_type: str,
        filename: str = "",
    ) -> str:
        """Extract text directly from file bytes — no S3 round-trip needed.

        This is the preferred entry point when the caller still has the raw bytes.
        """
        ct = (content_type or "").lower()
        name = (filename or "").lower()

        if ct in _PDF_TYPES or name.endswith(".pdf"):
            return self._extract_pdf(file_data)

        if ct in _IMAGE_TYPES or any(name.endswith(ext) for ext in (".jpg", ".jpeg", ".png", ".tiff", ".bmp", ".gif", ".webp")):
            return self._extract_image(file_data)

        # Plain text files
        if ct.startswith("text/") or name.endswith(".txt"):
            try:
                return file_data.decode("utf-8", errors="replace")
            except Exception:
                pass

        logger.warning(f"Unsupported content type for extraction: {content_type}")
        return f"[Unsupported file type: {content_type}. Supported: PDF, images (JPEG/PNG/TIFF), plain text.]"

    async def extract_text(
        self,
        object_key: str,
        content_type: str = "",
    ) -> str:
        """Extract text from a file already stored in S3."""
        client = self._get_s3_client()
        if client is None:
            return "[OCR unavailable — S3 not configured]"

        try:
            response = client.get_object(Bucket=self._s3_bucket, Key=object_key)
            file_data = response["Body"].read()
            # Infer content type from key extension if not provided
            if not content_type:
                content_type = self._guess_content_type(object_key)
            return await self.extract_text_from_bytes(file_data, content_type, object_key)
        except Exception as e:
            logger.error(f"S3 download for OCR failed ({object_key}): {e}")
            return f"[OCR failed: could not retrieve file from storage]"

    # ── Private extraction methods ────────────────────────────────────────────

    def _extract_pdf(self, file_data: bytes) -> str:
        """Extract text from PDF using pypdf."""
        try:
            import pypdf

            reader = pypdf.PdfReader(io.BytesIO(file_data))
            pages_text = []
            for i, page in enumerate(reader.pages):
                page_text = page.extract_text() or ""
                if page_text.strip():
                    pages_text.append(f"[Page {i + 1}]\n{page_text}")

            if not pages_text:
                return "[PDF contains no extractable text — it may be a scanned image. Try uploading a higher quality scan.]"

            result = "\n\n".join(pages_text)
            logger.info(f"PDF extraction: {len(reader.pages)} pages, {len(result)} chars")
            return result

        except ImportError:
            logger.error("pypdf not installed — run: pip install pypdf")
            return "[PDF extraction unavailable — pypdf not installed]"
        except Exception as e:
            logger.error(f"PDF extraction failed: {e}")
            return f"[PDF extraction failed: {e}]"

    def _extract_image(self, file_data: bytes) -> str:
        """Extract text from an image using Tesseract (pytesseract) if available,
        otherwise return a clear message."""
        try:
            import pytesseract
            from PIL import Image

            image = Image.open(io.BytesIO(file_data))
            # Convert to RGB if needed (handles RGBA PNGs etc.)
            if image.mode not in ("RGB", "L"):
                image = image.convert("RGB")

            text = pytesseract.image_to_string(image)
            if not text.strip():
                return "[Image OCR produced no text — the image may be low resolution or non-text.]"

            logger.info(f"Tesseract OCR extracted {len(text)} chars")
            return text

        except ImportError:
            return (
                "[Image OCR requires Tesseract. Install it with:\n"
                "  macOS:  brew install tesseract\n"
                "  Ubuntu: sudo apt install tesseract-ocr\n"
                "Then: pip install pytesseract pillow]"
            )
        except Exception as e:
            logger.error(f"Image OCR failed: {e}")
            return f"[Image OCR failed: {e}]"

    @staticmethod
    def _guess_content_type(key: str) -> str:
        """Guess MIME type from file extension in object key."""
        key_lower = key.lower()
        if key_lower.endswith(".pdf"):
            return "application/pdf"
        if key_lower.endswith((".jpg", ".jpeg")):
            return "image/jpeg"
        if key_lower.endswith(".png"):
            return "image/png"
        if key_lower.endswith(".tiff"):
            return "image/tiff"
        if key_lower.endswith(".txt"):
            return "text/plain"
        return "application/octet-stream"


# Singleton
ocr_worker = OCRWorker()

from __future__ import annotations

import io
from pathlib import Path

from app.core.config import Settings


class DocumentService:
    ALLOWED_TEXT_SUFFIXES = {".txt", ".md"}

    def __init__(self, settings: Settings):
        self.settings = settings

    def extract(self, filename: str, content_type: str | None, data: bytes) -> str:
        if not data:
            raise ValueError("Uploaded document is empty")
        # A conservative byte bound protects this local demo from accidental huge uploads.
        if len(data) > self.settings.max_document_chars * 5:
            raise ValueError("Uploaded document is too large for this demo")
        suffix = Path(filename or "").suffix.casefold()
        if suffix == ".pdf" or content_type == "application/pdf":
            text = self._extract_pdf(data)
        elif suffix in self.ALLOWED_TEXT_SUFFIXES or (content_type or "").startswith("text/"):
            try:
                text = data.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise ValueError("Text documents must use UTF-8 encoding") from exc
        else:
            raise ValueError("Only PDF, TXT and Markdown documents are supported")
        cleaned = text.strip()[: self.settings.max_document_chars]
        if len(cleaned) < 20:
            raise ValueError("The document did not contain enough extractable text")
        return cleaned

    @staticmethod
    def _extract_pdf(data: bytes) -> str:
        try:
            from pypdf import PdfReader

            reader = PdfReader(io.BytesIO(data))
            pages = [(page.extract_text() or "").strip() for page in reader.pages]
            return "\n\n".join(item for item in pages if item)
        except Exception as exc:
            raise ValueError("PDF text extraction failed; scanned PDFs require OCR") from exc

from io import BytesIO
import logging

from pypdf import PdfReader


logger = logging.getLogger(__name__)


def extract_text_from_pdf_bytes(file_bytes: bytes) -> str:
    logger.info("PDF text extraction started size_bytes=%d", len(file_bytes))
    reader = PdfReader(BytesIO(file_bytes))
    page_text: list[str] = []

    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if text.strip():
            page_text.append(text)
            logger.debug("PDF page extracted page=%d chars=%d", page_number, len(text))

    extracted_text = "\n\n".join(page_text).strip()
    logger.info(
        "PDF text extraction completed pages=%d pages_with_text=%d chars=%d",
        len(reader.pages),
        len(page_text),
        len(extracted_text),
    )
    return extracted_text


def make_protocol_excerpt(protocol_text: str, max_chars: int = 420) -> str:
    normalized = " ".join(protocol_text.split())

    if len(normalized) <= max_chars:
        return normalized

    return f"{normalized[:max_chars].rstrip()}..."

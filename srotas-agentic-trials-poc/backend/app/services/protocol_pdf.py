from io import BytesIO

from pypdf import PdfReader


def extract_text_from_pdf_bytes(file_bytes: bytes) -> str:
    reader = PdfReader(BytesIO(file_bytes))
    page_text: list[str] = []

    for page in reader.pages:
        text = page.extract_text() or ""
        if text.strip():
            page_text.append(text)

    return "\n\n".join(page_text).strip()


def make_protocol_excerpt(protocol_text: str, max_chars: int = 420) -> str:
    normalized = " ".join(protocol_text.split())

    if len(normalized) <= max_chars:
        return normalized

    return f"{normalized[:max_chars].rstrip()}..."

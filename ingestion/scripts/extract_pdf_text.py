"""Extract text from PDFs using pdfplumber."""

import io

import pdfplumber


def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> list[str]:
    """Extract text from in-memory PDF bytes, returning a list of strings (one per page)."""
    pages_text = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            pages_text.append(text)
    return pages_text

from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader


def extract_pdf_text(file_path: str | Path) -> tuple[str, float]:
    """
    Extract text from a normal text-based PDF.

    Returns:
        (extracted_text, confidence)

    Confidence is a heuristic extraction-quality signal.
    It is not an NLP/entity confidence score.
    """
    path = Path(file_path)

    reader = PdfReader(str(path))

    pages: list[str] = []

    for page in reader.pages:
        text = page.extract_text() or ""

        if text.strip():
            pages.append(text.strip())

    extracted_text = "\n\n".join(pages).strip()

    if not extracted_text:
        return "", 0.0

    # Simple prototype heuristic.
    # OCR can later be used when a PDF has no extractable text.
    confidence = 0.95

    return extracted_text, confidence
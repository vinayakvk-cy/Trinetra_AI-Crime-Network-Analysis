from __future__ import annotations

from pathlib import Path

from PIL import Image
import pytesseract


# Explicit Windows Tesseract installation path.
# This avoids depending on the process PATH.
TESSERACT_PATH = Path(
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

if TESSERACT_PATH.exists():
    pytesseract.pytesseract.tesseract_cmd = str(TESSERACT_PATH)


def extract_image_text(
    file_path: str | Path,
) -> tuple[str, float]:
    """
    Extract text from an image using Tesseract OCR.

    Returns:
        (extracted_text, confidence)
    """

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(
            f"Image does not exist: {path}"
        )

    if not TESSERACT_PATH.exists():
        raise FileNotFoundError(
            f"Tesseract executable not found: {TESSERACT_PATH}"
        )

    image = Image.open(path)

    text = pytesseract.image_to_string(image).strip()

    if not text:
        return "", 0.0

    # Prototype heuristic.
    # This is extraction confidence, not entity confidence.
    confidence = 0.80

    return text, confidence
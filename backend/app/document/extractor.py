from __future__ import annotations

import mimetypes
from dataclasses import dataclass
from pathlib import Path

from app.document.docx_extractor import extract_docx_text
from app.document.image_ocr import extract_image_text
from app.document.pdf_extractor import extract_pdf_text


@dataclass
class DocumentExtractionResult:
    file_name: str
    mime_type: str
    extracted_text: str
    extraction_confidence: float
    extraction_method: str
    page_count: int | None = None

    def to_dict(self) -> dict:
        return {
            "file_name": self.file_name,
            "mime_type": self.mime_type,
            "extracted_text": self.extracted_text,
            "extraction_confidence": self.extraction_confidence,
            "extraction_method": self.extraction_method,
            "page_count": self.page_count,
        }


class DocumentExtractor:
    """
    Unified document text extraction service.

    Supported prototype formats:
        PDF
        DOCX
        PNG
        JPG
        JPEG
    """

    IMAGE_EXTENSIONS = {
        ".png",
        ".jpg",
        ".jpeg",
        ".webp",
        ".tif",
        ".tiff",
        ".bmp",
    }

    def extract(self, file_path: str | Path) -> DocumentExtractionResult:
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(
                f"Document does not exist: {path}"
            )

        extension = path.suffix.lower()

        mime_type, _ = mimetypes.guess_type(path.name)

        if not mime_type:
            mime_type = "application/octet-stream"

        if extension == ".pdf":
            text, confidence = extract_pdf_text(path)

            return DocumentExtractionResult(
                file_name=path.name,
                mime_type="application/pdf",
                extracted_text=text,
                extraction_confidence=confidence,
                extraction_method="pdf_text_extraction",
            )

        if extension == ".docx":
            text, confidence = extract_docx_text(path)

            return DocumentExtractionResult(
                file_name=path.name,
                mime_type=(
                    "application/vnd.openxmlformats-"
                    "officedocument.wordprocessingml.document"
                ),
                extracted_text=text,
                extraction_confidence=confidence,
                extraction_method="docx_text_extraction",
            )

        if extension in self.IMAGE_EXTENSIONS:
            text, confidence = extract_image_text(path)

            return DocumentExtractionResult(
                file_name=path.name,
                mime_type=mime_type,
                extracted_text=text,
                extraction_confidence=confidence,
                extraction_method="tesseract_ocr",
            )

        raise ValueError(
            f"Unsupported document type: {extension}"
        )
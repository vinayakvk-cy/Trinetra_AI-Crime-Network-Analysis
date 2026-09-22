from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ============================================================
# EXCEPTIONS
# ============================================================


class ParserError(Exception):
    """
    Base exception for ingestion parser errors.
    """

    pass


class UnsupportedFileTypeError(ParserError):
    """
    Raised when the parser receives an unsupported file type.
    """

    pass


class FileParsingError(ParserError):
    """
    Raised when a supported file cannot be parsed.
    """

    pass


# ============================================================
# PARSED DATA
# ============================================================


@dataclass
class ParsedData:
    """
    Common representation returned by the parser.
    """

    source_file: str

    file_type: str

    records: list[dict[str, Any]] = field(
        default_factory=list
    )

    text: str | None = None

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    @property
    def record_count(self) -> int:
        """
        Return the number of structured records.
        """

        return len(self.records)


# ============================================================
# GENERIC PARSER
# ============================================================


class GenericParser:
    """
    Generic parser for TRINETRA ingestion.

    Supported file types:

        CSV
        JSON
        TXT
        XLSX
        XLS
        PDF
    """

    SUPPORTED_EXTENSIONS = {
        ".csv",
        ".json",
        ".txt",
        ".xlsx",
        ".xls",
        ".pdf",
    }

    # ========================================================
    # PUBLIC API
    # ========================================================

    def parse(
        self,
        file_path: str | Path,
    ) -> ParsedData:
        """
        Parse a file based on its extension.
        """

        path = Path(file_path)

        self._validate_file(path)

        extension = path.suffix.lower()

        if extension == ".csv":
            return self._parse_csv(path)

        if extension == ".json":
            return self._parse_json(path)

        if extension == ".txt":
            return self._parse_txt(path)

        if extension in {".xlsx", ".xls"}:
            return self._parse_excel(path)

        if extension == ".pdf":
            return self._parse_pdf(path)

        raise UnsupportedFileTypeError(
            f"Unsupported file type: {extension}"
        )

    # ========================================================
    # VALIDATE FILE
    # ========================================================

    def _validate_file(
        self,
        path: Path,
    ) -> None:
        """
        Validate that the input file exists and is supported.
        """

        if not path.exists():
            raise FileNotFoundError(
                f"Input file does not exist: {path}"
            )

        if not path.is_file():
            raise ParserError(
                f"Input path is not a file: {path}"
            )

        extension = path.suffix.lower()

        if extension not in self.SUPPORTED_EXTENSIONS:
            supported = ", ".join(
                sorted(self.SUPPORTED_EXTENSIONS)
            )

            raise UnsupportedFileTypeError(
                f"Unsupported file type: {extension}. "
                f"Supported types: {supported}"
            )

    # ========================================================
    # CSV
    # ========================================================

    def _parse_csv(
        self,
        path: Path,
    ) -> ParsedData:
        """
        Parse a CSV file into dictionaries.
        """

        try:
            records: list[dict[str, Any]] = []

            with path.open(
                "r",
                encoding="utf-8-sig",
                newline="",
            ) as file:

                reader = csv.DictReader(file)

                if reader.fieldnames is None:
                    raise FileParsingError(
                        f"CSV file has no header: {path}"
                    )

                columns = [
                    str(column).strip()
                    for column in reader.fieldnames
                    if column is not None
                ]

                for row in reader:
                    cleaned_row: dict[str, Any] = {}

                    for key, value in row.items():

                        if key is None:
                            continue

                        cleaned_key = str(key).strip()

                        cleaned_row[
                            cleaned_key
                        ] = self._clean_value(value)

                    records.append(cleaned_row)

            return ParsedData(
                source_file=str(path),
                file_type=".csv",
                records=records,
                metadata={
                    "columns": columns,
                    "record_count": len(records),
                },
            )

        except FileParsingError:
            raise

        except Exception as exc:
            raise FileParsingError(
                f"Failed to parse CSV file '{path}': {exc}"
            ) from exc

    # ========================================================
    # JSON
    # ========================================================

    def _parse_json(
        self,
        path: Path,
    ) -> ParsedData:
        """
        Parse JSON data.

        Supported structures:

            [
                {...},
                {...}
            ]

        or:

            {
                "records": [
                    {...},
                    {...}
                ]
            }

        or:

            {
                "name": "...",
                "phone": "..."
            }
        """

        try:
            with path.open(
                "r",
                encoding="utf-8",
            ) as file:

                data = json.load(file)

        except Exception as exc:
            raise FileParsingError(
                f"Failed to read JSON file '{path}': {exc}"
            ) from exc

        records: list[dict[str, Any]]

        if isinstance(data, list):

            records = [
                item
                for item in data
                if isinstance(item, dict)
            ]

        elif isinstance(data, dict):

            raw_records = data.get("records")

            if isinstance(raw_records, list):

                records = [
                    item
                    for item in raw_records
                    if isinstance(item, dict)
                ]

            else:

                records = [data]

        else:

            raise FileParsingError(
                f"Unsupported JSON structure in '{path}'."
            )

        return ParsedData(
            source_file=str(path),
            file_type=".json",
            records=records,
            metadata={
                "record_count": len(records),
            },
        )

    # ========================================================
    # TXT
    # ========================================================

    def _parse_txt(
        self,
        path: Path,
    ) -> ParsedData:
        """
        Parse a plain text file.

        Text is preserved for the NLP pipeline.
        """

        try:
            text = path.read_text(
                encoding="utf-8"
            )

        except UnicodeDecodeError as exc:
            raise FileParsingError(
                f"Unable to decode text file '{path}' "
                f"as UTF-8: {exc}"
            ) from exc

        except Exception as exc:
            raise FileParsingError(
                f"Failed to read TXT file '{path}': {exc}"
            ) from exc

        return ParsedData(
            source_file=str(path),
            file_type=".txt",
            records=[],
            text=text,
            metadata={
                "character_count": len(text),
                "line_count": len(text.splitlines()),
            },
        )

    # ========================================================
    # EXCEL
    # ========================================================

    def _parse_excel(
        self,
        path: Path,
    ) -> ParsedData:
        """
        Parse the first worksheet of an Excel file.
        """

        try:
            import pandas as pd

        except ImportError as exc:
            raise FileParsingError(
                "pandas is required to parse Excel files."
            ) from exc

        try:
            dataframe = pd.read_excel(path)

            dataframe = dataframe.where(
                dataframe.notna(),
                None,
            )

            records = dataframe.to_dict(
                orient="records"
            )

            return ParsedData(
                source_file=str(path),
                file_type=path.suffix.lower(),
                records=records,
                metadata={
                    "columns": [
                        str(column)
                        for column in dataframe.columns
                    ],
                    "record_count": len(records),
                },
            )

        except Exception as exc:
            raise FileParsingError(
                f"Failed to parse Excel file '{path}': {exc}"
            ) from exc

    # ========================================================
    # PDF
    # ========================================================

    def _parse_pdf(
        self,
        path: Path,
    ) -> ParsedData:
        """
        Extract text from a PDF.

        Scanned/image-only PDFs may require OCR.
        """

        try:
            import pypdf

        except ImportError as exc:
            raise FileParsingError(
                "pypdf is required to parse PDF files."
            ) from exc

        try:
            reader = pypdf.PdfReader(
                str(path)
            )

            pages: list[str] = []

            for page in reader.pages:

                page_text = page.extract_text()

                if page_text:
                    pages.append(page_text)

            text = "\n".join(pages)

            return ParsedData(
                source_file=str(path),
                file_type=".pdf",
                records=[],
                text=text,
                metadata={
                    "page_count": len(reader.pages),
                    "extracted_character_count": len(text),
                },
            )

        except Exception as exc:
            raise FileParsingError(
                f"Failed to parse PDF file '{path}': {exc}"
            ) from exc

    # ========================================================
    # VALUE CLEANING
    # ========================================================

    @staticmethod
    def _clean_value(
        value: Any,
    ) -> Any:
        """
        Clean values returned by CSV parsing.
        """

        if value is None:
            return None

        if isinstance(value, str):

            value = value.strip()

            if value == "":
                return None

        return value


# ============================================================
# PARSE RECORD
# ============================================================


def parse_record(
    record: Any,
) -> dict[str, Any]:
    """
    Normalize a single ingestion record.

    This function is provided for routes and ingestion
    services that receive an already-parsed record.

    Parameters
    ----------
    record:
        A dictionary containing one structured record.

    Returns
    -------
    dict[str, Any]
        Cleaned record.

    Raises
    ------
    ParserError
        If the supplied record is not a dictionary.
    """

    if not isinstance(record, dict):
        raise ParserError(
            "Record must be a dictionary."
        )

    cleaned_record: dict[str, Any] = {}

    for key, value in record.items():

        if key is None:
            continue

        cleaned_key = str(key).strip()

        if not cleaned_key:
            continue

        cleaned_record[
            cleaned_key
        ] = GenericParser._clean_value(value)

    return cleaned_record


# ============================================================
# PARSE FILE
# ============================================================


def parse_file(
    file_path: str | Path,
) -> ParsedData:
    """
    Convenience function for parsing an input file.
    """

    parser = GenericParser()

    return parser.parse(file_path)
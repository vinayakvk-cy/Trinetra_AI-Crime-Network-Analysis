"""
TRINETRA Data Source Ingestion
==============================

Source-specific ingestion modules.

Each module is responsible for interpreting one type of
intelligence data while using the common ingestion pipeline:

    parser.py
        ↓
    validators.py
        ↓
    normalizer.py
        ↓
    source-specific processor
        ↓
    NLP / Entity Linking
        ↓
    Graph
"""

__all__ = [
    "fir",
    "cdr",
    "transactions",
    "vehicles",
    "social_media",
    "jail_records",
    "gps",
    "forensic",
    "postmortem",
]
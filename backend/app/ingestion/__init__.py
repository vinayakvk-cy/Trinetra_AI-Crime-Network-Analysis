"""
TRINETRA Data Ingestion Package
================================

Responsible for importing and preparing data from different
intelligence sources.

Supported sources include:

    - FIR
    - CDR
    - Transactions
    - Vehicles
    - Social Media
    - Jail Records
    - GPS
    - Forensic Data
    - Post-mortem Reports

General pipeline:

    Raw Data
        ↓
    Parser
        ↓
    Validator
        ↓
    Normalizer
        ↓
    Structured Records
        ↓
    NLP / Entity Linking
        ↓
    Graph
        ↓
    Analytics
"""

__all__ = [
    "parser",
    "normalizer",
    "validators",
]
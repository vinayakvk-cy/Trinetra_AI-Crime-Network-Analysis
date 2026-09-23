# TRINETRA

## AI-Powered Investigative Intelligence & Crime Network Analysis Platform

TRINETRA (INFERRA-AI) is an API-driven investigative intelligence platform designed to transform fragmented investigation records into a connected, case-centric intelligence network.

The platform combines document processing, NLP/entity extraction, relationship extraction, SQL persistence, Neo4j knowledge graphs, analytics, AI-assisted investigation, investigation management, and report generation into a single workflow.

> **Core idea:**  
> **Case → Evidence → Extraction/OCR → NLP/NER → Relationship Extraction → SQL → Neo4j → Graph → Analytics → AI Assistant → Investigation → Reports**

---

## Features

### 1. Case Management

TRINETRA provides a centralized case-management workflow for investigative activities.

Each case can contain:

- Case number
- Case title
- Description
- Priority
- Status
- Evidence
- Entities
- Relationships
- Investigations
- Analytics
- Reports

---

### 2. Evidence Management

Investigators can ingest and manage investigation evidence such as:

- Business records
- Financial records
- Investigation documents
- PDF documents
- DOCX documents
- Other supported evidence sources

Evidence is associated with the relevant case and can be processed through the extraction pipeline.

---

### 3. Document Extraction and OCR

The platform supports document-processing workflows for extracting usable information from investigative documents.

The extraction pipeline prepares unstructured evidence for downstream NLP and graph processing.

The architecture supports OCR-based processing for documents where text is not directly available.

---

### 4. NLP and Named Entity Extraction

TRINETRA extracts structured entities from investigation evidence.

Examples include:

- Persons
- Organizations
- Banks
- Locations
- Vehicles
- Phones
- Devices
- Cases
- Evidence identifiers
- Other investigative entities

The NLP layer also performs normalization and confidence-based extraction.

---

### 5. Relationship Extraction

Extracted entities are connected through relationships detected from the evidence.

Examples include:

- `WORKS_FOR`
- `KNOWS`
- `CONTACTED`
- `TRANSFERRED_TO`
- `ASSOCIATED_WITH`
- `PERSON_USED_PHONE`
- `PERSON_USED_DEVICE`
- `PERSON_OWNS_VEHICLE`
- `PERSON_AT_LOCATION`
- `DEVICE_AT_LOCATION`
- `PHONE_AT_LOCATION`
- `PERSON_IN_CASE`
- `EVIDENCE_RELATED_CASE`

These relationships form the basis of the investigative knowledge graph.

---

### 6. SQL Database

Structured investigation information is persisted using SQLAlchemy and SQLite.

The relational database stores information such as:

- Cases
- Evidence
- Entities
- Entity sources
- Relationships
- Investigations
- Investigation metadata
- Reports
- Analytics-related data

---

### 7. Neo4j Knowledge Graph

TRINETRA uses Neo4j to represent investigative entities and their relationships as a graph.

The graph allows investigators to understand connections between:

- People
- Organizations
- Banks
- Evidence
- Cases
- Investigations
- Other entities

This makes complex relationships easier to explore than isolated database records.

---

### 8. Investigation Graph

The frontend provides an interactive investigation graph that visualizes connected entities and relationships.

For example:

                    Cedar Bank
                        |
                        |
                  transferred_to
                        |
                        |
                    Arjun Rao
                        |
                     works_for
                        |
                        |
              Blue Harbor Supplies
                        |
                  associated evidence
                   /             \
                EV-001          EV-002


The graph is generated from backend/database data rather than being hardcoded into the frontend.

9. Analytics

TRINETRA provides graph-based investigative analytics.

Current analytics include:

Graph connectivity
Entity relationships
Relationship diversity
Case-level graph statistics
Risk indicators
Investigation-level analysis

Analytics are derived from the underlying investigation data.

10. Risk Analysis

The platform provides analytical risk indicators based on graph-derived signals.

For example, the system can consider:

Number of entities connected to a case
Relationship diversity
Other graph-derived investigation signals

Risk scores are intended as analytical prioritization signals.

They are not determinations of guilt, criminal responsibility, or legal conclusions.

11. AI Assistant

TRINETRA includes an AI-assisted investigation interface.

The assistant can be used to summarize and interpret investigation information.

Example:

"Summarize the key entities and relationships in this investigation."

The AI Assistant is intended to help investigators understand connected information without replacing human investigative judgment.

12. Investigation Management

The platform separates cases from investigations.

Investigations can contain:

Investigation number
Investigation title
Objective
Investigator
Investigation unit
Status
Outcome
Findings
Conclusion
Risk information
Graph references

This provides a structured workflow for managing investigative activities.

13. Report Generation

TRINETRA supports investigation report generation.

Current report functionality includes:

Report preview
Intelligence reports
Documentary/investigative reports
Evidence inclusion
Entity inclusion
Relationship inclusion
Analytics inclusion
Timeline inclusion
Investigation summaries

Report functionality is connected to the investigation data rather than relying on static demo content.

14. Command Center

The Command Center provides a high-level view of the investigation platform.

It connects the major workflows:
                  Cases
                  ↓
                  Evidence
                  ↓
                  Extraction
                  ↓
                  Graph
                  ↓
                  Analytics
                  ↓
                  AI Assistant
                  ↓
                  Investigations
                  ↓
                  Reports

System Architecture
                                      TRINETRA
                                        |
                          +-------------+-------------+
                          |                           |
                       Frontend                    Backend
                       React/Vite                  FastAPI
                          |                           |
                          |                  +--------+--------+
                          |                  |                 |
                          |               SQLAlchemy        NLP/AI
                          |                  |                 |
                          |               SQLite          Entity/Relation
                          |                                    Extraction
                          |                                      |
                          |                              +-------+-------+
                          |                              |
                          |                           Neo4j
                          |                              |
                          |                       Knowledge Graph
                          |                              |
                          |                    +---------+---------+
                          |                    |                   |
                          |                Analytics         Investigation
                          |                    |                   |
                          |                    +---------+---------+
                          |                              |
                          +-------------------------- Reports

Data Processing Pipeline

TRINETRA processes investigative information through the following pipeline:
  1. Case Creation
         ↓
  2. Evidence Ingestion
         ↓
  3. Document Extraction / OCR
         ↓
  4. NLP / Entity Extraction
         ↓
  5. Relationship Extraction
         ↓
  6. SQL Persistence
         ↓
  7. Neo4j Graph Construction
         ↓
  8. Graph Analytics
         ↓
  9. Risk Analysis
         ↓
  10. AI-Assisted Investigation
         ↓
  11. Investigation Management
         ↓
  12. Report Generation

Technology Stack
Backend
Python
FastAPI
SQLAlchemy
SQLite
Neo4j
Python NLP components
Document processing
OCR
Report generation
Frontend
React
Vite
Axios
JavaScript
JSX
Database
SQLite
Neo4j

Project Structure:
  Trinetra_demo/
  │
  ├── backend/
  │   ├── app/
  │   │   ├── ai/
  │   │   ├── analytics/
  │   │   ├── api/
  │   │   │   └── routes/
  │   │   ├── document/
  │   │   ├── graph/
  │   │   ├── nlp/
  │   │   ├── reports/
  │   │   └── main.py
  │   │
  │   ├── trinetra.db
  │   ├── .env
  │   └── .venv/
  │
  ├── frontend/
  │   ├── src/
  │   │   ├── pages/
  │   │   ├── services/
  │   │   ├── components/
  │   │   └── App.jsx
  │   ├── package.json
  │   └── vite.config.js
  │
  ├── .gitignore
  └── README.md
  
Frontend Modules

The frontend currently contains the following major modules:

Command Center
Evidence
Investigation Graph
Analytics
AI Assistant
Cases
Investigations
Workspace
Reports
API

The backend is implemented using FastAPI.

Default local backend:
http://127.0.0.1:8000

Frontend:
http://localhost:5174

Health Check
GET /health

Graph Health
GET /graph/health

Cases
GET /cases

Investigations
GET /investigations

Evidence
GET /evidence

Risk Analysis
POST /analytics/risk

Graph Connectivity
GET /analytics/graph/connectivity

Reports
GET /reports/types
POST /reports/preview
POST /reports/intelligence
POST /reports/documentary

Local Development
Backend
Open PowerShell:
Activate the virtual environment if required:
.\.venv\Scripts\Activate.ps1

Start FastAPI:
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload

Backend will be available at:
http://127.0.0.1:8000

Backend Health Test
Invoke-RestMethod http://127.0.0.1:8000/health

Graph health:
Invoke-RestMethod http://127.0.0.1:8000/graph/health

Frontend
Open another PowerShell terminal:
Install dependencies if necessary:
npm install
Start the frontend:
npm run dev
Frontend is currently configured to run on:
http://localhost:5174

Neo4j Configuration
The backend uses environment variables for Neo4j configuration.

Example:

NEO4J_URI=bolt://127.0.0.1:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=YOUR_PASSWORD
NEO4J_DATABASE=neo4j

Never commit .env or database credentials to GitHub.

Demonstration Dataset

The primary demonstration case is:

Case:
TRI-TEST-001

Title:
Harbor Procurement Review

Entities include:

Arjun Rao
Blue Harbor Supplies
Cedar Bank

Evidence:

TRI-TEST-001-EV-001
TRI-TEST-001-EV-002

Investigation:

TRI-TEST-001-INV-001

Investigation title:

Harbor Procurement Network Investigation
Example Investigation Flow

A typical investigation can follow this workflow:

      Create Case
        ↓
    Upload Evidence
        ↓
    Extract Document Text
        ↓
    Extract Entities
        ↓
    Extract Relationships
        ↓
    Store Structured Data
        ↓
    Build Neo4j Graph
        ↓
    Explore Connections
        ↓
    Run Analytics
        ↓
    Review Risk Indicators
        ↓
    Ask AI Assistant
        ↓
    Create Investigation
        ↓
    Generate Report

Design Principles
TRINETRA follows several important architectural principles.
API-Driven
The frontend should reflect real backend/database state.
Case-Centric
Investigation information is organized around cases and investigations.
Graph-Based
Neo4j is used to model relationships between investigative entities.
Explainable
Analytics should expose the underlying signals and relationships used to produce results.
Modular

The system separates:
API
NLP
document processing
graph processing
analytics
AI
reporting
frontend services
Reproducible

The project is designed to be locally deployable and inspectable for academic and research purposes.

Security Considerations
The platform is designed with security considerations including:
API-based access
authentication/authorization architecture
protected environment variables
database separation
controlled evidence access
investigation-level organization
audit-oriented architecture

Production deployment should additionally use appropriate:
HTTPS
secret management
authentication
authorization
database security
logging
monitoring
network controls
Future Scope

Potential future enhancements include:
Multilingual OCR
Multilingual NLP and NER
Advanced entity resolution
Advanced graph anomaly detection
More external investigative data integrations
CDR integration
FIR integration
Vehicle information integration
Jail/prison record integration
Surveillance data integration
Intelligence report integration
Post-mortem report integration
Advanced timeline analysis
Similar-case analysis
Advanced AI investigation assistance
Zero-trust security architecture
Controlled case/file sharing
Evidence integrity verification
Blockchain-based chain-of-custody extensions
Scalable production deployment
Distributed database architecture

Blockchain-based evidence integrity and some advanced security/multilingual capabilities are considered future/extension areas unless explicitly implemented in the current source code.

Research Areas
TRINETRA is related to research in:
Artificial Intelligence
Natural Language Processing
Named Entity Recognition
Knowledge Graphs
Graph Analytics
Graph-based Anomaly Detection
Digital Forensics
Evidence Management
Financial Fraud Detection
Investigative Intelligence
AI-assisted Decision Support
Project Contribution

TRINETRA is not intended to compete directly with mature commercial investigation platforms.

Its primary contribution is the implementation of an integrated investigative intelligence architecture that connects:

    Evidence
        +
    NLP
        +
    SQL
        +
    Neo4j
        +
    Graph Analytics
        +
    Risk Analysis
        +
    AI Assistance
        +
    Investigation Management
        +
    Reporting

This makes the project suitable as an academic demonstration of how modern AI, NLP, databases, knowledge graphs and investigative workflows can be combined into a single platform.

USP
TRINETRA converts fragmented investigation records into a connected, case-centric intelligence network while keeping the complete investigation workflow inside one API-driven platform.

Development Status

TRINETRA is an actively developed prototype/academic investigative intelligence platform.

The major end-to-end architecture is operational:

Case
  ↓
Evidence
  ↓
Document Processing
  ↓
NLP
  ↓
Relationships
  ↓
SQL
  ↓
Neo4j
  ↓
Graph
  ↓
Analytics
  ↓
AI Assistant
  ↓
Investigations
  ↓
Reports

Current development focus is on stabilization, data quality, NLP accuracy, testing and demonstration readiness.

Disclaimer
TRINETRA is an investigative intelligence and analytical software project.

Its analytical outputs, including risk indicators, graph relationships and AI-generated summaries, are intended to support investigation and information analysis.

They should not be interpreted as determinations of guilt, criminal responsibility, or legal conclusions.

Human investigators and authorized decision-makers remain responsible for interpreting evidence and making investigative or legal decisions.

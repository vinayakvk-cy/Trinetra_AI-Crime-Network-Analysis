# TRINETRA Demo Readiness

## Purpose

These changes stabilize the investigation-scoped data flow without hard-coding the synthetic case.

## Important data-flow fixes

- Existing evidence detail now returns persisted NLP entities and relationships.
- Neo4j now receives a CASE projection and CASE → entity links during evidence ingestion.
- Investigation creation automatically links existing evidence belonging to its case as relevant.
- Investigation-scoped analytics now receives live case graph node/relationship counts.
- Assistant context retrieval uses Neo4j for the live graph and returns relationship evidence.
- Entity risk and similarity resolve canonical SQL entity IDs before running graph analytics.
- Frontend modules share the active investigation through the active-investigation store.
- Analytics, Assistant, Workspace and Reports refresh from the live investigation registry.

## Existing TRI-TEST-001 data

After replacing the backend/frontend source, restart the backend and run:

```powershell
cd C:\Users\vvkvi\INFERRA-AI\backend
. .\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

Create the demo investigation (case 1):

```powershell
$body = @{
  case_id = 1
  investigation_number = "TRI-TEST-001-INV-001"
  title = "Harbor Procurement Investigation"
  objective = "Review the evidence, entity relationships, and graph signals associated with the Harbor Procurement case."
  investigator = "TRINETRA Analyst"
  investigation_unit = "Intelligence Analysis"
  status = "in_progress"
  outcome = "undetermined"
} | ConvertTo-Json

Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/investigations" `
  -Method Post `
  -ContentType "application/json" `
  -Body $body
```

The investigation-creation endpoint automatically links the case's existing evidence.

Because the current TRI-TEST-001 evidence was ingested before the CASE graph projection was added, re-run ingestion for the two existing records once:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/evidence/1/ingest" -Method Post
Invoke-RestMethod -Uri "http://127.0.0.1:8000/evidence/2/ingest" -Method Post
```

## Validation

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/health"
Invoke-RestMethod "http://127.0.0.1:8000/graph/health"
Invoke-RestMethod "http://127.0.0.1:8000/investigations"
Invoke-RestMethod "http://127.0.0.1:8000/investigation-evidence?investigation_id=1"
Invoke-RestMethod "http://127.0.0.1:8000/evidence/1"
Invoke-RestMethod "http://127.0.0.1:8000/evidence/2"
Invoke-RestMethod "http://127.0.0.1:8000/analytics/investigations/1/summary"
```

For the assistant context:

```powershell
$contextBody = @{
  investigation_id = 1
  limit = 20
} | ConvertTo-Json

Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/assistant/context" `
  -Method Post `
  -ContentType "application/json" `
  -Body $contextBody
```

For a grounded assistant question:

```powershell
$askBody = @{
  investigation_id = 1
  question = "What do we know about Arjun Rao?"
} | ConvertTo-Json

Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/assistant/ask" `
  -Method Post `
  -ContentType "application/json" `
  -Body $askBody
```

Expected demo behavior:

- Evidence detail shows extracted text, entities and relationships.
- Investigation Registry shows the live investigation.
- Analytics shows non-zero live graph metrics and risk/pattern signals.
- AI Assistant returns a grounded answer.
- Workspace loads the selected investigation.
- Reports lists the same investigation and can preview/generate against it.

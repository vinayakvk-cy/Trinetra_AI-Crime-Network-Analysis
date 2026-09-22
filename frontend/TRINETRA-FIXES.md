# TRINETRA Frontend Stability Fixes

This build is based on the uploaded frontend project and keeps the existing visual design/API-driven architecture.

## Fixed

- Corrected the `landing-page.css` import path in `src/App.jsx`.
- Removed hardcoded investigation ID `1` from Assistant, Analytics, Dashboard, and related API defaults.
- Added `src/services/activeInvestigation.js` so the selected investigation is shared across modules using browser storage/events.
- Investigation Registry now loads real cases from `/cases` and uses a case selector instead of asking users to type a numeric case ID.
- Investigation create/update payloads now match the backend investigation schema (`outcome` instead of unsupported `priority`).
- Investigation status/outcome choices now match the backend enum values.
- Creating or explicitly selecting an investigation marks it as the active investigation.
- Assistant and Analytics automatically use the active investigation and refresh it from the live API.
- Dashboard reads the active investigation when one exists and does not call a nonexistent investigation on an empty database.
- Added structured API-error formatting so FastAPI validation-error objects are rendered as text instead of causing React's "Objects are not valid as a React child" crash.
- Removed the hardcoded evidence case ID `1`; Evidence now follows the active case.
- Cases now mark the selected/created case as the active case.
- Removed the Windows `node_modules` directory from this distribution. Run `npm install` on the target machine before starting Vite.

## Run

```powershell
cd frontend
npm install
npm run dev
```

The backend should be running at the API URL configured by `VITE_API_BASE_URL`, or `http://127.0.0.1:8000` by default.

## Recommended test order

1. Cases: create a case.
2. Cases: select the case and upload evidence.
3. Evidence: inspect extraction/ingestion results.
4. Investigations: create an investigation and select it as active.
5. Graph: inspect extracted entities and relationships.
6. Analytics: verify live investigation metrics.
7. Assistant: ask grounded questions about the active investigation.
8. Reports: generate intelligence/documentary reports.

No Aarav/Vertex/HDFC demo records are embedded in the frontend.

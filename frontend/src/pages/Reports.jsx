import { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  BookOpen,
  CheckCircle2,
  ChevronDown,
  ClipboardCheck,
  FileBarChart2,
  FileText,
  LoaderCircle,
  RefreshCw,
  ShieldCheck,
  Sparkles,
} from "lucide-react";

import { listInvestigations } from "../services/investigationsApi";
import {
  generateDocumentaryReport,
  generateIntelligenceReport,
  getReportTypes,
  previewReport,
} from "../services/reportsApi";
import {
  getActiveInvestigationId,
  setActiveInvestigationId,
} from "../services/activeInvestigation";

function unwrapList(value) {
  if (Array.isArray(value)) return value;
  if (Array.isArray(value?.investigations)) return value.investigations;
  if (Array.isArray(value?.items)) return value.items;
  if (Array.isArray(value?.results)) return value.results;
  if (Array.isArray(value?.data)) return value.data;
  return [];
}

function unwrapTypes(value) {
  if (Array.isArray(value)) return value;
  if (Array.isArray(value?.types)) return value.types;
  return [];
}

function prettyKey(key) {
  return String(key)
    .replace(/_/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function formatValue(value, depth = 0) {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (typeof value === "number") return Number.isFinite(value) ? String(value) : "—";
  if (typeof value === "string") return value;
  if (Array.isArray(value)) {
    if (!value.length) return "None recorded";
    if (depth > 2) return `${value.length} item${value.length === 1 ? "" : "s"}`;
    return value.map((item) => formatValue(item, depth + 1)).join("\n");
  }
  if (typeof value === "object") {
    if (depth > 2) return "[Structured data]";
    return Object.entries(value)
      .map(([key, item]) => `${prettyKey(key)}: ${formatValue(item, depth + 1)}`)
      .join("\n");
  }
  return String(value);
}

function extractReport(payload) {
  if (!payload) return null;
  return payload.report ?? payload.data ?? payload.result ?? payload;
}

function reportTitle(report) {
  if (!report || typeof report !== "object") return "Generated Report";
  return (
    report.title ||
    report.report_title ||
    report.name ||
    report.metadata?.title ||
    "Generated Report"
  );
}

function ReportValue({ value }) {
  if (value === null || value === undefined || value === "") {
    return <span className="reports-muted">—</span>;
  }

  if (Array.isArray(value)) {
    if (!value.length) return <span className="reports-muted">None recorded</span>;

    return (
      <div className="reports-list">
        {value.map((item, index) => (
          <div className="reports-list-item" key={index}>
            {typeof item === "object" && item !== null ? (
              <div className="reports-object">
                {Object.entries(item).map(([key, child]) => (
                  <div className="reports-object-row" key={key}>
                    <span>{prettyKey(key)}</span>
                    <ReportValue value={child} />
                  </div>
                ))}
              </div>
            ) : (
              String(item)
            )}
          </div>
        ))}
      </div>
    );
  }

  if (typeof value === "object") {
    return (
      <div className="reports-object">
        {Object.entries(value).map(([key, child]) => (
          <div className="reports-object-row" key={key}>
            <span>{prettyKey(key)}</span>
            <ReportValue value={child} />
          </div>
        ))}
      </div>
    );
  }

  return <span>{String(value)}</span>;
}

function ReportDocument({ report }) {
  if (!report) return null;

  if (typeof report === "string") {
    return <div className="reports-document-text">{report}</div>;
  }

  const preferredSections = [
    "executive_summary",
    "summary",
    "findings",
    "key_findings",
    "intelligence",
    "entities",
    "relationships",
    "evidence",
    "analytics",
    "timeline",
    "risk",
    "recommendations",
    "conclusion",
    "narrative",
  ];

  const keys = Object.keys(report);
  const orderedKeys = [
    ...preferredSections.filter((key) => keys.includes(key)),
    ...keys.filter((key) => !preferredSections.includes(key)),
  ];

  return (
    <div className="reports-document">
      {orderedKeys.map((key) => (
        <section className="reports-section" key={key}>
          <div className="reports-section-heading">
            <span>{prettyKey(key)}</span>
          </div>
          <ReportValue value={report[key]} />
        </section>
      ))}
    </div>
  );
}

export default function Reports() {
  const [investigations, setInvestigations] = useState([]);
  const [types, setTypes] = useState([]);
  const [investigationId, setInvestigationId] = useState(
    getActiveInvestigationId()
      ? String(getActiveInvestigationId())
      : ""
  );
  const [reportType, setReportType] = useState("intelligence");
  const [title, setTitle] = useState("");
  const [classification, setClassification] = useState("internal");
  const [summary, setSummary] = useState("");
  const [narrativeStyle, setNarrativeStyle] = useState("investigative");

  const [includeEvidence, setIncludeEvidence] = useState(true);
  const [includeEntities, setIncludeEntities] = useState(true);
  const [includeRelationships, setIncludeRelationships] = useState(true);
  const [includeAnalytics, setIncludeAnalytics] = useState(true);
  const [includeTimeline, setIncludeTimeline] = useState(true);
  const [includeNarrative, setIncludeNarrative] = useState(true);

  const [report, setReport] = useState(null);
  const [mode, setMode] = useState("idle");
  const [error, setError] = useState("");

  const selectedInvestigation = useMemo(
    () =>
      investigations.find(
        (item) => String(item.id ?? item.investigation_id) === String(investigationId)
      ),
    [investigations, investigationId]
  );

  async function loadReferenceData() {
    setError("");

    try {
      const [investigationResponse, typeResponse] = await Promise.all([
        listInvestigations({ skip: 0, limit: 100 }),
        getReportTypes(),
      ]);

      const investigationItems = unwrapList(investigationResponse);
      const reportTypes = unwrapTypes(typeResponse);

      setInvestigations(investigationItems);
      setTypes(reportTypes);

      const storedActiveId = getActiveInvestigationId();
      const storedExists = investigationItems.some(
        (item) =>
          String(item.id ?? item.investigation_id) ===
          String(storedActiveId ?? "")
      );

      if (storedActiveId && storedExists) {
        setInvestigationId(String(storedActiveId));
      } else if (investigationItems.length) {
        const nextId =
          investigationItems[0].id ??
          investigationItems[0].investigation_id;
        setInvestigationId(String(nextId));
        setActiveInvestigationId(nextId);
      } else {
        setInvestigationId("");
      }

      if (reportTypes.length && !reportTypes.some((item) => item.id === reportType)) {
        const firstUsable = reportTypes.find((item) => item.id !== "preview");
        setReportType(firstUsable?.id ?? reportTypes[0].id);
      }
    } catch (err) {
      setError(
        err?.response?.data?.detail ||
          err?.message ||
          "Unable to load investigation/report configuration."
      );
    }
  }

  useEffect(() => {
    const syncActiveInvestigation = () => {
      const activeId = getActiveInvestigationId();
      setInvestigationId(activeId ? String(activeId) : "");
    };

    window.addEventListener(
      "trinetra:active-investigation-changed",
      syncActiveInvestigation
    );

    return () =>
      window.removeEventListener(
        "trinetra:active-investigation-changed",
        syncActiveInvestigation
      );
  }, []);

  useEffect(() => {
    loadReferenceData();
    const timer = window.setInterval(loadReferenceData, 10000);
    return () => window.clearInterval(timer);
  }, []);

  async function handlePreview() {
    if (!investigationId) {
      setError("Select an investigation first.");
      return;
    }

    setMode("preview");
    setError("");

    try {
      const response = await previewReport({
        investigationId,
        title,
        includeEvidence,
        includeEntities,
        includeRelationships,
        includeAnalytics,
        includeTimeline,
      });
      setReport(extractReport(response));
    } catch (err) {
      setError(
        err?.response?.data?.detail ||
          err?.message ||
          "Report preview failed."
      );
    } finally {
      setMode("idle");
    }
  }

  async function handleGenerate() {
    if (!investigationId) {
      setError("Select an investigation first.");
      return;
    }

    setMode("generate");
    setError("");

    try {
      const response =
        reportType === "criminal_documentary"
          ? await generateDocumentaryReport({
              investigationId,
              title,
              narrativeStyle,
              includeNarrative,
              includeEvidence,
              includeEntities,
              includeRelationships,
              includeAnalytics,
              includeTimeline,
            })
          : await generateIntelligenceReport({
              investigationId,
              title,
              classification,
              summary,
              includeEvidence,
              includeEntities,
              includeRelationships,
              includeAnalytics,
              includeTimeline,
            });

      setReport(extractReport(response));
    } catch (err) {
      setError(
        err?.response?.data?.detail ||
          err?.message ||
          "Report generation failed."
      );
    } finally {
      setMode("idle");
    }
  }

  const typeDescription =
    types.find((item) => item.id === reportType)?.description ||
    "Generate a structured report from the selected investigation.";

  return (
    <main className="reports-page">
      <section className="reports-hero">
        <div>
          <div className="reports-eyebrow">
            <Sparkles size={14} />
            TRINETRA REPORT CENTER
          </div>
          <h1>Investigation Reports</h1>
          <p>
            Transform investigation evidence, entities, relationships, analytics,
            and timelines into an analyst-ready report.
          </p>
        </div>

        <button
          className="reports-refresh"
          type="button"
          onClick={loadReferenceData}
          disabled={mode !== "idle"}
        >
          <RefreshCw size={16} />
          Refresh
        </button>
      </section>

      {error && (
        <div className="reports-error">
          <AlertTriangle size={18} />
          <span>{error}</span>
        </div>
      )}

      <section className="reports-workspace">
        <aside className="reports-control-panel">
          <div className="reports-panel-title">
            <FileBarChart2 size={18} />
            Report Configuration
          </div>

          <label className="reports-field">
            <span>Investigation</span>
            <div className="reports-select-wrap">
              <select
                value={investigationId}
                onChange={(event) => {
                  setInvestigationId(event.target.value);
                  setActiveInvestigationId(event.target.value);
                  setReport(null);
                }}
              >
                <option value="">Select investigation</option>
                {investigations.map((item) => {
                  const id = item.id ?? item.investigation_id;
                  const number =
                    item.investigation_number ??
                    item.number ??
                    `Investigation ${id}`;
                  const itemTitle = item.title ?? "Untitled investigation";

                  return (
                    <option value={id} key={id}>
                      {number} — {itemTitle}
                    </option>
                  );
                })}
              </select>
              <ChevronDown size={16} />
            </div>
          </label>

          <label className="reports-field">
            <span>Report Type</span>
            <div className="reports-select-wrap">
              <select
                value={reportType}
                onChange={(event) => {
                  setReportType(event.target.value);
                  setReport(null);
                }}
              >
                {types
                  .filter((item) => item.id !== "preview")
                  .map((item) => (
                    <option value={item.id} key={item.id}>
                      {item.name}
                    </option>
                  ))}
              </select>
              <ChevronDown size={16} />
            </div>
          </label>

          <div className="reports-type-description">{typeDescription}</div>

          <label className="reports-field">
            <span>Report Title</span>
            <input
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              placeholder={
                selectedInvestigation?.title
                  ? `${selectedInvestigation.title} Report`
                  : "Investigation report"
              }
            />
          </label>

          {reportType === "intelligence" && (
            <>
              <label className="reports-field">
                <span>Classification</span>
                <select
                  value={classification}
                  onChange={(event) => setClassification(event.target.value)}
                >
                  <option value="internal">Internal</option>
                  <option value="confidential">Confidential</option>
                  <option value="restricted">Restricted</option>
                </select>
              </label>

              <label className="reports-field">
                <span>Analyst Summary</span>
                <textarea
                  value={summary}
                  onChange={(event) => setSummary(event.target.value)}
                  placeholder="Optional analyst context or summary..."
                  rows={4}
                />
              </label>
            </>
          )}

          {reportType === "criminal_documentary" && (
            <>
              <label className="reports-field">
                <span>Narrative Style</span>
                <select
                  value={narrativeStyle}
                  onChange={(event) => setNarrativeStyle(event.target.value)}
                >
                  <option value="investigative">Investigative</option>
                  <option value="chronological">Chronological</option>
                  <option value="documentary">Documentary</option>
                </select>
              </label>

              <label className="reports-check">
                <input
                  type="checkbox"
                  checked={includeNarrative}
                  onChange={(event) => setIncludeNarrative(event.target.checked)}
                />
                <span>Include narrative</span>
              </label>
            </>
          )}

          <div className="reports-field">
            <span>Include Sections</span>
            <div className="reports-check-grid">
              {[
                ["Evidence", includeEvidence, setIncludeEvidence],
                ["Entities", includeEntities, setIncludeEntities],
                ["Relationships", includeRelationships, setIncludeRelationships],
                ["Analytics", includeAnalytics, setIncludeAnalytics],
                ["Timeline", includeTimeline, setIncludeTimeline],
              ].map(([label, checked, setter]) => (
                <label className="reports-check" key={label}>
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={(event) => setter(event.target.checked)}
                  />
                  <span>{label}</span>
                </label>
              ))}
            </div>
          </div>

          <div className="reports-actions">
            <button
              type="button"
              className="reports-secondary-button"
              onClick={handlePreview}
              disabled={mode !== "idle" || !investigationId}
            >
              {mode === "preview" ? (
                <LoaderCircle className="reports-spin" size={17} />
              ) : (
                <BookOpen size={17} />
              )}
              Preview
            </button>

            <button
              type="button"
              className="reports-primary-button"
              onClick={handleGenerate}
              disabled={mode !== "idle" || !investigationId}
            >
              {mode === "generate" ? (
                <LoaderCircle className="reports-spin" size={17} />
              ) : (
                <FileText size={17} />
              )}
              Generate Report
            </button>
          </div>
        </aside>

        <section className="reports-preview-panel">
          <div className="reports-preview-header">
            <div>
              <div className="reports-preview-kicker">
                <ShieldCheck size={15} />
                ANALYST OUTPUT
              </div>
              <h2>{report ? reportTitle(report) : "Report Preview"}</h2>
            </div>

            {report && (
              <div className="reports-ready-badge">
                <CheckCircle2 size={15} />
                Generated
              </div>
            )}
          </div>

          {!report ? (
            <div className="reports-empty">
              <div className="reports-empty-icon">
                <ClipboardCheck size={28} />
              </div>
              <h3>Ready to generate</h3>
              <p>
                Select an investigation and report type, choose the sections you
                want included, then preview or generate the report.
              </p>
            </div>
          ) : (
            <ReportDocument report={report} />
          )}
        </section>
      </section>
    </main>
  );
}

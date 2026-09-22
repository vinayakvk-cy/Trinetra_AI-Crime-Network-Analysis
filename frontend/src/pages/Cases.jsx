import { useCallback, useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  BarChart3,
  CheckCircle2,
  ClipboardPlus,
  ExternalLink,
  FileText,
  FileUp,
  FolderKanban,
  Loader2,
  Network,
  RefreshCw,
  Search,
  ShieldCheck,
  UploadCloud,
  X,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import {
  createCase,
  listCases,
  uploadCaseEvidence,
} from "../services/casesApi";
import "./cases-page.css";
import { getApiErrorMessage } from "../services/api";
import { setActiveCaseId } from "../services/activeCase";

const REFRESH_INTERVAL_MS = 10000;

const EMPTY_FORM = {
  caseNumber: "",
  title: "",
  description: "",
};

const EMPTY_EVIDENCE = {
  evidenceNumber: "",
  title: "",
  evidenceType: "document",
  description: "",
  sourceReference: "",
  file: null,
};

const idOf = (x) =>
  x?.id ?? x?.case_id ?? x?.caseId ?? null;

const numberOf = (x) =>
  x?.case_number ?? x?.caseNumber ?? "—";

const titleOf = (x) =>
  x?.title ?? "Untitled case";

const descriptionOf = (x) =>
  x?.description ?? "";

function statusOf(x) {
  const value = x?.status ?? "created";

  if (
    typeof value === "object" &&
    value !== null &&
    "value" in value
  ) {
    return String(value.value);
  }

  return String(value);
}

function formatStatus(value) {
  return String(value ?? "created")
    .replace(/_/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function formatDate(value) {
  if (!value) return "—";

  const d = new Date(value);

  return Number.isNaN(d.getTime())
    ? String(value)
    : d.toLocaleString();
}

function valueOrDash(value) {
  if (
    value === null ||
    value === undefined ||
    String(value).trim() === ""
  ) {
    return "—";
  }

  return String(value);
}

export default function Cases() {
  const [cases, setCases] = useState([]);
  const [selectedCase, setSelectedCase] = useState(null);

  const [form, setForm] = useState(EMPTY_FORM);

  const [evidence, setEvidence] = useState(
    EMPTY_EVIDENCE
  );

  const [query, setQuery] = useState("");

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [creating, setCreating] = useState(false);
  const [uploading, setUploading] = useState(false);

  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const loadCases = useCallback(
    async (manual = false) => {
      manual
        ? setRefreshing(true)
        : setLoading(true);

      try {
        const data = await listCases();

        const rows = Array.isArray(data)
          ? data
          : data?.results ??
            data?.cases ??
            [];

        setCases(rows);
        setError("");

        /*
         * Keep the selected case synchronized with
         * the refreshed API record.
         */
        setSelectedCase((current) => {
          if (!current) return current;

          const currentId = idOf(current);

          const refreshed = rows.find(
            (item) =>
              String(idOf(item)) ===
              String(currentId)
          );

          return refreshed ?? current;
        });
      } catch (e) {
        setError(
          e?.response?.data?.detail ||
            e?.message ||
            "Unable to load cases."
        );
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    []
  );

  useEffect(() => {
    loadCases();

    const timer = window.setInterval(
      () => loadCases(),
      REFRESH_INTERVAL_MS
    );

    return () =>
      window.clearInterval(timer);
  }, [loadCases]);

  const filteredCases = useMemo(() => {
    const q = query.trim().toLowerCase();

    if (!q) return cases;

    return cases.filter((x) =>
      [
        numberOf(x),
        titleOf(x),
        descriptionOf(x),
        statusOf(x),
      ]
        .join(" ")
        .toLowerCase()
        .includes(q)
    );
  }, [cases, query]);

  const caseStats = useMemo(() => {
    const total = cases.length;

    const active = cases.filter((item) => {
      const status = statusOf(item).toLowerCase();

      return [
        "created",
        "planning",
        "in_progress",
        "evidence_review",
        "suspect_verification",
        "cross_case_analysis",
        "pending_review",
      ].includes(status);
    }).length;

    const completed = cases.filter((item) => {
      const status = statusOf(item).toLowerCase();

      return [
        "completed",
        "closed",
      ].includes(status);
    }).length;

    return {
      total,
      active,
      completed,
    };
  }, [cases]);

  const update = (field, value) =>
    setForm((current) => ({
      ...current,
      [field]: value,
    }));

  const updateEvidence = (field, value) =>
    setEvidence((current) => ({
      ...current,
      [field]: value,
    }));

  function clearMessages() {
    setError("");
    setNotice("");
  }

  function selectCase(item) {
    clearMessages();
    setSelectedCase(item);
    setActiveCaseId(idOf(item));
  }

  function closeDetails() {
    setSelectedCase(null);
  }

  async function handleCreateCase(event) {
    event.preventDefault();

    clearMessages();

    if (
      !form.caseNumber.trim() ||
      !form.title.trim()
    ) {
      setError(
        "Case number and case title are required."
      );
      return;
    }

    setCreating(true);

    try {
      const result = await createCase({
        caseNumber: form.caseNumber.trim(),
        title: form.title.trim(),
        description: form.description.trim(),
      });

      const created =
        result?.case ?? result;

      setSelectedCase(created);
      setActiveCaseId(idOf(created));
      setForm(EMPTY_FORM);

      setNotice(
        `Case ${numberOf(
          created
        )} created successfully.`
      );

      await loadCases(true);
    } catch (e) {
      setError(getApiErrorMessage(e, "Unable to create the case."));
    } finally {
      setCreating(false);
    }
  }

  async function handleUpload(event) {
    event.preventDefault();

    clearMessages();

    const caseId = idOf(selectedCase);

    if (!caseId) {
      setError(
        "Select a case before uploading evidence."
      );
      return;
    }

    if (
      !evidence.evidenceNumber.trim() ||
      !evidence.title.trim() ||
      !evidence.file
    ) {
      setError(
        "Evidence number, title, and file are required."
      );
      return;
    }

    setUploading(true);

    try {
      await uploadCaseEvidence({
        caseId,
        evidenceNumber:
          evidence.evidenceNumber.trim(),
        title: evidence.title.trim(),
        evidenceType:
          evidence.evidenceType,
        description:
          evidence.description.trim(),
        sourceReference:
          evidence.sourceReference.trim(),
        file: evidence.file,
      });

      setEvidence(EMPTY_EVIDENCE);

      event.target.reset();

      setNotice(
        "Evidence uploaded and linked to the selected case."
      );
    } catch (e) {
      setError(getApiErrorMessage(e, "Unable to upload evidence."));
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="tn-page tn-cases-page">
      <header className="tn-cases-header">
        <div>
          <div className="tn-eyebrow">
            TRINETRA / CASE MANAGEMENT
          </div>

          <h1 className="tn-page-title">
            Case Command Center
          </h1>

          <p className="tn-page-subtitle">
            Create cases from the live API, inspect
            case context, and attach source evidence
            for downstream graph, analytics, and
            assistant processing.
          </p>
        </div>

        <div className="tn-cases-live">
          <span className="tn-cases-live-dot" />

          <div>
            <strong>
              CASE SERVICE ONLINE
            </strong>

            <span>
              Auto-refresh every 10 seconds
            </span>
          </div>

          <button
            type="button"
            className="tn-icon-button"
            onClick={() => loadCases(true)}
            disabled={refreshing}
            aria-label="Refresh cases"
            title="Refresh cases"
          >
            <RefreshCw
              size={17}
              className={
                refreshing
                  ? "tn-spin"
                  : ""
              }
            />
          </button>
        </div>
      </header>

      <AnimatePresence initial={false}>
        {(error || notice) && (
          <motion.div
            className={`tn-cases-alert ${
              error
                ? "is-error"
                : "is-success"
            }`}
            initial={{
              opacity: 0,
              y: -8,
            }}
            animate={{
              opacity: 1,
              y: 0,
            }}
            exit={{
              opacity: 0,
              y: -8,
            }}
          >
            {error ? (
              <AlertTriangle size={17} />
            ) : (
              <CheckCircle2 size={17} />
            )}

            <span>
              {error || notice}
            </span>

            <button
              type="button"
              onClick={clearMessages}
              aria-label="Dismiss message"
            >
              <X size={15} />
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      <section className="tn-case-stats">
        <div className="tn-case-stat tn-glass-panel">
          <div className="tn-case-stat-icon">
            <FolderKanban size={18} />
          </div>

          <div>
            <span>Total cases</span>
            <strong>
              {caseStats.total}
            </strong>
          </div>
        </div>

        <div className="tn-case-stat tn-glass-panel">
          <div className="tn-case-stat-icon">
            <ShieldCheck size={18} />
          </div>

          <div>
            <span>Active cases</span>
            <strong>
              {caseStats.active}
            </strong>
          </div>
        </div>

        <div className="tn-case-stat tn-glass-panel">
          <div className="tn-case-stat-icon">
            <CheckCircle2 size={18} />
          </div>

          <div>
            <span>Completed</span>
            <strong>
              {caseStats.completed}
            </strong>
          </div>
        </div>
      </section>

      <section className="tn-cases-layout">
        <motion.div
          className="tn-case-intake tn-glass-panel"
          initial={{
            opacity: 0,
            x: -12,
          }}
          animate={{
            opacity: 1,
            x: 0,
          }}
        >
          <div className="tn-panel-heading">
            <div className="tn-panel-icon">
              <ClipboardPlus size={20} />
            </div>

            <div>
              <span>CASE INTAKE</span>

              <h2>
                Create a new case
              </h2>
            </div>
          </div>

          <form
            onSubmit={handleCreateCase}
            className="tn-case-form"
          >
            <label>
              <span>
                Case number *
              </span>

              <input
                value={form.caseNumber}
                onChange={(event) =>
                  update(
                    "caseNumber",
                    event.target.value
                  )
                }
                placeholder="TRI-2026-002"
              />
            </label>

            <label>
              <span>
                Case title *
              </span>

              <input
                value={form.title}
                onChange={(event) =>
                  update(
                    "title",
                    event.target.value
                  )
                }
                placeholder="Financial Network Investigation"
              />
            </label>

            <label>
              <span>
                Description
              </span>

              <textarea
                value={form.description}
                onChange={(event) =>
                  update(
                    "description",
                    event.target.value
                  )
                }
                placeholder="Describe the purpose and scope of this investigation..."
                rows={6}
              />
            </label>

            <div className="tn-intake-note">
              <ShieldCheck size={16} />

              <span>
                Creates the case through{" "}
                <code>POST /cases</code>.
                No case data is hardcoded.
              </span>
            </div>

            <button
              type="submit"
              className="tn-primary-button"
              disabled={creating}
            >
              {creating ? (
                <Loader2
                  size={17}
                  className="tn-spin"
                />
              ) : (
                <ClipboardPlus size={17} />
              )}

              {creating
                ? "Creating case…"
                : "Create case"}
            </button>
          </form>
        </motion.div>

        <div className="tn-case-list-panel tn-glass-panel">
          <div className="tn-list-heading">
            <div>
              <span>
                LIVE CASE REGISTER
              </span>

              <h2>
                {cases.length}{" "}
                {cases.length === 1
                  ? "case"
                  : "cases"}
              </h2>
            </div>

            <div className="tn-case-search">
              <Search size={16} />

              <input
                value={query}
                onChange={(event) =>
                  setQuery(
                    event.target.value
                  )
                }
                placeholder="Search cases…"
                aria-label="Search cases"
              />
            </div>
          </div>

          <div className="tn-case-list">
            {loading ? (
              <div className="tn-empty-state">
                <Loader2
                  size={22}
                  className="tn-spin"
                />

                Loading live case register…
              </div>
            ) : filteredCases.length === 0 ? (
              <div className="tn-empty-state">
                <ClipboardPlus size={22} />

                No matching cases found.
              </div>
            ) : (
              filteredCases.map((item) => {
                const active =
                  selectedCase &&
                  String(
                    idOf(selectedCase)
                  ) ===
                    String(idOf(item));

                return (
                  <button
                    type="button"
                    className={`tn-case-row ${
                      active
                        ? "is-active"
                        : ""
                    }`}
                    key={
                      idOf(item) ??
                      numberOf(item)
                    }
                    onClick={() =>
                      selectCase(item)
                    }
                  >
                    <div className="tn-case-row-mark">
                      <span />
                    </div>

                    <div className="tn-case-row-main">
                      <strong>
                        {titleOf(item)}
                      </strong>

                      <span>
                        {numberOf(item)}
                      </span>
                    </div>

                    <div className="tn-case-row-meta">
                      <span>
                        {formatStatus(
                          statusOf(item)
                        )}
                      </span>

                      <small>
                        {formatDate(
                          item?.created_at ??
                            item?.createdAt
                        )}
                      </small>
                    </div>
                  </button>
                );
              })
            )}
          </div>
        </div>
      </section>

      <section className="tn-evidence-intake tn-glass-panel">
        <div className="tn-panel-heading">
          <div className="tn-panel-icon">
            <FileUp size={20} />
          </div>

          <div>
            <span>
              EVIDENCE INTAKE
            </span>

            <h2>
              {selectedCase
                ? `Attach evidence to ${numberOf(
                    selectedCase
                  )}`
                : "Select a case to attach evidence"}
            </h2>
          </div>
        </div>

        <form
          onSubmit={handleUpload}
          className="tn-evidence-form"
        >
          <label>
            <span>
              Evidence number *
            </span>

            <input
              value={
                evidence.evidenceNumber
              }
              onChange={(event) =>
                updateEvidence(
                  "evidenceNumber",
                  event.target.value
                )
              }
              placeholder="EV-2026-001"
            />
          </label>

          <label>
            <span>
              Evidence title *
            </span>

            <input
              value={evidence.title}
              onChange={(event) =>
                updateEvidence(
                  "title",
                  event.target.value
                )
              }
              placeholder="Bank transaction record"
            />
          </label>

          <label>
            <span>
              Evidence type
            </span>

            <select
              value={
                evidence.evidenceType
              }
              onChange={(event) =>
                updateEvidence(
                  "evidenceType",
                  event.target.value
                )
              }
            >
              <option value="document">
                Document
              </option>

              <option value="financial">
                Financial
              </option>

              <option value="communication">
                Communication
              </option>

              <option value="image">
                Image
              </option>

              <option value="registry">
                Registry
              </option>

              <option value="other">
                Other
              </option>
            </select>
          </label>

          <label>
            <span>
              Source reference
            </span>

            <input
              value={
                evidence.sourceReference
              }
              onChange={(event) =>
                updateEvidence(
                  "sourceReference",
                  event.target.value
                )
              }
              placeholder="DOC-2026-001"
            />
          </label>

          <label className="tn-field-wide">
            <span>
              Description
            </span>

            <textarea
              value={evidence.description}
              onChange={(event) =>
                updateEvidence(
                  "description",
                  event.target.value
                )
              }
              rows={4}
              placeholder="What does this evidence contain?"
            />
          </label>

          <label className="tn-file-drop tn-field-wide">
            <input
              type="file"
              accept=".pdf,.doc,.docx,.jpg,.jpeg,.png,.tif,.tiff"
              onChange={(event) =>
                updateEvidence(
                  "file",
                  event.target.files?.[0] ??
                    null
                )
              }
            />

            <UploadCloud size={25} />

            <strong>
              {evidence.file
                ? evidence.file.name
                : "Choose evidence file"}
            </strong>

            <span>
              PDF, DOCX, JPG, PNG, TIFF
            </span>
          </label>

          <button
            type="submit"
            className="tn-primary-button tn-field-wide"
            disabled={
              !selectedCase ||
              uploading
            }
          >
            {uploading ? (
              <Loader2
                size={17}
                className="tn-spin"
              />
            ) : (
              <FileUp size={17} />
            )}

            {uploading
              ? "Uploading evidence…"
              : "Upload evidence to case"}
          </button>
        </form>
      </section>

      <AnimatePresence>
        {selectedCase && (
          <>
            <motion.div
              className="tn-case-drawer-backdrop"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={closeDetails}
            />

            <motion.aside
              className="tn-case-details-drawer"
              initial={{
                opacity: 0,
                x: "100%",
              }}
              animate={{
                opacity: 1,
                x: 0,
              }}
              exit={{
                opacity: 0,
                x: "100%",
              }}
              transition={{
                type: "spring",
                stiffness: 300,
                damping: 30,
              }}
              aria-label="Case details"
            >
              <div className="tn-case-drawer-header">
                <div>
                  <span>
                    CASE INTELLIGENCE
                  </span>

                  <h2>
                    Case details
                  </h2>
                </div>

                <button
                  type="button"
                  className="tn-case-drawer-close"
                  onClick={closeDetails}
                  aria-label="Close case details"
                >
                  <X size={18} />
                </button>
              </div>

              <div className="tn-case-drawer-content">
                <div className="tn-case-drawer-identity">
                  <div className="tn-case-drawer-symbol">
                    <FolderKanban size={24} />
                  </div>

                  <div>
                    <span>
                      {numberOf(
                        selectedCase
                      )}
                    </span>

                    <h3>
                      {titleOf(
                        selectedCase
                      )}
                    </h3>
                  </div>
                </div>

                <div className="tn-case-drawer-status-row">
                  <span className="tn-case-status-label">
                    STATUS
                  </span>

                  <span
                    className={`tn-case-status-pill status-${statusOf(
                      selectedCase
                    ).toLowerCase()}`}
                  >
                    <span className="tn-case-status-dot" />

                    {formatStatus(
                      statusOf(
                        selectedCase
                      )
                    )}
                  </span>
                </div>

                <div className="tn-case-detail-section">
                  <div className="tn-case-detail-section-heading">
                    <FileText size={16} />

                    <span>
                      CASE OVERVIEW
                    </span>
                  </div>

                  <div className="tn-case-detail-grid">
                    <div className="tn-case-detail-item">
                      <span>
                        Case ID
                      </span>

                      <strong>
                        {valueOrDash(
                          idOf(
                            selectedCase
                          )
                        )}
                      </strong>
                    </div>

                    <div className="tn-case-detail-item">
                      <span>
                        Case number
                      </span>

                      <strong>
                        {numberOf(
                          selectedCase
                        )}
                      </strong>
                    </div>

                    <div className="tn-case-detail-item">
                      <span>
                        Created
                      </span>

                      <strong>
                        {formatDate(
                          selectedCase?.created_at ??
                            selectedCase?.createdAt
                        )}
                      </strong>
                    </div>

                    <div className="tn-case-detail-item">
                      <span>
                        Updated
                      </span>

                      <strong>
                        {formatDate(
                          selectedCase?.updated_at ??
                            selectedCase?.updatedAt
                        )}
                      </strong>
                    </div>
                  </div>
                </div>

                <div className="tn-case-detail-section">
                  <div className="tn-case-detail-section-heading">
                    <ClipboardPlus size={16} />

                    <span>
                      DESCRIPTION
                    </span>
                  </div>

                  <div className="tn-case-description">
                    {descriptionOf(
                      selectedCase
                    ) || (
                      <span className="tn-case-muted">
                        No case description has
                        been recorded.
                      </span>
                    )}
                  </div>
                </div>

                <div className="tn-case-detail-section">
                  <div className="tn-case-detail-section-heading">
                    <ShieldCheck size={16} />

                    <span>
                      AVAILABLE OPERATIONS
                    </span>
                  </div>

                  <div className="tn-case-action-list">
                    <button
                      type="button"
                      onClick={() => {
                        closeDetails();

                        window.setTimeout(
                          () => {
                            document
                              .querySelector(
                                ".tn-evidence-intake"
                              )
                              ?.scrollIntoView({
                                behavior:
                                  "smooth",
                                block: "start",
                              });
                          },
                          50
                        );
                      }}
                    >
                      <FileUp size={17} />

                      <span>
                        Attach evidence
                      </span>

                      <ExternalLink
                        size={14}
                      />
                    </button>

                    <button
                      type="button"
                      onClick={() => {
                        closeDetails();
                        setNotice(
                          "Investigation workspace is available from the main navigation."
                        );
                      }}
                    >
                      <Network size={17} />

                      <span>
                        Open investigation graph
                      </span>

                      <ExternalLink
                        size={14}
                      />
                    </button>

                    <button
                      type="button"
                      onClick={() => {
                        closeDetails();
                        setNotice(
                          "Analytics workspace is available from the main navigation."
                        );
                      }}
                    >
                      <BarChart3 size={17} />

                      <span>
                        Open analytics
                      </span>

                      <ExternalLink
                        size={14}
                      />
                    </button>
                  </div>
                </div>

                <div className="tn-case-drawer-note">
                  <ShieldCheck size={15} />

                  <span>
                    Case information shown here is
                    retrieved from the live API. The
                    drawer does not create or modify
                    case records.
                  </span>
                </div>
              </div>
            </motion.aside>
          </>
        )}
      </AnimatePresence>
    </div>
  );
}
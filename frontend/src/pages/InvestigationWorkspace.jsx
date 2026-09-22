import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Activity,
  AlertTriangle,
  BarChart3,
  BrainCircuit,
  CheckCircle2,
  ChevronDown,
  CircleDot,
  Clock3,
  FileBarChart2,
  FileText,
  GitBranch,
  Loader2,
  Network,
  RefreshCw,
  ShieldAlert,
  ShieldCheck,
  Target,
  Users,
  X,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import api from "../services/api";
import {
  getActiveInvestigationId,
  setActiveInvestigationId,
} from "../services/activeInvestigation";
import "./investigation-workspace.css";

const REFRESH_INTERVAL_MS = 10000;

const STATUS_LABELS = {
  created: "Created",
  planning: "Planning",
  in_progress: "In Progress",
  evidence_review: "Evidence Review",
  suspect_verification: "Suspect Verification",
  cross_case_analysis: "Cross-Case Analysis",
  pending_review: "Pending Review",
  completed: "Completed",
  suspended: "Suspended",
  closed: "Closed",
};

function idOf(item) {
  return (
    item?.id ??
    item?.investigation_id ??
    item?.investigationId ??
    null
  );
}

function investigationNumberOf(item) {
  return (
    item?.investigation_number ??
    item?.investigationNumber ??
    item?.number ??
    `INV-${idOf(item) ?? "—"}`
  );
}

function titleOf(item) {
  return item?.title ?? "Untitled investigation";
}

function statusOf(item) {
  const value = item?.status ?? "created";

  if (
    typeof value === "object" &&
    value !== null &&
    "value" in value
  ) {
    return String(value.value);
  }

  return String(value);
}

function outcomeOf(item) {
  const value = item?.outcome ?? "undetermined";

  if (
    typeof value === "object" &&
    value !== null &&
    "value" in value
  ) {
    return String(value.value);
  }

  return String(value);
}

function formatLabel(value) {
  if (!value) return "—";

  return String(value)
    .replace(/_/g, " ")
    .replace(/\b\w/g, (letter) =>
      letter.toUpperCase()
    );
}

function formatDate(value) {
  if (!value) return "—";

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return String(value);
  }

  return date.toLocaleString();
}

function numberOrDash(value) {
  if (
    value === null ||
    value === undefined ||
    String(value).trim() === ""
  ) {
    return "—";
  }

  return value;
}

function normalizeArray(value) {
  if (Array.isArray(value)) return value;

  if (Array.isArray(value?.results)) {
    return value.results;
  }

  if (Array.isArray(value?.items)) {
    return value.items;
  }

  if (Array.isArray(value?.investigations)) {
    return value.investigations;
  }

  if (Array.isArray(value?.evidence)) {
    return value.evidence;
  }

  return [];
}

function getRiskScore(summary, investigation) {
  const candidates = [
    summary?.risk?.results?.risk_score,
    summary?.risk?.results?.score,
    summary?.risk?.risk_score,
    summary?.risk?.score,
    investigation?.final_risk_score,
    investigation?.initial_risk_score,
  ];

  const value = candidates.find(
    (candidate) =>
      candidate !== null &&
      candidate !== undefined &&
      candidate !== ""
  );

  if (value === undefined) {
    return null;
  }

  const numeric = Number(value);

  if (Number.isNaN(numeric)) {
    return null;
  }

  /*
   * Backend risk may be represented as either:
   * 0.0 - 1.0 or 0 - 100.
   */
  return numeric <= 1
    ? Math.round(numeric * 100)
    : Math.round(numeric);
}

function getRiskLevel(summary, score) {
  const backendLevel =
    summary?.risk?.results?.risk_level ??
    summary?.risk?.results?.level ??
    summary?.risk?.risk_level ??
    summary?.risk?.level;

  if (backendLevel) {
    return formatLabel(backendLevel);
  }

  if (score === null) return "Not Available";
  if (score >= 75) return "High";
  if (score >= 50) return "Moderate";
  if (score >= 25) return "Low";

  return "Minimal";
}

function getPatterns(summary) {
  return normalizeArray(
    summary?.patterns?.results ??
      summary?.patterns
  );
}

function getGraph(summary) {
  return (
    summary?.graph?.results ??
    summary?.graph ??
    {}
  );
}

function getGraphCount(summary) {
  const graph = getGraph(summary);

  const candidates = [
    graph?.relationship_count,
    graph?.relationships,
    graph?.count,
    graph?.total_relationships,
  ];

  const value = candidates.find(
    (item) =>
      typeof item === "number"
  );

  if (value !== undefined) {
    return value;
  }

  if (Array.isArray(graph)) {
    return graph.length;
  }

  return 0;
}

function getPatternCount(summary) {
  return getPatterns(summary).length;
}

function getRiskTone(score) {
  if (score === null) return "neutral";
  if (score >= 75) return "danger";
  if (score >= 50) return "warning";
  if (score >= 25) return "caution";
  return "safe";
}

function getEvidenceId(item) {
  return (
    item?.evidence_id ??
    item?.evidenceId ??
    item?.id ??
    null
  );
}

function getEvidenceNumber(item) {
  return (
    item?.evidence_number ??
    item?.evidenceNumber ??
    `Evidence ${getEvidenceId(item) ?? "—"}`
  );
}

function getEvidenceTitle(item) {
  return (
    item?.title ??
    "Untitled evidence"
  );
}

function getEvidenceStatus(item) {
  const value =
    item?.status ??
    item?.evidence_status ??
    "unknown";

  if (
    typeof value === "object" &&
    value !== null &&
    "value" in value
  ) {
    return String(value.value);
  }

  return String(value);
}

function getEntityName(item) {
  return (
    item?.value ??
    item?.name ??
    item?.entity_value ??
    item?.entity_name ??
    "Unknown entity"
  );
}

function getEntityType(item) {
  return (
    item?.entity_type ??
    item?.entityType ??
    item?.type ??
    "entity"
  );
}

function getRelationshipType(item) {
  return (
    item?.relationship_type ??
    item?.relationshipType ??
    item?.type ??
    "relationship"
  );
}

function getRelationshipConfidence(item) {
  const value =
    item?.confidence ??
    item?.relationship_confidence ??
    null;

  if (
    value === null ||
    value === undefined
  ) {
    return null;
  }

  const numeric = Number(value);

  if (Number.isNaN(numeric)) {
    return null;
  }

  return numeric <= 1
    ? Math.round(numeric * 100)
    : Math.round(numeric);
}

export default function InvestigationWorkspace() {
  const [investigations, setInvestigations] =
    useState([]);

  const [investigationId, setInvestigationId] =
    useState(() => {
      const activeId = getActiveInvestigationId();
      return activeId ? String(activeId) : "";
    });

  const [investigation, setInvestigation] =
    useState(null);

  const [summary, setSummary] =
    useState(null);

  const [evidence, setEvidence] =
    useState([]);

  const [loading, setLoading] =
    useState(true);

  const [refreshing, setRefreshing] =
    useState(false);

  const [error, setError] =
    useState("");

  const [activeTab, setActiveTab] =
    useState("overview");

  const [selectedEvidence, setSelectedEvidence] =
    useState(null);

  const loadInvestigations = useCallback(
    async () => {
      const response = await api.get(
        "/investigations"
      );

      const rows = normalizeArray(
        response.data
      );

      setInvestigations(rows);

      const activeId = getActiveInvestigationId();
      const activeExists = rows.some(
        (item) =>
          String(idOf(item)) ===
          String(activeId ?? "")
      );

      if (activeId && activeExists) {
        setInvestigationId(String(activeId));
      } else if (rows.length > 0) {
        const nextId = idOf(rows[0]);
        setInvestigationId(String(nextId));
        setActiveInvestigationId(nextId);
      } else {
        setInvestigationId("");
      }

      return rows;
    },
    [investigationId]
  );

  const loadWorkspace = useCallback(
    async (manual = false) => {
      if (!investigationId) {
        return;
      }

      if (manual) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }

      try {
        const [
          investigationResponse,
          summaryResponse,
          evidenceLinksResponse,
        ] = await Promise.all([
          api.get(
            `/investigations/${investigationId}`
          ),

          api.get(
            `/analytics/investigations/${investigationId}/summary`
          ),

          api.get(
            "/investigation-evidence",
            {
              params: {
                investigation_id:
                  investigationId,
              },
            }
          ),
        ]);

        const investigationData =
          investigationResponse.data;

        const summaryData =
          summaryResponse.data;

        const links =
          normalizeArray(
            evidenceLinksResponse.data
          );

        /*
         * InvestigationEvidence contains evidence_id.
         * Resolve those IDs into the actual evidence
         * records. This keeps the workspace scoped to
         * the selected investigation.
         */
        const evidenceRows =
          await Promise.all(
            links
              .map(getEvidenceId)
              .filter(Boolean)
              .map(async (evidenceId) => {
                try {
                  const response =
                    await api.get(
                      `/evidence/${evidenceId}`
                    );

                  const item =
                    response.data?.evidence ??
                    response.data;

                  const link =
                    links.find(
                      (candidate) =>
                        String(
                          getEvidenceId(
                            candidate
                          )
                        ) ===
                        String(evidenceId)
                    );

                  return {
                    ...item,
                    investigation_relation:
                      link?.relation ??
                      link?.relationship ??
                      null,
                    investigation_notes:
                      link?.notes ?? null,
                  };
                } catch {
                  return null;
                }
              })
          );

        setInvestigation(
          investigationData?.investigation ??
            investigationData
        );

        setSummary(
          summaryData
        );

        setEvidence(
          evidenceRows.filter(Boolean)
        );

        setError("");
      } catch (err) {
        setError(
          err?.response?.data?.detail ||
            err?.message ||
            "Unable to load the investigation workspace."
        );
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [investigationId]
  );

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
    loadInvestigations().catch(
      (err) => {
        setError(
          err?.response?.data?.detail ||
            err?.message ||
            "Unable to load investigations."
        );

        setLoading(false);
      }
    );
  }, [loadInvestigations]);

  useEffect(() => {
    if (!investigationId) return;

    loadWorkspace();

    const timer =
      window.setInterval(
        () => loadWorkspace(),
        REFRESH_INTERVAL_MS
      );

    return () =>
      window.clearInterval(timer);
  }, [
    investigationId,
    loadWorkspace,
  ]);

  const selectedInvestigation =
    useMemo(
      () =>
        investigations.find(
          (item) =>
            String(idOf(item)) ===
            String(investigationId)
        ) ??
        investigation,
      [
        investigations,
        investigationId,
        investigation,
      ]
    );

  const riskScore = useMemo(
    () =>
      getRiskScore(
        summary,
        selectedInvestigation
      ),
    [
      summary,
      selectedInvestigation,
    ]
  );

  const riskLevel = getRiskLevel(
    summary,
    riskScore
  );

  const riskTone =
    getRiskTone(riskScore);

  const patterns =
    getPatterns(summary);

  const graphCount =
    getGraphCount(summary);

  const patternCount =
    getPatternCount(summary);

  const findings = useMemo(() => {
    const raw =
      selectedInvestigation?.findings ??
      summary?.findings ??
      [];

    if (Array.isArray(raw)) {
      return raw;
    }

    if (
      typeof raw === "string" &&
      raw.trim()
    ) {
      return [
        {
          title: "Recorded findings",
          content: raw,
        },
      ];
    }

    return [];
  }, [
    selectedInvestigation,
    summary,
  ]);

  const relationships = useMemo(() => {
    const graph = getGraph(summary);

    if (Array.isArray(graph)) {
      return graph;
    }

    return (
      graph?.relationships ??
      graph?.results ??
      []
    );
  }, [summary]);

  const tabs = [
    {
      id: "overview",
      label: "Overview",
      icon: Target,
    },
    {
      id: "evidence",
      label: "Evidence",
      icon: FileText,
    },
    {
      id: "entities",
      label: "Entities",
      icon: Users,
    },
    {
      id: "relationships",
      label: "Relationships",
      icon: GitBranch,
    },
    {
      id: "analysis",
      label: "Analysis",
      icon: BarChart3,
    },
  ];

  return (
    <main className="tn-page tn-investigation-workspace">
      <section className="tn-iw-hero">
        <div className="tn-iw-hero-copy">
          <div className="tn-eyebrow">
            TRINETRA / INVESTIGATION OPERATIONS
          </div>

          <h1 className="tn-page-title">
            Investigation Workspace
          </h1>

          <p className="tn-page-subtitle">
            One operational view for investigation
            scope, evidence, graph relationships,
            analytical signals, and investigative
            context.
          </p>
        </div>

        <div className="tn-iw-controls">
          <label className="tn-iw-selector">
            <span>ACTIVE INVESTIGATION</span>

            <div>
              <Target size={16} />

              <select
                value={investigationId}
                onChange={(event) => {
                  setInvestigationId(
                    event.target.value
                  );
                  setActiveInvestigationId(
                    event.target.value
                  );
                  setSelectedEvidence(null);
                  setActiveTab("overview");
                }}
              >
                <option value="">
                  Select investigation
                </option>

                {investigations.map(
                  (item) => {
                    const id =
                      idOf(item);

                    return (
                      <option
                        key={id}
                        value={id}
                      >
                        {investigationNumberOf(
                          item
                        )}{" "}
                        —{" "}
                        {titleOf(item)}
                      </option>
                    );
                  }
                )}
              </select>

              <ChevronDown
                size={15}
              />
            </div>
          </label>

          <button
            type="button"
            className="tn-iw-refresh"
            onClick={() =>
              loadWorkspace(true)
            }
            disabled={
              refreshing ||
              !investigationId
            }
          >
            <RefreshCw
              size={16}
              className={
                refreshing
                  ? "tn-spin"
                  : ""
              }
            />

            Refresh
          </button>
        </div>
      </section>

      {error && (
        <motion.div
          className="tn-iw-alert"
          initial={{
            opacity: 0,
            y: -8,
          }}
          animate={{
            opacity: 1,
            y: 0,
          }}
        >
          <AlertTriangle size={17} />

          <span>{error}</span>

          <button
            type="button"
            onClick={() =>
              setError("")
            }
          >
            <X size={15} />
          </button>
        </motion.div>
      )}

      {loading &&
      !selectedInvestigation ? (
        <div className="tn-iw-loading tn-glass-panel">
          <Loader2
            size={30}
            className="tn-spin"
          />

          <strong>
            Loading investigation workspace
          </strong>

          <span>
            Resolving investigation context...
          </span>
        </div>
      ) : !selectedInvestigation ? (
        <div className="tn-iw-empty tn-glass-panel">
          <Target size={32} />

          <h2>
            No investigation selected
          </h2>

          <p>
            Select an investigation above to
            open its operational workspace.
          </p>
        </div>
      ) : (
        <>
          <section className="tn-iw-identity tn-glass-panel">
            <div className="tn-iw-identity-main">
              <div className="tn-iw-investigation-mark">
                <Activity size={25} />
              </div>

              <div>
                <div className="tn-iw-number">
                  {investigationNumberOf(
                    selectedInvestigation
                  )}
                </div>

                <h2>
                  {titleOf(
                    selectedInvestigation
                  )}
                </h2>

                <p>
                  {numberOrDash(
                    selectedInvestigation?.objective
                  )}
                </p>
              </div>
            </div>

            <div className="tn-iw-identity-meta">
              <div>
                <span>STATUS</span>

                <strong
                  className={`tn-iw-status status-${statusOf(
                    selectedInvestigation
                  )}`}
                >
                  <CircleDot
                    size={11}
                  />

                  {STATUS_LABELS[
                    statusOf(
                      selectedInvestigation
                    )
                  ] ??
                    formatLabel(
                      statusOf(
                        selectedInvestigation
                      )
                    )}
                </strong>
              </div>

              <div>
                <span>INVESTIGATOR</span>

                <strong>
                  {numberOrDash(
                    selectedInvestigation?.investigator
                  )}
                </strong>
              </div>

              <div>
                <span>UNIT</span>

                <strong>
                  {numberOrDash(
                    selectedInvestigation?.investigation_unit
                  )}
                </strong>
              </div>
            </div>
          </section>

          <section className="tn-iw-metrics">
            <div className="tn-iw-metric tn-glass-panel">
              <div className="tn-iw-metric-icon">
                <ShieldAlert size={18} />
              </div>

              <div>
                <span>Risk signal</span>

                <strong
                  className={`risk-${riskTone}`}
                >
                  {riskScore !== null
                    ? `${riskScore}/100`
                    : "—"}
                </strong>

                <small>
                  {riskLevel}
                </small>
              </div>
            </div>

            <div className="tn-iw-metric tn-glass-panel">
              <div className="tn-iw-metric-icon">
                <FileText size={18} />
              </div>

              <div>
                <span>Linked evidence</span>

                <strong>
                  {evidence.length}
                </strong>

                <small>
                  Investigation scoped
                </small>
              </div>
            </div>

            <div className="tn-iw-metric tn-glass-panel">
              <div className="tn-iw-metric-icon">
                <GitBranch size={18} />
              </div>

              <div>
                <span>Graph relationships</span>

                <strong>
                  {graphCount}
                </strong>

                <small>
                  Returned analytical records
                </small>
              </div>
            </div>

            <div className="tn-iw-metric tn-glass-panel">
              <div className="tn-iw-metric-icon">
                <BrainCircuit size={18} />
              </div>

              <div>
                <span>Patterns</span>

                <strong>
                  {patternCount}
                </strong>

                <small>
                  Analytical signals
                </small>
              </div>
            </div>
          </section>

          <section className="tn-iw-tabs tn-glass-panel">
            {tabs.map(
              ({
                id,
                label,
                icon: Icon,
              }) => (
                <button
                  type="button"
                  key={id}
                  className={
                    activeTab === id
                      ? "is-active"
                      : ""
                  }
                  onClick={() =>
                    setActiveTab(id)
                  }
                >
                  <Icon size={15} />

                  {label}
                </button>
              )
            )}
          </section>

          <AnimatePresence
            mode="wait"
          >
            {activeTab ===
              "overview" && (
              <motion.section
                key="overview"
                className="tn-iw-content-grid"
                initial={{
                  opacity: 0,
                  y: 8,
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
                <div className="tn-iw-card tn-glass-panel">
                  <div className="tn-iw-card-heading">
                    <div>
                      <span>
                        INVESTIGATION CONTEXT
                      </span>

                      <h3>
                        Operational overview
                      </h3>
                    </div>

                    <Target size={18} />
                  </div>

                  <div className="tn-iw-detail-grid">
                    <div>
                      <span>
                        Investigation ID
                      </span>

                      <strong>
                        {numberOrDash(
                          idOf(
                            selectedInvestigation
                          )
                        )}
                      </strong>
                    </div>

                    <div>
                      <span>
                        Case ID
                      </span>

                      <strong>
                        {numberOrDash(
                          selectedInvestigation?.case_id
                        )}
                      </strong>
                    </div>

                    <div>
                      <span>
                        Outcome
                      </span>

                      <strong>
                        {formatLabel(
                          outcomeOf(
                            selectedInvestigation
                          )
                        )}
                      </strong>
                    </div>

                    <div>
                      <span>
                        Started
                      </span>

                      <strong>
                        {formatDate(
                          selectedInvestigation?.started_at
                        )}
                      </strong>
                    </div>

                    <div>
                      <span>
                        Completed
                      </span>

                      <strong>
                        {formatDate(
                          selectedInvestigation?.completed_at
                        )}
                      </strong>
                    </div>

                    <div>
                      <span>
                        Updated
                      </span>

                      <strong>
                        {formatDate(
                          selectedInvestigation?.updated_at
                        )}
                      </strong>
                    </div>
                  </div>
                </div>

                <div className="tn-iw-card tn-glass-panel">
                  <div className="tn-iw-card-heading">
                    <div>
                      <span>
                        ANALYTICAL SIGNALS
                      </span>

                      <h3>
                        Detected patterns
                      </h3>
                    </div>

                    <BrainCircuit size={18} />
                  </div>

                  <div className="tn-iw-pattern-list">
                    {patterns.length >
                    0 ? (
                      patterns
                        .slice(0, 8)
                        .map(
                          (
                            pattern,
                            index
                          ) => (
                            <div
                              className="tn-iw-pattern"
                              key={
                                pattern?.id ??
                                pattern?.pattern_type ??
                                index
                              }
                            >
                              <div className="tn-iw-pattern-dot" />

                              <div>
                                <strong>
                                  {pattern?.title ??
                                    pattern?.pattern_type ??
                                    "Analytical pattern"}
                                </strong>

                                <span>
                                  {pattern?.description ??
                                    "Pattern returned by the analytics engine."}
                                </span>
                              </div>

                              <small>
                                {pattern?.confidence !=
                                null
                                  ? `${Math.round(
                                      Number(
                                        pattern.confidence
                                      ) *
                                        100
                                    )}%`
                                  : "—"}
                              </small>
                            </div>
                          )
                        )
                    ) : (
                      <div className="tn-iw-no-data">
                        No pattern observations
                        returned.
                      </div>
                    )}
                  </div>
                </div>

                <div className="tn-iw-card tn-glass-panel tn-iw-wide">
                  <div className="tn-iw-card-heading">
                    <div>
                      <span>
                        INVESTIGATIVE FINDINGS
                      </span>

                      <h3>
                        Recorded findings
                      </h3>
                    </div>

                    <CheckCircle2 size={18} />
                  </div>

                  {findings.length >
                  0 ? (
                    <div className="tn-iw-findings">
                      {findings.map(
                        (
                          finding,
                          index
                        ) => (
                          <div
                            className="tn-iw-finding"
                            key={
                              finding?.id ??
                              index
                            }
                          >
                            <span>
                              {String(
                                index + 1
                              ).padStart(
                                2,
                                "0"
                              )}
                            </span>

                            <div>
                              <strong>
                                {finding?.title ??
                                  "Finding"}
                              </strong>

                              <p>
                                {finding?.content ??
                                  finding?.description ??
                                  String(
                                    finding
                                  )}
                              </p>
                            </div>
                          </div>
                        )
                      )}
                    </div>
                  ) : (
                    <div className="tn-iw-no-data">
                      No structured findings
                      are currently recorded.
                    </div>
                  )}
                </div>
              </motion.section>
            )}

            {activeTab ===
              "evidence" && (
              <motion.section
                key="evidence"
                className="tn-iw-single-card tn-glass-panel"
                initial={{
                  opacity: 0,
                  y: 8,
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
                <div className="tn-iw-card-heading">
                  <div>
                    <span>
                      INVESTIGATION EVIDENCE
                    </span>

                    <h3>
                      {evidence.length} linked
                      evidence record
                      {evidence.length === 1
                        ? ""
                        : "s"}
                    </h3>
                  </div>

                  <FileText size={18} />
                </div>

                {evidence.length >
                0 ? (
                  <div className="tn-iw-evidence-list">
                    {evidence.map(
                      (item, index) => (
                        <button
                          type="button"
                          className="tn-iw-evidence-row"
                          key={
                            getEvidenceId(
                              item
                            ) ??
                            index
                          }
                          onClick={() =>
                            setSelectedEvidence(
                              item
                            )
                          }
                        >
                          <div className="tn-iw-evidence-icon">
                            <FileText
                              size={18}
                            />
                          </div>

                          <div className="tn-iw-evidence-main">
                            <strong>
                              {getEvidenceTitle(
                                item
                              )}
                            </strong>

                            <span>
                              {getEvidenceNumber(
                                item
                              )}
                            </span>
                          </div>

                          <div className="tn-iw-evidence-meta">
                            <span>
                              {formatLabel(
                                item?.evidence_type ??
                                  item?.evidenceType ??
                                  "document"
                              )}
                            </span>

                            <small>
                              {formatLabel(
                                getEvidenceStatus(
                                  item
                                )
                              )}
                            </small>
                          </div>

                          <ChevronDown
                            size={16}
                            className="tn-iw-evidence-chevron"
                          />
                        </button>
                      )
                    )}
                  </div>
                ) : (
                  <div className="tn-iw-no-data">
                    No evidence is explicitly
                    linked to this investigation.
                  </div>
                )}
              </motion.section>
            )}

            {activeTab ===
              "entities" && (
              <motion.section
                key="entities"
                className="tn-iw-single-card tn-glass-panel"
                initial={{
                  opacity: 0,
                  y: 8,
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
                <div className="tn-iw-card-heading">
                  <div>
                    <span>
                      GRAPH ENTITIES
                    </span>

                    <h3>
                      Investigation-connected
                      entities
                    </h3>
                  </div>

                  <Users size={18} />
                </div>

                {relationships.length >
                0 ? (
                  <div className="tn-iw-entity-grid">
                    {Array.from(
                      new Map(
                        relationships.flatMap(
                          (record) => {
                            const source =
                              record?.source ??
                              record;

                            const target =
                              record?.target ??
                              {};

                            const sourceEntity =
                              {
                                name:
                                  source?.value ??
                                  source?.name ??
                                  record?.value,
                                type:
                                  source?.type ??
                                  source?.entity_type ??
                                  record?.entity_type,
                              };

                            const targetEntity =
                              {
                                name:
                                  target?.value ??
                                  target?.name ??
                                  record?.neighbor_value,
                                type:
                                  target?.type ??
                                  target?.entity_type,
                              };

                            return [
                              sourceEntity,
                              targetEntity,
                            ].filter(
                              (entity) =>
                                entity.name
                            );
                          }
                        ).map(
                          (entity) => [
                            `${entity.type}:${entity.name}`,
                            entity,
                          ]
                        )
                      ).values()
                    ).map(
                      (entity) => (
                        <div
                          className="tn-iw-entity-card"
                          key={`${entity.type}:${entity.name}`}
                        >
                          <div className="tn-iw-entity-avatar">
                            <Users
                              size={17}
                            />
                          </div>

                          <div>
                            <span>
                              {formatLabel(
                                getEntityType(
                                  entity
                                )
                              )}
                            </span>

                            <strong>
                              {getEntityName(
                                entity
                              )}
                            </strong>
                          </div>
                        </div>
                      )
                    )}
                  </div>
                ) : (
                  <div className="tn-iw-no-data">
                    No connected entity records
                    were returned by the investigation
                    graph summary.
                  </div>
                )}
              </motion.section>
            )}

            {activeTab ===
              "relationships" && (
              <motion.section
                key="relationships"
                className="tn-iw-single-card tn-glass-panel"
                initial={{
                  opacity: 0,
                  y: 8,
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
                <div className="tn-iw-card-heading">
                  <div>
                    <span>
                      GRAPH RELATIONSHIPS
                    </span>

                    <h3>
                      Recorded connection
                      traces
                    </h3>
                  </div>

                  <GitBranch size={18} />
                </div>

                {relationships.length >
                0 ? (
                  <div className="tn-iw-relationship-list">
                    {relationships.map(
                      (
                        record,
                        index
                      ) => {
                        const source =
                          record?.source ??
                          record;

                        const target =
                          record?.target ??
                          {};

                        const sourceName =
                          source?.value ??
                          source?.name ??
                          record?.value ??
                          "Unknown";

                        const targetName =
                          target?.value ??
                          target?.name ??
                          record?.neighbor_value ??
                          "Unknown";

                        const confidence =
                          getRelationshipConfidence(
                            record
                          );

                        return (
                          <div
                            className="tn-iw-relationship-row"
                            key={
                              record?.id ??
                              record?.relationship_id ??
                              index
                            }
                          >
                            <div className="tn-iw-rel-entity">
                              <span>
                                {formatLabel(
                                  source?.type ??
                                    source?.entity_type ??
                                    record?.entity_type
                                )}
                              </span>

                              <strong>
                                {sourceName}
                              </strong>
                            </div>

                            <div className="tn-iw-rel-type">
                              <GitBranch
                                size={15}
                              />

                              <strong>
                                {formatLabel(
                                  getRelationshipType(
                                    record
                                  )
                                )}
                              </strong>

                              {confidence !==
                                null && (
                                <span>
                                  {confidence}%
                                </span>
                              )}
                            </div>

                            <div className="tn-iw-rel-entity">
                              <span>
                                {formatLabel(
                                  target?.type ??
                                    target?.entity_type
                                )}
                              </span>

                              <strong>
                                {targetName}
                              </strong>
                            </div>
                          </div>
                        );
                      }
                    )}
                  </div>
                ) : (
                  <div className="tn-iw-no-data">
                    No relationship records were
                    returned for this investigation.
                  </div>
                )}
              </motion.section>
            )}

            {activeTab ===
              "analysis" && (
              <motion.section
                key="analysis"
                className="tn-iw-analysis-grid"
                initial={{
                  opacity: 0,
                  y: 8,
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
                <div className="tn-iw-card tn-glass-panel">
                  <div className="tn-iw-card-heading">
                    <div>
                      <span>
                        RISK ASSESSMENT
                      </span>

                      <h3>
                        Analytical risk signal
                      </h3>
                    </div>

                    <ShieldAlert size={18} />
                  </div>

                  <div className="tn-iw-risk-display">
                    <div
                      className={`tn-iw-risk-ring risk-${riskTone}`}
                    >
                      <strong>
                        {riskScore !== null
                          ? riskScore
                          : "—"}
                      </strong>

                      <span>
                        /100
                      </span>
                    </div>

                    <div>
                      <span>
                        CURRENT LEVEL
                      </span>

                      <strong>
                        {riskLevel}
                      </strong>

                      <p>
                        Risk indicators are analytical
                        signals and should not be treated
                        as determinations of guilt.
                      </p>
                    </div>
                  </div>
                </div>

                <div className="tn-iw-card tn-glass-panel">
                  <div className="tn-iw-card-heading">
                    <div>
                      <span>
                        INVESTIGATION TIMELINE
                      </span>

                      <h3>
                        Operational dates
                      </h3>
                    </div>

                    <Clock3 size={18} />
                  </div>

                  <div className="tn-iw-timeline">
                    <div>
                      <span>
                        STARTED
                      </span>

                      <strong>
                        {formatDate(
                          selectedInvestigation?.started_at
                        )}
                      </strong>
                    </div>

                    <div>
                      <span>
                        COMPLETED
                      </span>

                      <strong>
                        {formatDate(
                          selectedInvestigation?.completed_at
                        )}
                      </strong>
                    </div>
                  </div>
                </div>

                <div className="tn-iw-card tn-glass-panel tn-iw-wide">
                  <div className="tn-iw-card-heading">
                    <div>
                      <span>
                        INVESTIGATION CONCLUSION
                      </span>

                      <h3>
                        Recorded analytical conclusion
                      </h3>
                    </div>

                    <CheckCircle2 size={18} />
                  </div>

                  <div className="tn-iw-conclusion">
                    {selectedInvestigation?.conclusion ||
                      "No investigation conclusion has been recorded."}
                  </div>
                </div>
              </motion.section>
            )}
          </AnimatePresence>
        </>
      )}

      <AnimatePresence>
        {selectedEvidence && (
          <>
            <motion.div
              className="tn-iw-drawer-backdrop"
              initial={{
                opacity: 0,
              }}
              animate={{
                opacity: 1,
              }}
              exit={{
                opacity: 0,
              }}
              onClick={() =>
                setSelectedEvidence(null)
              }
            />

            <motion.aside
              className="tn-iw-evidence-drawer"
              initial={{
                x: "100%",
              }}
              animate={{
                x: 0,
              }}
              exit={{
                x: "100%",
              }}
              transition={{
                type: "spring",
                stiffness: 300,
                damping: 30,
              }}
            >
              <div className="tn-iw-drawer-header">
                <div>
                  <span>
                    EVIDENCE RECORD
                  </span>

                  <h2>
                    {getEvidenceNumber(
                      selectedEvidence
                    )}
                  </h2>
                </div>

                <button
                  type="button"
                  onClick={() =>
                    setSelectedEvidence(
                      null
                    )
                  }
                  aria-label="Close evidence"
                >
                  <X size={18} />
                </button>
              </div>

              <div className="tn-iw-drawer-content">
                <div className="tn-iw-drawer-icon">
                  <FileText size={25} />
                </div>

                <h3>
                  {getEvidenceTitle(
                    selectedEvidence
                  )}
                </h3>

                <div className="tn-iw-drawer-status">
                  {formatLabel(
                    getEvidenceStatus(
                      selectedEvidence
                    )
                  )}
                </div>

                <div className="tn-iw-drawer-section">
                  <span>
                    EVIDENCE TYPE
                  </span>

                  <strong>
                    {formatLabel(
                      selectedEvidence?.evidence_type ??
                        selectedEvidence?.evidenceType ??
                        "document"
                    )}
                  </strong>
                </div>

                <div className="tn-iw-drawer-section">
                  <span>
                    SOURCE REFERENCE
                  </span>

                  <strong>
                    {numberOrDash(
                      selectedEvidence?.source_reference ??
                        selectedEvidence?.sourceReference
                    )}
                  </strong>
                </div>

                <div className="tn-iw-drawer-section">
                  <span>
                    INVESTIGATION RELATION
                  </span>

                  <strong>
                    {formatLabel(
                      selectedEvidence?.investigation_relation ??
                        "linked"
                    )}
                  </strong>
                </div>

                <div className="tn-iw-drawer-section">
                  <span>
                    DESCRIPTION
                  </span>

                  <p>
                    {selectedEvidence?.description ||
                      selectedEvidence?.extracted_text ||
                      "No description or extracted text is available."}
                  </p>
                </div>

                <div className="tn-iw-drawer-section">
                  <span>
                    EXTRACTION CONFIDENCE
                  </span>

                  <strong>
                    {selectedEvidence?.extraction_confidence !=
                    null
                      ? `${Math.round(
                          Number(
                            selectedEvidence.extraction_confidence
                          ) * 100
                        )}%`
                      : "—"}
                  </strong>
                </div>
              </div>
            </motion.aside>
          </>
        )}
      </AnimatePresence>

      <div className="tn-iw-footer-note">
        <ShieldCheck size={14} />

        <span>
          Workspace data is retrieved from the live
          TRINETRA APIs and is scoped to the selected
          investigation. Analytical signals require
          verification against underlying evidence.
        </span>
      </div>
    </main>
  );
}
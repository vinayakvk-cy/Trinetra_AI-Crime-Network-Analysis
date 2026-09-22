import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Activity,
  AlertTriangle,
  Database,
  FileText,
  GitBranch,
  RefreshCw,
  ShieldAlert,
  Users,
} from "lucide-react";

import GlassCard from "../components/ui/GlassCard";
import StatCard from "../components/ui/StatCard";
import Badge from "../components/ui/Badge";
import InvestigationGraph from "../components/graph/InvestigationGraph";

import { getDashboardData } from "../services/dashboardApi";
import { getActiveInvestigationId } from "../services/activeInvestigation";
import {
  extractInvestigationMetadata,
} from "../services/analyticsApi";
import { normalizeEvidence } from "../services/evidenceApi";
import {
  normalizeRelationships,
} from "../services/graphApi";


function getRiskScore(summary) {
  const candidates = [
    summary?.risk?.score,
    summary?.risk?.risk_score,
    summary?.risk?.results?.score,
    summary?.risk?.results?.risk_score,
    summary?.risk?.results?.overall_score,
    summary?.risk?.assessment?.score,
    summary?.risk?.assessment?.risk_score,

    summary?.risk?.results?.risk?.score,
    summary?.risk?.results?.risk?.risk_score,
  ];

  const value = candidates.find(
    (item) =>
      typeof item === "number" &&
      Number.isFinite(item)
  );

  if (value === undefined) {
    return null;
  }

  return value >= 0 && value <= 1
    ? Math.round(value * 100)
    : Math.round(value);
}

function getRiskLevel(score) {
  if (score === null || score === undefined) {
    return "UNKNOWN";
  }

  if (score >= 75) {
    return "HIGH";
  }

  if (score >= 50) {
    return "MEDIUM";
  }

  if (score >= 25) {
    return "LOW";
  }

  return "MINIMAL";
}

function extractEvidence(payload) {
  if (!payload) {
    return [];
  }

  const records = Array.isArray(payload)
    ? payload
    : payload.evidence ||
      payload.results ||
      payload.data ||
      [];

  return records
    .map(normalizeEvidence)
    .filter(Boolean);
}

function extractRelationships(summary) {
  if (!summary) {
    return [];
  }

  const graph = summary.graph;

  let records = [];

  if (Array.isArray(graph)) {
    records = graph;
  } else if (Array.isArray(graph?.relationships)) {
    records = graph.relationships;
  } else if (Array.isArray(graph?.results)) {
    records = graph.results;
  } else if (Array.isArray(graph?.connections)) {
    records = graph.connections;
  }

  return normalizeRelationships(records);
}

function formatStatus(value) {
  if (!value) {
    return "UNKNOWN";
  }

  return String(value)
    .replace(/_/g, " ")
    .toUpperCase();
}

function formatDate(value) {
  if (!value) {
    return "—";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return String(value);
  }

  return date.toLocaleString();
}

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);
  const [lastSync, setLastSync] = useState(null);

  const loadDashboard = useCallback(
    async (manual = false) => {
      if (manual) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }

      setError(null);

      try {
        const result =
          await getDashboardData(
            getActiveInvestigationId()
          );

        setData(result);
        setLastSync(new Date());

        if (result.errors?.length) {
          setError(result.errors.join(" • "));
        }
      } catch (err) {
        setError(
          typeof err?.response?.data?.detail === "string"
            ? err.response.data.detail
            : err?.message || "Failed to load dashboard."
        );
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    []
  );

  useEffect(() => {
    loadDashboard();

    const interval = setInterval(() => {
      loadDashboard();
    }, 10000);

    return () => clearInterval(interval);
  }, [loadDashboard]);

  const summary = data?.summary || null;

  const metadata = useMemo(
    () => extractInvestigationMetadata(summary),
    [summary]
  );

  const evidence = useMemo(
    () => extractEvidence(data?.evidence),
    [data?.evidence]
  );

  const relationships = useMemo(
    () => extractRelationships(summary),
    [summary]
  );

  const riskScore = useMemo(
    () => getRiskScore(summary),
    [summary]
  );

  const riskLevel = getRiskLevel(riskScore);

  const graphStats = data?.stats || {};

  const nodeCount =
    graphStats.nodes ??
    graphStats.node_count ??
    graphStats.results?.nodes ??
    0;

  const relationshipCount =
    graphStats.relationships ??
    graphStats.relationship_count ??
    graphStats.results?.relationships ??
    0;

  const neo4jHealthy =
    data?.health?.neo4j === true;

  const evidenceCount = evidence.length;

  const patternCount =
    Array.isArray(summary?.patterns)
      ? summary.patterns.length
      : Array.isArray(summary?.patterns?.results)
        ? summary.patterns.results.length
        : 0;

  return (
    <div className="tn-page tn-dashboard-page">
      <div className="tn-page-header">
        <div>
          <div className="tn-eyebrow">
            TRINETRA / COMMAND CENTER
          </div>

          <h1 className="tn-page-title">
            Investigation Dashboard
          </h1>

          <p className="tn-page-subtitle">
            Live intelligence overview for the active investigation.
          </p>
        </div>

        <div className="tn-dashboard-actions">
          <Badge>
            <Activity size={13} />
            {neo4jHealthy
              ? "SYSTEM ONLINE"
              : "GRAPH OFFLINE"}
          </Badge>

          <button
            type="button"
            className="tn-icon-button"
            onClick={() => loadDashboard(true)}
            disabled={refreshing}
            title="Refresh dashboard"
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
      </div>

      {error && (
        <GlassCard className="tn-api-warning">
          <AlertTriangle size={18} />

          <div>
            <strong>
              Partial API response
            </strong>

            <span>
              {error}
            </span>
          </div>
        </GlassCard>
      )}

      <div className="tn-dashboard-status-row">
        <span>
          Last synchronization:{" "}
          <strong>
            {formatDate(lastSync)}
          </strong>
        </span>

        <span className="tn-live-indicator">
          <span />
          AUTO REFRESH 10s
        </span>
      </div>

      <div className="tn-stat-grid">
        <StatCard
          icon={<Database size={18} />}
          label="Graph Nodes"
          value={loading ? "…" : nodeCount}
          meta="Neo4j"
        />

        <StatCard
          icon={<GitBranch size={18} />}
          label="Relationships"
          value={
            loading
              ? "…"
              : relationshipCount
          }
          meta="Connected"
        />

        <StatCard
          icon={<FileText size={18} />}
          label="Evidence"
          value={
            loading
              ? "…"
              : evidenceCount
          }
          meta="Records"
        />

        <StatCard
          icon={<ShieldAlert size={18} />}
          label="Risk Signal"
          value={
            loading
              ? "…"
              : riskScore ?? "—"
          }
          meta={
            riskScore !== null
              ? riskLevel
              : "NO SIGNAL"
          }
        />
      </div>

      <div className="tn-dashboard-main-grid">
        <GlassCard className="tn-investigation-card">
          <div className="tn-section-header">
            <div>
              <div className="tn-section-kicker">
                ACTIVE INVESTIGATION
              </div>

              <h2>
                {metadata?.investigationNumber ||
                  "No active investigation"}
              </h2>

              <p>
                {metadata?.title ||
                  "Investigation"}
              </p>
            </div>

            <Badge>
              {formatStatus(
                metadata?.status
              )}
            </Badge>
          </div>

          <div className="tn-investigation-details">
            <div>
              <span>Case</span>

              <strong>
                {metadata?.caseNumber ||
                  "UNKNOWN"}
              </strong>

              {metadata?.caseTitle && (
                <small>
                  {metadata.caseTitle}
                </small>
              )}
            </div>

            <div>
              <span>Priority</span>

              <strong>
                {formatStatus(
                  metadata?.priority
                )}
              </strong>
            </div>

            <div>
              <span>Investigator</span>

              <strong>
                {metadata?.investigator ||
                  "—"}
              </strong>
            </div>

            <div>
              <span>Unit</span>

              <strong>
                {metadata?.investigationUnit ||
                  "—"}
              </strong>
            </div>
          </div>

          {metadata?.objective && (
            <div className="tn-objective">
              <span>OBJECTIVE</span>

              <p>
                {metadata.objective}
              </p>
            </div>
          )}
        </GlassCard>

        <GlassCard className="tn-risk-card">
          <div className="tn-section-header">
            <div>
              <div className="tn-section-kicker">
                ANALYTICS
              </div>

              <h2>
                Risk Assessment
              </h2>
            </div>

            <ShieldAlert size={20} />
          </div>

          <div className="tn-risk-display">
            <div className="tn-risk-number">
              {riskScore ?? "—"}
              {riskScore !== null && (
                <small>/100</small>
              )}
            </div>

            <Badge>
              {riskLevel}
            </Badge>
          </div>

          <div className="tn-risk-bar">
            <div
              style={{
                width:
                  riskScore === null
                    ? "0%"
                    : `${Math.min(
                        100,
                        Math.max(
                          0,
                          riskScore
                        )
                      )}%`,
              }}
            />
          </div>

          <p className="tn-muted">
            Analytical signal only. Risk indicators
            must not be treated as determinations
            of guilt.
          </p>
        </GlassCard>
      </div>

      <GlassCard className="tn-graph-hero-card">
        <div className="tn-section-header">
          <div>
            <div className="tn-section-kicker">
              LIVE KNOWLEDGE GRAPH
            </div>

            <h2>
              Investigation Graph
            </h2>

            <p>
              {relationships.length
                ? `${relationships.length} relationship records available`
                : "No relationship records returned"}
            </p>
          </div>

          <Badge>
            <GitBranch size={13} />
            NEO4J
          </Badge>
        </div>

        <div className="tn-dashboard-graph-container">
          <InvestigationGraph
            relationships={relationships}
            loading={loading}
          />
        </div>
      </GlassCard>

      <div className="tn-dashboard-bottom-grid">
        <GlassCard>
          <div className="tn-section-header">
            <div>
              <div className="tn-section-kicker">
                EVIDENCE
              </div>

              <h2>
                Recent Evidence
              </h2>
            </div>

            <Badge>
              {evidenceCount} RECORDS
            </Badge>
          </div>

          <div className="tn-evidence-list">
            {evidence.length === 0 ? (
              <div className="tn-empty-state">
                No evidence records returned.
              </div>
            ) : (
              evidence
                .slice(0, 6)
                .map((item) => (
                  <div
                    key={
                      item.id ||
                      item.evidenceNumber
                    }
                    className="tn-evidence-row"
                  >
                    <div className="tn-evidence-icon">
                      <FileText size={17} />
                    </div>

                    <div className="tn-evidence-info">
                      <strong>
                        {item.title}
                      </strong>

                      <span>
                        {item.evidenceNumber}
                        {" • "}
                        {item.evidenceType}
                      </span>
                    </div>

                    <Badge>
                      {formatStatus(
                        item.status
                      )}
                    </Badge>
                  </div>
                ))
            )}
          </div>
        </GlassCard>

        <GlassCard>
          <div className="tn-section-header">
            <div>
              <div className="tn-section-kicker">
                INTELLIGENCE
              </div>

              <h2>
                Investigation Signals
              </h2>
            </div>

            <Badge>
              {patternCount} PATTERNS
            </Badge>
          </div>

          <div className="tn-signal-grid">
            <div className="tn-signal-item">
              <Users size={17} />

              <div>
                <span>
                  Connected entities
                </span>

                <strong>
                  {relationships.length
                    ? new Set(
                        relationships.flatMap(
                          (item) => [
                            item.sourceValue,
                            item.targetValue,
                          ]
                        )
                      ).size
                    : "—"}
                </strong>
              </div>
            </div>

            <div className="tn-signal-item">
              <GitBranch size={17} />

              <div>
                <span>
                  Relationship records
                </span>

                <strong>
                  {relationshipCount}
                </strong>
              </div>
            </div>

            <div className="tn-signal-item">
              <FileText size={17} />

              <div>
                <span>
                  Evidence records
                </span>

                <strong>
                  {evidenceCount}
                </strong>
              </div>
            </div>

            <div className="tn-signal-item">
              <ShieldAlert size={17} />

              <div>
                <span>
                  Risk score
                </span>

                <strong>
                  {riskScore ?? "—"}
                </strong>
              </div>
            </div>
          </div>
        </GlassCard>
      </div>
    </div>
  );
}
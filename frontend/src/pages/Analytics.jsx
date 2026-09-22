import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Activity,
  AlertTriangle,
  BarChart3,
  BrainCircuit,
  ChevronDown,
  CircleDot,
  Gauge,
  Network,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  Target,
  TrendingUp,
  Users,
} from "lucide-react";

import GlassCard from "../components/ui/GlassCard";
import Badge from "../components/ui/Badge";
import { getActiveInvestigationId, setActiveInvestigationId } from "../services/activeInvestigation";
import { listInvestigations } from "../services/investigationsApi";
import { getApiErrorMessage } from "../services/api";
import {
  getAnalyticsSummary,
  getGraphCentrality,
  getGraphConnectivity,
  getPatterns,
  getRisk,
  getSimilarity,
} from "../services/analyticsApi";
import "./analytics-page.css";

const REFRESH_INTERVAL_MS = 10000;

const firstDefined = (...values) =>
  values.find((value) => value !== undefined && value !== null);

const asArray = (value) => {
  if (Array.isArray(value)) return value;
  if (Array.isArray(value?.results)) return value.results;
  if (Array.isArray(value?.data)) return value.data;
  if (Array.isArray(value?.items)) return value.items;
  if (Array.isArray(value?.patterns)) return value.patterns;
  if (Array.isArray(value?.connections)) return value.connections;
  return [];
};

const asObject = (value) => {
  if (!value || typeof value !== "object") return {};
  if (value.results && typeof value.results === "object" && !Array.isArray(value.results)) {
    return value.results;
  }
  // Entity risk responses use `result`, while case/investigation
  // risk responses use `results`. Normalize both API shapes here.
  if (value.result && typeof value.result === "object" && !Array.isArray(value.result)) {
    return value.result;
  }
  if (value.data && typeof value.data === "object" && !Array.isArray(value.data)) {
    return value.data;
  }
  return value;
};

const numberValue = (value, fallback = 0) => {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : fallback;
};

const percentage = (value) => {
  const numeric = numberValue(value);
  if (numeric <= 1) return Math.round(numeric * 100);
  return Math.round(numeric);
};

const formatNumber = (value) =>
  new Intl.NumberFormat("en-US").format(numberValue(value));

const titleCase = (value) =>
  String(value || "")
    .replace(/_/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());

const getRiskValue = (payload) => {
  const root = asObject(payload);
  const candidates = [
    root.risk_score,
    root.score,
    root.risk,
    root.value,
    root.overall_risk,
    root.risk?.score,
    root.risk?.risk_score,
  ];

  for (const candidate of candidates) {
    if (candidate !== undefined && candidate !== null && Number.isFinite(Number(candidate))) {
      const n = Number(candidate);
      return n <= 1 ? Math.round(n * 100) : Math.round(n);
    }
  }

  return null;
};

const getRiskLevel = (payload, score) => {
  const root = asObject(payload);
  const explicit = firstDefined(
    root.risk_level,
    root.level,
    root.risk_label,
    root.category,
    root.risk?.level
  );

  if (explicit) return titleCase(explicit);
  if (score === null) return "Unavailable";

  if (score >= 75) return "High";
  if (score >= 50) return "Moderate";
  if (score >= 25) return "Low";
  return "Minimal";
};

const normalizeCentrality = (payload) => {
  const rows = asArray(payload);

  return rows
    .map((row, index) => {
      const item = asObject(row);
      const entityType = firstDefined(
        item.entity_type,
        item.entityType,
        item.type,
        item.node_type
      );
      const entityValue = firstDefined(
        item.entity_value,
        item.entityValue,
        item.value,
        item.name,
        item.entity_name
      );

      const score = numberValue(
        firstDefined(
          item.centrality,
          item.centrality_score,
          item.score,
          item.value,
          item.degree
        )
      );

      const degree = numberValue(
        firstDefined(item.degree, item.total_degree, item.connectivity, item.neighbor_count),
        score
      );

      return {
        id: firstDefined(item.entity_id, item.id, item.node_id, `${entityType}-${entityValue}-${index}`),
        entityId: firstDefined(item.entity_id, item.id),
        type: String(entityType || "ENTITY"),
        value: String(entityValue || "Unknown entity"),
        score,
        degree,
      };
    })
    .filter((row) => row.value !== "Unknown entity")
    .sort((a, b) => b.score - a.score);
};

const normalizePatterns = (payload) => {
  const rows = asArray(payload);

  return rows.map((row, index) => {
    const item = asObject(row);

    return {
      id: firstDefined(item.id, item.pattern_id, item.name, `pattern-${index}`),
      name: String(
        firstDefined(
          item.pattern_name,
          item.pattern_type,
          item.type,
          item.name,
          "Analytical pattern"
        )
      ),
      description: String(
        firstDefined(
          item.description,
          item.explanation,
          item.summary,
          "Pattern signal returned by the analytics engine."
        )
      ),
      severity: String(
        firstDefined(item.severity, item.level, item.risk_level, "signal")
      ),
      entity: String(
        firstDefined(item.entity_value, item.entity_name, item.value, "")
      ),
    };
  });
};

const extractSummaryGraph = (summary) => {
  const root = summary?.graph ?? {};
  return asObject(root);
};

const extractSummaryRisk = (summary) => summary?.risk ?? {};

const getGraphMetric = (graph, ...keys) =>
  numberValue(
    firstDefined(
      ...keys.map((key) => graph?.[key]),
      ...keys.map((key) => graph?.graph_statistics?.[key]),
      ...keys.map((key) => graph?.statistics?.[key]),
      ...keys.map((key) => graph?.graph?.[key])
    )
  );

export default function Analytics() {
  const [investigationId, setInvestigationId] = useState(getActiveInvestigationId());

  const [summary, setSummary] = useState(null);
  const [investigationRiskPayload, setInvestigationRiskPayload] = useState(null);
  const [centrality, setCentrality] = useState([]);
  const [connectivity, setConnectivity] = useState(null);
  const [patterns, setPatterns] = useState([]);
  const [entityRisk, setEntityRisk] = useState(null);
  const [similarity, setSimilarity] = useState([]);

  const [selectedEntity, setSelectedEntity] = useState(null);
  const [loading, setLoading] = useState(true);
  const [entityLoading, setEntityLoading] = useState(false);
  const [error, setError] = useState("");
  const [lastUpdated, setLastUpdated] = useState(null);

  useEffect(() => {
    const syncActiveInvestigation = () => setInvestigationId(getActiveInvestigationId());
    window.addEventListener("trinetra:active-investigation-changed", syncActiveInvestigation);
    const timer = window.setInterval(syncActiveInvestigation, 1000);
    return () => {
      window.removeEventListener("trinetra:active-investigation-changed", syncActiveInvestigation);
      window.clearInterval(timer);
    };
  }, []);

  const loadAnalytics = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      let activeId = investigationId;
      if (!activeId) {
        const registry = await listInvestigations({ skip: 0, limit: 100 });
        const rows = Array.isArray(registry) ? registry : registry?.investigations || registry?.items || registry?.results || registry?.data || [];
        const first = rows.find((item) => Number(item.id ?? item.investigation_id) > 0);
        if (first) {
          activeId = Number(first.id ?? first.investigation_id);
          setActiveInvestigationId(activeId);
          setInvestigationId(activeId);
        }
      }

      const [
        summaryResult,
        centralityResult,
        connectivityResult,
        patternsResult,
      ] = await Promise.all([
        activeId ? getAnalyticsSummary(activeId) : Promise.resolve(null),
        getGraphCentrality(20),
        getGraphConnectivity(),
        activeId ? getPatterns(activeId) : Promise.resolve([]),
      ]);

      // Risk is fetched directly from the live risk endpoint instead of
      // relying on a nested summary shape. This keeps the KPI synchronized
      // with the same investigation currently selected in the workspace.
      let liveRisk = null;
      if (activeId) {
        try {
          liveRisk = await getRisk({ investigationId: activeId });
        } catch (riskError) {
          liveRisk = null;
          setError(getApiErrorMessage(riskError, "Risk analytics could not be refreshed."));
        }
      }

      const normalizedCentrality = normalizeCentrality(centralityResult);
      const normalizedPatterns = normalizePatterns(patternsResult);

      setSummary(summaryResult);
      setInvestigationRiskPayload(liveRisk);
      setCentrality(normalizedCentrality);
      setConnectivity(connectivityResult);
      setPatterns(normalizedPatterns);

      if (selectedEntity) {
        const refreshedRisk = await getRisk({ entityId: selectedEntity.entityId });
        setEntityRisk(refreshedRisk);

        if (selectedEntity.entityId !== undefined && selectedEntity.entityId !== null) {
          try {
            const similar = await getSimilarity({
              sourceEntityId: selectedEntity.entityId,
              limit: 5,
            });
            setSimilarity(asArray(similar));
          } catch {
            setSimilarity([]);
          }
        }
      }

      setLastUpdated(new Date());
      if (!activeId) setError("No investigation is currently selected. Create or select an investigation to view investigation analytics.");
    } catch (err) {
      setError(getApiErrorMessage(err, "Analytics service could not be reached."));
    } finally {
      setLoading(false);
    }
  }, [investigationId, selectedEntity]);

  useEffect(() => {
    loadAnalytics();

    const interval = window.setInterval(loadAnalytics, REFRESH_INTERVAL_MS);
    return () => window.clearInterval(interval);
  }, [loadAnalytics]);

  const summaryGraph = useMemo(() => extractSummaryGraph(summary), [summary]);
  const summaryRisk = useMemo(() => extractSummaryRisk(summary), [summary]);

  // Prefer the direct live risk response. Keep the summary value as a
  // compatibility fallback for older backend responses.
  const investigationRiskPayloadResolved =
    investigationRiskPayload ?? summaryRisk;
  const investigationRisk = getRiskValue(investigationRiskPayloadResolved);
  const investigationRiskLevel = getRiskLevel(
    investigationRiskPayloadResolved,
    investigationRisk
  );

  const graphNodes = getGraphMetric(
    summaryGraph,
    "node_count",
    "nodes",
    "entity_count",
    "entities"
  );

  const graphRelationships = getGraphMetric(
    summaryGraph,
    "relationship_count",
    "relationships",
    "link_count",
    "links"
  );

  const selectedRisk = entityRisk ? getRiskValue(entityRisk) : null;
  const selectedRiskLevel = entityRisk
    ? getRiskLevel(entityRisk, selectedRisk)
    : "";

  const connectedComponents = getGraphMetric(
    asObject(connectivity),
    "connected_components",
    "component_count",
    "components"
  );

  const bridgeCount = getGraphMetric(
    asObject(connectivity),
    "bridge_count",
    "bridges",
    "bridge_entities"
  );

  const selectEntity = async (entity) => {
    setSelectedEntity(entity);
    setEntityLoading(true);

    try {
      const risk = await getRisk({
        entityId: entity.entityId,
      });
      setEntityRisk(risk);

      if (entity.entityId !== undefined && entity.entityId !== null) {
        try {
          const similar = await getSimilarity({
            sourceEntityId: entity.entityId,
            limit: 5,
          });
          setSimilarity(asArray(similar));
        } catch {
          setSimilarity([]);
        }
      }
    } catch (err) {
      setEntityRisk(null);
      setError(
        err?.response?.data?.detail ||
          err?.message ||
          "Entity risk analysis failed."
      );
    } finally {
      setEntityLoading(false);
    }
  };

  return (
    <div className="tn-page tn-analytics-page">
      <header className="tn-analytics-header">
        <div>
          <div className="tn-eyebrow">TRINETRA / ANALYTICAL INTELLIGENCE</div>

          <div className="tn-analytics-title-row">
            <div className="tn-analytics-title-icon">
              <BarChart3 size={22} />
            </div>

            <div>
              <h1 className="tn-page-title">Investigation Analytics</h1>
              <p className="tn-page-subtitle">
                Live analytical signals derived from the investigation graph,
                entity relationships and evidence-linked intelligence.
              </p>
            </div>
          </div>
        </div>

        <div className="tn-analytics-live">
          <span className="tn-live-dot" />
          <div>
            <strong>ANALYTICS ONLINE</strong>
            <small>
              {lastUpdated
                ? `Updated ${lastUpdated.toLocaleTimeString()}`
                : "Synchronizing live signals"}
            </small>
          </div>
          <button
            type="button"
            className="tn-icon-button"
            onClick={loadAnalytics}
            disabled={loading}
            aria-label="Refresh analytics"
          >
            <RefreshCw size={16} className={loading ? "tn-spin" : ""} />
          </button>
        </div>
      </header>

      {error && (
        <GlassCard className="tn-analytics-error">
          <AlertTriangle size={18} />
          <div>
            <strong>Analytics service warning</strong>
            <span>{error}</span>
          </div>
        </GlassCard>
      )}

      <section className="tn-analytics-kpis">
        <GlassCard className="tn-analytics-kpi tn-kpi-risk">
          <div className="tn-kpi-icon"><Gauge size={18} /></div>
          <span>Investigation risk</span>
          <strong>
            {loading
              ? "—"
              : investigationRisk === null
                ? "—"
                : `${investigationRisk}/100`}
          </strong>
          <small>{investigationRiskLevel}</small>
        </GlassCard>

        <GlassCard className="tn-analytics-kpi">
          <div className="tn-kpi-icon"><Network size={18} /></div>
          <span>Graph entities</span>
          <strong>{loading ? "—" : formatNumber(graphNodes)}</strong>
          <small>Live graph scope</small>
        </GlassCard>

        <GlassCard className="tn-analytics-kpi">
          <div className="tn-kpi-icon"><Activity size={18} /></div>
          <span>Graph relationships</span>
          <strong>{loading ? "—" : formatNumber(graphRelationships)}</strong>
          <small>Observed links</small>
        </GlassCard>

        <GlassCard className="tn-analytics-kpi">
          <div className="tn-kpi-icon"><Target size={18} /></div>
          <span>Detected patterns</span>
          <strong>{loading ? "—" : formatNumber(patterns.length)}</strong>
          <small>Analytical signals</small>
        </GlassCard>
      </section>

      <section className="tn-analytics-main-grid">
        <GlassCard className="tn-analytics-panel tn-centrality-panel">
          <div className="tn-panel-head">
            <div>
              <div className="tn-section-kicker">GRAPH STRUCTURE</div>
              <h2>Centrality leaders</h2>
              <p>Entities ranked by the live graph analytics engine.</p>
            </div>
            <Users size={20} />
          </div>

          <div className="tn-centrality-list">
            {centrality.length ? (
              centrality.slice(0, 8).map((entity, index) => (
                <button
                  type="button"
                  className={`tn-centrality-row ${
                    selectedEntity?.id === entity.id ? "is-selected" : ""
                  }`}
                  key={entity.id}
                  onClick={() => selectEntity(entity)}
                >
                  <span className="tn-rank">{String(index + 1).padStart(2, "0")}</span>

                  <span className="tn-centrality-avatar">
                    <CircleDot size={15} />
                  </span>

                  <span className="tn-centrality-identity">
                    <strong>{entity.value}</strong>
                    <small>{titleCase(entity.type)}</small>
                  </span>

                  <span className="tn-centrality-metric">
                    <strong>{entity.degree}</strong>
                    <small>degree</small>
                  </span>

                  <span className="tn-centrality-bar">
                    <i
                      style={{
                        width: `${Math.max(
                          6,
                          Math.min(
                            100,
                            (entity.score /
                              Math.max(centrality[0]?.score || 1, 1)) *
                              100
                          )
                        )}%`,
                      }}
                    />
                  </span>
                </button>
              ))
            ) : (
              <div className="tn-analytics-empty">
                {loading ? "Loading graph centrality…" : "No centrality signals returned."}
              </div>
            )}
          </div>
        </GlassCard>

        <GlassCard className="tn-analytics-panel tn-risk-panel">
          <div className="tn-panel-head">
            <div>
              <div className="tn-section-kicker">RISK ENGINE</div>
              <h2>{selectedEntity ? selectedEntity.value : "Investigation signal"}</h2>
              <p>
                {selectedEntity
                  ? "Entity-level analytical risk signal."
                  : "Select an entity from centrality to inspect its risk."}
              </p>
            </div>
            <ShieldCheck size={20} />
          </div>

          <div className="tn-risk-display">
            <div className="tn-risk-ring">
              <div>
                <strong>
                  {entityLoading
                    ? "…"
                    : selectedRisk !== null
                      ? selectedRisk
                      : investigationRisk !== null
                        ? investigationRisk
                        : "—"}
                </strong>
                <span>/100</span>
              </div>
            </div>

            <div className="tn-risk-copy">
              <Badge>
                {entityLoading
                  ? "CALCULATING"
                  : selectedEntity
                    ? selectedRiskLevel.toUpperCase()
                    : investigationRiskLevel.toUpperCase()}
              </Badge>

              <strong>
                {selectedEntity ? "Entity risk indicator" : "Investigation risk indicator"}
              </strong>

              <p>
                Analytical signal only. It does not constitute a determination
                of guilt or wrongdoing.
              </p>
            </div>
          </div>

          <div className="tn-risk-source">
            <span>ENGINE</span>
            <strong>TRINETRA RISK ENGINE</strong>
            <span>LIVE</span>
          </div>
        </GlassCard>
      </section>

      <section className="tn-analytics-secondary-grid">
        <GlassCard className="tn-analytics-panel">
          <div className="tn-panel-head">
            <div>
              <div className="tn-section-kicker">PATTERN DETECTION</div>
              <h2>Observed analytical patterns</h2>
            </div>
            <Sparkles size={20} />
          </div>

          <div className="tn-pattern-grid">
            {patterns.length ? (
              patterns.slice(0, 6).map((pattern) => (
                <article className="tn-pattern-card" key={pattern.id}>
                  <div className="tn-pattern-top">
                    <span>{titleCase(pattern.severity)}</span>
                    <TrendingUp size={15} />
                  </div>
                  <h3>{titleCase(pattern.name)}</h3>
                  <p>{pattern.description}</p>
                  {pattern.entity && (
                    <footer>{pattern.entity}</footer>
                  )}
                </article>
              ))
            ) : (
              <div className="tn-analytics-empty">
                {loading ? "Detecting graph patterns…" : "No patterns returned."}
              </div>
            )}
          </div>
        </GlassCard>
      </section>

      <section className="tn-analytics-bottom-grid">
        <GlassCard className="tn-analytics-panel tn-connectivity-panel">
          <div className="tn-panel-head">
            <div>
              <div className="tn-section-kicker">CONNECTIVITY</div>
              <h2>Graph topology</h2>
            </div>
            <Network size={20} />
          </div>

          <div className="tn-topology-stats">
            <div>
              <span>Components</span>
              <strong>{connectedComponents || "—"}</strong>
            </div>
            <div>
              <span>Bridge signals</span>
              <strong>{bridgeCount || "—"}</strong>
            </div>
            <div>
              <span>Centrality rows</span>
              <strong>{centrality.length}</strong>
            </div>
          </div>
        </GlassCard>

        <GlassCard className="tn-analytics-panel tn-similarity-panel">
          <div className="tn-panel-head">
            <div>
              <div className="tn-section-kicker">ENTITY SIMILARITY</div>
              <h2>{selectedEntity ? "Related entities" : "Select an entity"}</h2>
              <p>
                {selectedEntity
                  ? "Closest matches returned by the live similarity engine."
                  : "Choose a centrality leader to compare graph profiles."}
              </p>
            </div>
            <BrainCircuit size={20} />
          </div>

          <div className="tn-similarity-list">
            {similarity.length ? (
              similarity.slice(0, 5).map((item, index) => {
                const row = asObject(item);
                const name = firstDefined(
                  row.entity_value,
                  row.entity_name,
                  row.value,
                  row.name,
                  "Related entity"
                );
                const score = percentage(
                  firstDefined(row.similarity, row.similarity_score, row.score, 0)
                );

                return (
                  <div className="tn-similarity-row" key={`${name}-${index}`}>
                    <span>{name}</span>
                    <div><i style={{ width: `${Math.max(3, score)}%` }} /></div>
                    <strong>{score}%</strong>
                  </div>
                );
              })
            ) : (
              <div className="tn-analytics-empty">
                {selectedEntity ? "No similarity matches returned." : "Awaiting entity selection."}
              </div>
            )}
          </div>
        </GlassCard>
      </section>

      <footer className="tn-analytics-disclaimer">
        <ShieldCheck size={16} />
        <span>
          Analytics are derived from available graph and investigation data.
          Results are investigative signals and should be verified against
          underlying evidence.
        </span>
      </footer>
    </div>
  );
}

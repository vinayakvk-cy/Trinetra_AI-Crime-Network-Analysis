import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Activity,
  ArrowRight,
  ChevronDown,
  CircleDot,
  Crosshair,
  GitBranch,
  Loader2,
  Network,
  RefreshCw,
  Search,
  ShieldCheck,
  Sparkles,
  Target,
  X,
} from "lucide-react";
import {
  getGraphHealth,
  getGraphStats,
  searchGraphEntities,
  getGraphNeighborhood,
  getGraphRelationships,
  getShortestGraphPath,
} from "../services/graphApi";
import InvestigationGraph from "../components/graph/InvestigationGraph";
import "./graph-page.css";

const MAX_SEARCH_RESULTS = 50;
const REFRESH_MS = 10000;

function text(value, fallback = "") {
  return value === null || value === undefined ? fallback : String(value);
}

function typeLabel(value) {
  return text(value, "UNKNOWN").replace(/_/g, " ").toUpperCase();
}

function normalizeType(value) {
  return text(value).trim().toUpperCase();
}

function normalizeValue(value) {
  return text(value).trim();
}

function confidencePercent(value) {
  if (typeof value !== "number" || !Number.isFinite(value)) return null;
  return Math.round(value <= 1 ? value * 100 : value);
}

function extractList(payload, keys = []) {
  if (Array.isArray(payload)) return payload;
  for (const key of keys) {
    if (Array.isArray(payload?.[key])) return payload[key];
  }
  return [];
}

function entityFromRecord(record, side) {
  if (!record) return null;
  if (side === "source") {
    return {
      type: record.source_type ?? record.sourceType ?? record.start_type ?? record.startType,
      value: record.source_value ?? record.sourceValue ?? record.start_value ?? record.startValue,
    };
  }
  return {
    type:
      record.target_type ??
      record.targetType ??
      record.neighbor_type ??
      record.neighborType ??
      record.related_type ??
      record.relatedType,
    value:
      record.target_value ??
      record.targetValue ??
      record.neighbor_value ??
      record.neighborValue ??
      record.related_value ??
      record.relatedValue,
  };
}

function relationshipFromRecord(record) {
  const source = entityFromRecord(record, "source");
  const target = entityFromRecord(record, "target");
  if (!source?.value || !target?.value) return null;

  const properties = record.relationship_properties || record.relationshipProperties || {};

  return {
    ...record,
    id: String(
      record.id ??
        record.relationship_id ??
        record.relationshipId ??
        `${source.type}:${source.value}:${record.relationship_type ?? record.relationshipType ?? "RELATED_TO"}:${target.type}:${target.value}`
    ),
    source_type: source.type,
    source_value: source.value,
    target_type: target.type,
    target_value: target.value,
    relationship_type:
      record.relationship_type ??
      record.relationshipType ??
      record.type ??
      "RELATED_TO",
    confidence:
      record.confidence ??
      record.relationship_confidence ??
      record.relationshipConfidence ??
      properties.confidence ??
      null,
    evidence_text:
      record.evidence_text ??
      record.evidenceText ??
      properties.evidence_text ??
      null,
    source_field: record.source_field ?? properties.source_field ?? null,
  };
}

function uniqueRelationships(records) {
  const map = new Map();
  records.forEach((record) => {
    const normalized = relationshipFromRecord(record);
    if (!normalized) return;
    const pair = [
      `${normalizeType(normalized.source_type)}:${normalizeValue(normalized.source_value).toLowerCase()}`,
      `${normalizeType(normalized.target_type)}:${normalizeValue(normalized.target_value).toLowerCase()}`,
    ].sort();
    const key = `${pair.join("|")}|${text(normalized.relationship_type).toUpperCase()}`;
    if (!map.has(key)) map.set(key, normalized);
  });
  return Array.from(map.values());
}

async function fetchGraphMeta() {
  const [nextHealth, nextStats] = await Promise.all([
    getGraphHealth(),
    getGraphStats(),
  ]);
  return { health: nextHealth, stats: nextStats };
}

function buildNeighborhoodRecords(focus, neighborhoodRows, directRows) {
  const direct = uniqueRelationships(directRows);
  const discovered = [];

  neighborhoodRows.forEach((row) => {
    const start = {
      type: row.start_type ?? row.startType ?? focus.type,
      value: row.start_value ?? row.startValue ?? focus.value,
    };
    const neighbor = {
      type: row.neighbor_type ?? row.neighborType,
      value: row.neighbor_value ?? row.neighborValue,
    };
    const nested = Array.isArray(row.relationships) ? row.relationships : [];

    if (neighbor.value && nested.length === 0) {
      discovered.push({
        source_type: start.type,
        source_value: start.value,
        target_type: neighbor.type,
        target_value: neighbor.value,
        relationship_type: "CONNECTED",
        confidence: null,
        path_depth: row.path_depth ?? row.distance ?? null,
      });
    }
  });

  return uniqueRelationships([...direct, ...discovered]);
}

export default function Graph() {
  const [health, setHealth] = useState(null);
  const [stats, setStats] = useState(null);
  const [entities, setEntities] = useState([]);
  const [entityType, setEntityType] = useState("");
  const [entityValue, setEntityValue] = useState("");
  const [depth, setDepth] = useState(2);
  const [searchText, setSearchText] = useState("");
  const [showEntityMenu, setShowEntityMenu] = useState(false);
  const [showDepthMenu, setShowDepthMenu] = useState(false);
  const [relationships, setRelationships] = useState([]);
  const [selectedNode, setSelectedNode] = useState(null);
  const [pathResult, setPathResult] = useState(null);
  const [targetType, setTargetType] = useState("");
  const [targetValue, setTargetValue] = useState("");
  const [loading, setLoading] = useState(false);
  const [pathLoading, setPathLoading] = useState(false);
  const [bootLoading, setBootLoading] = useState(true);
  const [error, setError] = useState("");
  const [lastUpdated, setLastUpdated] = useState(null);

  const graphOnline = health?.neo4j === true || health?.success === true;
  const nodeCount = Number(stats?.nodes ?? stats?.node_count ?? 0);
  const relationshipCount = Number(stats?.relationships ?? stats?.relationship_count ?? 0);

  const refreshMeta = useCallback(async () => {
    try {
      const { health: nextHealth, stats: nextStats } = await fetchGraphMeta();
      setHealth(nextHealth);
      setStats(nextStats);
      setLastUpdated(new Date());
    } catch (err) {
      setHealth({ success: false, neo4j: false });
      setError(err?.response?.data?.detail || err?.message || "Unable to reach the graph API.");
    }
  }, []);

  const loadEntities = useCallback(async (query = "") => {
    try {
      const rows = await searchGraphEntities(query);
      const normalized = rows
        .map((row) => ({
          id: row.node_id ?? row.id ?? `${row.entity_type}:${row.value}`,
          type: row.entity_type ?? row.entityType,
          value: row.value ?? row.entity_value,
          normalizedValue: row.normalized_value ?? row.normalizedValue,
        }))
        .filter((row) => row.value);
      setEntities(normalized.slice(0, MAX_SEARCH_RESULTS));
      return normalized;
    } catch (err) {
      setError(err?.response?.data?.detail || err?.message || "Unable to search graph entities.");
      return [];
    }
  }, []);

  useEffect(() => {
    let alive = true;
    (async () => {
      setBootLoading(true);
      await refreshMeta();
      const rows = await loadEntities("");
      if (alive && rows.length && !entityValue) {
        // No entity is hardcoded. The UI starts un-focused and uses the live graph registry.
        setEntityType("");
        setEntityValue("");
      }
      if (alive) setBootLoading(false);
    })();
    return () => {
      alive = false;
    };
  }, [loadEntities, refreshMeta]);

  useEffect(() => {
    const timer = window.setInterval(async () => {
      await refreshMeta();
      if (entityType && entityValue && relationships.length) {
        try {
          const [direct, neighborhoodRows] = await Promise.all([
            getGraphRelationships({ entityType, entityValue }),
            getGraphNeighborhood({ entityType, entityValue, depth, limit: 100 }),
          ]);
          const merged = buildNeighborhoodRecords(
            { type: entityType, value: entityValue },
            neighborhoodRows,
            direct
          );
          if (merged.length) setRelationships(merged);
        } catch {
          // Keep the last successful graph visible during transient refresh failures.
        }
      }
    }, REFRESH_MS);
    return () => window.clearInterval(timer);
  }, [depth, entityType, entityValue, refreshMeta, relationships.length]);

  const filteredEntities = useMemo(() => {
    const q = searchText.trim().toLowerCase();
    if (!q) return entities.slice(0, 12);
    return entities
      .filter(
        (item) =>
          text(item.value).toLowerCase().includes(q) ||
          text(item.type).toLowerCase().includes(q)
      )
      .slice(0, 12);
  }, [entities, searchText]);

  const graphEntities = useMemo(() => {
    const map = new Map();
    relationships.forEach((rel) => {
      const source = entityFromRecord(rel, "source");
      const target = entityFromRecord(rel, "target");
      [source, target].forEach((entity) => {
        if (!entity?.value) return;
        const key = `${normalizeType(entity.type)}:${normalizeValue(entity.value).toLowerCase()}`;
        if (!map.has(key)) map.set(key, entity);
      });
    });
    return Array.from(map.values());
  }, [relationships]);

  const relationshipTypes = useMemo(() => {
    const counts = new Map();
    relationships.forEach((rel) => {
      const key = typeLabel(rel.relationship_type);
      counts.set(key, (counts.get(key) || 0) + 1);
    });
    return Array.from(counts.entries()).sort((a, b) => b[1] - a[1]);
  }, [relationships]);

  const focusDegree = useMemo(() => {
    if (!entityValue) return 0;
    const focus = normalizeValue(entityValue).toLowerCase();
    return relationships.filter((rel) => {
      const s = normalizeValue(rel.source_value).toLowerCase();
      const t = normalizeValue(rel.target_value).toLowerCase();
      return s === focus || t === focus;
    }).length;
  }, [entityValue, relationships]);

  const averageConfidence = useMemo(() => {
    const values = relationships
      .map((rel) => confidencePercent(rel.confidence))
      .filter((value) => value !== null);
    if (!values.length) return null;
    return Math.round(values.reduce((a, b) => a + b, 0) / values.length);
  }, [relationships]);

  const handleEntitySearch = async (event) => {
    const value = event.target.value;
    setSearchText(value);
    setShowEntityMenu(true);
    if (!value.trim()) {
      await loadEntities("");
      return;
    }
    await loadEntities(value);
  };

  const selectEntity = (entity) => {
    setEntityType(entity.type);
    setEntityValue(entity.value);
    setSearchText(entity.value);
    setShowEntityMenu(false);
    setShowDepthMenu(false);
    setPathResult(null);
  };

  const explore = async (event) => {
    event?.preventDefault();
    if (!entityType || !entityValue.trim()) {
      setError("Select an entity from the live graph registry or enter both entity type and value.");
      return;
    }

    setLoading(true);
    setError("");
    setPathResult(null);
    try {
      const [directRows, neighborhoodRows] = await Promise.all([
        getGraphRelationships({ entityType, entityValue: entityValue.trim() }),
        getGraphNeighborhood({ entityType, entityValue: entityValue.trim(), depth, limit: 100 }),
      ]);

      let merged = buildNeighborhoodRecords(
        { type: entityType, value: entityValue.trim() },
        neighborhoodRows,
        directRows
      );

      // For depth > 1, expand the discovered frontier through the real API.
      if (depth > 1 && merged.length) {
        const frontier = graphEntitiesFromRecords(merged, entityType, entityValue).slice(0, 25);
        const expanded = await Promise.all(
          frontier.map(async (item) => {
            try {
              return await getGraphRelationships({ entityType: item.type, entityValue: item.value });
            } catch {
              return [];
            }
          })
        );
        merged = uniqueRelationships([...merged, ...expanded.flat()]);
      }

      setRelationships(merged);
      setSelectedNode({ type: entityType, value: entityValue.trim() });
      if (!merged.length) {
        setError("The graph API returned no connected relationships for this entity.");
      }
      setLastUpdated(new Date());
    } catch (err) {
      setRelationships([]);
      setError(err?.response?.data?.detail || err?.message || "Graph exploration failed.");
    } finally {
      setLoading(false);
    }
  };

  const trace = async (event) => {
    event.preventDefault();
    if (!entityType || !entityValue.trim() || !targetType || !targetValue.trim()) return;
    setPathLoading(true);
    setError("");
    try {
      const result = await getShortestGraphPath({
        sourceType: entityType,
        sourceValue: entityValue.trim(),
        targetType,
        targetValue: targetValue.trim(),
        maxDepth: Math.max(1, depth + 2),
      });
      setPathResult(result?.result ?? result);
    } catch (err) {
      setPathResult(null);
      setError(err?.response?.data?.detail || err?.message || "Shortest-path analysis failed.");
    } finally {
      setPathLoading(false);
    }
  };

  const clear = () => {
    setRelationships([]);
    setSelectedNode(null);
    setPathResult(null);
    setEntityType("");
    setEntityValue("");
    setSearchText("");
    setTargetType("");
    setTargetValue("");
    setError("");
  };

  const selectGraphNode = (node) => {
    setSelectedNode(node);
    setEntityType(node.type);
    setEntityValue(node.value);
    setSearchText(node.value);
  };

  return (
    <div className="tn-page tn-graph-page-new">
      <header className="tn-graph-page-head">
        <div>
          <div className="tn-eyebrow">TRINETRA / LIVE GRAPH INTELLIGENCE</div>
          <div className="tn-graph-title-row">
            <div className="tn-graph-title-icon"><Network size={21} /></div>
            <div>
              <h1 className="tn-page-title">Investigation Graph</h1>
              <p className="tn-page-subtitle">
                Explore the connected intelligence graph directly from Neo4j. Entities, links, paths,
                confidence and graph status below are populated from live API responses.
              </p>
            </div>
          </div>
        </div>

        <div className="tn-live-status">
          <span className={graphOnline ? "tn-live-dot" : "tn-live-dot tn-live-dot-off"} />
          <div>
            <strong>{graphOnline ? "GRAPH ONLINE" : "GRAPH OFFLINE"}</strong>
            <span>{lastUpdated ? `Updated ${lastUpdated.toLocaleTimeString()}` : "Connecting…"}</span>
          </div>
          <button type="button" className="tn-refresh-button" onClick={refreshMeta} title="Refresh graph status">
            <RefreshCw size={15} />
          </button>
        </div>
      </header>

      {error && (
        <div className="tn-graph-alert">
          <Activity size={17} />
          <span>{error}</span>
          <button type="button" onClick={() => setError("")}><X size={15} /></button>
        </div>
      )}

      <section className="tn-graph-command-grid">
        <div className="tn-graph-command-card">
          <div className="tn-command-heading">
            <div>
              <span className="tn-section-kicker">ENTITY EXPLORER</span>
              <h2>Start from live graph data</h2>
              <p>Search the current Neo4j entity registry. Nothing here is tied to a fixed person or organization.</p>
            </div>
            <Crosshair size={20} />
          </div>

          <form onSubmit={explore} className="tn-entity-form">
            <div className="tn-entity-search-row">
              <div className="tn-entity-search-wrap">
              <Search size={16} />
              <input
                value={searchText}
                onChange={handleEntitySearch}
                onFocus={() => setShowEntityMenu(true)}
                placeholder="Search any entity…"
                autoComplete="off"
              />
              {searchText && (
                <button type="button" onClick={() => { setSearchText(""); setEntityType(""); setEntityValue(""); setShowEntityMenu(true); }}>
                  <X size={14} />
                </button>
              )}
                {showEntityMenu && filteredEntities.length > 0 && (
                  <div className="tn-entity-menu">
                    {filteredEntities.map((entity) => (
                      <button key={entity.id} type="button" onClick={() => selectEntity(entity)}>
                        <span className="tn-entity-menu-type">{typeLabel(entity.type)}</span>
                        <strong>{entity.value}</strong>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>

            <div className="tn-entity-control-row">
              <label className="tn-field">
              <span>Entity type</span>
              <input value={entityType} onChange={(e) => setEntityType(e.target.value)} placeholder="PERSON / ORGANIZATION / BANK" />
              </label>

              <div className="tn-field tn-depth-field">
              <span>Expansion</span>
              <button
                type="button"
                className="tn-select-trigger"
                onClick={() => setShowDepthMenu((value) => !value)}
                aria-expanded={showDepthMenu}
              >
                <span>{depth} {depth === 1 ? "hop" : "hops"}</span>
                <ChevronDown size={14} />
              </button>
                {showDepthMenu && (
                  <div className="tn-depth-menu">
                    {[1, 2, 3, 4, 5].map((value) => (
                      <button
                        key={value}
                        type="button"
                        className={value === depth ? "is-active" : ""}
                        onClick={() => {
                          setDepth(value);
                          setShowDepthMenu(false);
                        }}
                      >
                        <span>{value} {value === 1 ? "hop" : "hops"}</span>
                        {value === depth && <span className="tn-depth-check">✓</span>}
                      </button>
                    ))}
                  </div>
                )}
              </div>

              <button className="tn-primary-graph-button" type="submit" disabled={loading || bootLoading}>
                {loading ? <Loader2 size={16} className="tn-spin" /> : <Sparkles size={16} />}
                {loading ? "Resolving…" : "Explore graph"}
              </button>
            </div>
          </form>
        </div>

        <div className="tn-graph-metrics-card">
          <span className="tn-section-kicker">GRAPH TELEMETRY</span>
          <div className="tn-telemetry-grid">
            <div><span>Nodes</span><strong>{nodeCount}</strong></div>
            <div><span>Relationships</span><strong>{relationshipCount}</strong></div>
            <div><span>Loaded links</span><strong>{relationships.length}</strong></div>
            <div><span>Focus degree</span><strong>{focusDegree}</strong></div>
          </div>
          <div className="tn-telemetry-footer">
            <ShieldCheck size={15} />
            <span>Neo4j is the source of truth for this graph view.</span>
          </div>
        </div>
      </section>

      <section className="tn-graph-main-grid">
        <div className="tn-graph-canvas-card">
          <div className="tn-canvas-head">
            <div>
              <span className="tn-section-kicker">CONNECTED INTELLIGENCE</span>
              <h2>{selectedNode ? selectedNode.value : "Graph workspace"}</h2>
              <p>
                {relationships.length
                  ? `${relationships.length} unique relationship links currently loaded from the API.`
                  : "Select an entity and explore to render its live connected neighborhood."}
              </p>
            </div>
            <div className="tn-canvas-actions">
              {selectedNode && <span className="tn-focus-chip"><Target size={13} /> {typeLabel(selectedNode.type)}</span>}
              {relationships.length > 0 && <button type="button" className="tn-clear-button" onClick={clear}>Clear</button>}
            </div>
          </div>

          <div className="tn-graph-canvas-shell">
            {bootLoading ? (
              <div className="tn-graph-empty-state">
                <Loader2 size={30} className="tn-spin" />
                <strong>Connecting to graph services</strong>
                <span>Reading Neo4j telemetry and the live entity registry…</span>
              </div>
            ) : (
              <InvestigationGraph relationships={relationships} loading={loading} onNodeClick={selectGraphNode} />
            )}
          </div>

          <div className="tn-graph-legend">
            <span><i className="tn-legend-person" /> Person</span>
            <span><i className="tn-legend-org" /> Organization</span>
            <span><i className="tn-legend-bank" /> Bank</span>
            <span><i className="tn-legend-case" /> Case</span>
            <span className="tn-legend-note">Drag nodes · scroll to zoom · click a node to focus</span>
          </div>
        </div>

        <aside className="tn-graph-inspector">
          <div className="tn-inspector-head">
            <div>
              <span className="tn-section-kicker">ENTITY INSPECTOR</span>
              <h2>{selectedNode?.value || "No focus selected"}</h2>
            </div>
            <CircleDot size={19} />
          </div>

          {selectedNode ? (
            <>
              <div className="tn-inspector-type-row">
                <span>TYPE</span><strong>{typeLabel(selectedNode.type)}</strong>
              </div>
              <div className="tn-inspector-stats">
                <div><span>CONNECTED</span><strong>{focusDegree}</strong></div>
                <div><span>CONFIDENCE</span><strong>{averageConfidence === null ? "—" : `${averageConfidence}%`}</strong></div>
              </div>
              <div className="tn-inspector-section">
                <span className="tn-section-kicker">RELATIONSHIP MIX</span>
                {relationshipTypes.length ? relationshipTypes.slice(0, 6).map(([name, count]) => (
                  <div className="tn-mix-row" key={name}><span>{name}</span><strong>{count}</strong></div>
                )) : <p>No relationship records loaded.</p>}
              </div>
              <div className="tn-inspector-section">
                <span className="tn-section-kicker">CURRENT FRONTIER</span>
                <div className="tn-frontier-list">
                  {graphEntities.filter((entity) => normalizeValue(entity.value).toLowerCase() !== normalizeValue(selectedNode.value).toLowerCase()).slice(0, 8).map((entity) => (
                    <button key={`${entity.type}:${entity.value}`} type="button" onClick={() => selectEntity(entity)}>
                      <span>{typeLabel(entity.type)}</span><strong>{entity.value}</strong><ArrowRight size={13} />
                    </button>
                  ))}
                </div>
              </div>
            </>
          ) : (
            <div className="tn-inspector-empty">
              <Target size={25} />
              <strong>Choose a focus entity</strong>
              <span>The inspector will populate from the same live relationship records rendered in the graph.</span>
            </div>
          )}
        </aside>
      </section>

      <section className="tn-path-card">
        <div className="tn-path-head">
          <div>
            <span className="tn-section-kicker">PATH ANALYSIS</span>
            <h2>Trace a connection</h2>
            <p>Run the backend shortest-path algorithm between two entities.</p>
          </div>
          <GitBranch size={20} />
        </div>
        <form className="tn-path-form" onSubmit={trace}>
          <div className="tn-path-endpoint"><span>SOURCE</span><strong>{entityValue || "Select an entity above"}</strong><small>{typeLabel(entityType)}</small></div>
          <ArrowRight className="tn-path-arrow" size={17} />
          <label className="tn-field"><span>Target type</span><input value={targetType} onChange={(e) => setTargetType(e.target.value)} placeholder="BANK" /></label>
          <label className="tn-field"><span>Target value</span><input value={targetValue} onChange={(e) => setTargetValue(e.target.value)} placeholder="Target entity" /></label>
          <button className="tn-trace-button" type="submit" disabled={pathLoading || !entityValue || !targetValue.trim()}>
            {pathLoading ? <Loader2 size={15} className="tn-spin" /> : <GitBranch size={15} />}
            Trace path
          </button>
        </form>

        {pathResult && <PathResult result={pathResult} />}
      </section>
    </div>
  );
}

function graphEntitiesFromRecords(records, focusType, focusValue) {
  const map = new Map();
  records.forEach((record) => {
    const source = entityFromRecord(record, "source");
    const target = entityFromRecord(record, "target");
    [source, target].forEach((entity) => {
      if (!entity?.value) return;
      const key = `${normalizeType(entity.type)}:${normalizeValue(entity.value).toLowerCase()}`;
      const focusKey = `${normalizeType(focusType)}:${normalizeValue(focusValue).toLowerCase()}`;
      if (key !== focusKey && !map.has(key)) map.set(key, entity);
    });
  });
  return Array.from(map.values());
}

function PathResult({ result }) {
  const candidate = Array.isArray(result) ? result[0] : result;
  const nodes = Array.isArray(candidate?.nodes) ? candidate.nodes : [];
  const relationships = Array.isArray(candidate?.relationships) ? candidate.relationships : [];
  const distance = candidate?.distance ?? (nodes.length ? nodes.length - 1 : null);

  if (!nodes.length) {
    return <div className="tn-path-result-empty">The shortest-path API returned no traversable path.</div>;
  }

  return (
    <div className="tn-path-result-panel">
      <div className="tn-path-summary"><span>PATH LENGTH</span><strong>{distance ?? "—"}</strong><small>hops</small></div>
      <div className="tn-path-chain">
        {nodes.map((node, index) => (
          <div className="tn-path-node-wrap" key={node.id ?? `${node.type}:${node.value}`}>
            <div className="tn-path-node"><span>{typeLabel(node.type)}</span><strong>{node.value}</strong></div>
            {index < nodes.length - 1 && (
              <div className="tn-path-link"><GitBranch size={13} /><span>{typeLabel(relationships[index]?.type ?? "CONNECTED")}</span></div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

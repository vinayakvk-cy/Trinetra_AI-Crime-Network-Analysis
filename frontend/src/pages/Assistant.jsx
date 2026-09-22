import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Activity,
  BrainCircuit,
  ChevronDown,
  CircleAlert,
  Clock3,
  Database,
  FileSearch,
  Loader2,
  MessageSquareText,
  Network,
  RefreshCw,
  Send,
  ShieldCheck,
  Sparkles,
  UserRound,
} from "lucide-react";
import {
  askAssistant,
  getAssistantContext,
  getAssistantHealth,
} from "../services/assistantApi";
import { listInvestigations } from "../services/investigationsApi";
import { getActiveInvestigationId, setActiveInvestigationId } from "../services/activeInvestigation";
import { getApiErrorMessage } from "../services/api";
import "./assistant-page.css";

const REFRESH_MS = 10000;

const SUGGESTED_QUESTIONS = [
  "What do we know about the focused entity?",
  "What evidence supports the recorded relationships?",
  "Which entities appear most important in this investigation?",
  "What are the main investigative patterns?",
];

function textValue(value) {
  if (value === null || value === undefined) return "";
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  return "";
}

function firstText(...values) {
  for (const value of values) {
    const text = textValue(value).trim();
    if (text) return text;
  }
  return "";
}

function prettyJson(value) {
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value ?? "");
  }
}

function extractAnswer(data) {
  return firstText(
    data?.answer,
    data?.response,
    data?.message,
    data?.result?.answer,
    data?.result?.response,
    data?.data?.answer,
    data?.data?.response
  );
}

function normalizeContext(data) {
  const root = data?.context ?? data?.result ?? data?.data ?? data ?? {};

  const entity =
    root?.focused_entity ??
    root?.entity ??
    root?.focusedEntity ??
    null;

  const relationships =
    root?.relationships ??
    root?.relationship_evidence ??
    root?.entity_relationships ??
    root?.direct_relationships ??
    root?.graph ??
    [];

  const evidence =
    root?.evidence ??
    root?.retrieved_evidence ??
    root?.evidence_items ??
    [];

  const memory =
    root?.memory ??
    root?.conversation_memory ??
    root?.recent_memory ??
    [];

  return {
    entity,
    relationships: Array.isArray(relationships) ? relationships : [],
    evidence: Array.isArray(evidence) ? evidence : [],
    memory: Array.isArray(memory) ? memory : [],
    raw: root,
  };
}

function entityLabel(entity) {
  if (!entity) return "No focused entity";
  return firstText(
    entity.value,
    entity.name,
    entity.entity_value,
    entity.normalized_value,
    entity.label,
    "Focused entity"
  );
}

function relationshipLabel(item) {
  if (!item || typeof item !== "object") return textValue(item);
  const from = firstText(
    item.from,
    item.source,
    item.source_entity,
    item.source_value,
    item.from_value
  );
  const relation = firstText(item.relationship_type, item.type, item.relationship, item.relation);
  const to = firstText(
    item.to,
    item.target,
    item.target_entity,
    item.target_value,
    item.to_value
  );

  if (from || relation || to) {
    return [from, relation, to].filter(Boolean).join(" → ");
  }

  return firstText(item.label, item.description, item.name, prettyJson(item));
}

function evidenceLabel(item) {
  if (!item || typeof item !== "object") return textValue(item);
  return firstText(
    item.evidence_number,
    item.title,
    item.name,
    item.description,
    item.source_reference,
    item.file_name,
    prettyJson(item)
  );
}

function statusTone(ok) {
  return ok ? "online" : "offline";
}

export default function Assistant() {
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState([]);
  const [context, setContext] = useState(null);
  const [health, setHealth] = useState(null);
  const [investigationId, setInvestigationId] = useState(getActiveInvestigationId());
  const [loading, setLoading] = useState(false);
  const [contextLoading, setContextLoading] = useState(true);
  const [error, setError] = useState("");
  const [lastUpdated, setLastUpdated] = useState(null);
  const inputRef = useRef(null);
  const bottomRef = useRef(null);

  useEffect(() => {
    const syncActiveInvestigation = () => {
      setInvestigationId(getActiveInvestigationId());
    };
    window.addEventListener("trinetra:active-investigation-changed", syncActiveInvestigation);
    const timer = window.setInterval(syncActiveInvestigation, 1000);
    return () => {
      window.removeEventListener("trinetra:active-investigation-changed", syncActiveInvestigation);
      window.clearInterval(timer);
    };
  }, []);

  const loadLiveState = useCallback(async () => {
    setContextLoading(true);
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

      const healthData = await getAssistantHealth();
      const contextData = activeId
        ? await getAssistantContext({ investigationId: activeId, memoryLimit: 10 })
        : null;

      setHealth(healthData);
      setContext(contextData ? normalizeContext(contextData) : normalizeContext({}));
      setLastUpdated(new Date());
      setError(activeId ? "" : "No investigation is currently selected. Create or select an investigation to begin.");
    } catch (err) {
      setError(getApiErrorMessage(err, "Unable to retrieve live assistant state."));
    } finally {
      setContextLoading(false);
    }
  }, [investigationId]);

  useEffect(() => {
    loadLiveState();
    const timer = window.setInterval(loadLiveState, REFRESH_MS);
    return () => window.clearInterval(timer);
  }, [loadLiveState]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const sendQuestion = useCallback(
    async (overrideQuestion = null) => {
      const value = (overrideQuestion ?? question).trim();
      if (!value || loading) return;

      setMessages((current) => [
        ...current,
        {
          id: `${Date.now()}-user`,
          role: "user",
          content: value,
          createdAt: new Date(),
        },
      ]);
      setQuestion("");
      setLoading(true);
      setError("");

      try {
        if (!investigationId) {
          throw new Error("No active investigation is selected. Create or select an investigation first.");
        }

        const data = await askAssistant({
          question: value,
          investigationId,
        });

        const answer =
          extractAnswer(data) ||
          "The assistant returned no answer text. Inspect the live context for the retrieved records.";

        setMessages((current) => [
          ...current,
          {
            id: `${Date.now()}-assistant`,
            role: "assistant",
            content: answer,
            createdAt: new Date(),
          },
        ]);

        // Refresh context after every answer so the side panel reflects
        // the current API state rather than a hardcoded snapshot.
        try {
          const freshContext = await getAssistantContext({
            investigationId,
            memoryLimit: 10,
          });
          setContext(normalizeContext(freshContext));
          setLastUpdated(new Date());
        } catch {
          // The answer itself is still useful if context refresh fails.
        }
      } catch (err) {
        const detail =
          err?.response?.data?.detail ||
          err?.message ||
          "Assistant request failed.";

        setError(detail);
        setMessages((current) => [
          ...current,
          {
            id: `${Date.now()}-error`,
            role: "assistant",
            content:
              "I could not retrieve a grounded answer from the assistant API.",
            createdAt: new Date(),
            isError: true,
          },
        ]);
      } finally {
        setLoading(false);
        window.setTimeout(() => inputRef.current?.focus(), 0);
      }
    },
    [loading, question, investigationId]
  );

  const handleSubmit = (event) => {
    event.preventDefault();
    sendQuestion();
  };

  const graphStatus =
    health?.neo4j ??
    health?.graph ??
    health?.services?.neo4j ??
    health?.success ??
    false;

  const apiStatus =
    health?.success ??
    health?.healthy ??
    health?.status === "healthy" ??
    true;

  const focusedEntity = context?.entity;
  const relationshipCount = context?.relationships?.length ?? 0;
  const evidenceCount = context?.evidence?.length ?? 0;
  const memoryCount = context?.memory?.length ?? 0;

  const telemetry = useMemo(
    () => [
      { label: "API", value: apiStatus ? "ONLINE" : "OFFLINE", icon: Activity, tone: statusTone(apiStatus) },
      { label: "Neo4j", value: graphStatus ? "CONNECTED" : "CHECK", icon: Database, tone: statusTone(graphStatus) },
      { label: "Relationships", value: relationshipCount, icon: Network, tone: "neutral" },
      { label: "Evidence", value: evidenceCount, icon: FileSearch, tone: "neutral" },
    ],
    [apiStatus, graphStatus, relationshipCount, evidenceCount]
  );

  return (
    <main className="assistant-page">
      <header className="assistant-hero">
        <div className="assistant-hero-copy">
          <div className="assistant-eyebrow">
            <span className="assistant-live-dot" />
            LIVE INTELLIGENCE INTERFACE
          </div>
          <h1>AI Assistant</h1>
          <p>
            Ask questions against the active investigation. Answers and context
            are retrieved from the live TRINETRA APIs.
          </p>
        </div>

        <div className="assistant-hero-actions">
          <button
            className="assistant-refresh-button"
            type="button"
            onClick={() => {
              setContextLoading(true);
              loadLiveState();
            }}
            title="Refresh live API state"
          >
            <RefreshCw size={16} className={contextLoading ? "spin" : ""} />
            Refresh
          </button>
        </div>
      </header>

      <section className="assistant-telemetry">
        {telemetry.map(({ label, value, icon: Icon, tone }) => (
          <div className="assistant-telemetry-card" key={label}>
            <div className="assistant-telemetry-icon">
              <Icon size={16} />
            </div>
            <div>
              <span>{label}</span>
              <strong className={`telemetry-${tone}`}>{value}</strong>
            </div>
          </div>
        ))}
        <div className="assistant-telemetry-card assistant-investigation-card">
          <div className="assistant-telemetry-icon">
            <ShieldCheck size={16} />
          </div>
          <div>
            <span>Investigation</span>
            <strong>{investigationId ? `LIVE · #${investigationId}` : "NO ACTIVE INVESTIGATION"}</strong>
          </div>
        </div>
      </section>

      {error && (
        <div className="assistant-error">
          <CircleAlert size={17} />
          <span>{error}</span>
        </div>
      )}

      <section className="assistant-workspace">
        <div className="assistant-chat-panel">
          <div className="assistant-panel-header">
            <div>
              <div className="assistant-panel-kicker">
                <BrainCircuit size={15} />
                GROUNDED CONVERSATION
              </div>
              <h2>Investigation Copilot</h2>
            </div>
            <div className="assistant-live-badge">
              <span />
              Real-time API
            </div>
          </div>

          <div className="assistant-messages">
            {messages.length === 0 && (
              <div className="assistant-empty-state">
                <div className="assistant-empty-orb">
                  <Sparkles size={28} />
                </div>
                <h3>Ask the investigation</h3>
                <p>
                  Start with a question below. The assistant will query the
                  active investigation context instead of relying on UI data.
                </p>

                <div className="assistant-suggestions">
                  {SUGGESTED_QUESTIONS.map((item) => (
                    <button
                      type="button"
                      key={item}
                      onClick={() => sendQuestion(item)}
                      disabled={loading}
                    >
                      <MessageSquareText size={15} />
                      <span>{item}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((message) => (
              <article
                className={`assistant-message-row ${
                  message.role === "user" ? "assistant-message-user" : "assistant-message-bot"
                }`}
                key={message.id}
              >
                <div className="assistant-message-avatar">
                  {message.role === "user" ? (
                    <UserRound size={16} />
                  ) : (
                    <BrainCircuit size={16} />
                  )}
                </div>
                <div className="assistant-message-content">
                  <div className="assistant-message-meta">
                    <strong>
                      {message.role === "user" ? "You" : "TRINETRA Assistant"}
                    </strong>
                    <span>
                      {message.createdAt?.toLocaleTimeString([], {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </span>
                  </div>
                  <div className={`assistant-message-bubble ${message.isError ? "message-error" : ""}`}>
                    {message.content}
                  </div>
                </div>
              </article>
            ))}

            {loading && (
              <article className="assistant-message-row assistant-message-bot">
                <div className="assistant-message-avatar">
                  <BrainCircuit size={16} />
                </div>
                <div className="assistant-message-content">
                  <div className="assistant-message-meta">
                    <strong>TRINETRA Assistant</strong>
                    <span>retrieving live context</span>
                  </div>
                  <div className="assistant-thinking">
                    <Loader2 size={16} className="spin" />
                    <span>Analyzing investigation data…</span>
                  </div>
                </div>
              </article>
            )}

            <div ref={bottomRef} />
          </div>

          <form className="assistant-composer" onSubmit={handleSubmit}>
            <div className="assistant-input-wrap">
              <MessageSquareText size={18} />
              <input
                ref={inputRef}
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                placeholder="Ask about entities, evidence, relationships, risk, or patterns…"
                disabled={loading}
              />
              <button type="submit" disabled={!question.trim() || loading}>
                {loading ? <Loader2 size={17} className="spin" /> : <Send size={17} />}
              </button>
            </div>
            <div className="assistant-composer-note">
              <ShieldCheck size={13} />
              Grounded responses only · analytical signals are not determinations of guilt
            </div>
          </form>
        </div>

        <aside className="assistant-context-panel">
          <div className="assistant-panel-header context-header">
            <div>
              <div className="assistant-panel-kicker">
                <Database size={15} />
                LIVE RETRIEVED CONTEXT
              </div>
              <h2>Investigation Context</h2>
            </div>
            <ChevronDown size={17} />
          </div>

          {contextLoading ? (
            <div className="assistant-context-loading">
              <Loader2 size={19} className="spin" />
              <span>Loading live context…</span>
            </div>
          ) : (
            <div className="assistant-context-content">
              <div className="context-focus-card">
                <span className="context-label">FOCUSED ENTITY</span>
                <strong>{entityLabel(focusedEntity)}</strong>
                {focusedEntity && (
                  <div className="context-entity-type">
                    {firstText(
                      focusedEntity.entity_type,
                      focusedEntity.type,
                      focusedEntity.kind,
                      "Entity"
                    )}
                  </div>
                )}
              </div>

              <section className="context-section">
                <div className="context-section-title">
                  <Network size={14} />
                  <span>Relationships</span>
                  <b>{relationshipCount}</b>
                </div>

                {relationshipCount === 0 ? (
                  <div className="context-empty">No relationships returned by the API.</div>
                ) : (
                  <div className="context-list">
                    {context.relationships.slice(0, 8).map((item, index) => (
                      <div className="context-list-item" key={`rel-${index}`}>
                        <span className="context-index">{String(index + 1).padStart(2, "0")}</span>
                        <span>{relationshipLabel(item)}</span>
                      </div>
                    ))}
                  </div>
                )}
              </section>

              <section className="context-section">
                <div className="context-section-title">
                  <FileSearch size={14} />
                  <span>Evidence</span>
                  <b>{evidenceCount}</b>
                </div>

                {evidenceCount === 0 ? (
                  <div className="context-empty">No evidence items returned by the API.</div>
                ) : (
                  <div className="context-list">
                    {context.evidence.slice(0, 8).map((item, index) => (
                      <div className="context-list-item" key={`ev-${index}`}>
                        <span className="context-index">EV</span>
                        <span>{evidenceLabel(item)}</span>
                      </div>
                    ))}
                  </div>
                )}
              </section>

              <section className="context-section">
                <div className="context-section-title">
                  <Clock3 size={14} />
                  <span>Recent memory</span>
                  <b>{memoryCount}</b>
                </div>
                <div className="context-memory-note">
                  {memoryCount
                    ? `${memoryCount} live memory item${memoryCount === 1 ? "" : "s"} retrieved.`
                    : "No recent memory items returned."}
                </div>
              </section>

              {lastUpdated && (
                <div className="context-updated">
                  <span>Last API sync</span>
                  <strong>
                    {lastUpdated.toLocaleTimeString([], {
                      hour: "2-digit",
                      minute: "2-digit",
                      second: "2-digit",
                    })}
                  </strong>
                </div>
              )}
            </div>
          )}

          <div className="assistant-grounding-box">
            <ShieldCheck size={16} />
            <div>
              <strong>Grounding policy</strong>
              <p>
                The interface displays records returned by the assistant and
                context APIs. It does not invent entities, evidence, or
                relationships in the UI.
              </p>
            </div>
          </div>
        </aside>
      </section>
    </main>
  );
}

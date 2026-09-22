import { useEffect, useMemo, useRef, useState } from "react";
import {
  Search,
  X,
  UserRound,
  Building2,
  FileText,
  BriefcaseBusiness,
  ClipboardList,
  ArrowRight,
  Loader2,
} from "lucide-react";

import api from "../services/api";

const SEARCH_LIMIT = 200;

function asArray(value) {
  if (Array.isArray(value)) {
    return value;
  }

  if (Array.isArray(value?.items)) {
    return value.items;
  }

  if (Array.isArray(value?.results)) {
    return value.results;
  }

  if (Array.isArray(value?.data)) {
    return value.data;
  }

  return [];
}

function text(value) {
  return String(value ?? "").trim();
}

function searchableValue(item) {
  return [
    item?.id,
    item?.name,
    item?.title,
    item?.value,
    item?.entity_name,
    item?.entity_value,
    item?.normalized_name,
    item?.normalized_value,
    item?.evidence_number,
    item?.case_number,
    item?.investigation_number,
    item?.description,
    item?.objective,
    item?.source_reference,
  ]
    .map(text)
    .join(" ")
    .toLowerCase();
}

function normalizeEntity(item) {
  return {
    id: item?.id,
    title:
      item?.name ||
      item?.value ||
      item?.entity_name ||
      item?.normalized_name ||
      "Unknown entity",
    subtitle:
      item?.entity_type ||
      item?.type ||
      "ENTITY",
    kind: "entity",
    icon:
      String(item?.entity_type || item?.type || "")
        .toLowerCase() === "organization"
        ? Building2
        : UserRound,
    raw: item,
  };
}

function normalizeEvidence(item) {
  return {
    id: item?.id,
    title:
      item?.title ||
      item?.evidence_number ||
      "Evidence record",
    subtitle:
      item?.evidence_number ||
      item?.evidence_type ||
      "EVIDENCE",
    kind: "evidence",
    icon: FileText,
    raw: item,
  };
}

function normalizeCase(item) {
  return {
    id: item?.id,
    title:
      item?.title ||
      item?.case_number ||
      "Case",
    subtitle:
      item?.case_number ||
      "CASE",
    kind: "case",
    icon: BriefcaseBusiness,
    raw: item,
  };
}

function normalizeInvestigation(item) {
  return {
    id: item?.id,
    title:
      item?.title ||
      item?.investigation_number ||
      "Investigation",
    subtitle:
      item?.investigation_number ||
      item?.status ||
      "INVESTIGATION",
    kind: "investigation",
    icon: ClipboardList,
    raw: item,
  };
}

export default function GlobalSearch({
  open,
  onClose,
  onNavigate,
}) {
  const inputRef = useRef(null);

  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const [records, setRecords] = useState({
    entities: [],
    evidence: [],
    cases: [],
    investigations: [],
  });

  useEffect(() => {
    if (!open) {
      return;
    }

    setQuery("");
    setError(null);

    const timer = window.setTimeout(() => {
      inputRef.current?.focus();
    }, 40);

    return () => {
      window.clearTimeout(timer);
    };
  }, [open]);

  useEffect(() => {
    if (!open) {
      return;
    }

    let cancelled = false;

    async function loadSearchIndex() {
      setLoading(true);
      setError(null);

      try {
        const [
          entitiesResponse,
          evidenceResponse,
          casesResponse,
          investigationsResponse,
        ] = await Promise.all([
          api.get("/entities", {
            params: {
              skip: 0,
              limit: SEARCH_LIMIT,
            },
          }),

          api.get("/evidence", {
            params: {
              skip: 0,
              limit: SEARCH_LIMIT,
            },
          }),

          api.get("/cases", {
            params: {
              skip: 0,
              limit: SEARCH_LIMIT,
            },
          }),

          api.get("/investigations", {
            params: {
              skip: 0,
              limit: SEARCH_LIMIT,
            },
          }),
        ]);

        if (cancelled) {
          return;
        }

        setRecords({
          entities: asArray(entitiesResponse.data),
          evidence: asArray(evidenceResponse.data),
          cases: asArray(casesResponse.data),
          investigations: asArray(
            investigationsResponse.data
          ),
        });
      } catch (requestError) {
        if (cancelled) {
          return;
        }

        setError(
          requestError?.response?.data?.detail ||
            requestError?.message ||
            "Unable to load intelligence search data."
        );
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    loadSearchIndex();

    return () => {
      cancelled = true;
    };
  }, [open]);

  useEffect(() => {
    if (!open) {
      return;
    }

    const handleKeyDown = (event) => {
      if (event.key === "Escape") {
        onClose?.();
      }
    };

    window.addEventListener(
      "keydown",
      handleKeyDown
    );

    return () => {
      window.removeEventListener(
        "keydown",
        handleKeyDown
      );
    };
  }, [open, onClose]);

  const results = useMemo(() => {
    const normalized = [
      ...records.entities.map(normalizeEntity),
      ...records.evidence.map(normalizeEvidence),
      ...records.cases.map(normalizeCase),
      ...records.investigations.map(
        normalizeInvestigation
      ),
    ];

    const cleanQuery = query.trim().toLowerCase();

    if (!cleanQuery) {
      return normalized.slice(0, 12);
    }

    return normalized
      .filter((item) => {
        return searchableValue(item.raw).includes(
          cleanQuery
        );
      })
      .slice(0, 20);
  }, [records, query]);

  const groupedResults = useMemo(() => {
    return {
      investigations: results.filter(
        (item) => item.kind === "investigation"
      ),
      cases: results.filter(
        (item) => item.kind === "case"
      ),
      entities: results.filter(
        (item) => item.kind === "entity"
      ),
      evidence: results.filter(
        (item) => item.kind === "evidence"
      ),
    };
  }, [results]);

  const handleResultClick = (result) => {
    switch (result.kind) {
      case "investigation":
        onNavigate?.(
          "investigations",
          result.id,
          result.raw
        );
        break;

      case "case":
        onNavigate?.(
          "cases",
          result.id,
          result.raw
        );
        break;

      case "evidence":
        onNavigate?.(
          "evidence",
          result.id,
          result.raw
        );
        break;

      case "entity":
        onNavigate?.(
          "graph",
          result.id,
          result.raw
        );
        break;

      default:
        break;
    }

    onClose?.();
  };

  if (!open) {
    return null;
  }

  const sections = [
    {
      key: "investigations",
      label: "Investigations",
      items: groupedResults.investigations,
    },
    {
      key: "cases",
      label: "Cases",
      items: groupedResults.cases,
    },
    {
      key: "entities",
      label: "Entities",
      items: groupedResults.entities,
    },
    {
      key: "evidence",
      label: "Evidence",
      items: groupedResults.evidence,
    },
  ];

  return (
    <div
      className="tn-global-search-backdrop"
      onMouseDown={(event) => {
        if (
          event.target === event.currentTarget
        ) {
          onClose?.();
        }
      }}
    >
      <div
        className="tn-global-search"
        role="dialog"
        aria-modal="true"
        aria-label="TRINETRA intelligence search"
      >
        <div className="tn-global-search-header">
          <div className="tn-global-search-input-wrap">
            {loading ? (
              <Loader2
                size={19}
                className="tn-global-search-loading tn-spin"
              />
            ) : (
              <Search size={19} />
            )}

            <input
              ref={inputRef}
              value={query}
              onChange={(event) =>
                setQuery(event.target.value)
              }
              placeholder="Search entities, evidence, cases, investigations..."
              autoComplete="off"
            />

            <kbd>ESC</kbd>
          </div>

          <button
            type="button"
            className="tn-global-search-close"
            onClick={onClose}
            aria-label="Close search"
          >
            <X size={18} />
          </button>
        </div>

        <div className="tn-global-search-body">
          {error && (
            <div className="tn-global-search-error">
              <span>{error}</span>
            </div>
          )}

          {!loading &&
            !error &&
            query.trim() &&
            results.length === 0 && (
              <div className="tn-global-search-empty">
                <Search size={28} />
                <strong>
                  No intelligence records found
                </strong>
                <span>
                  Try an entity name, evidence number,
                  case number, or investigation number.
                </span>
              </div>
            )}

          {!loading &&
            !error &&
            !query.trim() && (
              <div className="tn-global-search-hint">
                <span>
                  SEARCH ACROSS TRINETRA
                </span>
                <p>
                  Entities · Evidence · Cases ·
                  Investigations
                </p>
              </div>
            )}

          {sections.map((section) => {
            if (section.items.length === 0) {
              return null;
            }

            return (
              <section
                key={section.key}
                className="tn-global-search-section"
              >
                <div className="tn-global-search-section-title">
                  {section.label}
                </div>

                <div className="tn-global-search-results">
                  {section.items.map((result) => {
                    const Icon = result.icon;

                    return (
                      <button
                        type="button"
                        className="tn-global-search-result"
                        key={`${result.kind}-${result.id}`}
                        onClick={() =>
                          handleResultClick(
                            result
                          )
                        }
                      >
                        <div className="tn-global-search-result-icon">
                          <Icon size={17} />
                        </div>

                        <div className="tn-global-search-result-content">
                          <strong>
                            {result.title}
                          </strong>

                          <span>
                            {String(
                              result.subtitle
                            ).replace(
                              /_/g,
                              " "
                            )}
                          </span>
                        </div>

                        <ArrowRight
                          size={15}
                          className="tn-global-search-result-arrow"
                        />
                      </button>
                    );
                  })}
                </div>
              </section>
            );
          })}
        </div>

        <div className="tn-global-search-footer">
          <span>
            TRINETRA INTELLIGENCE INDEX
          </span>

          <span>
            {records.entities.length} entities ·{" "}
            {records.evidence.length} evidence ·{" "}
            {records.cases.length} cases ·{" "}
            {records.investigations.length} investigations
          </span>
        </div>
      </div>
    </div>
  );
}
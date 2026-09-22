import {
  AlertTriangle,
  Building2,
  ChevronRight,
  CircleUserRound,
  ExternalLink,
  Loader2,
  Network,
  ShieldAlert,
  UserRound,
  X,
} from "lucide-react";

import GlassCard from "../ui/GlassCard";
import Badge from "../ui/Badge";

function formatType(value) {
  return String(value || "unknown")
    .replace(/_/g, " ")
    .toUpperCase();
}

function getEntityIcon(type) {
  const normalized = String(type || "")
    .trim()
    .toLowerCase();

  if (normalized === "person") {
    return <UserRound size={18} />;
  }

  if (
    normalized === "organization" ||
    normalized === "org"
  ) {
    return <Building2 size={18} />;
  }

  if (normalized === "bank") {
    return <Building2 size={18} />;
  }

  return <CircleUserRound size={18} />;
}

function normalizeConfidence(value) {
  if (
    typeof value !== "number" ||
    !Number.isFinite(value)
  ) {
    return null;
  }

  return value <= 1 ? value * 100 : value;
}

function getRelationshipSource(record) {
  return (
    record.source_value ??
    record.sourceValue ??
    record.start_value ??
    record.startValue ??
    ""
  );
}

function getRelationshipTarget(record) {
  return (
    record.target_value ??
    record.targetValue ??
    record.neighbor_value ??
    record.neighborValue ??
    record.related_value ??
    record.relatedValue ??
    ""
  );
}

function getRelationshipType(record) {
  return (
    record.relationship_type ??
    record.relationshipType ??
    record.type ??
    record.relationship ??
    "RELATED_TO"
  );
}

function getRelationshipConfidence(record) {
  return normalizeConfidence(
    record.confidence ??
      record.relationship_confidence ??
      record.relationshipConfidence
  );
}

function getRelationshipEvidence(record) {
  return (
    record.evidence_text ??
    record.evidenceText ??
    record.source_field ??
    record.sourceField ??
    null
  );
}

function RelationshipItem({
  relationship,
  entityValue,
}) {
  const source =
    getRelationshipSource(
      relationship
    );

  const target =
    getRelationshipTarget(
      relationship
    );

  const relationshipType =
    getRelationshipType(
      relationship
    );

  const confidence =
    getRelationshipConfidence(
      relationship
    );

  const evidence =
    getRelationshipEvidence(
      relationship
    );

  const connectedEntity =
    source &&
    source.toLowerCase() ===
      String(entityValue || "")
        .toLowerCase()
      ? target
      : source;

  return (
    <div className="tn-entity-relationship">
      <div className="tn-entity-relationship-icon">
        <Network size={15} />
      </div>

      <div className="tn-entity-relationship-main">
        <div className="tn-entity-relationship-top">
          <strong>
            {connectedEntity ||
              "Unknown entity"}
          </strong>

          {confidence !== null && (
            <span>
              {Math.round(
                confidence
              )}
              %
            </span>
          )}
        </div>

        <div className="tn-entity-relationship-type">
          {formatType(
            relationshipType
          )}
        </div>

        {evidence && (
          <div className="tn-entity-relationship-evidence">
            {evidence}
          </div>
        )}
      </div>

      <ChevronRight size={15} />
    </div>
  );
}

export default function EntityPanel({
  entity,
  relationships = [],
  loading = false,
  error = null,
  onClose,
  onTracePath,
}) {
  if (!entity) {
    return null;
  }

  const entityType =
    entity.entity_type ??
    entity.entityType ??
    entity.type ??
    "unknown";

  const entityValue =
    entity.entity_value ??
    entity.entityValue ??
    entity.value ??
    entity.name ??
    "Unknown entity";

  const riskValue =
    entity.risk_score ??
    entity.riskScore ??
    entity.risk ??
    null;

  const normalizedRisk =
    typeof riskValue === "number"
      ? riskValue <= 1
        ? riskValue * 100
        : riskValue
      : null;

  const riskLevel =
    normalizedRisk === null
      ? "UNKNOWN"
      : normalizedRisk >= 70
      ? "HIGH"
      : normalizedRisk >= 40
      ? "MODERATE"
      : "LOW";

  return (
    <div className="tn-entity-panel-backdrop">
      <div className="tn-entity-panel">
        <GlassCard>
          <div className="tn-entity-panel-header">
            <div className="tn-entity-heading">
              <div className="tn-entity-icon">
                {getEntityIcon(
                  entityType
                )}
              </div>

              <div>
                <div className="tn-section-kicker">
                  ENTITY INTELLIGENCE
                </div>

                <h2>
                  {entityValue}
                </h2>

                <span>
                  {formatType(
                    entityType
                  )}
                </span>
              </div>
            </div>

            <button
              type="button"
              className="tn-icon-button"
              onClick={onClose}
              title="Close entity panel"
            >
              <X size={17} />
            </button>
          </div>

          {error && (
            <div className="tn-entity-error">
              <AlertTriangle
                size={16}
              />

              <span>
                {error}
              </span>
            </div>
          )}

          <div className="tn-entity-summary-grid">
            <div className="tn-entity-summary-item">
              <span>
                TYPE
              </span>

              <strong>
                {formatType(
                  entityType
                )}
              </strong>
            </div>

            <div className="tn-entity-summary-item">
              <span>
                RELATIONSHIPS
              </span>

              <strong>
                {relationships.length}
              </strong>
            </div>

            <div className="tn-entity-summary-item">
              <span>
                RISK SIGNAL
              </span>

              <strong>
                {normalizedRisk ===
                null
                  ? "—"
                  : `${Math.round(
                      normalizedRisk
                    )}/100`}
              </strong>
            </div>
          </div>

          <div className="tn-entity-risk">
            <div className="tn-entity-risk-header">
              <div>
                <div className="tn-section-kicker">
                  ANALYTICAL SIGNAL
                </div>

                <h3>
                  Risk indicator
                </h3>
              </div>

              <Badge>
                {riskLevel}
              </Badge>
            </div>

            {normalizedRisk !==
            null ? (
              <div className="tn-entity-risk-bar">
                <div
                  style={{
                    width: `${Math.min(
                      100,
                      Math.max(
                        0,
                        normalizedRisk
                      )
                    )}%`,
                  }}
                />
              </div>
            ) : (
              <div className="tn-empty-state">
                No entity-level risk score
                was returned.
              </div>
            )}

            <p>
              Risk is an analytical signal
              derived from recorded
              intelligence. It is not a
              determination of guilt.
            </p>
          </div>

          <div className="tn-entity-section">
            <div className="tn-section-header">
              <div>
                <div className="tn-section-kicker">
                  NETWORK INTELLIGENCE
                </div>

                <h3>
                  Connected entities
                </h3>
              </div>

              {loading && (
                <Loader2
                  size={17}
                  className="tn-spin"
                />
              )}
            </div>

            {loading ? (
              <div className="tn-empty-state">
                Loading entity relationships...
              </div>
            ) : relationships.length >
              0 ? (
              <div className="tn-entity-relationships">
                {relationships.map(
                  (
                    relationship,
                    index
                  ) => (
                    <RelationshipItem
                      key={
                        relationship.id ??
                        relationship.relationship_id ??
                        `${getRelationshipType(
                          relationship
                        )}-${index}`
                      }
                      relationship={
                        relationship
                      }
                      entityValue={
                        entityValue
                      }
                    />
                  )
                )}
              </div>
            ) : (
              <div className="tn-empty-state">
                No relationship records
                returned for this entity.
              </div>
            )}
          </div>

          {onTracePath && (
            <button
              type="button"
              className="tn-entity-trace-button"
              onClick={() =>
                onTracePath(
                  entity
                )
              }
            >
              <ShieldAlert size={16} />

              Trace entity through graph

              <ExternalLink
                size={15}
              />
            </button>
          )}
        </GlassCard>
      </div>
    </div>
  );
}
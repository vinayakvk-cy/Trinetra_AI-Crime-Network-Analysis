import api from "./api";

export async function getReportTypes() {
  const response = await api.get("/reports/types");
  return response.data;
}

function buildCommonPayload({
  investigationId,
  title = "",
  includeEvidence = true,
  includeEntities = true,
  includeRelationships = true,
  includeAnalytics = true,
  includeTimeline = true,
}) {
  return {
    investigation_id: Number(investigationId),
    title: title.trim() || null,
    include_evidence: Boolean(includeEvidence),
    include_entities: Boolean(includeEntities),
    include_relationships: Boolean(includeRelationships),
    include_analytics: Boolean(includeAnalytics),
    include_timeline: Boolean(includeTimeline),
  };
}

export async function previewReport(options = {}) {
  const response = await api.post("/reports/preview", buildCommonPayload(options));
  return response.data;
}

export async function generateIntelligenceReport({
  investigationId,
  title = "",
  classification = "internal",
  summary = "",
  includeEvidence = true,
  includeEntities = true,
  includeRelationships = true,
  includeAnalytics = true,
  includeTimeline = true,
} = {}) {
  const payload = {
    ...buildCommonPayload({
      investigationId,
      title,
      includeEvidence,
      includeEntities,
      includeRelationships,
      includeAnalytics,
      includeTimeline,
    }),
    classification,
    summary: summary.trim() || null,
  };

  const response = await api.post("/reports/intelligence", payload);
  return response.data;
}

export async function generateDocumentaryReport({
  investigationId,
  title = "",
  narrativeStyle = "investigative",
  includeNarrative = true,
  includeEvidence = true,
  includeEntities = true,
  includeRelationships = true,
  includeAnalytics = true,
  includeTimeline = true,
} = {}) {
  const payload = {
    ...buildCommonPayload({
      investigationId,
      title,
      includeEvidence,
      includeEntities,
      includeRelationships,
      includeAnalytics,
      includeTimeline,
    }),
    narrative_style: narrativeStyle,
    include_narrative: Boolean(includeNarrative),
  };

  const response = await api.post("/reports/documentary", payload);
  return response.data;
}

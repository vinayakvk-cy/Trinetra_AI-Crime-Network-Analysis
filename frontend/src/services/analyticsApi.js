import api from "./api";

export async function getAnalyticsSummary(investigationId) {
  const response = await api.get(
    `/analytics/investigations/${investigationId}/summary`
  );
  return response.data;
}

export async function getGraphCentrality(limit = 20) {
  const response = await api.get("/analytics/graph/centrality", {
    params: { limit },
  });
  return response.data;
}

export async function getGraphConnectivity() {
  const response = await api.get("/analytics/graph/connectivity");
  return response.data;
}

export async function getPatterns(investigationId, entityId = null) {
  const payload = { investigation_id: investigationId };

  if (entityId !== null && entityId !== undefined) {
    payload.entity_id = entityId;
  }

  const response = await api.post("/analytics/patterns", payload);
  return response.data;
}

export async function getRisk({ investigationId = null, entityId = null } = {}) {
  const payload = {};

  if (investigationId !== null && investigationId !== undefined) {
    payload.investigation_id = investigationId;
  }

  if (entityId !== null && entityId !== undefined) {
    payload.entity_id = entityId;
  }

  const response = await api.post("/analytics/risk", payload);
  return response.data;
}

export async function getSimilarity({
  sourceEntityId,
  targetEntityId = null,
  limit = 5,
} = {}) {
  const payload = {
    source_entity_id: sourceEntityId,
    limit,
  };

  if (targetEntityId !== null && targetEntityId !== undefined) {
    payload.target_entity_id = targetEntityId;
  }

  const response = await api.post("/analytics/similarity", payload);
  return response.data;
}
export async function getInvestigationSummary(investigationId) {
  const response = await api.get(
    `/analytics/investigations/${investigationId}/summary`
  );

  return response.data;
}
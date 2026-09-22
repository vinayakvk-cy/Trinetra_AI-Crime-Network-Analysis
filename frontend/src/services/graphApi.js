import api from "./api";

function normalizeType(value) {
  return String(value ?? "").trim().toUpperCase();
}

function normalizeValue(value) {
  return String(value ?? "").trim();
}

function listFrom(payload, keys = []) {
  if (Array.isArray(payload)) return payload;
  for (const key of keys) {
    if (Array.isArray(payload?.[key])) return payload[key];
  }
  return [];
}

export async function getGraphHealth() {
  const response = await api.get("/graph/health");
  return response.data;
}

export async function getGraphStats() {
  const response = await api.get("/graph/stats");
  return response.data;
}

export async function searchGraphEntities(value = "") {
  const response = await api.post("/graph/query", {
    query_name: "search_entities",
    parameters: { value: String(value ?? "") },
  });

  return listFrom(response.data?.results, ["results", "entities"]);
}

export async function getGraphNeighborhood({ entityType, entityValue, depth = 1, limit = 100 }) {
  const response = await api.post("/graph/neighborhood", {
    entity_type: normalizeType(entityType),
    entity_value: normalizeValue(entityValue),
    depth,
    limit,
  });

  return listFrom(response.data, ["results", "neighborhood"]);
}

export async function getGraphRelationships({ entityType, entityValue, limit = 1000 }) {
  const response = await api.get("/graph/relationships", {
    params: {
      entity_type: normalizeType(entityType),
      entity_value: normalizeValue(entityValue),
      limit,
    },
  });

  return listFrom(response.data, ["relationships", "results"]);
}

export async function getShortestGraphPath({ sourceType, sourceValue, targetType, targetValue, maxDepth = 6 }) {
  const response = await api.get("/graph/shortest-path", {
    params: {
      source_type: normalizeType(sourceType),
      source_value: normalizeValue(sourceValue),
      target_type: normalizeType(targetType),
      target_value: normalizeValue(targetValue),
      max_depth: maxDepth,
    },
  });

  return response.data;
}

import api from "./api";

import {
  getInvestigationSummary,
} from "./analyticsApi";

import {
  listEvidence,
} from "./evidenceApi";

import {
  getGraphHealth,
  getGraphStats,
} from "./graphApi";

/**
 * Load all data required by the Dashboard.
 *
 * Every request is independent so that one failed
 * service does not destroy the entire dashboard.
 */
export async function getDashboardData(
  investigationId = null
) {
  const [
    healthResult,
    statsResult,
    evidenceResult,
    summaryResult,
  ] = await Promise.allSettled([
    getGraphHealth(),

    getGraphStats(),

    listEvidence({
      limit: 100,
    }),

    investigationId
      ? getInvestigationSummary(investigationId)
      : Promise.resolve(null),
  ]);

  const errors = [];

  if (healthResult.status === "rejected") {
    errors.push(
      formatApiError(
        healthResult.reason,
        "Graph health"
      )
    );
  }

  if (statsResult.status === "rejected") {
    errors.push(
      formatApiError(
        statsResult.reason,
        "Graph statistics"
      )
    );
  }

  if (evidenceResult.status === "rejected") {
    errors.push(
      formatApiError(
        evidenceResult.reason,
        "Evidence"
      )
    );
  }

  if (summaryResult.status === "rejected") {
    errors.push(
      formatApiError(
        summaryResult.reason,
        "Investigation analytics"
      )
    );
  }

  return {
    health:
      healthResult.status === "fulfilled"
        ? healthResult.value
        : null,

    stats:
      statsResult.status === "fulfilled"
        ? statsResult.value
        : null,

    evidence:
      evidenceResult.status === "fulfilled"
        ? evidenceResult.value
        : null,

    summary:
      summaryResult.status === "fulfilled"
        ? summaryResult.value
        : null,

    errors,
  };
}

/**
 * Format an Axios/backend error into something
 * useful for the UI.
 */
function formatApiError(
  error,
  serviceName
) {
  const detail =
    error?.response?.data?.detail ||
    error?.response?.data?.message ||
    error?.response?.data?.error ||
    error?.message ||
    "Request failed.";

  let text = detail;
  if (Array.isArray(detail)) text = detail.map((item) => item?.msg || item?.message || String(item)).join(" • ");
  else if (detail && typeof detail === "object") text = detail.message || detail.msg || JSON.stringify(detail);

  return `${serviceName}: ${text}`;
}

/**
 * Load only the graph portion of the dashboard.
 */
export async function refreshGraphData() {
  const [
    healthResult,
    statsResult,
  ] = await Promise.allSettled([
    getGraphHealth(),
    getGraphStats(),
  ]);

  return {
    health:
      healthResult.status === "fulfilled"
        ? healthResult.value
        : null,

    stats:
      statsResult.status === "fulfilled"
        ? statsResult.value
        : null,

    errors: [
      healthResult,
      statsResult,
    ]
      .filter(
        (result) =>
          result.status === "rejected"
      )
      .map((result) =>
        formatApiError(
          result.reason,
          "Graph"
        )
      ),
  };
}

/**
 * Load only the active investigation.
 */
export async function refreshInvestigationData(
  investigationId
) {
  try {
    return await getInvestigationSummary(
      investigationId
    );
  } catch (error) {
    throw new Error(
      formatApiError(
        error,
        "Investigation analytics"
      )
    );
  }
}

/**
 * Load only evidence data.
 */
export async function refreshEvidenceData() {
  try {
    return await listEvidence({
      limit: 100,
    });
  } catch (error) {
    throw new Error(
      formatApiError(
        error,
        "Evidence"
      )
    );
  }
}

/**
 * Extract graph node count from the backend response.
 */
export function extractNodeCount(payload) {
  if (!payload) {
    return 0;
  }

  const candidates = [
    payload.nodes,
    payload.node_count,
    payload.nodeCount,

    payload.results?.nodes,
    payload.results?.node_count,
    payload.results?.nodeCount,

    payload.data?.nodes,
    payload.data?.node_count,
    payload.data?.nodeCount,
  ];

  const value = candidates.find(
    (item) =>
      typeof item === "number" &&
      Number.isFinite(item)
  );

  return value ?? 0;
}

/**
 * Extract graph relationship count.
 */
export function extractRelationshipCount(
  payload
) {
  if (!payload) {
    return 0;
  }

  const candidates = [
    payload.relationships,
    payload.relationship_count,
    payload.relationshipCount,

    payload.results?.relationships,
    payload.results?.relationship_count,
    payload.results?.relationshipCount,

    payload.data?.relationships,
    payload.data?.relationship_count,
    payload.data?.relationshipCount,
  ];

  const value = candidates.find(
    (item) =>
      typeof item === "number" &&
      Number.isFinite(item)
  );

  return value ?? 0;
}

/**
 * Extract the evidence collection.
 */
export function extractEvidenceRecords(
  payload
) {
  if (!payload) {
    return [];
  }

  if (Array.isArray(payload)) {
    return payload;
  }

  if (Array.isArray(payload.evidence)) {
    return payload.evidence;
  }

  if (Array.isArray(payload.results)) {
    return payload.results;
  }

  if (Array.isArray(payload.data)) {
    return payload.data;
  }

  return [];
}

/**
 * Extract graph relationship records from an
 * investigation summary.
 *
 * The analytics endpoint can return graph information
 * in several forms depending on the backend analysis
 * implementation.
 */
export function extractRelationshipRecords(
  payload
) {
  if (!payload) {
    return [];
  }

  const graph = payload.graph || payload;

  if (Array.isArray(graph)) {
    return graph;
  }

  const candidates = [
    graph.relationships,
    graph.results,
    graph.connections,
    graph.relationship_records,
    graph.relationshipRecords,

    graph.data?.relationships,
    graph.data?.results,
    graph.data?.connections,
  ];

  for (const candidate of candidates) {
    if (Array.isArray(candidate)) {
      return candidate;
    }
  }

  return [];
}

/**
 * Determine whether the graph API is online.
 */
export function isGraphOnline(payload) {
  if (!payload) {
    return false;
  }

  if (payload.neo4j === true) {
    return true;
  }

  if (payload.success === true) {
    return true;
  }

  if (
    payload.status &&
    String(payload.status).toLowerCase() ===
      "healthy"
  ) {
    return true;
  }

  return false;
}
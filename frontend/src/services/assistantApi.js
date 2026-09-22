import api from "./api";

/**
 * Ask the main TRINETRA assistant.
 */
export async function askAssistant({
  question,
  investigationId = null,
  entityId = null,
} = {}) {
  const payload = {
    question,
    investigation_id: investigationId,
  };

  if (entityId !== null && entityId !== undefined) {
    payload.entity_id = entityId;
  }

  const response = await api.post(
    "/assistant/ask",
    payload
  );

  return response.data;
}

/**
 * Ask the assistant specifically about an investigation.
 */
export async function askInvestigationAssistant(
  investigationId = null,
  question
) {
  const response = await api.post(
    `/assistant/investigations/${investigationId}/ask`,
    {
      question,
    }
  );

  return response.data;
}

/**
 * Load investigation context.
 *
 * IMPORTANT:
 * /assistant/context is a POST endpoint.
 * Do not use GET here.
 */
export async function getAssistantContext({
  investigationId = null,
  entityId = null,
  memoryLimit = 10,
} = {}) {
  const payload = {
    investigation_id: investigationId,
    limit: memoryLimit,
  };

  if (entityId !== null && entityId !== undefined) {
    payload.entity_id = entityId;
  }

  const response = await api.post(
    "/assistant/context",
    payload
  );

  return response.data;
}

/**
 * Check assistant service health.
 */
export async function getAssistantHealth() {
  const response = await api.get(
    "/assistant/health"
  );

  return response.data;
}

/**
 * Extract the assistant's answer from different
 * possible backend response shapes.
 */
export function extractAssistantAnswer(
  payload
) {
  if (!payload) {
    return "";
  }

  if (typeof payload === "string") {
    return payload;
  }

  const candidates = [
    payload.answer,
    payload.response,
    payload.message,
    payload.content,

    payload.result?.answer,
    payload.result?.response,
    payload.result?.message,
    payload.result?.content,

    payload.data?.answer,
    payload.data?.response,
    payload.data?.message,
    payload.data?.content,

    payload.results?.answer,
    payload.results?.response,
    payload.results?.message,
    payload.results?.content,
  ];

  const value = candidates.find(
    (item) =>
      typeof item === "string" &&
      item.trim().length > 0
  );

  return value || "";
}

/**
 * Extract source/evidence records from an
 * assistant response.
 */
export function extractAssistantSources(
  payload
) {
  if (!payload) {
    return [];
  }

  const candidates = [
    payload.sources,
    payload.source_documents,
    payload.evidence,

    payload.result?.sources,
    payload.result?.source_documents,
    payload.result?.evidence,

    payload.data?.sources,
    payload.data?.source_documents,
    payload.data?.evidence,

    payload.results?.sources,
    payload.results?.source_documents,
    payload.results?.evidence,
  ];

  for (const candidate of candidates) {
    if (Array.isArray(candidate)) {
      return candidate;
    }
  }

  return [];
}

/**
 * Extract investigation context from the backend.
 */
export function extractAssistantContext(
  payload
) {
  if (!payload) {
    return null;
  }

  if (typeof payload === "string") {
    return payload;
  }

  const candidates = [
    payload.context,
    payload.investigation_context,
    payload.data,
    payload.result,
    payload.results,
  ];

  for (const candidate of candidates) {
    if (
      candidate !== undefined &&
      candidate !== null
    ) {
      return candidate;
    }
  }

  return payload;
}

/**
 * Normalize an assistant message for the UI.
 */
export function normalizeAssistantMessage(
  payload,
  role = "assistant"
) {
  const answer =
    extractAssistantAnswer(payload);

  const sources =
    extractAssistantSources(payload);

  return {
    id:
      payload?.id ??
      `${role}-${Date.now()}`,

    role,

    content: answer,

    answer,

    sources,
  };
}
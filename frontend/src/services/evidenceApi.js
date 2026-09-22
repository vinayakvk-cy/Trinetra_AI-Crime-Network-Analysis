import api from "./api";

/**
 * Get all evidence records.
 */
export async function listEvidence(params = {}) {
  const response = await api.get("/evidence", {
    params,
  });

  return response.data;
}

/**
 * Get a single evidence record.
 */
export async function getEvidence(evidenceId) {
  if (!evidenceId) {
    throw new Error("Evidence ID is required.");
  }

  const response = await api.get(`/evidence/${evidenceId}`);

  return response.data;
}

/**
 * Search evidence.
 */
export async function searchEvidence(query, params = {}) {
  if (!query || !query.trim()) {
    throw new Error("Evidence search query is required.");
  }

  const response = await api.get("/evidence/search/", {
    params: {
      q: query.trim(),
      ...params,
    },
  });

  return response.data;
}

/**
 * Upload evidence to the backend.
 *
 * The backend expects multipart/form-data:
 * - case_id
 * - evidence_number
 * - title
 * - evidence_type
 * - description
 * - source_type
 * - source_reference
 * - file
 */
export async function uploadEvidence({
  caseId,
  evidenceNumber,
  title,
  evidenceType = "document",
  description = "",
  sourceType = "",
  sourceReference = "",
  file,
  onUploadProgress,
}) {
  if (!caseId) {
    throw new Error("Case ID is required.");
  }

  if (!evidenceNumber) {
    throw new Error("Evidence number is required.");
  }

  if (!title) {
    throw new Error("Evidence title is required.");
  }

  if (!file) {
    throw new Error("Evidence file is required.");
  }

  const formData = new FormData();

  formData.append("case_id", String(caseId));
  formData.append("evidence_number", evidenceNumber);
  formData.append("title", title);
  formData.append("evidence_type", evidenceType);

  if (description) {
    formData.append("description", description);
  }

  if (sourceType) {
    formData.append("source_type", sourceType);
  }

  if (sourceReference) {
    formData.append("source_reference", sourceReference);
  }

  formData.append("file", file);

  const response = await api.post("/evidence/upload", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },

    onUploadProgress,
  });

  return response.data;
}

/**
 * Ingest an existing evidence record.
 */
export async function ingestEvidence(evidenceId) {
  if (!evidenceId) {
    throw new Error("Evidence ID is required.");
  }

  const response = await api.post(
    `/evidence/${evidenceId}/ingest`
  );

  return response.data;
}

/**
 * Extract a useful evidence object from different
 * backend response shapes.
 */
export function normalizeEvidence(record) {
  if (!record || typeof record !== "object") {
    return null;
  }

  const evidence =
    record.evidence ||
    record.data ||
    record;

  return {
    id:
      evidence.id ||
      evidence.evidence_id ||
      null,

    evidenceNumber:
      evidence.evidence_number ||
      evidence.evidenceNumber ||
      "UNKNOWN",

    title:
      evidence.title ||
      "Untitled Evidence",

    evidenceType:
      evidence.evidence_type ||
      evidence.evidenceType ||
      "document",

    description:
      evidence.description ||
      "",

    status:
      evidence.status ||
      "unknown",

    fileName:
      evidence.file_name ||
      evidence.fileName ||
      "",

    filePath:
      evidence.file_path ||
      evidence.filePath ||
      "",

    mimeType:
      evidence.mime_type ||
      evidence.mimeType ||
      "",

    fileSize:
      evidence.file_size ||
      evidence.fileSize ||
      null,

    fileHash:
      evidence.file_hash ||
      evidence.fileHash ||
      "",

    extractionConfidence:
      typeof evidence.extraction_confidence === "number"
        ? evidence.extraction_confidence
        : typeof evidence.extractionConfidence === "number"
          ? evidence.extractionConfidence
          : null,

    createdAt:
      evidence.created_at ||
      evidence.createdAt ||
      null,

    updatedAt:
      evidence.updated_at ||
      evidence.updatedAt ||
      null,

    sourceType:
      evidence.source_type ||
      evidence.sourceType ||
      "",

    sourceReference:
      evidence.source_reference ||
      evidence.sourceReference ||
      "",

    extractedText:
      evidence.extracted_text ||
      evidence.extractedText ||
      "",

    extractedEntities:
      evidence.extracted_entities ||
      evidence.extractedEntities ||
      [],

    extractedRelationships:
      evidence.extracted_relationships ||
      evidence.extractedRelationships ||
      [],
  };
}

/**
 * Normalize the extraction result returned after upload.
 */
export function normalizeExtraction(payload) {
  if (!payload || typeof payload !== "object") {
    return null;
  }

  const extraction =
    payload.extraction ||
    payload.data?.extraction ||
    null;

  if (!extraction) {
    return null;
  }

  return {
    extractedText:
      extraction.extracted_text ||
      extraction.extractedText ||
      "",

    extractionConfidence:
      typeof extraction.extraction_confidence === "number"
        ? extraction.extraction_confidence
        : typeof extraction.extractionConfidence === "number"
          ? extraction.extractionConfidence
          : null,

    extractionMethod:
      extraction.extraction_method ||
      extraction.extractionMethod ||
      "",

    fileName:
      extraction.file_name ||
      extraction.fileName ||
      "",

    mimeType:
      extraction.mime_type ||
      extraction.mimeType ||
      "",

    pageCount:
      extraction.page_count ||
      extraction.pageCount ||
      null,
  };
}

/**
 * Normalize the ingestion result returned after upload.
 */
export function normalizeIngestion(payload) {
  if (!payload || typeof payload !== "object") {
    return null;
  }

  const ingestion =
    payload.ingestion ||
    payload.data?.ingestion ||
    null;

  if (!ingestion) {
    return null;
  }

  return {
    evidenceId:
      ingestion.evidence_id ||
      ingestion.evidenceId ||
      null,

    entitiesCreated:
      ingestion.entities_created ??
      ingestion.entitiesCreated ??
      0,

    entitiesReused:
      ingestion.entities_reused ??
      ingestion.entitiesReused ??
      0,

    caseEntitiesCreated:
      ingestion.case_entities_created ??
      ingestion.caseEntitiesCreated ??
      0,

    caseEntitiesReused:
      ingestion.case_entities_reused ??
      ingestion.caseEntitiesReused ??
      0,

    relationshipsCreated:
      ingestion.relationships_created ??
      ingestion.relationshipsCreated ??
      0,

    relationshipsReused:
      ingestion.relationships_reused ??
      ingestion.relationshipsReused ??
      0,

    graphNodesSynced:
      ingestion.graph_nodes_synced ??
      ingestion.graphNodesSynced ??
      0,

    graphRelationshipsSynced:
      ingestion.graph_relationships_synced ??
      ingestion.graphRelationshipsSynced ??
      0,

    extractedEntities:
      ingestion.extracted_entities ||
      ingestion.extractedEntities ||
      [],

    extractedRelationships:
      ingestion.extracted_relationships ||
      ingestion.extractedRelationships ||
      [],
  };
}
import { useCallback, useEffect, useState } from "react";

import {
  listEvidence,
  searchEvidence,
  uploadEvidence,
  ingestEvidence,
  getEvidence,
  normalizeEvidence,
  normalizeExtraction,
  normalizeIngestion,
} from "../services/evidenceApi";

export function useEvidence(caseId = null) {
  const [evidence, setEvidence] = useState([]);
  const [selectedEvidence, setSelectedEvidence] =
    useState(null);

  const [extraction, setExtraction] = useState(null);
  const [ingestion, setIngestion] = useState(null);

  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);

  const [error, setError] = useState(null);

  /**
   * Load evidence records.
   */
  const loadEvidence = useCallback(
    async (params = {}) => {
      setLoading(true);
      setError(null);

      try {
        const result = await listEvidence(params);

        const records =
          Array.isArray(result)
            ? result
            : result?.evidence ||
              result?.results ||
              result?.data ||
              [];

        const normalized = records
          .map(normalizeEvidence)
          .filter(Boolean);

        setEvidence(normalized);

        return normalized;
      } catch (err) {
        const message =
          (typeof err?.response?.data?.detail === "string" ? err.response.data.detail : err?.response?.data?.detail?.message || err?.response?.data?.detail?.msg) ||
          err?.message ||
          "Failed to load evidence.";

        setError(message);

        throw err;
      } finally {
        setLoading(false);
      }
    },
    []
  );

  /**
   * Search evidence.
   */
  const search = useCallback(async (query) => {
    setLoading(true);
    setError(null);

    try {
      const result = await searchEvidence(query);

      const records =
        Array.isArray(result)
          ? result
          : result?.evidence ||
            result?.results ||
            result?.data ||
            [];

      const normalized = records
        .map(normalizeEvidence)
        .filter(Boolean);

      setEvidence(normalized);

      return normalized;
    } catch (err) {
      const message =
        err?.response?.data?.detail ||
        err?.message ||
        "Evidence search failed.";

      setError(message);

      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * Upload evidence and wait for the backend
   * extraction + ingestion response.
   */
  const upload = useCallback(
    async ({
      evidenceNumber,
      title,
      evidenceType = "document",
      description = "",
      sourceType = "",
      sourceReference = "",
      file,
    }) => {
      setUploading(true);
      setUploadProgress(0);
      setError(null);
      setExtraction(null);
      setIngestion(null);

      try {
        const result = await uploadEvidence({
          caseId,
          evidenceNumber,
          title,
          evidenceType,
          description,
          sourceType,
          sourceReference,
          file,

          onUploadProgress: (event) => {
            if (!event?.total) {
              return;
            }

            const progress = Math.round(
              (event.loaded / event.total) * 100
            );

            setUploadProgress(progress);
          },
        });

        const normalizedEvidence =
          normalizeEvidence(result?.evidence);

        const normalizedExtraction =
          normalizeExtraction(result);

        const normalizedIngestion =
          normalizeIngestion(result);

        if (normalizedEvidence) {
          setSelectedEvidence(
            normalizedEvidence
          );

          setEvidence((current) => {
            const exists = current.some(
              (item) =>
                item.id === normalizedEvidence.id
            );

            if (exists) {
              return current.map((item) =>
                item.id === normalizedEvidence.id
                  ? normalizedEvidence
                  : item
              );
            }

            return [
              normalizedEvidence,
              ...current,
            ];
          });
        }

        setExtraction(normalizedExtraction);
        setIngestion(normalizedIngestion);
        setUploadProgress(100);

        return result;
      } catch (err) {
        const message =
          (typeof err?.response?.data?.detail === "string" ? err.response.data.detail : err?.response?.data?.detail?.message || err?.response?.data?.detail?.msg) ||
          err?.message ||
          "Evidence upload failed.";

        setError(message);

        throw err;
      } finally {
        setUploading(false);
      }
    },
    [caseId]
  );

  /**
   * Re-run ingestion for an existing evidence record.
   */
  const ingest = useCallback(async (evidenceId) => {
    setLoading(true);
    setError(null);

    try {
      const result =
        await ingestEvidence(evidenceId);

      const normalizedExtraction =
        normalizeExtraction(result);

      const normalizedIngestion =
        normalizeIngestion(result);

      setExtraction(normalizedExtraction);
      setIngestion(normalizedIngestion);

      await loadEvidence();

      return result;
    } catch (err) {
      const message =
        err?.response?.data?.detail ||
        err?.message ||
        "Evidence ingestion failed.";

      setError(message);

      throw err;
    } finally {
      setLoading(false);
    }
  }, [loadEvidence]);

  /**
   * Select an evidence record.
   */
  const selectEvidence = useCallback(
    async (item) => {
      if (!item?.id) {
        setSelectedEvidence(item);
        setExtraction(null);
        setIngestion(null);
        return item;
      }

      setLoading(true);
      setError(null);

      try {
        const detail = await getEvidence(item.id);
        const normalized = normalizeEvidence(detail);

        const selected = normalized || item;
        setSelectedEvidence(selected);

        const detailExtraction = normalizeExtraction({
          extraction: {
            extractedText: detail?.extracted_text ?? detail?.extractedText ?? selected?.extractedText ?? "",
            extractionConfidence:
              detail?.extraction_confidence ??
              detail?.extractionConfidence ??
              selected?.extractionConfidence,
            extractionMethod:
              detail?.extraction_method ??
              detail?.extractionMethod ??
              "persisted",
            fileName:
              detail?.file_name ??
              detail?.fileName ??
              selected?.fileName ??
              "",
            mimeType:
              detail?.mime_type ??
              detail?.mimeType ??
              selected?.mimeType ??
              "",
          },
        });

        const detailIngestion = normalizeIngestion({
          ingestion: detail?.ingestion ?? {
            evidenceId: detail?.id,
            extractedEntities:
              detail?.extracted_entities ??
              detail?.extractedEntities ??
              [],
            extractedRelationships:
              detail?.extracted_relationships ??
              detail?.extractedRelationships ??
              [],
            entitiesCreated:
              detail?.extracted_entities?.length ?? 0,
            relationshipsCreated:
              detail?.extracted_relationships?.length ?? 0,
            graphNodesSynced:
              detail?.extracted_entities?.length ?? 0,
            graphRelationshipsSynced:
              detail?.extracted_relationships?.length ?? 0,
          },
        });

        setExtraction(detailExtraction);
        setIngestion(detailIngestion);

        return detail;
      } catch (err) {
        setError(
          err?.response?.data?.detail ||
            err?.message ||
            "Failed to load evidence details."
        );
        setSelectedEvidence(item);
        throw err;
      } finally {
        setLoading(false);
      }
    },
    []
  );

  /**
   * Clear selected evidence and processing output.
   */
  const clearSelection = useCallback(() => {
    setSelectedEvidence(null);
    setExtraction(null);
    setIngestion(null);
    setError(null);
  }, []);

  /**
   * Load evidence automatically when the hook mounts.
   */
  useEffect(() => {
    loadEvidence().catch(() => {
      // Error is already stored in state.
    });
  }, [loadEvidence]);

  return {
    evidence,
    selectedEvidence,

    extraction,
    ingestion,

    loading,
    uploading,
    uploadProgress,
    error,

    loadEvidence,
    search,
    upload,
    ingest,
    selectEvidence,
    clearSelection,
  };
}
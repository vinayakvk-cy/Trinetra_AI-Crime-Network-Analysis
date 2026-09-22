import { useEffect, useMemo, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Archive,
  CheckCircle2,
  ChevronDown,
  CircleDot,
  Database,
  FileArchive,
  FileCode2,
  FileImage,
  FileSpreadsheet,
  FileText,
  Fingerprint,
  HardDrive,
  Info,
  Loader2,
  Network,
  Search,
  ShieldCheck,
  Sparkles,
  Upload,
  X,
  XCircle,
} from "lucide-react";

import GlassCard from "../components/ui/GlassCard";
import Badge from "../components/ui/Badge";

import { useEvidence } from "../hooks/useEvidence";
import { getActiveCaseId } from "../services/activeCase";



const EASE = [0.22, 1, 0.36, 1];

function formatStatus(status) {
  if (!status) {
    return "UNKNOWN";
  }

  return String(status)
    .replace(/_/g, " ")
    .toUpperCase();
}

function formatLabel(value) {
  if (!value) {
    return "—";
  }

  return String(value)
    .replace(/_/g, " ")
    .replace(/\b\w/g, (character) =>
      character.toUpperCase()
    );
}

function formatConfidence(value) {
  if (typeof value !== "number") {
    return "—";
  }

  const percent = value <= 1 ? value * 100 : value;

  return `${Math.round(percent)}%`;
}

function confidenceValue(value) {
  if (typeof value !== "number") {
    return 0;
  }

  const percent = value <= 1 ? value * 100 : value;

  return Math.max(0, Math.min(100, percent));
}

function formatFileSize(bytes) {
  if (
    typeof bytes !== "number" ||
    !Number.isFinite(bytes)
  ) {
    return "—";
  }

  if (bytes < 1024) {
    return `${bytes} B`;
  }

  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`;
  }

  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function getEvidenceTypeIcon(type) {
  const normalized = String(type || "")
    .toLowerCase()
    .trim();

  if (
    normalized.includes("image") ||
    normalized.includes("photo") ||
    normalized.includes("ocr")
  ) {
    return FileImage;
  }

  if (
    normalized.includes("csv") ||
    normalized.includes("spreadsheet") ||
    normalized.includes("excel")
  ) {
    return FileSpreadsheet;
  }

  if (
    normalized.includes("code") ||
    normalized.includes("json") ||
    normalized.includes("xml")
  ) {
    return FileCode2;
  }

  if (
    normalized.includes("archive") ||
    normalized.includes("zip")
  ) {
    return FileArchive;
  }

  if (normalized.includes("document")) {
    return FileText;
  }

  return FileText;
}

function getEvidenceTypeLabel(type) {
  const normalized = String(type || "")
    .toLowerCase()
    .trim();

  if (normalized.includes("ocr")) {
    return "OCR";
  }

  if (normalized.includes("image")) {
    return "IMAGE";
  }

  if (normalized.includes("pdf")) {
    return "PDF";
  }

  if (normalized.includes("csv")) {
    return "CSV";
  }

  if (normalized.includes("document")) {
    return "DOCUMENT";
  }

  if (normalized.includes("communication")) {
    return "COMMUNICATION";
  }

  if (normalized.includes("transaction")) {
    return "TRANSACTION";
  }

  return formatStatus(type);
}

function getEvidenceBadgeVariant(status) {
  const normalized = String(status || "")
    .toLowerCase()
    .trim();

  if (
    normalized.includes("received") ||
    normalized.includes("complete") ||
    normalized.includes("processed") ||
    normalized.includes("indexed") ||
    normalized.includes("ingested")
  ) {
    return "success";
  }

  if (
    normalized.includes("processing") ||
    normalized.includes("pending")
  ) {
    return "warning";
  }

  if (
    normalized.includes("failed") ||
    normalized.includes("error") ||
    normalized.includes("rejected")
  ) {
    return "danger";
  }

  return "default";
}

function getConfidenceVariant(value) {
  const score = confidenceValue(value);

  if (score >= 85) {
    return "high";
  }

  if (score >= 65) {
    return "medium";
  }

  return "low";
}

function getSourceLabel(item) {
  return (
    item?.sourceType ||
    item?.sourceReference ||
    item?.source ||
    "Unknown source"
  );
}

function getEvidenceDescription(item) {
  return (
    item?.description ||
    item?.extractedText ||
    item?.extracted_text ||
    "No description available for this evidence record."
  );
}

function getIngestionTotal(ingestion) {
  if (!ingestion) {
    return 0;
  }

  return [
    ingestion.entitiesCreated,
    ingestion.entitiesReused,
    ingestion.relationshipsCreated,
    ingestion.relationshipsReused,
    ingestion.graphNodesSynced,
    ingestion.graphRelationshipsSynced,
  ].reduce((total, value) => {
    return total + (Number(value) || 0);
  }, 0);
}

function StatMetric({
  icon: Icon,
  label,
  value,
  detail,
  accent = "cyan",
}) {
  return (
    <motion.div
      className={`tn-evidence-stat tn-evidence-stat-${accent}`}
      initial={{
        opacity: 0,
        y: 10,
      }}
      animate={{
        opacity: 1,
        y: 0,
      }}
      transition={{
        duration: 0.3,
        ease: EASE,
      }}
    >
      <div className="tn-evidence-stat-icon">
        <Icon size={17} />
      </div>

      <div className="tn-evidence-stat-content">
        <span>{label}</span>

        <strong>{value}</strong>

        {detail && <small>{detail}</small>}
      </div>
    </motion.div>
  );
}

function ConfidenceBar({ value }) {
  const percentage = confidenceValue(value);

  return (
    <div className="tn-confidence">
      <div className="tn-confidence-header">
        <span>Extraction confidence</span>

        <strong>
          {formatConfidence(value)}
        </strong>
      </div>

      <div className="tn-confidence-track">
        <motion.div
          className={`tn-confidence-fill tn-confidence-${getConfidenceVariant(
            value
          )}`}
          initial={{ width: 0 }}
          animate={{
            width: `${percentage}%`,
          }}
          transition={{
            duration: 0.7,
            ease: EASE,
          }}
        />
      </div>
    </div>
  );
}

function EvidenceCard({
  item,
  selected,
  onSelect,
  index,
}) {
  const Icon = getEvidenceTypeIcon(
    item?.evidenceType
  );

  const confidence =
    item?.extractionConfidence;

  return (
    <motion.button
      type="button"
      className={`tn-evidence-card ${
        selected ? "is-selected" : ""
      }`}
      onClick={onSelect}
      initial={{
        opacity: 0,
        y: 12,
      }}
      animate={{
        opacity: 1,
        y: 0,
      }}
      transition={{
        duration: 0.28,
        delay: Math.min(index * 0.04, 0.2),
        ease: EASE,
      }}
      whileHover={{
        y: -3,
      }}
      whileTap={{
        scale: 0.995,
      }}
    >
      <div className="tn-evidence-card-top">
        <div className="tn-evidence-file-icon">
          <Icon size={20} />
        </div>

        <div className="tn-evidence-card-heading">
          <div className="tn-evidence-card-number">
            {item?.evidenceNumber || "UNREGISTERED"}
          </div>

          <h3>
            {item?.title || "Untitled evidence"}
          </h3>
        </div>

        <div className="tn-evidence-card-chevron">
          <ChevronDown size={16} />
        </div>
      </div>

      <div className="tn-evidence-card-tags">
        <Badge
          variant="info"
          size="sm"
        >
          {getEvidenceTypeLabel(
            item?.evidenceType
          )}
        </Badge>

        <Badge
          variant={getEvidenceBadgeVariant(
            item?.status
          )}
          size="sm"
        >
          <span className="tn-status-dot" />
          {formatStatus(item?.status)}
        </Badge>
      </div>

      <p className="tn-evidence-card-description">
        {getEvidenceDescription(item)}
      </p>

      <ConfidenceBar value={confidence} />

      <div className="tn-evidence-card-footer">
        <span>
          <HardDrive size={13} />
          {formatFileSize(item?.fileSize)}
        </span>

        <span>
          <Database size={13} />
          {getSourceLabel(item)}
        </span>
      </div>
    </motion.button>
  );
}

function DetailMetric({
  icon: Icon,
  label,
  value,
}) {
  return (
    <div className="tn-detail-metric">
      <div className="tn-detail-metric-icon">
        <Icon size={15} />
      </div>

      <div>
        <span>{label}</span>
        <strong>{value}</strong>
      </div>
    </div>
  );
}

function IngestionMetric({
  icon: Icon = CheckCircle2,
  label,
  value,
}) {
  return (
    <div className="tn-ingestion-metric">
      <div className="tn-ingestion-icon">
        <Icon size={15} />
      </div>

      <div>
        <span>{label}</span>
        <strong>
          {typeof value === "number"
            ? value
            : value ?? "—"}
        </strong>
      </div>
    </div>
  );
}

function UploadField({
  label,
  children,
  wide = false,
}) {
  return (
    <label
      className={`tn-upload-field ${
        wide ? "tn-upload-field-wide" : ""
      }`}
    >
      <span>{label}</span>
      {children}
    </label>
  );
}

export default function Evidence() {
  const [caseId, setCaseId] = useState(getActiveCaseId());

  useEffect(() => {
    const syncActiveCase = () => setCaseId(getActiveCaseId());
    window.addEventListener("trinetra:active-case-changed", syncActiveCase);
    const timer = window.setInterval(syncActiveCase, 1000);
    return () => {
      window.removeEventListener("trinetra:active-case-changed", syncActiveCase);
      window.clearInterval(timer);
    };
  }, []);

  const {
    evidence,
    selectedEvidence,
    extraction,
    ingestion,

    loading,
    uploading,
    uploadProgress,
    error,

    upload,
    search,
    selectEvidence,
    clearSelection,
  } = useEvidence(caseId);

  const fileInputRef = useRef(null);

  const [searchQuery, setSearchQuery] =
    useState("");

  const [showUpload, setShowUpload] =
    useState(false);

  const [uploadForm, setUploadForm] =
    useState({
      evidenceNumber: "",
      title: "",
      evidenceType: "document",
      description: "",
      sourceType: "",
      sourceReference: "",
      file: null,
    });

  const [uploadError, setUploadError] =
    useState(null);

  const [searching, setSearching] =
    useState(false);

  const displayedEvidence = useMemo(
    () => evidence || [],
    [evidence]
  );

  const metrics = useMemo(() => {
    const records = displayedEvidence;

    const documents = records.filter((item) => {
      const type = String(
        item?.evidenceType || ""
      ).toLowerCase();

      return (
        type.includes("document") ||
        type.includes("pdf")
      );
    }).length;

    const images = records.filter((item) => {
      const type = String(
        item?.evidenceType || ""
      ).toLowerCase();

      return (
        type.includes("image") ||
        type.includes("ocr")
      );
    }).length;

    const communications = records.filter(
      (item) => {
        const text = [
          item?.evidenceType,
          item?.title,
        ]
          .filter(Boolean)
          .join(" ")
          .toLowerCase();

        return (
          text.includes("communication") ||
          text.includes("cdr") ||
          text.includes("call")
        );
      }
    ).length;

    const processed = records.filter(
      (item) => {
        const status = String(
          item?.status || ""
        ).toLowerCase();

        return (
          status.includes("received") ||
          status.includes("processed") ||
          status.includes("indexed") ||
          status.includes("ingested") ||
          status.includes("complete")
        );
      }
    ).length;

    return {
      total: records.length,
      documents,
      images,
      communications,
      processed,
    };
  }, [displayedEvidence]);

  const handleSearch = async (event) => {
    event.preventDefault();

    const query = searchQuery.trim();

    if (!query) {
      return;
    }

    setSearching(true);

    try {
      await search(query);
    } catch {
      // Hook stores the API error.
    } finally {
      setSearching(false);
    }
  };

  const clearSearch = async () => {
    setSearchQuery("");

    /*
     * Reload the normal evidence list when the
     * search field is cleared.
     *
     * The hook's search function is intentionally
     * not called with an empty query because the
     * backend treats empty search as invalid.
     *
     * The evidence list is already maintained by
     * useEvidence, so clearing the UI field keeps
     * the currently loaded records visible.
     */
  };

  const handleFileChange = (event) => {
    const file =
      event.target.files?.[0] || null;

    setUploadForm((current) => ({
      ...current,
      file,
    }));

    setUploadError(null);
  };

  const handleUpload = async (event) => {
    event.preventDefault();

    setUploadError(null);

    if (!uploadForm.evidenceNumber.trim()) {
      setUploadError(
        "Evidence number is required."
      );
      return;
    }

    if (!uploadForm.title.trim()) {
      setUploadError(
        "Evidence title is required."
      );
      return;
    }

    if (!uploadForm.file) {
      setUploadError(
        "Please select an evidence file."
      );
      return;
    }

    try {
      await upload({
        evidenceNumber:
          uploadForm.evidenceNumber.trim(),

        title:
          uploadForm.title.trim(),

        evidenceType:
          uploadForm.evidenceType,

        description:
          uploadForm.description.trim(),

        sourceType:
          uploadForm.sourceType.trim(),

        sourceReference:
          uploadForm.sourceReference.trim(),

        file: uploadForm.file,
      });

      setUploadForm({
        evidenceNumber: "",
        title: "",
        evidenceType: "document",
        description: "",
        sourceType: "",
        sourceReference: "",
        file: null,
      });

      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }

      setShowUpload(false);
    } catch (err) {
      setUploadError(
        err?.response?.data?.detail ||
          err?.message ||
          "Evidence upload failed."
      );
    }
  };

  const closeDetails = () => {
    clearSelection();
  };

  return (
    <div className="tn-page tn-evidence-page">
      {/* =====================================================
          HEADER
      ====================================================== */}

      <motion.div
        className="tn-page-header tn-evidence-header"
        initial={{
          opacity: 0,
          y: -8,
        }}
        animate={{
          opacity: 1,
          y: 0,
        }}
        transition={{
          duration: 0.35,
          ease: EASE,
        }}
      >
        <div>
          <div className="tn-eyebrow">
            TRINETRA / EVIDENCE INTELLIGENCE
          </div>

          <div className="tn-title-row">
            <div className="tn-title-orb">
              <Fingerprint size={22} />
            </div>

            <div>
              <h1 className="tn-page-title">
                Evidence
              </h1>

              <p className="tn-page-subtitle">
                Review source material, extraction
                results, provenance, and graph
                ingestion activity.
              </p>
            </div>
          </div>
        </div>

        <div className="tn-evidence-header-actions">
          <div className="tn-live-indicator">
            <span />
            LIVE REGISTRY
          </div>

          <button
            type="button"
            className="tn-glow-button"
            onClick={() =>
              setShowUpload((current) => !current)
            }
            disabled={uploading}
          >
            <Upload size={17} />

            {showUpload
              ? "Close Upload"
              : "Upload Evidence"}
          </button>
        </div>
      </motion.div>

      {/* =====================================================
          API ERROR
      ====================================================== */}

      <AnimatePresence>
        {error && (
          <motion.div
            initial={{
              opacity: 0,
              height: 0,
              y: -5,
            }}
            animate={{
              opacity: 1,
              height: "auto",
              y: 0,
            }}
            exit={{
              opacity: 0,
              height: 0,
              y: -5,
            }}
          >
            <GlassCard className="tn-api-warning">
              <XCircle size={18} />

              <div>
                <strong>
                  Evidence service error
                </strong>

                <span>{error}</span>
              </div>
            </GlassCard>
          </motion.div>
        )}
      </AnimatePresence>

      {/* =====================================================
          SUMMARY METRICS
      ====================================================== */}

      <div className="tn-evidence-stat-grid">
        <StatMetric
          icon={Archive}
          label="Evidence records"
          value={metrics.total}
          detail="Registered sources"
          accent="cyan"
        />

        <StatMetric
          icon={FileText}
          label="Documents"
          value={metrics.documents}
          detail="Documentary sources"
          accent="blue"
        />

        <StatMetric
          icon={FileImage}
          label="Visual / OCR"
          value={metrics.images}
          detail="Images and OCR sources"
          accent="violet"
        />

        <StatMetric
          icon={ShieldCheck}
          label="Processed"
          value={metrics.processed}
          detail={
            metrics.total
              ? `${Math.round(
                  (metrics.processed /
                    metrics.total) *
                    100
                )}% processed`
              : "Awaiting sources"
          }
          accent="success"
        />
      </div>

      {/* =====================================================
          UPLOAD WORKSPACE
      ====================================================== */}

      <AnimatePresence initial={false}>
        {showUpload && (
          <motion.div
            initial={{
              opacity: 0,
              height: 0,
              overflow: "hidden",
            }}
            animate={{
              opacity: 1,
              height: "auto",
            }}
            exit={{
              opacity: 0,
              height: 0,
              overflow: "hidden",
            }}
            transition={{
              duration: 0.38,
              ease: EASE,
            }}
          >
            <GlassCard className="tn-upload-card tn-evidence-upload-workspace">
              <div className="tn-upload-heading">
                <div className="tn-upload-heading-icon">
                  <Sparkles size={18} />
                </div>

                <div>
                  <div className="tn-section-kicker">
                    INGEST NEW SOURCE
                  </div>

                  <h2>
                    Evidence Upload
                  </h2>

                  <p>
                    Add a source to the investigation.
                    TRINETRA will extract content,
                    resolve entities, identify
                    relationships, and synchronize
                    the graph.
                  </p>
                </div>
              </div>

              <form
                className="tn-evidence-upload-form"
                onSubmit={handleUpload}
              >
                <div className="tn-form-grid">
                  <UploadField label="Evidence number">
                    <input
                      value={
                        uploadForm.evidenceNumber
                      }
                      onChange={(event) =>
                        setUploadForm(
                          (current) => ({
                            ...current,
                            evidenceNumber:
                              event.target.value,
                          })
                        )
                      }
                      placeholder="TRI-OCR-005"
                      disabled={uploading}
                    />
                  </UploadField>

                  <UploadField label="Evidence title">
                    <input
                      value={uploadForm.title}
                      onChange={(event) =>
                        setUploadForm(
                          (current) => ({
                            ...current,
                            title:
                              event.target.value,
                          })
                        )
                      }
                      placeholder="Evidence title"
                      disabled={uploading}
                    />
                  </UploadField>

                  <UploadField label="Evidence type">
                    <div className="tn-select-wrap">
                      <select
                        value={
                          uploadForm.evidenceType
                        }
                        onChange={(event) =>
                          setUploadForm(
                            (current) => ({
                              ...current,
                              evidenceType:
                                event.target.value,
                            })
                          )
                        }
                        disabled={uploading}
                      >
                        <option value="document">
                          Document
                        </option>

                        <option value="image">
                          Image / OCR
                        </option>

                        <option value="pdf">
                          PDF
                        </option>

                        <option value="csv">
                          CSV
                        </option>

                        <option value="other">
                          Other
                        </option>
                      </select>

                      <ChevronDown size={15} />
                    </div>
                  </UploadField>

                  <UploadField label="Source type">
                    <input
                      value={
                        uploadForm.sourceType
                      }
                      onChange={(event) =>
                        setUploadForm(
                          (current) => ({
                            ...current,
                            sourceType:
                              event.target.value,
                          })
                        )
                      }
                      placeholder="Manual / OCR / CDR"
                      disabled={uploading}
                    />
                  </UploadField>

                  <UploadField
                    label="Source reference"
                    wide
                  >
                    <input
                      value={
                        uploadForm.sourceReference
                      }
                      onChange={(event) =>
                        setUploadForm(
                          (current) => ({
                            ...current,
                            sourceReference:
                              event.target.value,
                          })
                        )
                      }
                      placeholder="Optional source reference"
                      disabled={uploading}
                    />
                  </UploadField>

                  <UploadField
                    label="Description"
                    wide
                  >
                    <textarea
                      value={
                        uploadForm.description
                      }
                      onChange={(event) =>
                        setUploadForm(
                          (current) => ({
                            ...current,
                            description:
                              event.target.value,
                          })
                        )
                      }
                      placeholder="Describe the evidence..."
                      rows={3}
                      disabled={uploading}
                    />
                  </UploadField>
                </div>

                {/* FILE DROP */}
                <label className="tn-evidence-file-drop">
                  <div className="tn-file-drop-icon">
                    {uploadForm.file ? (
                      <CheckCircle2 size={22} />
                    ) : (
                      <Upload size={22} />
                    )}
                  </div>

                  <div className="tn-file-drop-content">
                    <strong>
                      {uploadForm.file
                        ? uploadForm.file.name
                        : "Select an evidence file"}
                    </strong>

                    <span>
                      PDF, DOCX, CSV, image or
                      supported evidence source
                    </span>

                    {uploadForm.file && (
                      <small>
                        {formatFileSize(
                          uploadForm.file.size
                        )}
                      </small>
                    )}
                  </div>

                  <span className="tn-file-drop-action">
                    Browse
                  </span>

                  <input
                    ref={fileInputRef}
                    type="file"
                    onChange={handleFileChange}
                    disabled={uploading}
                  />
                </label>

                {/* FORM ERROR */}
                <AnimatePresence>
                  {uploadError && (
                    <motion.div
                      className="tn-form-error"
                      initial={{
                        opacity: 0,
                        y: -4,
                      }}
                      animate={{
                        opacity: 1,
                        y: 0,
                      }}
                    >
                      <XCircle size={16} />
                      {uploadError}
                    </motion.div>
                  )}
                </AnimatePresence>

                {/* PROCESSING */}
                <AnimatePresence>
                  {uploading && (
                    <motion.div
                      className="tn-processing-box"
                      initial={{
                        opacity: 0,
                        y: 8,
                      }}
                      animate={{
                        opacity: 1,
                        y: 0,
                      }}
                    >
                      <div className="tn-processing-header">
                        <div>
                          <span>
                            PROCESSING SOURCE
                          </span>

                          <strong>
                            Evidence intelligence
                            pipeline
                          </strong>
                        </div>

                        <strong>
                          {uploadProgress}%
                        </strong>
                      </div>

                      <div className="tn-progress-track">
                        <motion.div
                          initial={{
                            width: 0,
                          }}
                          animate={{
                            width: `${uploadProgress}%`,
                          }}
                          transition={{
                            duration: 0.3,
                            ease: "easeOut",
                          }}
                        />
                      </div>

                      <div className="tn-processing-steps">
                        <span
                          className={
                            uploadProgress >= 1
                              ? "is-active"
                              : ""
                          }
                        >
                          <CircleDot size={12} />
                          Upload
                        </span>

                        <span
                          className={
                            uploadProgress >= 25
                              ? "is-active"
                              : ""
                          }
                        >
                          <CircleDot size={12} />
                          Extraction
                        </span>

                        <span
                          className={
                            uploadProgress >= 50
                              ? "is-active"
                              : ""
                          }
                        >
                          <CircleDot size={12} />
                          Entity resolution
                        </span>

                        <span
                          className={
                            uploadProgress >= 75
                              ? "is-active"
                              : ""
                          }
                        >
                          <CircleDot size={12} />
                          Graph ingestion
                        </span>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>

                <div className="tn-form-actions">
                  <button
                    type="button"
                    className="tn-secondary-button"
                    onClick={() =>
                      setShowUpload(false)
                    }
                    disabled={uploading}
                  >
                    Cancel
                  </button>

                  <button
                    type="submit"
                    className="tn-glow-button"
                    disabled={uploading}
                  >
                    {uploading ? (
                      <>
                        <Loader2
                          size={17}
                          className="tn-spin"
                        />

                        Processing...
                      </>
                    ) : (
                      <>
                        <Upload size={17} />
                        Upload & Ingest
                      </>
                    )}
                  </button>
                </div>
              </form>
            </GlassCard>
          </motion.div>
        )}
      </AnimatePresence>

      {/* =====================================================
          SEARCH / FILTER BAR
      ====================================================== */}

      <GlassCard className="tn-evidence-toolbar">
        <form
          className="tn-evidence-search"
          onSubmit={handleSearch}
        >
          <Search size={17} />

          <input
            value={searchQuery}
            onChange={(event) =>
              setSearchQuery(event.target.value)
            }
            placeholder="Search evidence, sources, references..."
          />

          {searchQuery && (
            <button
              type="button"
              className="tn-search-clear"
              onClick={clearSearch}
              aria-label="Clear search"
            >
              <X size={14} />
            </button>
          )}

          <button
            type="submit"
            disabled={
              searching ||
              !searchQuery.trim()
            }
          >
            {searching ? (
              <Loader2
                size={16}
                className="tn-spin"
              />
            ) : (
              "Search"
            )}
          </button>
        </form>

        <div className="tn-evidence-toolbar-meta">
          <div className="tn-registry-status">
            <span />
            Registry synchronized
          </div>

          <Badge
            variant="info"
            size="sm"
          >
            {displayedEvidence.length} RECORDS
          </Badge>
        </div>
      </GlassCard>

      {/* =====================================================
          MAIN EVIDENCE WORKSPACE
      ====================================================== */}

      <div className="tn-evidence-workspace">
        {/* RECORDS */}
        <GlassCard className="tn-evidence-records-panel">
          <div className="tn-section-header tn-evidence-section-header">
            <div>
              <div className="tn-section-kicker">
                SOURCE REGISTRY
              </div>

              <h2>
                Evidence Records
              </h2>

              <p>
                Select a source to inspect its
                intelligence and provenance.
              </p>
            </div>

            <div className="tn-records-summary">
              <span>
                {metrics.total}
              </span>
              <small>
                active sources
              </small>
            </div>
          </div>

          <div className="tn-evidence-list">
            {loading &&
            displayedEvidence.length === 0 ? (
              <div className="tn-evidence-loading">
                <div className="tn-loading-orb">
                  <Loader2
                    size={22}
                    className="tn-spin"
                  />
                </div>

                <div>
                  <strong>
                    Loading evidence registry
                  </strong>

                  <span>
                    Synchronizing investigation
                    sources...
                  </span>
                </div>
              </div>
            ) : displayedEvidence.length ===
              0 ? (
              <div className="tn-evidence-empty">
                <div className="tn-empty-icon">
                  <FileText size={24} />
                </div>

                <h3>
                  No evidence records
                </h3>

                <p>
                  Upload a source or change your
                  search query to populate the
                  registry.
                </p>

                <button
                  type="button"
                  className="tn-secondary-button"
                  onClick={() =>
                    setShowUpload(true)
                  }
                >
                  <Upload size={15} />
                  Add evidence
                </button>
              </div>
            ) : (
              <AnimatePresence mode="popLayout">
                {displayedEvidence.map(
                  (item, index) => (
                    <EvidenceCard
                      key={
                        item?.id ||
                        item?.evidenceNumber ||
                        `evidence-${index}`
                      }
                      item={item}
                      index={index}
                      selected={
                        selectedEvidence?.id ===
                        item?.id
                      }
                      onSelect={() =>
                        selectEvidence(item)
                      }
                    />
                  )
                )}
              </AnimatePresence>
            )}
          </div>
        </GlassCard>

        {/* ===================================================
            DETAIL PANEL
        ==================================================== */}

        <GlassCard className="tn-evidence-detail-card">
          {!selectedEvidence ? (
            <div className="tn-detail-empty">
              <motion.div
                className="tn-detail-empty-icon"
                animate={{
                  y: [0, -4, 0],
                }}
                transition={{
                  duration: 3,
                  repeat: Infinity,
                  ease: "easeInOut",
                }}
              >
                <Fingerprint size={30} />
              </motion.div>

              <div className="tn-section-kicker">
                EVIDENCE INSPECTOR
              </div>

              <h3>
                Select an evidence record
              </h3>

              <p>
                Choose a source from the registry
                to inspect its metadata, extraction
                results, provenance, and graph
                ingestion.
              </p>

              <div className="tn-detail-empty-hint">
                <Info size={14} />
                Evidence details appear here
                without leaving the workspace.
              </div>
            </div>
          ) : (
            <AnimatePresence mode="wait">
              <motion.div
                key={
                  selectedEvidence?.id ||
                  selectedEvidence?.evidenceNumber
                }
                className="tn-evidence-detail-inner"
                initial={{
                  opacity: 0,
                  x: 8,
                }}
                animate={{
                  opacity: 1,
                  x: 0,
                }}
                transition={{
                  duration: 0.3,
                  ease: EASE,
                }}
              >
                {/* DETAIL HEADER */}
                <div className="tn-detail-header">
                  <div className="tn-detail-title-wrap">
                    <div className="tn-detail-file-icon">
                      {(() => {
                        const Icon =
                          getEvidenceTypeIcon(
                            selectedEvidence?.evidenceType
                          );

                        return <Icon size={21} />;
                      })()}
                    </div>

                    <div>
                      <div className="tn-section-kicker">
                        EVIDENCE DETAIL
                      </div>

                      <h2>
                        {selectedEvidence.title ||
                          "Untitled evidence"}
                      </h2>

                      <span className="tn-detail-id">
                        {selectedEvidence.evidenceNumber ||
                          "UNREGISTERED"}
                      </span>
                    </div>
                  </div>

                  <button
                    type="button"
                    className="tn-icon-button"
                    onClick={closeDetails}
                    title="Close evidence"
                    aria-label="Close evidence"
                  >
                    <X size={17} />
                  </button>
                </div>

                {/* STATUS */}
                <div className="tn-detail-status-row">
                  <Badge
                    variant={getEvidenceBadgeVariant(
                      selectedEvidence?.status
                    )}
                  >
                    <span className="tn-status-dot" />
                    {formatStatus(
                      selectedEvidence?.status
                    )}
                  </Badge>

                  <Badge
                    variant="info"
                  >
                    {getEvidenceTypeLabel(
                      selectedEvidence?.evidenceType
                    )}
                  </Badge>

                  {selectedEvidence?.sourceType && (
                    <span className="tn-source-chip">
                      <Database size={13} />
                      {formatLabel(
                        selectedEvidence.sourceType
                      )}
                    </span>
                  )}
                </div>

                {/* METADATA */}
                <section className="tn-detail-section">
                  <div className="tn-detail-section-heading">
                    <div>
                      <div className="tn-section-kicker">
                        SOURCE METADATA
                      </div>

                      <h3>
                        Registry information
                      </h3>
                    </div>
                  </div>

                  <div className="tn-detail-metrics">
                    <DetailMetric
                      icon={FileText}
                      label="Type"
                      value={getEvidenceTypeLabel(
                        selectedEvidence?.evidenceType
                      )}
                    />

                    <DetailMetric
                      icon={ShieldCheck}
                      label="Confidence"
                      value={formatConfidence(
                        selectedEvidence?.extractionConfidence
                      )}
                    />

                    <DetailMetric
                      icon={HardDrive}
                      label="File size"
                      value={formatFileSize(
                        selectedEvidence?.fileSize
                      )}
                    />

                    <DetailMetric
                      icon={Database}
                      label="Source"
                      value={getSourceLabel(
                        selectedEvidence
                      )}
                    />
                  </div>

                  <div className="tn-detail-file-path">
                    <span>
                      File
                    </span>

                    <strong>
                      {selectedEvidence?.fileName ||
                        "No filename recorded"}
                    </strong>
                  </div>

                  {selectedEvidence?.sourceReference && (
                    <div className="tn-detail-file-path">
                      <span>
                        Reference
                      </span>

                      <strong>
                        {
                          selectedEvidence.sourceReference
                        }
                      </strong>
                    </div>
                  )}
                </section>

                {/* DESCRIPTION */}
                {selectedEvidence?.description && (
                  <section className="tn-detail-section">
                    <div className="tn-detail-section-heading">
                      <div>
                        <div className="tn-section-kicker">
                          DESCRIPTION
                        </div>

                        <h3>
                          Source context
                        </h3>
                      </div>
                    </div>

                    <div className="tn-detail-description">
                      {
                        selectedEvidence.description
                      }
                    </div>
                  </section>
                )}

                {/* EXTRACTION */}
                <section className="tn-detail-section">
                  <div className="tn-detail-section-heading">
                    <div>
                      <div className="tn-section-kicker">
                        EXTRACTION
                      </div>

                      <h3>
                        Extracted intelligence
                      </h3>
                    </div>

                    {extraction && (
                      <Badge
                        variant="violet"
                        size="sm"
                      >
                        {formatLabel(
                          extraction.extractionMethod
                        )}
                      </Badge>
                    )}
                  </div>

                  {extraction ? (
                    <>
                      <div className="tn-extraction-confidence">
                        <div>
                          <span>
                            Extraction confidence
                          </span>

                          <strong>
                            {formatConfidence(
                              extraction.extractionConfidence
                            )}
                          </strong>
                        </div>

                        <div className="tn-confidence-track">
                          <motion.div
                            className={`tn-confidence-fill tn-confidence-${getConfidenceVariant(
                              extraction.extractionConfidence
                            )}`}
                            initial={{
                              width: 0,
                            }}
                            animate={{
                              width: `${confidenceValue(
                                extraction.extractionConfidence
                              )}%`,
                            }}
                            transition={{
                              duration: 0.65,
                              ease: EASE,
                            }}
                          />
                        </div>
                      </div>

                      <div className="tn-extraction-result">
                        <div className="tn-extraction-label">
                          <Sparkles size={14} />
                          Extracted text
                        </div>

                        <div className="tn-extraction-text">
                          {extraction.extractedText ||
                            "No extracted text returned."}
                        </div>
                      </div>
                    </>
                  ) : (
                    <div className="tn-detail-muted">
                      <Info size={15} />
                      Extraction details are not
                      available for this record.
                    </div>
                  )}
                </section>

                {/* EXTRACTED ENTITIES */}
                {((ingestion?.extractedEntities?.length ?? 0) > 0 ||
                  (selectedEvidence?.extractedEntities?.length ?? 0) > 0) && (
                  <section className="tn-detail-section">
                    <div className="tn-detail-section-heading">
                      <div>
                        <div className="tn-section-kicker">ENTITIES</div>
                        <h3>Extracted entities</h3>
                      </div>
                      <Badge variant="info" size="sm">
                        {(ingestion?.extractedEntities?.length ??
                          selectedEvidence?.extractedEntities?.length ??
                          0)}{" "}
                        detected
                      </Badge>
                    </div>

                    <div className="tn-extracted-entities">
                      {(ingestion?.extractedEntities?.length
                        ? ingestion.extractedEntities
                        : selectedEvidence.extractedEntities
                      ).map((entity, index) => (
                        <div
                          className="tn-extracted-entity"
                          key={
                            entity.entity_id ??
                            entity.entityId ??
                            `${entity.entity_type}-${entity.name}-${index}`
                          }
                        >
                          <span className="tn-extracted-entity-type">
                            {formatLabel(
                              entity.entity_type ??
                                entity.entityType ??
                                entity.type ??
                                "entity"
                            )}
                          </span>
                          <strong>
                            {entity.name ??
                              entity.value ??
                              entity.entity_name ??
                              "Unknown entity"}
                          </strong>
                          {(entity.confidence !== undefined &&
                            entity.confidence !== null) && (
                            <span className="tn-extracted-entity-confidence">
                              {formatConfidence(entity.confidence)}
                            </span>
                          )}
                        </div>
                      ))}
                    </div>
                  </section>
                )}

                {/* EXTRACTED RELATIONSHIPS */}
                {((ingestion?.extractedRelationships?.length ?? 0) > 0 ||
                  (selectedEvidence?.extractedRelationships?.length ?? 0) > 0) && (
                  <section className="tn-detail-section">
                    <div className="tn-detail-section-heading">
                      <div>
                        <div className="tn-section-kicker">RELATIONSHIPS</div>
                        <h3>Extracted relationships</h3>
                      </div>
                    </div>

                    <div className="tn-extracted-relationships">
                      {(ingestion?.extractedRelationships?.length
                        ? ingestion.extractedRelationships
                        : selectedEvidence.extractedRelationships
                      ).map((relationship, index) => (
                        <div
                          className="tn-extracted-relationship"
                          key={
                            relationship.relationship_id ??
                            relationship.relationshipId ??
                            `relationship-${index}`
                          }
                        >
                          <div>
                            <strong>
                              {relationship.source_entity_name ??
                                relationship.sourceEntityName ??
                                "Unknown source"}
                            </strong>
                            <span>
                              {formatLabel(
                                relationship.relationship_type ??
                                  relationship.relationshipType ??
                                  relationship.type ??
                                  "related"
                              )}
                            </span>
                            <strong>
                              {relationship.target_entity_name ??
                                relationship.targetEntityName ??
                                "Unknown target"}
                            </strong>
                          </div>
                          {relationship.confidence !== undefined &&
                            relationship.confidence !== null && (
                              <Badge variant="success" size="sm">
                                {formatConfidence(relationship.confidence)}
                              </Badge>
                            )}
                        </div>
                      ))}
                    </div>
                  </section>
                )}

                {/* INGESTION */}
                {ingestion && (
                  <section className="tn-detail-section">
                    <div className="tn-detail-section-heading">
                      <div>
                        <div className="tn-section-kicker">
                          GRAPH INGESTION
                        </div>

                        <h3>
                          Intelligence synchronization
                        </h3>
                      </div>

                      <div className="tn-ingestion-total">
                        <Network size={14} />

                        <strong>
                          {getIngestionTotal(
                            ingestion
                          )}
                        </strong>

                        <span>
                          operations
                        </span>
                      </div>
                    </div>

                    <div className="tn-ingestion-grid">
                      <IngestionMetric
                        label="Entities created"
                        value={
                          ingestion.entitiesCreated
                        }
                      />

                      <IngestionMetric
                        label="Entities reused"
                        value={
                          ingestion.entitiesReused
                        }
                      />

                      <IngestionMetric
                        label="Relationships created"
                        value={
                          ingestion.relationshipsCreated
                        }
                      />

                      <IngestionMetric
                        label="Relationships reused"
                        value={
                          ingestion.relationshipsReused
                        }
                      />

                      <IngestionMetric
                        icon={Network}
                        label="Graph nodes synced"
                        value={
                          ingestion.graphNodesSynced
                        }
                      />

                      <IngestionMetric
                        icon={Network}
                        label="Graph relationships"
                        value={
                          ingestion.graphRelationshipsSynced
                        }
                      />
                    </div>
                  </section>
                )}

                {/* FOOTER */}
                <div className="tn-detail-footer">
                  <div>
                    <ShieldCheck size={15} />

                    <span>
                      Evidence remains grounded to
                      the underlying source record.
                    </span>
                  </div>
                </div>
              </motion.div>
            </AnimatePresence>
          )}
        </GlassCard>
      </div>
    </div>
  );
}
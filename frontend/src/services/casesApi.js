import api from "./api";

export async function listCases({ skip = 0, limit = 100 } = {}) {
  const response = await api.get("/cases", {
    params: { skip, limit },
  });

  return response.data;
}

export async function createCase({
  caseNumber,
  title,
  description = "",
} = {}) {
  const response = await api.post("/cases", {
    case_number: caseNumber,
    title,
    description,
  });

  return response.data;
}

export async function uploadCaseEvidence({
  caseId,
  evidenceNumber,
  title,
  evidenceType = "document",
  description = "",
  sourceReference = "",
  file,
} = {}) {
  if (!caseId) {
    throw new Error("A case must be selected before uploading evidence.");
  }

  if (!evidenceNumber?.trim()) {
    throw new Error("Evidence number is required.");
  }

  if (!title?.trim()) {
    throw new Error("Evidence title is required.");
  }

  if (!(file instanceof File)) {
    throw new Error("Please select an evidence file.");
  }

  const form = new FormData();

  form.append("case_id", String(caseId));
  form.append("evidence_number", evidenceNumber.trim());
  form.append("title", title.trim());
  form.append("evidence_type", evidenceType || "document");
  form.append("description", description?.trim() || "");
  form.append("source_type", "manual");
  form.append("source_reference", sourceReference?.trim() || "");
  form.append("file", file, file.name);

  const response = await api.post("/evidence/upload", form, {
    transformRequest: [
      (data, headers) => {
        if (data instanceof FormData) {
          // Let the browser/Axios generate:
          // multipart/form-data; boundary=...
          delete headers["Content-Type"];
          delete headers["content-type"];
        }

        return data;
      },
    ],
  });

  return response.data;
}
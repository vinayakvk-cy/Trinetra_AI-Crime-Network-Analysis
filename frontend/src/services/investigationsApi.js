import api from "./api";

export async function listInvestigations({ skip = 0, limit = 100 } = {}) {
  const response = await api.get("/investigations", { params: { skip, limit } });
  return response.data;
}

export async function getInvestigation(investigationId) {
  const response = await api.get(`/investigations/${investigationId}`);
  return response.data;
}

export async function createInvestigation(data = {}) {
  const response = await api.post("/investigations", {
    case_id: Number(data.caseId),
    investigation_number: data.investigationNumber.trim(),
    title: data.title.trim(),
    objective: (data.objective || "").trim(),
    investigator: (data.investigator || "").trim(),
    investigation_unit: (data.investigationUnit || "").trim(),
    status: data.status || "in_progress",
    outcome: data.outcome || "undetermined",
  });
  return response.data;
}

export async function updateInvestigation(investigationId, data = {}) {
  const payload = {};
  if (data.caseId !== undefined && data.caseId !== "") payload.case_id = Number(data.caseId);
  if (data.investigationNumber !== undefined) payload.investigation_number = data.investigationNumber.trim();
  if (data.title !== undefined) payload.title = data.title.trim();
  if (data.objective !== undefined) payload.objective = data.objective.trim();
  if (data.investigator !== undefined) payload.investigator = data.investigator.trim();
  if (data.investigationUnit !== undefined) payload.investigation_unit = data.investigationUnit.trim();
  if (data.status !== undefined) payload.status = data.status;
  if (data.outcome !== undefined) payload.outcome = data.outcome;

  const response = await api.patch(`/investigations/${investigationId}`, payload);
  return response.data;
}

export async function deleteInvestigation(investigationId) {
  const response = await api.delete(`/investigations/${investigationId}`);
  return response.data;
}

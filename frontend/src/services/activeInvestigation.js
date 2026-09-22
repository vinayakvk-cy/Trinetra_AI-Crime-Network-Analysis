const ACTIVE_INVESTIGATION_KEY = "trinetra.activeInvestigationId";

export function getActiveInvestigationId() {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(ACTIVE_INVESTIGATION_KEY);
  if (!raw) return null;
  const id = Number(raw);
  return Number.isInteger(id) && id > 0 ? id : null;
}

export function setActiveInvestigationId(id) {
  if (typeof window === "undefined") return null;
  const numericId = Number(id);
  if (!Number.isInteger(numericId) || numericId < 1) {
    window.localStorage.removeItem(ACTIVE_INVESTIGATION_KEY);
    window.dispatchEvent(new Event("trinetra:active-investigation-changed"));
    return null;
  }
  window.localStorage.setItem(ACTIVE_INVESTIGATION_KEY, String(numericId));
  window.dispatchEvent(new Event("trinetra:active-investigation-changed"));
  return numericId;
}

export function clearActiveInvestigationId() {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(ACTIVE_INVESTIGATION_KEY);
  window.dispatchEvent(new Event("trinetra:active-investigation-changed"));
}

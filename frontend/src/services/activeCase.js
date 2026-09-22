const ACTIVE_CASE_KEY = "trinetra.activeCaseId";

export function getActiveCaseId() {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(ACTIVE_CASE_KEY);
  if (!raw) return null;
  const id = Number(raw);
  return Number.isInteger(id) && id > 0 ? id : null;
}

export function setActiveCaseId(id) {
  if (typeof window === "undefined") return null;
  const numericId = Number(id);
  if (!Number.isInteger(numericId) || numericId < 1) {
    window.localStorage.removeItem(ACTIVE_CASE_KEY);
    window.dispatchEvent(new Event("trinetra:active-case-changed"));
    return null;
  }
  window.localStorage.setItem(ACTIVE_CASE_KEY, String(numericId));
  window.dispatchEvent(new Event("trinetra:active-case-changed"));
  return numericId;
}

export function clearActiveCaseId() {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(ACTIVE_CASE_KEY);
  window.dispatchEvent(new Event("trinetra:active-case-changed"));
}

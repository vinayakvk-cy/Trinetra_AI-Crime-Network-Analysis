import axios from "axios";

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 30000,
});

// Add useful logging while developing.
api.interceptors.request.use(
  (config) => {
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

api.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    const message =
      error?.response?.data?.detail ||
      error?.response?.data?.message ||
      error?.message ||
      "API request failed";

    console.error("TRINETRA API Error:", {
      url: error?.config?.url,
      method: error?.config?.method,
      status: error?.response?.status,
      message,
    });

    return Promise.reject(error);
  }
);


export function getApiErrorMessage(error, fallback = "API request failed") {
  const detail = error?.response?.data?.detail;
  const message = error?.response?.data?.message;

  const format = (value) => {
    if (typeof value === "string") return value;
    if (Array.isArray(value)) {
      return value
        .map((item) => {
          if (typeof item === "string") return item;
          if (item?.msg) return item.msg;
          if (item?.message) return item.message;
          if (item?.loc) return `${item.loc.join(".")}: ${item.msg || "Invalid value"}`;
          return JSON.stringify(item);
        })
        .join(" • ");
    }
    if (value && typeof value === "object") {
      if (value.message) return String(value.message);
      if (value.msg) return String(value.msg);
      try { return JSON.stringify(value); } catch { return fallback; }
    }
    return "";
  };

  return format(detail) || format(message) || error?.message || fallback;
}

export default api;
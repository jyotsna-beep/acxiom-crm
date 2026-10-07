import axios from "axios";

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000",
  withCredentials: true,
});

function readCookie(name) {
  const prefix = `${name}=`;
  return document.cookie.split("; ").find((cookie) => cookie.startsWith(prefix))?.slice(prefix.length);
}

apiClient.interceptors.request.use((config) => {
  if (["post", "put", "patch", "delete"].includes(config.method?.toLowerCase())) {
    const csrfToken = readCookie("acxiomcrm_csrf");
    if (csrfToken) {
      config.headers["X-CSRF-Token"] = csrfToken;
    }
  }
  return config;
});

export async function establishPublicCsrfToken() {
  await apiClient.get("/api/auth/csrf");
}

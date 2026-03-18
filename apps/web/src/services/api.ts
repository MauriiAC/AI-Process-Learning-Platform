import axios from "axios";
import { clearAuth } from "@/lib/auth";

const configuredBaseUrl = import.meta.env.VITE_API_BASE_URL?.trim();
const baseURL = configuredBaseUrl ? configuredBaseUrl.replace(/\/+$/, "") : "/api";

const api = axios.create({ baseURL });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (r) => r,
  (error) => {
    if (error.response?.status === 401) {
      const hasToken = !!localStorage.getItem("token");
      if (hasToken) {
        clearAuth();
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);

export default api;

/**
 * lib/api.ts
 */
import axios from "axios";

const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const api = axios.create({
  baseURL: BASE,
  timeout: 60000,
});

export const setAuthHeader = (userId: string) => {
  api.defaults.headers.common["x-user-id"] = userId;
};

// ── Audit ──────────────────────────────────────────────────────
export const runAudit    = (form: FormData)          => api.post("/audit", form);
export const getAudit    = (id: string)              => api.get(`/audit/${id}`);
export const getReports  = ()                        => api.get("/reports");
export const downloadPdf = (id: string, lang = "en") =>
  api.get(`/reports/${id}/pdf?lang=${lang}`, { responseType: "arraybuffer" });

// ── Clients ────────────────────────────────────────────────────
export const getClients   = ()             => api.get("/clients");
export const getClient    = (id: string)   => api.get(`/clients/${id}`);
export const addClient    = (data: {
  business_name: string;
  gstin:         string;
  sector?:       string | null;
})                                         => api.post("/clients", data);
export const deleteClient = (id: string)   => api.delete(`/clients/${id}`);
/**
 * lib/api.ts
 * Axios API client — Node.js middleware se baat karta hai
 */
import axios from "axios";

const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:3001";

export const api = axios.create({
  baseURL: BASE,
  timeout: 60000,
});

export const setAuthHeader = (userId: string, email?: string, fullName?: string) => {
  api.defaults.headers.common["x-user-id"] = userId;
  if (email)    api.defaults.headers.common["x-user-email"] = email;
  if (fullName) api.defaults.headers.common["x-user-name"]  = fullName;
};

// ── Audit ─────────────────────────────────────────────────────────────────────
// runAudit → turant task_id milta hai (Celery background mein kaam karta hai)
export const runAudit = (form: FormData) =>
  api.post("/api/audit", form);

// getAuditStatus → poll karo jab tak status "completed" na ho
// Response: { status: "processing"|"completed"|"failed", audit_id?: string, error?: string }
export const getAuditStatus = (taskId: string) =>
  api.get(`/api/audit/status/${taskId}`);

// getAudit → final audit result fetch karo audit_id se
export const getAudit = (auditId: string) =>
  api.get(`/api/audit/${auditId}`);

// ── Reports ───────────────────────────────────────────────────────────────────
export const getReports  = ()                        => api.get("/api/reports");
export const downloadPdf = (id: string, lang = "en") =>
  api.get(`/api/reports/${id}/pdf?lang=${lang}`, { responseType: "arraybuffer" });

// ── Suppliers ─────────────────────────────────────────────────────────────────
export const getSupplierTrustScores = () => api.get("/api/reports/suppliers");

// ── Clients ───────────────────────────────────────────────────────────────────
export const getClients = ()           => api.get("/api/clients");
export const getClient  = (id: string) => api.get(`/api/clients/${id}`);

export const addClient = (data: {
  business_name:   string;
  gstin:           string;
  sector?:         string | null;
  contact_person?: string | null;
  phone?:          string | null;
  email?:          string | null;
  address?:        string | null;
}) => api.post("/api/clients", data);

export const updateClient = (id: string, data: {
  business_name?:  string;
  gstin?:          string;
  sector?:         string | null;
  contact_person?: string | null;
  phone?:          string | null;
  email?:          string | null;
  address?:        string | null;
}) => api.put(`/api/clients/${id}`, data);

export const deleteClient = (id: string) => api.delete(`/api/clients/${id}`);

// ── Reconciliation ────────────────────────────────────────────────────────────
export const runReconciliation = (form: FormData) => api.post("/api/reconcile", form);
export const getReconciliation = (id: string)     => api.get(`/api/reconcile/${id}`);
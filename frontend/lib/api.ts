import axios from "axios";

const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:3001";

export const api = axios.create({
  baseURL: BASE,
  timeout: 60000,
});

export const setAuthHeader = (userId: string) => {
  api.defaults.headers.common["x-user-id"] = userId;
};

export const runAudit    = (form: FormData)          => api.post("/api/audit", form);
export const getAudit    = (id: string)              => api.get(`/api/audit/${id}`);
export const getReports  = ()                        => api.get("/api/reports");
export const downloadPdf = (id: string, lang = "en") =>
  api.get(`/api/reports/${id}/pdf?lang=${lang}`, { responseType: "arraybuffer" });

export const getClients   = ()             => api.get("/api/clients");
export const getClient    = (id: string)   => api.get(`/api/clients/${id}`);
export const addClient    = (data: {
  business_name: string;
  gstin:         string;
  sector?:       string | null;
})                                         => api.post("/api/clients", data);
export const deleteClient = (id: string)   => api.delete(`/api/clients/${id}`);

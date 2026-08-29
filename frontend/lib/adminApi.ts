/**
 * lib/adminApi.ts
 * ----------------
 * Axios instance for all /admin/* API calls.
 * Automatically attaches Clerk session token to every request.
 */
import axios from "axios";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const ADMIN_KEY = process.env.NEXT_PUBLIC_ADMIN_API_KEY || "";

export const adminApi = axios.create({
  baseURL: API_URL,
  headers: {
    "Content-Type": "application/json",
    // Admin key for backend admin route protection
    "x-admin-key": ADMIN_KEY,
  },
  timeout: 15000,
});

// ── Types ─────────────────────────────────────────────────────

export interface Rule {
  id: string;
  rule_code: string;
  title: string;
  description?: string;
  category: string;
  severity: string;
  condition_type: string;
  condition_config?: Record<string, unknown>;
  law_code?: string;
  plain_explanation?: string;
  penalty_formula_type?: string;
  penalty_formula_config?: Record<string, unknown>;
  notice_risk_weight: number;
  notice_risk_max: number;
  is_active: boolean;
  version: number;
  effective_from?: string;
  effective_to?: string;
  created_at: string;
  updated_at: string;
}

export interface Law {
  id: string;
  law_code: string;
  act_name: string;
  section: string;
  short_text: string;
  official_source_url?: string;
  reviewed_on?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Threshold {
  id: string;
  profile_name: string;
  low_max: number;
  medium_max: number;
  high_max: number;
  critical_min: number;
  is_default: boolean;
  created_at: string;
  updated_at: string;
}

export interface FixStep {
  id: string;
  rule_code: string;
  step_order: number;
  step_text_en: string;
  step_text_hi?: string;
  step_text_mr?: string;
  created_at: string;
  updated_at: string;
}

// ── API functions ─────────────────────────────────────────────

// Rules
export const rulesApi = {
  list: (params?: { active_only?: boolean; category?: string; limit?: number; offset?: number }) =>
    adminApi.get<{ rules: Rule[]; total: number; active_count: number }>("/admin/rules", { params }),
  get: (id: string) => adminApi.get<Rule>(`/admin/rules/${id}`),
  create: (data: Partial<Rule>) => adminApi.post<{ rule: Rule }>("/admin/rules", data),
  update: (id: string, data: Partial<Rule>) => adminApi.patch<{ rule: Rule }>(`/admin/rules/${id}`, data),
  activate: (id: string) => adminApi.post(`/admin/rules/${id}/activate`),
  deactivate: (id: string) => adminApi.post(`/admin/rules/${id}/deactivate`),
  weights: () => adminApi.get("/admin/rules/active/weights"),
};

// Laws
export const lawsApi = {
  list: (params?: { active_only?: boolean }) =>
    adminApi.get<{ laws: Law[]; total: number }>("/admin/laws", { params }),
  create: (data: Partial<Law>) => adminApi.post<{ law: Law }>("/admin/laws", data),
  update: (id: string, data: Partial<Law>) => adminApi.patch<{ law: Law }>(`/admin/laws/${id}`, data),
};

// Thresholds
export const thresholdsApi = {
  list: () => adminApi.get<{ thresholds: Threshold[] }>("/admin/thresholds"),
  create: (data: Partial<Threshold>) => adminApi.post<{ threshold: Threshold }>("/admin/thresholds", data),
  update: (id: string, data: Partial<Threshold>) =>
    adminApi.patch<{ threshold: Threshold }>(`/admin/thresholds/${id}`, data),
};

// Fix Steps
export const fixStepsApi = {
  getByRule: (ruleCode: string) =>
    adminApi.get<{ rule_code: string; steps: { en: string[]; hi: string[]; mr: string[] } }>(
      `/admin/fix-steps/${ruleCode}`
    ),
  add: (data: Partial<FixStep>) => adminApi.post<{ step: FixStep }>("/admin/fix-steps", data),
  update: (id: string, data: Partial<FixStep>) =>
    adminApi.patch<{ step: FixStep }>(`/admin/fix-steps/${id}`, data),
  delete: (id: string) => adminApi.delete(`/admin/fix-steps/${id}`),
  reorder: (ruleCode: string, stepIds: string[]) =>
    adminApi.post(`/admin/fix-steps/${ruleCode}/reorder`, stepIds),
};
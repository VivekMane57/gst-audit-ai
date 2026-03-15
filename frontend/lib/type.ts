export type Language = "en" | "hi" | "mr";
export type RiskLevel = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
export type Severity  = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
export type Plan      = "free" | "pro" | "firm" | "enterprise";

export interface Client {
  id: string;
  business_name: string;
  gstin_masked: string;
  state_code: string;
  turnover_range?: string;
  is_active: boolean;
  latest_score?: number;
  latest_risk?: RiskLevel;
  created_at: string;
}

export interface Issue {
  issue_type: string;
  severity: Severity;
  invoice_number: string;
  party_name?: string;
  party_gstin?: string;
  amount?: number;
  problem_en: string;
  problem_hi: string;
  problem_mr: string;
  legal_ref: string;
  penalty_risk?: string;
  fix_steps: string[];
  itc_at_risk: number;
}

export interface ITCSummary {
  eligible: number;
  at_risk: number;
  blocked: number;
  total: number;
}

export interface AuditReport {
  audit_id: string;
  client_gstin_masked: string;
  period: string;
  language: string;
  compliance_score: number;
  risk_level: RiskLevel;
  risk_level_translated: string;
  total_invoices: number;
  issues: Issue[];
  critical_count: number;
  high_count: number;
  medium_count: number;
  low_count: number;
  itc_summary: ITCSummary;
  pdf_url?: string;
  created_at: string;
}
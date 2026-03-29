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

// ── Reconciliation Types ──────────────────────────────────────

export interface MatchedInvoice {
  invoice_number: string;
  party_name?: string;
  party_gstin?: string;
  books_tax: number;
  gstr2b_tax: number;
  diff: number;
  match_type: "exact" | "fuzzy";
  matched_inv_no: string;
  status: "matched";
}

export interface MissingInvoice {
  invoice_number: string;
  party_name?: string;
  party_gstin?: string;
  invoice_date?: string;
  taxable_value: number;
  itc_at_risk: number;
  status: "missing_in_2b";
}

export interface MismatchedInvoice {
  invoice_number: string;
  party_name?: string;
  party_gstin?: string;
  books_tax: number;
  gstr2b_tax: number;
  diff: number;
  excess_itc: number;
  status: "amount_mismatch";
}

export interface ReconciliationSummary {
  total_purchase_invoices: number;
  total_gstr2b_invoices: number;
  matched_count: number;
  missing_count: number;
  mismatch_count: number;
  risk_level: RiskLevel;
  summary_en: string;
  summary_hi: string;
  summary_mr: string;
}

export interface ITCImpact {
  total_itc_books: number;
  total_itc_gstr2b: number;
  itc_at_risk: number;
  itc_excess_claimed: number;
  total_tax_loss: number;
}

export interface ReconciliationResult {
  reconciliation_id: string;
  period: string;
  our_gstin: string;
  summary: ReconciliationSummary;
  itc_impact: ITCImpact;
  matched: MatchedInvoice[];
  missing: MissingInvoice[];
  mismatched: MismatchedInvoice[];
  parse_errors?: string[];
}
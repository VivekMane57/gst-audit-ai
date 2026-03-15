"use client";
import { useEffect, useState } from "react";
import { useUser } from "@clerk/nextjs";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  CheckCircle, Download, ArrowLeft,
  Shield, ChevronDown, ChevronUp, AlertCircle,
  AlertTriangle, TrendingDown, FileText, Zap,
} from "lucide-react";
import { getAudit, downloadPdf, setAuthHeader } from "@/lib/api";

// ── Types ──────────────────────────────────────────────────────
type Lang = "en" | "hi" | "mr";

interface Issue {
  severity:        string;
  invoice_number?: string;
  party_name?:     string;
  party_gstin?:    string;
  itc_at_risk?:    number;
  amount?:         number;
  problem_en?:     string;
  problem_hi?:     string;
  problem_mr?:     string;
  legal_ref?:      string;
  penalty_risk?:   string;
  fix_steps_en?:   string[];
  fix_steps_hi?:   string[];
  fix_steps_mr?:   string[];
  fix_steps?:      string[];
  issue_type?:     string;
}

interface RiskArea {
  category:      string;
  label:         string;
  label_hi?:     string;
  label_mr?:     string;
  score:         number;
  dept_priority: string;
}

interface PossibleNotice {
  notice_type:     string;
  description_en:  string;
  description_hi?: string;
  description_mr?: string;
  likelihood:      string;
}

interface WhatIf {
  current_probability: number;
  new_probability:     number;
  reduction:           number;
  reduction_percent:   number;
  current_risk_level:  string;
  new_risk_level:      string;
  fixes_count:         number;
}

interface Recommendation {
  priority:       number;
  issue_type:     string;
  invoice:        string;
  action:         string;
  risk_reduction: string;
  severity:       string;
}

interface NoticeSimulation {
  probability:        number;
  risk_level:         string;
  risk_message:       string;
  risk_areas:         RiskArea[];
  possible_notices:   PossibleNotice[];
  what_if_fix_all:    WhatIf;
  what_if_fix_critical?: WhatIf | null;
  recommendations:    Recommendation[];
  notice_reply_draft?: string;
  breakdown?: {
    base_risk:      number;
    issues_risk:    number;
    filing_risk:    number;
    compliance_risk:number;
    turnover_risk:  number;
    history_risk:   number;
    revenue_risk:   number;
  };
  labels?: Record<string, string>;
}

interface AuditData {
  id:                      string;
  period?:                 string;
  compliance_score:        number;
  risk_level?:             string;
  client_gstin_masked?:    string;
  total_invoices?:         number;
  total_invoices_scanned?: number;
  issues_json?:            Issue[];
  issues?:                 Issue[];
  itc_at_risk?:            number;
  itc_summary?:            { at_risk?: number; total?: number };
  critical_count?:         number;
  high_count?:             number;
  medium_count?:           number;
  low_count?:              number;
  notice_simulation?:      NoticeSimulation;
}

// ── Helpers ────────────────────────────────────────────────────
const SEV_WRAP: Record<string, string> = {
  CRITICAL: "bg-red-50 border-red-300",
  HIGH:     "bg-orange-50 border-orange-200",
  MEDIUM:   "bg-yellow-50 border-yellow-200",
  LOW:      "bg-gray-50 border-gray-200",
};
const SEV_BADGE: Record<string, string> = {
  CRITICAL: "bg-red-600 text-white",
  HIGH:     "bg-orange-500 text-white",
  MEDIUM:   "bg-yellow-500 text-white",
  LOW:      "bg-gray-400 text-white",
};
const scoreColor = (s: number) =>
  s >= 80 ? "text-green-600" : s >= 60 ? "text-yellow-600" : "text-red-600";

const NOTICE_COLORS: Record<string, { bg: string; text: string; bar: string }> = {
  VERY_HIGH: { bg: "bg-red-50",    text: "text-red-700",    bar: "bg-red-500" },
  HIGH:      { bg: "bg-orange-50", text: "text-orange-700", bar: "bg-orange-500" },
  MEDIUM:    { bg: "bg-yellow-50", text: "text-yellow-700", bar: "bg-yellow-500" },
  LOW:       { bg: "bg-green-50",  text: "text-green-700",  bar: "bg-green-500" },
};

const PRIORITY_BADGE: Record<string, string> = {
  "VERY HIGH": "bg-red-100 text-red-700",
  "HIGH":      "bg-orange-100 text-orange-700",
  "MEDIUM":    "bg-yellow-100 text-yellow-700",
  "LOW":       "bg-gray-100 text-gray-600",
};

function getProblem(issue: Issue, lang: Lang): string {
  if (lang === "hi") return issue.problem_hi || issue.problem_en || "";
  if (lang === "mr") return issue.problem_mr || issue.problem_en || "";
  return issue.problem_en || "";
}

function getFixSteps(issue: Issue, lang: Lang): string[] {
  if (lang === "hi") return issue.fix_steps_hi?.length ? issue.fix_steps_hi : (issue.fix_steps_en || issue.fix_steps || []);
  if (lang === "mr") return issue.fix_steps_mr?.length ? issue.fix_steps_mr : (issue.fix_steps_en || issue.fix_steps || []);
  return issue.fix_steps_en?.length ? issue.fix_steps_en : (issue.fix_steps || []);
}

function getRiskAreaLabel(area: RiskArea, lang: Lang): string {
  if (lang === "hi") return area.label_hi || area.label;
  if (lang === "mr") return area.label_mr || area.label;
  return area.label;
}

function getNoticeDesc(notice: PossibleNotice, lang: Lang): string {
  if (lang === "hi") return notice.description_hi || notice.description_en;
  if (lang === "mr") return notice.description_mr || notice.description_en;
  return notice.description_en;
}


// ── Notice Probability Gauge ───────────────────────────────────
function NoticeGauge({ probability, riskLevel }: { probability: number; riskLevel: string }) {
  const colors = NOTICE_COLORS[riskLevel] || NOTICE_COLORS.MEDIUM;

  return (
    <div className="relative">
      {/* Background bar */}
      <div className="w-full h-4 bg-gray-200 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-1000 ease-out ${colors.bar}`}
          style={{ width: `${probability}%` }}
        />
      </div>
      {/* Percentage label */}
      <div className="flex justify-between mt-1.5">
        <span className="text-xs text-gray-400">0%</span>
        <span className={`text-sm font-bold ${colors.text}`}>{probability}%</span>
        <span className="text-xs text-gray-400">100%</span>
      </div>
    </div>
  );
}


// ── Notice Simulator Section ───────────────────────────────────
function NoticeSimulatorSection({ sim, lang }: { sim: NoticeSimulation; lang: Lang }) {
  const [showReply, setShowReply] = useState(false);
  const [showBreakdown, setShowBreakdown] = useState(false);
  const colors = NOTICE_COLORS[sim.risk_level] || NOTICE_COLORS.MEDIUM;
  const whatIf = sim.what_if_fix_all;

  return (
    <div className={`rounded-2xl border-2 overflow-hidden mb-6 ${
      sim.risk_level === "VERY_HIGH" ? "border-red-300" :
      sim.risk_level === "HIGH" ? "border-orange-300" :
      sim.risk_level === "MEDIUM" ? "border-yellow-300" : "border-green-300"
    }`}>

      {/* Header */}
      <div className={`px-6 py-5 ${colors.bg}`}>
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div className="flex items-center gap-3">
            <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${
              sim.probability >= 50 ? "bg-red-100" : sim.probability >= 25 ? "bg-orange-100" : "bg-green-100"
            }`}>
              <AlertTriangle size={24} className={
                sim.probability >= 50 ? "text-red-600" : sim.probability >= 25 ? "text-orange-600" : "text-green-600"
              } />
            </div>
            <div>
              <h2 className="text-lg font-bold text-gray-900">
                {lang === "hi" ? "GST नोटिस की संभावना" :
                 lang === "mr" ? "GST नोटिसची शक्यता" :
                 "GST Notice Probability"}
              </h2>
              <p className={`text-sm font-semibold ${colors.text}`}>
                {sim.risk_message}
              </p>
            </div>
          </div>
          <div className="text-right">
            <p className={`text-4xl font-black ${colors.text}`}>{sim.probability}%</p>
            <p className="text-xs text-gray-500">
              {lang === "hi" ? "नोटिस का जोखिम" :
               lang === "mr" ? "नोटिसचा धोका" :
               "Notice Risk"}
            </p>
          </div>
        </div>

        {/* Gauge bar */}
        <div className="mt-4">
          <NoticeGauge probability={sim.probability} riskLevel={sim.risk_level} />
        </div>
      </div>

      <div className="px-6 py-5 space-y-6 bg-white">

        {/* Risk Areas */}
        {sim.risk_areas && sim.risk_areas.length > 0 && (
          <div>
            <h3 className="text-sm font-bold text-gray-700 mb-3 flex items-center gap-2">
              <Shield size={14} />
              {lang === "hi" ? "मुख्य जोखिम क्षेत्र" :
               lang === "mr" ? "मुख्य धोका क्षेत्रे" :
               "Main Risk Areas"}
            </h3>
            <div className="space-y-2">
              {sim.risk_areas.slice(0, 5).map((area, i) => (
                <div key={i} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <div className="flex items-center gap-3">
                    <div className={`w-2 h-8 rounded-full ${
                      area.dept_priority === "VERY HIGH" ? "bg-red-500" :
                      area.dept_priority === "HIGH" ? "bg-orange-500" :
                      area.dept_priority === "MEDIUM" ? "bg-yellow-500" : "bg-gray-400"
                    }`} />
                    <div>
                      <p className="text-sm font-medium text-gray-800">
                        {getRiskAreaLabel(area, lang)}
                      </p>
                      <p className="text-xs text-gray-500">
                        {lang === "hi" ? "विभाग प्राथमिकता" :
                         lang === "mr" ? "विभाग प्राधान्य" :
                         "Dept Priority"}: {area.dept_priority}
                      </p>
                    </div>
                  </div>
                  <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${
                    PRIORITY_BADGE[area.dept_priority] || "bg-gray-100 text-gray-600"
                  }`}>
                    {area.score}%
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* What-If Analysis */}
        {whatIf && (
          <div className="bg-gradient-to-r from-green-50 to-blue-50 rounded-xl p-5 border border-green-200">
            <h3 className="text-sm font-bold text-gray-700 mb-3 flex items-center gap-2">
              <TrendingDown size={14} className="text-green-600" />
              {lang === "hi" ? "अगर सब ठीक करें तो" :
               lang === "mr" ? "सर्व दुरुस्त केल्यास" :
               "If You Fix All Issues"}
            </h3>
            <div className="flex items-center gap-4 flex-wrap">
              {/* Current */}
              <div className="text-center">
                <p className="text-2xl font-black text-red-600">{whatIf.current_probability}%</p>
                <p className="text-xs text-gray-500">
                  {lang === "hi" ? "अभी" : lang === "mr" ? "सध्या" : "Current"}
                </p>
              </div>
              {/* Arrow */}
              <div className="text-2xl text-green-600 font-bold">→</div>
              {/* After fix */}
              <div className="text-center">
                <p className="text-2xl font-black text-green-600">{whatIf.new_probability}%</p>
                <p className="text-xs text-gray-500">
                  {lang === "hi" ? "सुधार के बाद" : lang === "mr" ? "दुरुस्तीनंतर" : "After Fix"}
                </p>
              </div>
              {/* Reduction badge */}
              <div className="ml-auto bg-green-600 text-white px-4 py-2 rounded-xl text-center">
                <p className="text-lg font-black">-{whatIf.reduction}%</p>
                <p className="text-xs opacity-80">
                  {lang === "hi" ? "कम हुआ" : lang === "mr" ? "कमी" : "Reduced"}
                </p>
              </div>
            </div>

            {/* Risk level change */}
            {whatIf.current_risk_level !== whatIf.new_risk_level && (
              <p className="text-xs text-green-700 mt-3 font-medium">
                {whatIf.current_risk_level.replace("_", " ")} → {whatIf.new_risk_level.replace("_", " ")}
              </p>
            )}
          </div>
        )}

        {/* Possible Notice Types */}
        {sim.possible_notices && sim.possible_notices.length > 0 && (
          <div>
            <h3 className="text-sm font-bold text-gray-700 mb-3 flex items-center gap-2">
              <FileText size={14} />
              {lang === "hi" ? "संभावित नोटिस प्रकार" :
               lang === "mr" ? "संभाव्य नोटिस प्रकार" :
               "Possible Notice Types"}
            </h3>
            <div className="space-y-2">
              {sim.possible_notices.map((notice, i) => (
                <div key={i} className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg border border-gray-100">
                  <span className="px-2 py-0.5 bg-gray-200 text-gray-700 rounded text-xs font-mono font-bold shrink-0 mt-0.5">
                    {notice.notice_type}
                  </span>
                  <div className="flex-1">
                    <p className="text-sm text-gray-700">{getNoticeDesc(notice, lang)}</p>
                  </div>
                  <span className={`px-2 py-0.5 rounded-full text-xs font-bold shrink-0 ${
                    notice.likelihood === "HIGH" ? "bg-red-100 text-red-700" : "bg-yellow-100 text-yellow-700"
                  }`}>
                    {notice.likelihood}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Recommendations */}
        {sim.recommendations && sim.recommendations.length > 0 && (
          <div>
            <h3 className="text-sm font-bold text-gray-700 mb-3 flex items-center gap-2">
              <Zap size={14} className="text-yellow-600" />
              {lang === "hi" ? "तुरंत कार्रवाई" :
               lang === "mr" ? "तातडीने कारवाई" :
               "Immediate Actions"}
            </h3>
            <div className="space-y-2">
              {sim.recommendations.slice(0, 5).map((rec, i) => (
                <div key={i} className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg">
                  <span className="w-6 h-6 rounded-full bg-blue-600 text-white text-xs font-bold flex items-center justify-center shrink-0 mt-0.5">
                    {rec.priority}
                  </span>
                  <div className="flex-1">
                    <p className="text-sm text-gray-700">{rec.action}</p>
                    <p className="text-xs text-gray-400 mt-1">
                      {lang === "hi" ? "जोखिम कम" : lang === "mr" ? "धोका कमी" : "Risk reduction"}: {rec.risk_reduction}
                    </p>
                  </div>
                  <span className={`px-2 py-0.5 rounded text-xs font-bold shrink-0 ${
                    SEV_BADGE[rec.severity?.toUpperCase()] || "bg-gray-400 text-white"
                  }`}>
                    {rec.severity?.toUpperCase()}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Breakdown toggle */}
        {sim.breakdown && (
          <div>
            <button
              onClick={() => setShowBreakdown(!showBreakdown)}
              className="flex items-center gap-2 text-xs text-gray-500 hover:text-gray-700 transition-colors"
            >
              {showBreakdown ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
              {lang === "hi" ? "विस्तृत विवरण" : lang === "mr" ? "तपशीलवार" : "Detailed Breakdown"}
            </button>
            {showBreakdown && (
              <div className="mt-3 grid grid-cols-2 gap-2">
                {Object.entries(sim.breakdown).map(([key, val]) => (
                  <div key={key} className="flex justify-between p-2 bg-gray-50 rounded text-xs">
                    <span className="text-gray-500">{key.replace(/_/g, " ")}</span>
                    <span className="font-mono font-bold text-gray-700">
                      {typeof val === "number" && key.includes("multiplier") ? `×${val}` : `${val}%`}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Notice Reply Draft */}
        {sim.notice_reply_draft && (
          <div>
            <button
              onClick={() => setShowReply(!showReply)}
              className="flex items-center gap-2 px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg text-sm font-medium text-gray-700 transition-colors"
            >
              <FileText size={14} />
              {showReply
                ? (lang === "hi" ? "नोटिस रिप्लाई छुपाएं" : lang === "mr" ? "नोटिस उत्तर लपवा" : "Hide Notice Reply Draft")
                : (lang === "hi" ? "नोटिस रिप्लाई देखें" : lang === "mr" ? "नोटिस उत्तर पहा" : "View Notice Reply Draft")
              }
            </button>
            {showReply && (
              <div className="mt-3 relative">
                <pre className="bg-gray-50 border border-gray-200 rounded-xl p-4 text-xs text-gray-700 whitespace-pre-wrap leading-relaxed font-sans max-h-96 overflow-y-auto">
                  {sim.notice_reply_draft}
                </pre>
                <button
                  onClick={() => {
                    navigator.clipboard?.writeText(sim.notice_reply_draft || "");
                    alert(lang === "hi" ? "कॉपी हो गया!" : lang === "mr" ? "कॉपी झाले!" : "Copied!");
                  }}
                  className="absolute top-2 right-2 px-3 py-1 bg-blue-600 text-white text-xs rounded-lg hover:bg-blue-700 transition-colors"
                >
                  {lang === "hi" ? "कॉपी" : lang === "mr" ? "कॉपी" : "Copy"}
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}


// ── IssueCard ──────────────────────────────────────────────────
function IssueCard({ issue, lang }: { issue: Issue; lang: Lang }) {
  const [open, setOpen] = useState(false);
  const sev      = (issue.severity || "LOW").toUpperCase();
  const itcRisk  = issue.itc_at_risk ?? issue.amount ?? 0;
  const problem  = getProblem(issue, lang);
  const fixSteps = getFixSteps(issue, lang);

  return (
    <div className={`border rounded-xl overflow-hidden ${SEV_WRAP[sev] ?? "bg-gray-50 border-gray-200"}`}>
      <button
        onClick={() => setOpen(!open)}
        className="w-full text-left p-4 flex items-start justify-between gap-3 hover:bg-black/5 transition-colors"
      >
        <div className="flex items-start gap-3">
          <span className={`px-2 py-0.5 rounded text-xs font-bold mt-0.5 shrink-0 ${SEV_BADGE[sev] ?? "bg-gray-400 text-white"}`}>
            {sev}
          </span>
          <div>
            <p className="font-semibold text-sm text-gray-900">
              {issue.invoice_number || issue.issue_type || "Issue"}
            </p>
            {(issue.party_name || issue.party_gstin) && (
              <p className="text-xs text-gray-500 mt-0.5">
                {issue.party_name || issue.party_gstin}
              </p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-3 shrink-0">
          {itcRisk > 0 && (
            <div className="text-right">
              <p className="text-xs text-gray-400">ITC at Risk</p>
              <p className="text-sm font-bold text-red-600">
                ₹{itcRisk.toLocaleString("en-IN")}
              </p>
            </div>
          )}
          {open ? <ChevronUp size={16} className="text-gray-400" /> : <ChevronDown size={16} className="text-gray-400" />}
        </div>
      </button>

      {open && (
        <div className="px-4 pb-4 pt-3 border-t border-gray-200 space-y-3">
          {problem && <p className="text-sm text-gray-700 leading-relaxed">{problem}</p>}

          {(issue.legal_ref || issue.penalty_risk) && (
            <div className="bg-white rounded-lg p-3 text-xs space-y-1.5 border border-gray-100">
              {issue.legal_ref && (
                <p><span className="font-semibold text-gray-700">Legal Reference: </span>{issue.legal_ref}</p>
              )}
              {issue.penalty_risk && (
                <p><span className="font-semibold text-red-600">Potential Penalty: </span>{issue.penalty_risk}</p>
              )}
            </div>
          )}

          {fixSteps.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-gray-700 mb-2">Steps to Fix:</p>
              <ol className="space-y-1.5">
                {fixSteps.map((step, i) => (
                  <li key={i} className="text-xs flex gap-2 text-gray-700">
                    <span className="w-4 h-4 rounded-full bg-blue-100 text-blue-700 text-xs font-bold flex items-center justify-center shrink-0 mt-0.5">
                      {i + 1}
                    </span>
                    {step}
                  </li>
                ))}
              </ol>
            </div>
          )}
        </div>
      )}
    </div>
  );
}


// ── Page ───────────────────────────────────────────────────────
export default function ReportPage() {
  const { user }                    = useUser();
  const { id }                      = useParams<{ id: string }>();
  const [data, setData]             = useState<AuditData | null>(null);
  const [loading, setLoading]       = useState(true);
  const [pdfLoading, setPdfLoading] = useState(false);
  const [lang, setLang]             = useState<Lang>("en");

  useEffect(() => {
    if (!user || !id) return;
    setAuthHeader(user.id);
    getAudit(id)
      .then((r) => setData(r.data as AuditData))
      .catch((e) => console.error("getAudit error:", e))
      .finally(() => setLoading(false));
  }, [user, id]);

  const handleDownload = async () => {
    if (!data) return;
    setPdfLoading(true);
    try {
      const res = await downloadPdf(id, lang);
      const url = URL.createObjectURL(new Blob([res.data], { type: "application/pdf" }));
      const a   = document.createElement("a");
      a.href     = url;
      a.download = `GST_Audit_${data.period || id.slice(0, 8)}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      alert("PDF download failed. Please try again.");
    } finally {
      setPdfLoading(false);
    }
  };

  if (loading) return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="text-center">
        <div className="w-10 h-10 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto" />
        <p className="text-gray-500 mt-3 text-sm">Loading report...</p>
      </div>
    </div>
  );

  if (!data) return (
    <div className="p-8 text-center">
      <AlertCircle size={40} className="text-gray-300 mx-auto mb-3" />
      <p className="text-gray-500 font-medium">Report not found.</p>
      <Link href="/upload" className="text-blue-600 mt-2 inline-block hover:underline text-sm">
        Run a new audit →
      </Link>
    </div>
  );

  const issues: Issue[] =
    Array.isArray(data.issues_json) ? data.issues_json :
    Array.isArray(data.issues)      ? data.issues       : [];

  const totalInvoices = data.total_invoices ?? data.total_invoices_scanned ?? 0;
  const itcAtRisk     = data.itc_summary?.at_risk ?? data.itc_at_risk ?? 0;
  const critCount     = data.critical_count ?? issues.filter(i => i.severity?.toUpperCase() === "CRITICAL").length;
  const highCount     = data.high_count     ?? issues.filter(i => i.severity?.toUpperCase() === "HIGH").length;
  const medCount      = data.medium_count   ?? issues.filter(i => i.severity?.toUpperCase() === "MEDIUM").length;
  const lowCount      = data.low_count      ?? issues.filter(i => i.severity?.toUpperCase() === "LOW").length;

  const noticeSim     = data.notice_simulation;

  return (
    <div className="p-8 max-w-3xl mx-auto">

      {/* Back */}
      <Link href="/reports" className="flex items-center gap-2 text-gray-500 hover:text-gray-700 text-sm mb-6">
        <ArrowLeft size={15} /> All Reports
      </Link>

      {/* Summary card */}
      <div className="bg-white rounded-2xl border border-gray-200 p-6 mb-6">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <Shield className="text-blue-600" size={20} />
              <h1 className="text-xl font-bold text-gray-900">GST Audit Report</h1>
            </div>
            <p className="text-gray-500 text-sm">
              {data.client_gstin_masked || "—"}
              {data.period ? ` · ${data.period}` : ""}
            </p>
          </div>
          <button
            onClick={handleDownload}
            disabled={pdfLoading}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-xl hover:bg-blue-700 disabled:opacity-60 transition-colors"
          >
            <Download size={15} />
            {pdfLoading ? "Generating..." : "Download PDF"}
          </button>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-4 gap-4 mt-6 text-center">
          {[
            { value: data.compliance_score, label: "Score /100",   color: scoreColor(data.compliance_score) },
            { value: totalInvoices,          label: "Invoices",     color: "text-gray-700" },
            { value: issues.length,          label: "Issues Found", color: issues.length > 0 ? "text-red-600" : "text-green-600" },
            {
              value: itcAtRisk >= 1000
                ? `₹${(itcAtRisk / 1000).toFixed(0)}K`
                : `₹${itcAtRisk.toLocaleString("en-IN")}`,
              label: "ITC at Risk",
              color: "text-orange-600",
            },
          ].map((m, i) => (
            <div key={i}>
              <p className={`text-3xl font-bold ${m.color}`}>{m.value}</p>
              <p className="text-xs text-gray-400 mt-1">{m.label}</p>
            </div>
          ))}
        </div>

        {/* Severity pills */}
        <div className="flex flex-wrap gap-2 mt-5">
          {[
            { label: "Critical", count: critCount, cls: "bg-red-100 text-red-700" },
            { label: "High",     count: highCount, cls: "bg-orange-100 text-orange-700" },
            { label: "Medium",   count: medCount,  cls: "bg-yellow-100 text-yellow-700" },
            { label: "Low",      count: lowCount,  cls: "bg-gray-100 text-gray-600" },
          ].map(({ label, count, cls }) => (
            <span key={label} className={`px-3 py-1 rounded-full text-xs font-semibold ${cls}`}>
              {label}: {count}
            </span>
          ))}
        </div>
      </div>

      {/* Language toggle */}
      <div className="flex gap-2 mb-5">
        {(["en", "hi", "mr"] as Lang[]).map((l) => (
          <button
            key={l}
            onClick={() => setLang(l)}
            className={`px-4 py-1.5 rounded-lg text-xs font-medium border transition-all
              ${lang === l
                ? "bg-blue-600 text-white border-blue-600"
                : "bg-white text-gray-600 border-gray-300 hover:border-gray-400"}`}
          >
            {l === "en" ? "English" : l === "hi" ? "Hindi" : "Marathi"}
          </button>
        ))}
      </div>

      {/* ═══ NOTICE SIMULATOR SECTION ═══ */}
      {noticeSim && (
        <NoticeSimulatorSection sim={noticeSim} lang={lang} />
      )}

      {/* Issues */}
      {issues.length === 0 ? (
        <div className="bg-green-50 border border-green-200 rounded-2xl p-12 text-center">
          <CheckCircle className="text-green-500 mx-auto mb-3" size={44} />
          <p className="font-bold text-green-700 text-lg">No issues found!</p>
          <p className="text-green-600 text-sm mt-1">Excellent GST compliance</p>
        </div>
      ) : (
        <div className="space-y-3">
          <p className="text-sm text-gray-500 mb-3">
            {issues.length} issue{issues.length !== 1 ? "s" : ""} found — click to expand details
          </p>
          {issues.map((issue, i) => (
            <IssueCard key={i} issue={issue} lang={lang} />
          ))}
        </div>
      )}
    </div>
  );
}
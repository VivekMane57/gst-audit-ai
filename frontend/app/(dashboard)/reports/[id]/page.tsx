"use client";
import { useEffect, useState } from "react";
import { useUser } from "@clerk/nextjs";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  CheckCircle, Download, ArrowLeft, Shield,
  ChevronDown, ChevronUp, AlertCircle, AlertTriangle,
  TrendingDown, FileText, Zap, Copy, ExternalLink,
  BarChart3, Info, Loader2,
} from "lucide-react";
import { getAudit, getAuditStatus, downloadPdf, setAuthHeader } from "@/lib/api";

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
  category: string; label: string; label_hi?: string; label_mr?: string;
  score: number; dept_priority: string;
}

interface PossibleNotice {
  notice_type: string; description_en: string; description_hi?: string;
  description_mr?: string; likelihood: string;
}

interface WhatIf {
  current_probability: number; new_probability: number; reduction: number;
  reduction_percent: number; current_risk_level: string; new_risk_level: string; fixes_count: number;
}

interface Recommendation {
  priority: number; issue_type: string; invoice: string;
  action: string; risk_reduction: string; severity: string;
}

interface NoticeSimulation {
  probability: number; risk_level: string; risk_message: string;
  risk_areas: RiskArea[]; possible_notices: PossibleNotice[];
  what_if_fix_all: WhatIf; what_if_fix_critical?: WhatIf | null;
  recommendations: Recommendation[]; notice_reply_draft?: string;
  breakdown?: Record<string, number>; labels?: Record<string, string>;
}

interface AuditData {
  id: string; period?: string; compliance_score: number; risk_level?: string;
  client_gstin_masked?: string; total_invoices?: number; total_invoices_scanned?: number;
  issues_json?: Issue[]; issues?: Issue[]; itc_at_risk?: number;
  itc_summary?: { at_risk?: number; total?: number };
  critical_count?: number; high_count?: number; medium_count?: number; low_count?: number;
  notice_simulation?: NoticeSimulation;
}

// ── Helpers ──────────────────────────────────────────────────
const SEV_WRAP: Record<string, string> = {
  CRITICAL: "bg-red-50 border-red-200",
  HIGH:     "bg-orange-50 border-orange-200",
  MEDIUM:   "bg-amber-50 border-amber-200",
  LOW:      "bg-gray-50 border-gray-200",
};
const SEV_BADGE: Record<string, string> = {
  CRITICAL: "bg-red-600 text-white",
  HIGH:     "bg-orange-500 text-white",
  MEDIUM:   "bg-amber-500 text-white",
  LOW:      "bg-gray-400 text-white",
};
const SEV_DOT: Record<string, string> = {
  CRITICAL: "bg-red-500",
  HIGH:     "bg-orange-500",
  MEDIUM:   "bg-amber-500",
  LOW:      "bg-gray-400",
};
const NOTICE_COLORS: Record<string, { ring: string; bg: string; text: string; bar: string; glow: string }> = {
  VERY_HIGH: { ring: "ring-red-300",    bg: "bg-red-50",    text: "text-red-700",    bar: "bg-red-500",    glow: "shadow-red-100" },
  HIGH:      { ring: "ring-orange-300", bg: "bg-orange-50", text: "text-orange-700", bar: "bg-orange-500", glow: "shadow-orange-100" },
  MEDIUM:    { ring: "ring-amber-300",  bg: "bg-amber-50",  text: "text-amber-700",  bar: "bg-amber-500",  glow: "shadow-amber-100" },
  LOW:       { ring: "ring-green-300",  bg: "bg-green-50",  text: "text-green-700",  bar: "bg-green-500",  glow: "shadow-green-100" },
};

const scoreColor = (s: number) =>
  s >= 80 ? "text-green-600" : s >= 60 ? "text-amber-600" : "text-red-600";
const scoreRing = (s: number) =>
  s >= 80 ? "#16a34a" : s >= 60 ? "#d97706" : "#dc2626";

function getProblem(issue: Issue, lang: Lang) {
  if (lang === "hi") return issue.problem_hi || issue.problem_en || "";
  if (lang === "mr") return issue.problem_mr || issue.problem_en || "";
  return issue.problem_en || "";
}
function getFixSteps(issue: Issue, lang: Lang): string[] {
  if (lang === "hi") return issue.fix_steps_hi?.length ? issue.fix_steps_hi : (issue.fix_steps_en || issue.fix_steps || []);
  if (lang === "mr") return issue.fix_steps_mr?.length ? issue.fix_steps_mr : (issue.fix_steps_en || issue.fix_steps || []);
  return issue.fix_steps_en?.length ? issue.fix_steps_en : (issue.fix_steps || []);
}
function getRiskAreaLabel(area: RiskArea, lang: Lang) {
  if (lang === "hi") return area.label_hi || area.label;
  if (lang === "mr") return area.label_mr || area.label;
  return area.label;
}
function getNoticeDesc(n: PossibleNotice, lang: Lang) {
  if (lang === "hi") return n.description_hi || n.description_en;
  if (lang === "mr") return n.description_mr || n.description_en;
  return n.description_en;
}

// ── Score Ring ────────────────────────────────────────────────
function ScoreRing({ score }: { score: number }) {
  const r = 36, c = 44, circ = 2 * Math.PI * r;
  const dash = (score / 100) * circ;
  return (
    <div className="relative w-24 h-24 flex items-center justify-center">
      <svg width="88" height="88" viewBox="0 0 88 88" className="-rotate-90">
        <circle cx={c} cy={c} r={r} fill="none" stroke="#e5e7eb" strokeWidth="7" />
        <circle cx={c} cy={c} r={r} fill="none"
          stroke={scoreRing(score)} strokeWidth="7"
          strokeDasharray={`${dash} ${circ}`}
          strokeLinecap="round"
          style={{ transition: "stroke-dasharray 1s ease" }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className={`text-2xl font-black ${scoreColor(score)}`}>{score}</span>
        <span className="text-[10px] text-gray-400 -mt-0.5">/ 100</span>
      </div>
    </div>
  );
}

// ── Notice Gauge ──────────────────────────────────────────────
function NoticeGauge({ probability, riskLevel }: { probability: number; riskLevel: string }) {
  const colors = NOTICE_COLORS[riskLevel] || NOTICE_COLORS.MEDIUM;
  return (
    <div>
      <div className="w-full h-3 bg-gray-100 rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all duration-1000 ${colors.bar}`}
          style={{ width: `${probability}%` }} />
      </div>
      <div className="flex justify-between mt-1">
        <span className="text-[10px] text-gray-400">0%</span>
        <span className={`text-[10px] font-bold ${colors.text}`}>{probability}%</span>
        <span className="text-[10px] text-gray-400">100%</span>
      </div>
    </div>
  );
}

// ── Notice Simulator Section ──────────────────────────────────
function NoticeSimulatorSection({ sim, lang }: { sim: NoticeSimulation; lang: Lang }) {
  const [showReply, setShowReply]         = useState(false);
  const [showBreakdown, setShowBreakdown] = useState(false);
  const [copied, setCopied]               = useState(false);
  const colors  = NOTICE_COLORS[sim.risk_level] || NOTICE_COLORS.MEDIUM;
  const whatIf  = sim.what_if_fix_all;

  const handleCopy = () => {
    navigator.clipboard?.writeText(sim.notice_reply_draft || "");
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className={`rounded-2xl border overflow-hidden ring-2 ${colors.ring} shadow-lg ${colors.glow} mb-5`}>
      <div className={`px-4 lg:px-6 py-4 lg:py-5 ${colors.bg}`}>
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-start gap-3">
            <div className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${
              sim.probability >= 50 ? "bg-red-100" : sim.probability >= 25 ? "bg-orange-100" : "bg-green-100"
            }`}>
              <AlertTriangle size={20} className={
                sim.probability >= 50 ? "text-red-600" : sim.probability >= 25 ? "text-orange-600" : "text-green-600"
              } />
            </div>
            <div>
              <h2 className="font-bold text-gray-900 text-base">
                {lang === "hi" ? "GST नोटिस की संभावना" : lang === "mr" ? "GST नोटिसची शक्यता" : "GST Notice Probability"}
              </h2>
              <p className={`text-xs font-medium mt-0.5 ${colors.text}`}>{sim.risk_message}</p>
            </div>
          </div>
          <div className={`text-3xl lg:text-4xl font-black shrink-0 ${colors.text}`}>{sim.probability}%</div>
        </div>
        <div className="mt-3">
          <NoticeGauge probability={sim.probability} riskLevel={sim.risk_level} />
        </div>
      </div>

      <div className="px-4 lg:px-6 py-4 lg:py-5 space-y-5 bg-white">
        {sim.risk_areas?.length > 0 && (
          <div>
            <h3 className="text-xs font-bold text-gray-600 uppercase tracking-wide mb-2.5 flex items-center gap-1.5">
              <BarChart3 size={12} />
              {lang === "hi" ? "मुख्य जोखिम क्षेत्र" : lang === "mr" ? "मुख्य धोका क्षेत्रे" : "Main Risk Areas"}
            </h3>
            <div className="space-y-2">
              {sim.risk_areas.slice(0, 5).map((area, i) => (
                <div key={i} className="flex items-center gap-2.5 p-2.5 bg-gray-50 rounded-lg">
                  <div className={`w-1.5 h-8 rounded-full shrink-0 ${
                    area.dept_priority === "VERY HIGH" ? "bg-red-500" :
                    area.dept_priority === "HIGH" ? "bg-orange-500" :
                    area.dept_priority === "MEDIUM" ? "bg-amber-500" : "bg-gray-400"
                  }`} />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-800 truncate">{getRiskAreaLabel(area, lang)}</p>
                    <p className="text-[10px] text-gray-400">
                      {lang === "hi" ? "प्राथमिकता" : lang === "mr" ? "प्राधान्य" : "Priority"}: {area.dept_priority}
                    </p>
                  </div>
                  <span className={`text-xs font-bold px-2 py-0.5 rounded-full shrink-0 ${
                    area.dept_priority === "VERY HIGH" ? "bg-red-100 text-red-700" :
                    area.dept_priority === "HIGH" ? "bg-orange-100 text-orange-700" :
                    area.dept_priority === "MEDIUM" ? "bg-amber-100 text-amber-700" :
                    "bg-gray-100 text-gray-600"
                  }`}>{area.score}%</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {whatIf && (
          <div className="bg-gradient-to-br from-green-50 to-emerald-50 rounded-xl p-4 border border-green-200">
            <h3 className="text-xs font-bold text-gray-600 uppercase tracking-wide mb-3 flex items-center gap-1.5">
              <TrendingDown size={12} className="text-green-600" />
              {lang === "hi" ? "सब ठीक करने पर" : lang === "mr" ? "सर्व दुरुस्त केल्यास" : "If You Fix All Issues"}
            </h3>
            <div className="flex items-center gap-3">
              <div className="text-center">
                <p className="text-2xl font-black text-red-600">{whatIf.current_probability}%</p>
                <p className="text-[10px] text-gray-500">{lang === "hi" ? "अभी" : lang === "mr" ? "सध्या" : "Now"}</p>
              </div>
              <div className="text-green-500 font-bold text-lg">→</div>
              <div className="text-center">
                <p className="text-2xl font-black text-green-600">{whatIf.new_probability}%</p>
                <p className="text-[10px] text-gray-500">{lang === "hi" ? "बाद में" : lang === "mr" ? "नंतर" : "After"}</p>
              </div>
              <div className="ml-auto bg-green-600 text-white px-3 py-2 rounded-xl text-center">
                <p className="text-base font-black leading-none">-{whatIf.reduction}%</p>
                <p className="text-[10px] opacity-80 mt-0.5">{lang === "hi" ? "कम" : lang === "mr" ? "कमी" : "Reduced"}</p>
              </div>
            </div>
          </div>
        )}

        {sim.possible_notices?.length > 0 && (
          <div>
            <h3 className="text-xs font-bold text-gray-600 uppercase tracking-wide mb-2.5 flex items-center gap-1.5">
              <FileText size={12} />
              {lang === "hi" ? "संभावित नोटिस" : lang === "mr" ? "संभाव्य नोटिस" : "Possible Notices"}
            </h3>
            <div className="space-y-2">
              {sim.possible_notices.map((n, i) => (
                <div key={i} className="flex items-start gap-2.5 p-2.5 bg-gray-50 rounded-lg">
                  <span className="px-1.5 py-0.5 bg-gray-200 text-gray-700 rounded text-[10px] font-mono font-bold shrink-0 mt-0.5">
                    {n.notice_type}
                  </span>
                  <p className="text-xs text-gray-700 flex-1">{getNoticeDesc(n, lang)}</p>
                  <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded-full shrink-0 ${
                    n.likelihood === "HIGH" ? "bg-red-100 text-red-700" : "bg-amber-100 text-amber-700"
                  }`}>{n.likelihood}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {sim.recommendations?.length > 0 && (
          <div>
            <h3 className="text-xs font-bold text-gray-600 uppercase tracking-wide mb-2.5 flex items-center gap-1.5">
              <Zap size={12} className="text-amber-500" />
              {lang === "hi" ? "तुरंत करें" : lang === "mr" ? "तातडीने करा" : "Immediate Actions"}
            </h3>
            <div className="space-y-2">
              {sim.recommendations.slice(0, 5).map((rec, i) => (
                <div key={i} className="flex items-start gap-2.5 p-2.5 bg-gray-50 rounded-lg">
                  <span className="w-5 h-5 rounded-full bg-blue-600 text-white text-[10px] font-bold flex items-center justify-center shrink-0 mt-0.5">
                    {rec.priority}
                  </span>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs text-gray-700">{rec.action}</p>
                    <p className="text-[10px] text-gray-400 mt-0.5">
                      {lang === "hi" ? "जोखिम कम" : lang === "mr" ? "धोका कमी" : "Risk ↓"}: {rec.risk_reduction}
                    </p>
                  </div>
                  <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded shrink-0 ${
                    SEV_BADGE[rec.severity?.toUpperCase()] || "bg-gray-400 text-white"
                  }`}>{rec.severity?.toUpperCase()}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {sim.notice_reply_draft && (
          <div>
            <button onClick={() => setShowReply(!showReply)}
              className="flex items-center gap-2 px-3 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg text-xs font-medium text-gray-700 transition-colors active:scale-95">
              <FileText size={12} />
              {showReply
                ? (lang === "hi" ? "रिप्लाई छुपाएं" : lang === "mr" ? "उत्तर लपवा" : "Hide Reply Draft")
                : (lang === "hi" ? "नोटिस रिप्लाई देखें" : lang === "mr" ? "नोटिस उत्तर पहा" : "View Notice Reply Draft")}
            </button>
            {showReply && (
              <div className="mt-2 relative">
                <pre className="bg-gray-50 border border-gray-200 rounded-xl p-4 text-[11px] text-gray-700 whitespace-pre-wrap leading-relaxed font-sans max-h-80 overflow-y-auto">
                  {sim.notice_reply_draft}
                </pre>
                <button onClick={handleCopy}
                  className="absolute top-2 right-2 flex items-center gap-1 px-2.5 py-1 bg-blue-600 text-white text-[10px] rounded-lg hover:bg-blue-700 transition-colors active:scale-95">
                  <Copy size={10} />
                  {copied ? "Copied!" : "Copy"}
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Issue Card ────────────────────────────────────────────────
function IssueCard({ issue, lang, index }: { issue: Issue; lang: Lang; index: number }) {
  const [open, setOpen] = useState(false);
  const sev      = (issue.severity || "LOW").toUpperCase();
  const itcRisk  = issue.itc_at_risk ?? issue.amount ?? 0;
  const problem  = getProblem(issue, lang);
  const fixSteps = getFixSteps(issue, lang);

  return (
    <div className={`border rounded-xl overflow-hidden transition-all ${SEV_WRAP[sev] ?? "bg-gray-50 border-gray-200"}`}>
      <button onClick={() => setOpen(!open)}
        className="w-full text-left p-4 flex items-start justify-between gap-3 hover:bg-black/[0.03] transition-colors">
        <div className="flex items-start gap-3 min-w-0">
          <div className="flex items-center gap-2 shrink-0">
            <div className={`w-2 h-2 rounded-full mt-1.5 ${SEV_DOT[sev] ?? "bg-gray-400"}`} />
            <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${SEV_BADGE[sev] ?? "bg-gray-400 text-white"}`}>
              {sev}
            </span>
          </div>
          <div className="min-w-0">
            <p className="font-semibold text-sm text-gray-900 truncate">
              {issue.invoice_number || issue.issue_type || "Issue"}
            </p>
            {(issue.party_name || issue.party_gstin) && (
              <p className="text-[11px] text-gray-500 mt-0.5 truncate">
                {issue.party_name || issue.party_gstin}
              </p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2.5 shrink-0">
          {itcRisk > 0 && (
            <div className="text-right">
              <p className="text-[10px] text-gray-400">ITC Risk</p>
              <p className="text-sm font-bold text-red-600">
                ₹{itcRisk >= 1000 ? `${(itcRisk / 1000).toFixed(0)}K` : itcRisk.toLocaleString("en-IN")}
              </p>
            </div>
          )}
          {open ? <ChevronUp size={15} className="text-gray-400" /> : <ChevronDown size={15} className="text-gray-400" />}
        </div>
      </button>

      {open && (
        <div className="px-4 pb-4 pt-3 border-t border-gray-200 space-y-3">
          {problem && (
            <p className="text-sm text-gray-700 leading-relaxed bg-white rounded-lg p-3 border border-gray-100">
              {problem}
            </p>
          )}
          {(issue.legal_ref || issue.penalty_risk) && (
            <div className="bg-white rounded-lg p-3 text-xs space-y-1.5 border border-gray-100">
              {issue.legal_ref && (
                <div className="flex items-start gap-1.5">
                  <span className="font-semibold text-gray-600 shrink-0">⚖️ Legal:</span>
                  <span className="text-gray-600">{issue.legal_ref}</span>
                </div>
              )}
              {issue.penalty_risk && (
                <div className="flex items-start gap-1.5">
                  <span className="font-semibold text-red-600 shrink-0">⚠️ Penalty:</span>
                  <span className="text-red-700">{issue.penalty_risk}</span>
                </div>
              )}
            </div>
          )}
          {fixSteps.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-gray-600 mb-2 flex items-center gap-1.5">
                <Zap size={11} className="text-blue-500" />
                {lang === "hi" ? "सुधार के कदम:" : lang === "mr" ? "दुरुस्तीचे टप्पे:" : "Steps to Fix:"}
              </p>
              <ol className="space-y-2">
                {fixSteps.map((step, i) => (
                  <li key={i} className="text-xs flex gap-2 text-gray-700 bg-white rounded-lg p-2.5 border border-gray-100">
                    <span className="w-5 h-5 rounded-full bg-blue-600 text-white text-[10px] font-bold flex items-center justify-center shrink-0">
                      {i + 1}
                    </span>
                    <span className="leading-relaxed">{step}</span>
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

// ── Main Page ─────────────────────────────────────────────────
export default function ReportPage() {
  const { user }                    = useUser();
  const { id }                      = useParams<{ id: string }>();
  const router                      = useRouter();
  const [data, setData]             = useState<AuditData | null>(null);
  const [loading, setLoading]       = useState(true);
  const [loadingMsg, setLoadingMsg] = useState("Loading report...");
  const [pdfLoading, setPdfLoading] = useState(false);
  const [lang, setLang]             = useState<Lang>("en");
  const [error, setError]           = useState("");

  useEffect(() => {
    if (!user || !id) return;

    // ── Guard: id "undefined" string se protect karo ─────────
    if (id === "undefined" || id === "null" || id.length < 8) {
      setError("Invalid report ID. Please run a new audit.");
      setLoading(false);
      return;
    }

    setAuthHeader(user.id);
    loadReport(id);
  }, [user, id]);

  const loadReport = async (reportId: string) => {
    try {
      setLoadingMsg("Loading report...");

      // Direct audit fetch try karo pehle
      const res = await getAudit(reportId);
      setData(res.data as AuditData);

    } catch (err: any) {
      // Agar 404 aaya — shayad ye task_id hai, audit_id nahi
      // Poll karo status se audit_id lene ke liye
      if (err?.response?.status === 404) {
        try {
          setLoadingMsg("Audit processing... please wait");
          const auditId = await pollForAuditId(reportId);
          const res = await getAudit(auditId);
          setData(res.data as AuditData);
          // URL bhi update karo sahi audit_id se
          router.replace(`/reports/${auditId}`);
        } catch (pollErr: any) {
          setError(pollErr?.message || "Report not found.");
        }
      } else {
        setError(err?.message || "Failed to load report.");
      }
    } finally {
      setLoading(false);
    }
  };

  // ── Poll task status → audit_id lao ──────────────────────
  const pollForAuditId = async (taskId: string): Promise<string> => {
    const MAX = 40;
    for (let i = 0; i < MAX; i++) {
      await new Promise(r => setTimeout(r, 3000));
      try {
        const res = await getAuditStatus(taskId);
        const { status, audit_id, result } = res.data;

        // audit_id directly ya result ke andar ho sakta hai
        const finalId = audit_id || result?.audit_id;

        if ((status === "completed" || status === "complete") && finalId) {
          return finalId;
        }
        if (status === "failed") {
          throw new Error(res.data.error || "Audit processing failed.");
        }
        setLoadingMsg(`Processing... (${i + 1}/${MAX})`);
      } catch (e: any) {
        if (e?.message?.includes("failed")) throw e;
      }
    }
    throw new Error("Audit timed out. Please try again.");
  };

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

  // ── Loading State ─────────────────────────────────────────
  if (loading) return (
    <div className="flex items-center justify-center min-h-screen bg-gray-50">
      <div className="text-center">
        <div className="w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto" />
        <p className="text-gray-500 mt-4 text-sm font-medium">{loadingMsg}</p>
      </div>
    </div>
  );

  // ── Error State ───────────────────────────────────────────
  if (error || !data) return (
    <div className="p-8 text-center">
      <AlertCircle size={44} className="text-gray-200 mx-auto mb-4" />
      <p className="text-gray-500 font-semibold">{error || "Report not found."}</p>
      <Link href="/upload"
        className="text-blue-600 mt-3 inline-flex items-center gap-1 hover:underline text-sm">
        Run a new audit <ExternalLink size={12} />
      </Link>
    </div>
  );

  const issues        = Array.isArray(data.issues_json) ? data.issues_json : Array.isArray(data.issues) ? data.issues : [];
  const totalInvoices = data.total_invoices ?? data.total_invoices_scanned ?? 0;
  const itcAtRisk     = data.itc_summary?.at_risk ?? data.itc_at_risk ?? 0;
  const critCount     = data.critical_count ?? issues.filter(i => i.severity?.toUpperCase() === "CRITICAL").length;
  const highCount     = data.high_count     ?? issues.filter(i => i.severity?.toUpperCase() === "HIGH").length;
  const medCount      = data.medium_count   ?? issues.filter(i => i.severity?.toUpperCase() === "MEDIUM").length;
  const lowCount      = data.low_count      ?? issues.filter(i => i.severity?.toUpperCase() === "LOW").length;

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-3xl mx-auto px-4 py-5 lg:py-8">

        <Link href="/reports"
          className="inline-flex items-center gap-1.5 text-gray-400 hover:text-gray-700 text-sm mb-5 transition-colors">
          <ArrowLeft size={14} /> All Reports
        </Link>

        {/* Summary Card */}
        <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden mb-5">
          <div className="bg-gradient-to-r from-slate-800 to-slate-700 px-5 lg:px-6 py-4 lg:py-5">
            <div className="flex items-start justify-between gap-3">
              <div>
                <h1 className="text-base lg:text-lg font-bold text-white">GST Audit Report</h1>
                <p className="text-slate-400 text-xs lg:text-sm">
                  {data.client_gstin_masked || "—"}{data.period ? ` · ${data.period}` : ""}
                </p>
              </div>
              <button onClick={handleDownload} disabled={pdfLoading}
                className="flex items-center gap-1.5 px-3 lg:px-4 py-2 bg-white/10 hover:bg-white/20 text-white text-xs lg:text-sm font-medium rounded-xl transition-all active:scale-95 disabled:opacity-60 backdrop-blur-sm border border-white/20">
                <Download size={13} />
                {pdfLoading ? "Generating..." : "Download PDF"}
              </button>
            </div>
          </div>

          <div className="p-4 lg:p-6">
            <div className="flex items-start gap-4 lg:gap-6">
              <div className="shrink-0">
                <ScoreRing score={data.compliance_score} />
                <p className="text-[10px] text-gray-400 text-center mt-1">Compliance</p>
              </div>
              <div className="flex-1 grid grid-cols-3 gap-3">
                {[
                  { value: totalInvoices, label: "Invoices", color: "text-gray-700" },
                  { value: issues.length, label: "Issues",   color: issues.length > 0 ? "text-red-600" : "text-green-600" },
                  {
                    value: itcAtRisk >= 1000
                      ? `₹${(itcAtRisk / 1000).toFixed(0)}K`
                      : `₹${itcAtRisk.toLocaleString("en-IN")}`,
                    label: "ITC Risk",
                    color: itcAtRisk > 0 ? "text-orange-600" : "text-gray-500",
                  },
                ].map((m, i) => (
                  <div key={i} className="bg-gray-50 rounded-xl p-3 text-center">
                    <p className={`text-xl lg:text-2xl font-bold ${m.color}`}>{m.value}</p>
                    <p className="text-[10px] text-gray-400 mt-0.5">{m.label}</p>
                  </div>
                ))}
              </div>
            </div>
            <div className="flex flex-wrap gap-2 mt-4">
              {[
                { label: "Critical", count: critCount, cls: "bg-red-100 text-red-700" },
                { label: "High",     count: highCount, cls: "bg-orange-100 text-orange-700" },
                { label: "Medium",   count: medCount,  cls: "bg-amber-100 text-amber-700" },
                { label: "Low",      count: lowCount,  cls: "bg-gray-100 text-gray-600" },
              ].filter(x => x.count > 0).map(({ label, count, cls }) => (
                <span key={label} className={`px-3 py-1 rounded-full text-xs font-semibold ${cls}`}>
                  {label}: {count}
                </span>
              ))}
            </div>
          </div>
        </div>

        {/* Language Toggle */}
        <div className="flex gap-2 mb-5">
          {(["en", "hi", "mr"] as Lang[]).map((l) => (
            <button key={l} onClick={() => setLang(l)}
              className={`px-3 lg:px-4 py-1.5 rounded-lg text-xs font-semibold border-2 transition-all active:scale-95 ${
                lang === l
                  ? "bg-blue-600 text-white border-blue-600"
                  : "bg-white text-gray-500 border-gray-200 hover:border-gray-300"
              }`}>
              {l === "en" ? "English" : l === "hi" ? "हिंदी" : "मराठी"}
            </button>
          ))}
        </div>

        {/* Notice Simulator */}
        {data.notice_simulation && (
          <NoticeSimulatorSection sim={data.notice_simulation} lang={lang} />
        )}

        {/* Issues */}
        {issues.length === 0 ? (
          <div className="bg-green-50 border-2 border-green-200 rounded-2xl p-10 text-center">
            <CheckCircle className="text-green-500 mx-auto mb-3" size={48} />
            <p className="font-bold text-green-700 text-lg">
              {lang === "hi" ? "कोई समस्या नहीं!" : lang === "mr" ? "कोणतीही समस्या नाही!" : "No issues found!"}
            </p>
            <p className="text-green-600 text-sm mt-1">
              {lang === "hi" ? "उत्कृष्ट GST अनुपालन" : lang === "mr" ? "उत्कृष्ट GST अनुपालन" : "Excellent GST compliance"}
            </p>
          </div>
        ) : (
          <div>
            <div className="flex items-center justify-between mb-3">
              <p className="text-sm font-semibold text-gray-700">
                {issues.length} {issues.length !== 1 ? "issues" : "issue"} found
              </p>
              <p className="text-xs text-gray-400">Tap to expand</p>
            </div>
            <div className="space-y-2.5">
              {issues.map((issue, i) => (
                <IssueCard key={i} issue={issue} lang={lang} index={i} />
              ))}
            </div>
          </div>
        )}

        <div className="h-6 lg:h-0" />
      </div>
    </div>
  );
}
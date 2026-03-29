"use client";

import { useEffect, useState, useMemo } from "react";
import { useUser } from "@clerk/nextjs";
import { useRouter } from "next/navigation";
import {
  Shield, ShieldAlert, ShieldCheck, ShieldX,
  Search, ChevronDown, ChevronUp,
  AlertTriangle, XCircle, Info,
  Building2, FileText,
} from "lucide-react";
import { getSupplierTrustScores, setAuthHeader } from "@/lib/api";

/* ── Types ──────────────────────────────────────────────── */
interface SupplierIssue {
  type: string;
  severity: string;
  description: string;
  invoice: string;
  amount: number;
  period: string;
  fix_steps: string;
}

interface SupplierData {
  gstin: string;
  gstin_masked: string;
  name: string;
  state_code: string;
  total_invoices: number;
  total_amount: number;
  total_tax: number;
  total_audits: number;
  trust_score: number;
  risk_level: "HIGH" | "MEDIUM" | "LOW";
  in_gstr2b: boolean;
  amount_mismatch: boolean;
  invalid_gstin: boolean;
  issues: SupplierIssue[];
  recommendation: string;
}

/* ── Score Ring ──────────────────────────────────────────── */
function ScoreRing({ score, size = 56 }: { score: number; size?: number }) {
  const radius = (size - 8) / 2;
  const circ = 2 * Math.PI * radius;
  const offset = circ - (score / 100) * circ;
  const color = score >= 70 ? "#10b981" : score >= 40 ? "#f59e0b" : "#ef4444";

  return (
    <svg width={size} height={size} className="transform -rotate-90 shrink-0">
      <circle cx={size/2} cy={size/2} r={radius} fill="none" stroke="#f1f5f9" strokeWidth="4" />
      <circle
        cx={size/2} cy={size/2} r={radius} fill="none" stroke={color} strokeWidth="4"
        strokeDasharray={circ} strokeDashoffset={offset} strokeLinecap="round"
        className="transition-all duration-1000"
      />
      <text
        x={size/2} y={size/2} textAnchor="middle" dominantBaseline="central"
        className="transform rotate-90 origin-center"
        fill={color} fontSize={size * 0.28} fontWeight="700"
      >{score}</text>
    </svg>
  );
}

/* ── Risk Badge ─────────────────────────────────────────── */
function RiskBadge({ level }: { level: string }) {
  const c: Record<string, { bg: string; text: string; Icon: any }> = {
    HIGH:   { bg: "bg-red-50 border-red-200",       text: "text-red-700",     Icon: ShieldX },
    MEDIUM: { bg: "bg-amber-50 border-amber-200",   text: "text-amber-700",   Icon: ShieldAlert },
    LOW:    { bg: "bg-emerald-50 border-emerald-200",text: "text-emerald-700", Icon: ShieldCheck },
  };
  const { bg, text, Icon } = c[level] || c.LOW;
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold border ${bg} ${text}`}>
      <Icon size={12} /> {level}
    </span>
  );
}

/* ── Main Page ───────────────────────────────────────────── */
export default function SupplierTrustPage() {
  const { user, isLoaded } = useUser();
  const router = useRouter();

  const [suppliers, setSuppliers] = useState<SupplierData[]>([]);
  const [stats, setStats] = useState({ high_risk: 0, medium_risk: 0, low_risk: 0, total_itc_risk: 0 });
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [filterRisk, setFilterRisk] = useState("all");
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [sortBy, setSortBy] = useState<"score" | "amount" | "invoices">("score");

  useEffect(() => {
    if (!isLoaded) return;
    if (!user) { router.push("/login"); return; }

    setAuthHeader(user.id);
    getSupplierTrustScores()
      .then((res) => {
        setSuppliers(res.data?.suppliers || []);
        setStats(res.data?.stats || { high_risk: 0, medium_risk: 0, low_risk: 0, total_itc_risk: 0 });
      })
      .catch((err) => console.error("Supplier load failed:", err))
      .finally(() => setLoading(false));
  }, [isLoaded, user, router]);

  /* ── Filter + Sort ────────────────────────────────────── */
  const filtered = useMemo(() => {
    let r = [...suppliers];
    if (search) {
      const q = search.toLowerCase();
      r = r.filter((s) => s.name.toLowerCase().includes(q) || s.gstin.toLowerCase().includes(q));
    }
    if (filterRisk !== "all") r = r.filter((s) => s.risk_level === filterRisk);
    if (sortBy === "score")    r.sort((a, b) => a.trust_score - b.trust_score);
    else if (sortBy === "amount") r.sort((a, b) => b.total_tax - a.total_tax);
    else r.sort((a, b) => b.total_invoices - a.total_invoices);
    return r;
  }, [suppliers, search, filterRisk, sortBy]);

  /* ── Loading ──────────────────────────────────────────── */
  if (!isLoaded || loading) {
    return (
      <div className="px-4 py-8 lg:p-8 animate-pulse">
        <div className="h-8 bg-gray-200 rounded w-64 mb-6" />
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {[1, 2, 3, 4].map((i) => <div key={i} className="h-24 bg-gray-100 rounded-xl" />)}
        </div>
      </div>
    );
  }

  return (
    <div className="px-4 py-5 lg:p-8 max-w-6xl mx-auto space-y-5 lg:space-y-6">

      {/* Header */}
      <div>
        <h1 className="text-xl lg:text-2xl font-bold text-gray-900 flex items-center gap-2">
          <Shield className="text-blue-600" size={22} />
          Supplier Trust Score
        </h1>
        <p className="text-sm text-gray-500 mt-1">
          Risk analysis based on your audit data — identify risky suppliers before filing
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <div className="bg-white rounded-xl border border-gray-100 p-4 shadow-sm">
          <div className="flex items-center gap-2 text-gray-500 text-xs font-medium mb-1">
            <Building2 size={14} /> Total Suppliers
          </div>
          <p className="text-2xl font-bold text-gray-900">{suppliers.length}</p>
        </div>
        <div className="bg-white rounded-xl border border-red-100 p-4 shadow-sm">
          <div className="flex items-center gap-2 text-red-500 text-xs font-medium mb-1">
            <ShieldX size={14} /> High Risk
          </div>
          <p className="text-2xl font-bold text-red-600">{stats.high_risk}</p>
        </div>
        <div className="bg-white rounded-xl border border-amber-100 p-4 shadow-sm">
          <div className="flex items-center gap-2 text-amber-500 text-xs font-medium mb-1">
            <ShieldAlert size={14} /> Medium Risk
          </div>
          <p className="text-2xl font-bold text-amber-600">{stats.medium_risk}</p>
        </div>
        <div className="bg-white rounded-xl border border-gray-100 p-4 shadow-sm">
          <div className="flex items-center gap-2 text-gray-500 text-xs font-medium mb-1">
            <AlertTriangle size={14} /> ITC at Risk
          </div>
          <p className="text-2xl font-bold text-gray-900">
            ₹{stats.total_itc_risk.toLocaleString("en-IN")}
          </p>
        </div>
      </div>

      {/* Search + Filter */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text" placeholder="Search supplier name or GSTIN..."
            value={search} onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-4 py-2.5 border border-gray-200 rounded-xl text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
          />
        </div>
        <div className="flex gap-2">
          {["all", "HIGH", "MEDIUM", "LOW"].map((lv) => (
            <button key={lv} onClick={() => setFilterRisk(lv)}
              className={`px-3 py-2 rounded-lg text-xs font-medium border transition-all active:scale-95 ${
                filterRisk === lv
                  ? "bg-blue-600 text-white border-blue-600"
                  : "bg-white text-gray-600 border-gray-200 hover:bg-gray-50"
              }`}
            >{lv === "all" ? "All" : lv}</button>
          ))}
        </div>
        <select value={sortBy} onChange={(e) => setSortBy(e.target.value as any)}
          className="px-3 py-2 border border-gray-200 rounded-lg text-xs font-medium bg-white text-gray-600 outline-none"
        >
          <option value="score">Sort: Trust Score</option>
          <option value="amount">Sort: ITC at Risk</option>
          <option value="invoices">Sort: Invoice Count</option>
        </select>
      </div>

      {/* Empty State */}
      {suppliers.length === 0 && !loading && (
        <div className="bg-white rounded-xl border border-gray-100 p-8 lg:p-12 text-center shadow-sm">
          <ShieldCheck size={48} className="mx-auto text-gray-300 mb-4" />
          <h3 className="font-semibold text-gray-900 text-lg mb-2">No Supplier Data Yet</h3>
          <p className="text-sm text-gray-500 mb-4">
            Run an audit with purchase invoices to see supplier trust scores
          </p>
          <button onClick={() => router.push("/upload")}
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 active:scale-95 transition-all"
          >
            <FileText size={16} /> Run New Audit
          </button>
        </div>
      )}

      {/* Supplier Cards */}
      {filtered.length > 0 && (
        <div className="space-y-3">
          <p className="text-xs text-gray-400 font-medium">
            {filtered.length} supplier{filtered.length !== 1 ? "s" : ""} found
          </p>

          {filtered.map((supplier) => {
            const uid = supplier.gstin + supplier.name;
            const isOpen = expandedId === uid;

            return (
              <div key={uid} className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden transition-all hover:shadow-md">

                {/* Header Row */}
                <button onClick={() => setExpandedId(isOpen ? null : uid)}
                  className="w-full flex items-center gap-3 lg:gap-4 p-4 text-left active:scale-[0.99] transition-transform"
                >
                  <ScoreRing score={supplier.trust_score} size={52} />

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <h3 className="font-semibold text-gray-900 text-sm truncate">{supplier.name}</h3>
                      <RiskBadge level={supplier.risk_level} />
                    </div>
                    <p className="text-xs text-gray-400 mt-0.5 font-mono">
                      {supplier.gstin_masked !== "N/A" ? supplier.gstin_masked : "GSTIN not available"}
                    </p>
                    <div className="flex items-center gap-3 mt-1 text-xs text-gray-500">
                      <span>{supplier.total_invoices} invoice{supplier.total_invoices !== 1 ? "s" : ""}</span>
                      <span>•</span>
                      <span>₹{supplier.total_tax.toLocaleString("en-IN")} at risk</span>
                      <span>•</span>
                      <span>{supplier.issues.length} issue{supplier.issues.length !== 1 ? "s" : ""}</span>
                    </div>
                  </div>

                  {/* Flags - Desktop */}
                  <div className="hidden sm:flex items-center gap-2">
                    {!supplier.in_gstr2b && (
                      <span className="flex items-center gap-1 px-2 py-1 bg-red-50 text-red-600 rounded-md text-xs font-medium border border-red-100">
                        <XCircle size={12} /> Not in 2B
                      </span>
                    )}
                    {supplier.amount_mismatch && (
                      <span className="flex items-center gap-1 px-2 py-1 bg-amber-50 text-amber-600 rounded-md text-xs font-medium border border-amber-100">
                        <AlertTriangle size={12} /> Mismatch
                      </span>
                    )}
                    {supplier.invalid_gstin && (
                      <span className="flex items-center gap-1 px-2 py-1 bg-red-50 text-red-600 rounded-md text-xs font-medium border border-red-100">
                        <XCircle size={12} /> Invalid
                      </span>
                    )}
                  </div>

                  {isOpen ? <ChevronUp size={18} className="text-gray-400 shrink-0" /> : <ChevronDown size={18} className="text-gray-400 shrink-0" />}
                </button>

                {/* Expanded Detail */}
                {isOpen && (
                  <div className="border-t border-gray-100 p-4 bg-gray-50/50 space-y-3">

                    {/* Mobile Flags */}
                    <div className="flex flex-wrap gap-2 sm:hidden">
                      {!supplier.in_gstr2b && (
                        <span className="flex items-center gap-1 px-2 py-1 bg-red-50 text-red-600 rounded-md text-xs font-medium border border-red-100">
                          <XCircle size={12} /> Not in GSTR-2B
                        </span>
                      )}
                      {supplier.amount_mismatch && (
                        <span className="flex items-center gap-1 px-2 py-1 bg-amber-50 text-amber-600 rounded-md text-xs font-medium border border-amber-100">
                          <AlertTriangle size={12} /> Amount Mismatch
                        </span>
                      )}
                      {supplier.invalid_gstin && (
                        <span className="flex items-center gap-1 px-2 py-1 bg-red-50 text-red-600 rounded-md text-xs font-medium border border-red-100">
                          <XCircle size={12} /> Invalid GSTIN
                        </span>
                      )}
                    </div>

                    {/* Quick Stats */}
                    <div className="grid grid-cols-3 gap-3">
                      <div className="bg-white rounded-lg p-3 border border-gray-100">
                        <p className="text-xs text-gray-400">Total Amount</p>
                        <p className="font-bold text-gray-900">₹{supplier.total_amount.toLocaleString("en-IN")}</p>
                      </div>
                      <div className="bg-white rounded-lg p-3 border border-gray-100">
                        <p className="text-xs text-gray-400">ITC at Risk</p>
                        <p className="font-bold text-red-600">₹{supplier.total_tax.toLocaleString("en-IN")}</p>
                      </div>
                      <div className="bg-white rounded-lg p-3 border border-gray-100">
                        <p className="text-xs text-gray-400">State Code</p>
                        <p className="font-bold text-gray-900">{supplier.state_code}</p>
                      </div>
                    </div>

                    {/* Issues */}
                    <div>
                      <h4 className="text-xs font-semibold text-gray-700 mb-2">Issues ({supplier.issues.length})</h4>
                      <div className="space-y-2">
                        {supplier.issues.map((issue, i) => (
                          <div key={i} className={`flex items-start gap-3 p-3 rounded-lg border text-sm ${
                            issue.severity === "critical" ? "bg-red-50/50 border-red-100" :
                            issue.severity === "high" ? "bg-amber-50/50 border-amber-100" :
                            "bg-gray-50 border-gray-100"
                          }`}>
                            {issue.severity === "critical" ? <XCircle size={16} className="text-red-500 mt-0.5 shrink-0" /> :
                             issue.severity === "high" ? <AlertTriangle size={16} className="text-amber-500 mt-0.5 shrink-0" /> :
                             <Info size={16} className="text-gray-400 mt-0.5 shrink-0" />}
                            <div className="flex-1 min-w-0">
                              <p className="text-gray-800 text-xs leading-relaxed">{issue.description || issue.type}</p>
                              <div className="flex items-center gap-3 mt-1 text-xs text-gray-400">
                                <span className="font-mono">{issue.invoice}</span>
                                {issue.amount > 0 && <span>₹{issue.amount.toLocaleString("en-IN")}</span>}
                                {issue.period && <span>{issue.period}</span>}
                              </div>
                              {issue.fix_steps && (
                                <p className="mt-1.5 text-xs text-blue-600 leading-relaxed">{issue.fix_steps}</p>
                              )}
                            </div>
                            <span className={`shrink-0 px-1.5 py-0.5 rounded text-[10px] font-bold uppercase ${
                              issue.severity === "critical" ? "bg-red-100 text-red-700" :
                              issue.severity === "high" ? "bg-amber-100 text-amber-700" :
                              "bg-gray-100 text-gray-600"
                            }`}>{issue.severity}</span>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Recommendation */}
                    <div className={`rounded-lg p-3 text-sm ${
                      supplier.trust_score < 40 ? "bg-red-50 border border-red-100" :
                      supplier.trust_score < 70 ? "bg-amber-50 border border-amber-100" :
                      "bg-emerald-50 border border-emerald-100"
                    }`}>
                      <p className="text-xs text-gray-700 leading-relaxed">{supplier.recommendation}</p>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* No Results */}
      {filtered.length === 0 && suppliers.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-100 p-8 text-center shadow-sm">
          <Search size={32} className="mx-auto text-gray-300 mb-3" />
          <p className="text-sm text-gray-500">No suppliers match your filters</p>
          <button onClick={() => { setSearch(""); setFilterRisk("all"); }}
            className="mt-3 text-sm text-blue-600 font-medium hover:underline"
          >Clear filters</button>
        </div>
      )}
    </div>
  );
}
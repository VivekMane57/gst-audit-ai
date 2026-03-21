"use client";
import { useEffect, useState } from "react";
import { useUser } from "@clerk/nextjs";
import { useRouter } from "next/navigation";
import { Download, Search, Filter, FileText, ArrowUpRight } from "lucide-react";
import { getReports, downloadPdf, setAuthHeader } from "@/lib/api";

interface Report {
  id: string; period?: string; compliance_score: number; risk_level?: string;
  total_invoices?: number; total_invoices_scanned?: number;
  itc_at_risk?: number; itc_summary?: { at_risk?: number };
  created_at?: string; client_name?: string; sector?: string; language?: string;
}

const scoreColor = (s: number) => s >= 80 ? "text-emerald-600" : s >= 60 ? "text-amber-500" : "text-red-500";
const scoreBg = (s: number) => s >= 80 ? "bg-emerald-50 text-emerald-700" : s >= 60 ? "bg-amber-50 text-amber-700" : "bg-red-50 text-red-600";
const riskBadge = (s: number) => s >= 80 ? "bg-emerald-50 text-emerald-700 border-emerald-200" : s >= 60 ? "bg-amber-50 text-amber-700 border-amber-200" : "bg-red-50 text-red-600 border-red-200";
const riskLabel = (s: number) => s >= 80 ? "Low" : s >= 60 ? "Medium" : "High";
const progressColor = (s: number) => s >= 80 ? "bg-emerald-500" : s >= 60 ? "bg-amber-400" : "bg-red-500";

export default function ReportsPage() {
  const { user } = useUser();
  const router = useRouter();
  const [reports, setReports] = useState<Report[]>([]);
  const [filtered, setFiltered] = useState<Report[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [riskFilter, setRiskFilter] = useState<"all"|"high"|"medium"|"low">("all");
  const [downloading, setDownloading] = useState<string|null>(null);

  useEffect(() => {
    if (!user) return;
    setAuthHeader(user.id);
    getReports().then(r => {
      const list = Array.isArray(r.data) ? r.data : r.data?.reports ?? [];
      const sorted = list.sort((a: Report, b: Report) => new Date(b.created_at||0).getTime() - new Date(a.created_at||0).getTime());
      setReports(sorted); setFiltered(sorted);
    }).catch(() => setReports([])).finally(() => setLoading(false));
  }, [user]);

  useEffect(() => {
    let r = [...reports];
    if (search.trim()) { const q = search.toLowerCase(); r = r.filter(x => x.client_name?.toLowerCase().includes(q) || x.period?.toLowerCase().includes(q) || x.sector?.toLowerCase().includes(q)); }
    if (riskFilter !== "all") r = r.filter(x => riskFilter === "high" ? x.compliance_score < 60 : riskFilter === "medium" ? x.compliance_score >= 60 && x.compliance_score < 80 : x.compliance_score >= 80);
    setFiltered(r);
  }, [search, riskFilter, reports]);

  const handleDownload = async (report: Report, e: React.MouseEvent) => {
    e.stopPropagation(); setDownloading(report.id);
    try {
      const res = await downloadPdf(report.id, report.language || "en");
      const url = URL.createObjectURL(new Blob([res.data], { type: "application/pdf" }));
      const a = document.createElement("a"); a.href = url;
      a.download = `GST_Audit_${report.period || report.id.slice(0,8)}.pdf`; a.click(); URL.revokeObjectURL(url);
    } catch { alert("PDF download failed."); } finally { setDownloading(null); }
  };

  const formatDate = (d?: string) => d ? new Date(d).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" }) : "—";
  const formatItc = (r: Report) => { const v = r.itc_summary?.at_risk ?? r.itc_at_risk ?? 0; return v >= 100000 ? `₹${(v/100000).toFixed(1)}L` : v >= 1000 ? `₹${(v/1000).toFixed(0)}K` : `₹${v}`; };

  return (
    <div className="px-4 py-5 lg:px-8 lg:py-8 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-5 lg:mb-6 animate-fade-in">
        <div>
          <h1 className="text-2xl lg:text-3xl font-bold text-slate-900 tracking-tight">Reports</h1>
          <p className="text-slate-500 text-xs lg:text-sm mt-0.5">{reports.length} audit{reports.length !== 1 ? "s" : ""} total</p>
        </div>
        <button onClick={() => router.push("/upload")}
          className="flex items-center gap-1.5 brand-gradient text-white text-xs lg:text-sm font-semibold px-4 py-2.5 rounded-xl btn-press shadow-sm shadow-blue-600/20">
          + New Audit
        </button>
      </div>

      {/* Search + Filters */}
      <div className="flex flex-col sm:flex-row gap-3 mb-5 animate-slide-up">
        <div className="flex-1 relative">
          <Search size={15} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
          <input type="text" placeholder="Search by client, period, sector..." value={search}
            onChange={e => setSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 border border-slate-200 rounded-xl text-sm bg-white focus:outline-none transition-all" />
        </div>
        <div className="flex items-center gap-1.5 overflow-x-auto scrollbar-hide">
          <Filter size={14} className="text-slate-400 shrink-0 ml-0.5" />
          {(["all","high","medium","low"] as const).map(f => (
            <button key={f} onClick={() => setRiskFilter(f)}
              className={`px-3 py-2 rounded-xl text-xs font-semibold border transition-all capitalize shrink-0 btn-press
                ${riskFilter === f ? "brand-gradient text-white border-blue-600 shadow-sm" : "bg-white text-slate-600 border-slate-200 hover:border-slate-300"}`}>
              {f === "all" ? "All" : f}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      {loading ? (
        <div className="space-y-3">{[1,2,3].map(i => <div key={i} className="h-16 animate-shimmer rounded-xl" />)}</div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-16 bg-white border border-slate-200 rounded-2xl shadow-sm">
          <div className="w-14 h-14 bg-slate-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <FileText size={24} className="text-slate-300" />
          </div>
          <p className="text-slate-500 font-medium">{reports.length === 0 ? "No audits yet" : "No results found"}</p>
          {reports.length === 0 && (
            <button onClick={() => router.push("/upload")} className="text-blue-600 text-xs mt-2 hover:underline font-medium">Run your first audit →</button>
          )}
        </div>
      ) : (
        <>
          {/* Desktop table */}
          <div className="hidden lg:block bg-white border border-slate-200 rounded-2xl overflow-hidden shadow-sm animate-slide-up">
            <div className="grid grid-cols-12 gap-4 px-6 py-3.5 bg-slate-50 border-b border-slate-100 text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
              <div className="col-span-3">Client / Period</div>
              <div className="col-span-2">Score</div>
              <div className="col-span-2">Risk</div>
              <div className="col-span-2">ITC at Risk</div>
              <div className="col-span-2">Date</div>
              <div className="col-span-1"></div>
            </div>
            {filtered.map((r, i) => (
              <div key={r.id} onClick={() => router.push(`/reports/${r.id}`)}
                className={`grid grid-cols-12 gap-4 px-6 py-4 items-center cursor-pointer hover:bg-blue-50/30 transition-colors group ${i < filtered.length - 1 ? "border-b border-slate-100" : ""}`}>
                <div className="col-span-3 min-w-0">
                  <p className="text-sm font-semibold text-slate-900 truncate group-hover:text-blue-600 transition-colors">{r.client_name || "Audit"}</p>
                  <p className="text-xs text-slate-400 mt-0.5">{r.period || "—"}{r.sector ? ` · ${r.sector.replace("_"," ")}` : ""}</p>
                </div>
                <div className="col-span-2">
                  <p className={`text-xl font-bold ${scoreColor(r.compliance_score)}`}>{r.compliance_score}</p>
                  <div className="w-full bg-slate-100 rounded-full h-1 mt-1.5">
                    <div className={`h-1 rounded-full ${progressColor(r.compliance_score)}`} style={{ width: `${r.compliance_score}%` }} />
                  </div>
                </div>
                <div className="col-span-2">
                  <span className={`px-2.5 py-1 rounded-full text-[11px] font-bold border ${riskBadge(r.compliance_score)}`}>
                    {riskLabel(r.compliance_score)} Risk
                  </span>
                </div>
                <div className="col-span-2">
                  <p className="text-sm font-bold text-amber-600">{formatItc(r)}</p>
                  <p className="text-[11px] text-slate-400">{(r.total_invoices ?? r.total_invoices_scanned ?? 0)} invoices</p>
                </div>
                <div className="col-span-2"><p className="text-xs text-slate-500">{formatDate(r.created_at)}</p></div>
                <div className="col-span-1 flex justify-end gap-1">
                  <button onClick={e => handleDownload(r, e)} disabled={downloading === r.id}
                    className="p-2 rounded-lg hover:bg-slate-100 text-slate-400 hover:text-slate-600 transition-colors">
                    <Download size={14} className={downloading === r.id ? "animate-bounce" : ""} />
                  </button>
                  <ArrowUpRight size={14} className="text-slate-300 mt-2" />
                </div>
              </div>
            ))}
          </div>

          {/* Mobile cards */}
          <div className="lg:hidden space-y-2.5 animate-slide-up">
            {filtered.map(r => (
              <div key={r.id} onClick={() => router.push(`/reports/${r.id}`)}
                className="bg-white border border-slate-200 rounded-2xl p-4 active:bg-slate-50 transition-all shadow-sm">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <div className={`w-11 h-11 rounded-xl flex items-center justify-center font-bold text-sm score-ring ${scoreBg(r.compliance_score)}`}>
                      {r.compliance_score}
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-slate-900 truncate">{r.client_name || "Audit"}</p>
                      <p className="text-[11px] text-slate-400">{r.period || "—"}{r.sector ? ` · ${r.sector.replace("_"," ")}` : ""}</p>
                    </div>
                  </div>
                  <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold border shrink-0 ${riskBadge(r.compliance_score)}`}>
                    {riskLabel(r.compliance_score)}
                  </span>
                </div>
                <div className="flex items-center justify-between text-xs text-slate-400 pt-2.5 border-t border-slate-100">
                  <span className="font-bold text-amber-600">{formatItc(r)}</span>
                  <span>{(r.total_invoices ?? r.total_invoices_scanned ?? 0)} invoices</span>
                  <span>{formatDate(r.created_at)}</span>
                  <button onClick={e => handleDownload(r, e)} className="p-1 text-slate-400 hover:text-slate-600">
                    <Download size={13} />
                  </button>
                </div>
              </div>
            ))}
          </div>

          {/* Summary */}
          <div className="mt-4 flex flex-wrap gap-4 text-[11px] text-slate-400 px-1 font-medium">
            <span>{filtered.length} reports</span>
            <span>Avg: {Math.round(filtered.reduce((s,r) => s + r.compliance_score, 0) / filtered.length)}</span>
            <span>ITC: ₹{(filtered.reduce((s,r) => s + (r.itc_summary?.at_risk ?? r.itc_at_risk ?? 0), 0) / 1000).toFixed(0)}K</span>
          </div>
        </>
      )}
    </div>
  );
}
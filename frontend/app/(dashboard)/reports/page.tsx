"use client";
import { useEffect, useState } from "react";
import { useUser } from "@clerk/nextjs";
import { useRouter } from "next/navigation";
import { Download, Search, Filter, FileText } from "lucide-react";
import { getReports, downloadPdf, setAuthHeader } from "@/lib/api";

interface Report {
  id:               string;
  period?:          string;
  compliance_score: number;
  risk_level?:      string;
  total_invoices?:  number;
  total_invoices_scanned?: number;
  itc_at_risk?:     number;
  itc_summary?:     { at_risk?: number };
  created_at?:      string;
  client_name?:     string;
  sector?:          string;
  language?:        string;
}

const scoreColor = (s: number) =>
  s >= 80 ? "text-green-600" : s >= 60 ? "text-yellow-600" : "text-red-600";
const scoreBg = (s: number) =>
  s >= 80 ? "bg-green-100" : s >= 60 ? "bg-yellow-100" : "bg-red-100";
const riskBadge = (s: number) =>
  s >= 80 ? "bg-green-100 text-green-700" : s >= 60 ? "bg-yellow-100 text-yellow-700" : "bg-red-100 text-red-700";
const riskLabel = (s: number) =>
  s >= 80 ? "Low" : s >= 60 ? "Medium" : "High";

export default function ReportsPage() {
  const { user } = useUser();
  const router = useRouter();

  const [reports, setReports] = useState<Report[]>([]);
  const [filtered, setFiltered] = useState<Report[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [riskFilter, setRiskFilter] = useState<"all" | "high" | "medium" | "low">("all");
  const [downloading, setDownloading] = useState<string | null>(null);

  useEffect(() => {
    if (!user) return;
    setAuthHeader(user.id);
    getReports()
      .then((r) => {
        const list = Array.isArray(r.data) ? r.data : r.data?.reports ?? [];
        const sorted = list.sort((a: Report, b: Report) =>
          new Date(b.created_at || 0).getTime() - new Date(a.created_at || 0).getTime()
        );
        setReports(sorted);
        setFiltered(sorted);
      })
      .catch(() => setReports([]))
      .finally(() => setLoading(false));
  }, [user]);

  useEffect(() => {
    let result = [...reports];
    if (search.trim()) {
      const q = search.toLowerCase();
      result = result.filter(r =>
        r.client_name?.toLowerCase().includes(q) ||
        r.period?.toLowerCase().includes(q) ||
        r.sector?.toLowerCase().includes(q)
      );
    }
    if (riskFilter !== "all") {
      result = result.filter(r => {
        if (riskFilter === "high") return r.compliance_score < 60;
        if (riskFilter === "medium") return r.compliance_score >= 60 && r.compliance_score < 80;
        if (riskFilter === "low") return r.compliance_score >= 80;
        return true;
      });
    }
    setFiltered(result);
  }, [search, riskFilter, reports]);

  const handleDownload = async (report: Report, e: React.MouseEvent) => {
    e.stopPropagation();
    setDownloading(report.id);
    try {
      const res = await downloadPdf(report.id, report.language || "en");
      const url = URL.createObjectURL(new Blob([res.data], { type: "application/pdf" }));
      const a = document.createElement("a");
      a.href = url;
      a.download = `GST_Audit_${report.period || report.id.slice(0, 8)}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      alert("PDF download failed.");
    } finally {
      setDownloading(null);
    }
  };

  const formatDate = (d?: string) => {
    if (!d) return "—";
    return new Date(d).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
  };

  const formatItc = (r: Report) => {
    const v = r.itc_summary?.at_risk ?? r.itc_at_risk ?? 0;
    if (v >= 100000) return `₹${(v / 100000).toFixed(1)}L`;
    if (v >= 1000) return `₹${(v / 1000).toFixed(0)}K`;
    return `₹${v}`;
  };

  return (
    <div className="px-4 py-5 lg:p-8 max-w-5xl mx-auto">

      {/* Header */}
      <div className="flex items-center justify-between mb-5 lg:mb-6">
        <div>
          <h1 className="text-xl lg:text-2xl font-bold text-gray-900">Reports</h1>
          <p className="text-gray-500 text-xs lg:text-sm mt-0.5">
            {reports.length} audit{reports.length !== 1 ? "s" : ""} total
          </p>
        </div>
        <button
          onClick={() => router.push("/upload")}
          className="flex items-center gap-1.5 bg-blue-600 text-white text-xs lg:text-sm font-semibold px-3 lg:px-4 py-2 lg:py-2.5 rounded-xl hover:bg-blue-700 active:scale-95 transition-transform"
        >
          + New Audit
        </button>
      </div>

      {/* Search + Filters */}
      <div className="flex flex-col sm:flex-row gap-3 mb-5 lg:mb-6">
        <div className="flex-1 relative">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Search by client, period, sector..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="w-full pl-9 pr-4 py-2.5 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div className="flex items-center gap-1.5 overflow-x-auto">
          <Filter size={14} className="text-gray-400 shrink-0" />
          {(["all", "high", "medium", "low"] as const).map(f => (
            <button
              key={f}
              onClick={() => setRiskFilter(f)}
              className={`px-2.5 lg:px-3 py-2 rounded-xl text-xs font-medium border transition-all capitalize shrink-0 active:scale-95 ${
                riskFilter === f
                  ? "bg-blue-600 text-white border-blue-600"
                  : "bg-white text-gray-600 border-gray-200"
              }`}
            >
              {f === "all" ? "All" : `${f}`}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3].map(i => <div key={i} className="h-16 bg-gray-100 rounded-xl animate-pulse" />)}
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-16 bg-white border border-gray-200 rounded-xl">
          <FileText size={36} className="text-gray-200 mx-auto mb-3" />
          <p className="text-gray-500 font-medium text-sm">
            {reports.length === 0 ? "No audits yet" : "No results found"}
          </p>
          {reports.length === 0 && (
            <button onClick={() => router.push("/upload")} className="text-blue-600 text-xs mt-2 hover:underline">
              Run your first audit →
            </button>
          )}
        </div>
      ) : (
        <>
          {/* Desktop table */}
          <div className="hidden lg:block bg-white border border-gray-200 rounded-2xl overflow-hidden">
            <div className="grid grid-cols-12 gap-4 px-5 py-3 bg-gray-50 border-b border-gray-100 text-xs font-medium text-gray-500 uppercase tracking-wide">
              <div className="col-span-3">Client / Period</div>
              <div className="col-span-2">Score</div>
              <div className="col-span-2">Risk</div>
              <div className="col-span-2">ITC at Risk</div>
              <div className="col-span-2">Date</div>
              <div className="col-span-1"></div>
            </div>
            {filtered.map((r, i) => (
              <div
                key={r.id}
                onClick={() => router.push(`/reports/${r.id}`)}
                className={`grid grid-cols-12 gap-4 px-5 py-4 items-center cursor-pointer hover:bg-gray-50 transition-colors ${
                  i < filtered.length - 1 ? "border-b border-gray-100" : ""
                }`}
              >
                <div className="col-span-3 min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate">{r.client_name || "Audit"}</p>
                  <p className="text-xs text-gray-400 mt-0.5">{r.period || "—"}{r.sector ? ` · ${r.sector.replace("_", " ")}` : ""}</p>
                </div>
                <div className="col-span-2">
                  <p className={`text-lg font-bold ${scoreColor(r.compliance_score)}`}>{r.compliance_score}</p>
                  <div className="w-full bg-gray-100 rounded-full h-1 mt-1">
                    <div className={`h-1 rounded-full ${r.compliance_score >= 80 ? "bg-green-500" : r.compliance_score >= 60 ? "bg-yellow-500" : "bg-red-500"}`} style={{ width: `${r.compliance_score}%` }} />
                  </div>
                </div>
                <div className="col-span-2">
                  <span className={`px-2.5 py-1 rounded-full text-xs font-semibold ${riskBadge(r.compliance_score)}`}>{riskLabel(r.compliance_score)} Risk</span>
                </div>
                <div className="col-span-2">
                  <p className="text-sm font-semibold text-orange-600">{formatItc(r)}</p>
                  <p className="text-xs text-gray-400">{(r.total_invoices ?? r.total_invoices_scanned ?? 0)} invoices</p>
                </div>
                <div className="col-span-2">
                  <p className="text-xs text-gray-500">{formatDate(r.created_at)}</p>
                </div>
                <div className="col-span-1 flex justify-end">
                  <button onClick={(e) => handleDownload(r, e)} disabled={downloading === r.id} className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-400">
                    <Download size={14} className={downloading === r.id ? "animate-bounce" : ""} />
                  </button>
                </div>
              </div>
            ))}
          </div>

          {/* Mobile card list */}
          <div className="lg:hidden space-y-2.5">
            {filtered.map((r) => (
              <div
                key={r.id}
                onClick={() => router.push(`/reports/${r.id}`)}
                className="bg-white border border-gray-200 rounded-xl p-4 active:bg-gray-50 transition-colors"
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2.5">
                    <div className={`w-10 h-10 rounded-xl flex items-center justify-center font-bold text-sm ${scoreBg(r.compliance_score)} ${scoreColor(r.compliance_score)}`}>
                      {r.compliance_score}
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-gray-900 truncate">{r.client_name || "Audit"}</p>
                      <p className="text-xs text-gray-400">{r.period || "—"}{r.sector ? ` · ${r.sector.replace("_", " ")}` : ""}</p>
                    </div>
                  </div>
                  <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold shrink-0 ${riskBadge(r.compliance_score)}`}>
                    {riskLabel(r.compliance_score)}
                  </span>
                </div>
                <div className="flex items-center justify-between text-xs text-gray-400 pt-2 border-t border-gray-100">
                  <span className="font-semibold text-orange-600">{formatItc(r)}</span>
                  <span>{(r.total_invoices ?? r.total_invoices_scanned ?? 0)} invoices</span>
                  <span>{formatDate(r.created_at)}</span>
                  <button onClick={(e) => handleDownload(r, e)} disabled={downloading === r.id} className="p-1 text-gray-400">
                    <Download size={13} />
                  </button>
                </div>
              </div>
            ))}
          </div>

          {/* Summary */}
          <div className="mt-4 flex flex-wrap gap-3 lg:gap-6 text-[10px] lg:text-xs text-gray-400 px-1">
            <span>{filtered.length} reports</span>
            <span>Avg: {Math.round(filtered.reduce((s, r) => s + r.compliance_score, 0) / filtered.length)}</span>
            <span>ITC: ₹{(filtered.reduce((s, r) => s + (r.itc_summary?.at_risk ?? r.itc_at_risk ?? 0), 0) / 1000).toFixed(0)}K</span>
          </div>
        </>
      )}
    </div>
  );
}
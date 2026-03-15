"use client";
import { useEffect, useState } from "react";
import { useUser } from "@clerk/nextjs";
import { useRouter } from "next/navigation";
import { Download, Search, Filter, ArrowRight, FileText } from "lucide-react";
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

const riskBadge = (s: number) =>
  s >= 80 ? "bg-green-100 text-green-700"
  : s >= 60 ? "bg-yellow-100 text-yellow-700"
  : "bg-red-100 text-red-700";

const riskLabel = (s: number) =>
  s >= 80 ? "Low" : s >= 60 ? "Medium" : "High";

export default function ReportsPage() {
  const { user }   = useUser();
  const router     = useRouter();

  const [reports,     setReports]     = useState<Report[]>([]);
  const [filtered,    setFiltered]    = useState<Report[]>([]);
  const [loading,     setLoading]     = useState(true);
  const [search,      setSearch]      = useState("");
  const [riskFilter,  setRiskFilter]  = useState<"all" | "high" | "medium" | "low">("all");
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

  // ── Filter logic ────────────────────────────────────────────
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
        if (riskFilter === "high")   return r.compliance_score < 60;
        if (riskFilter === "medium") return r.compliance_score >= 60 && r.compliance_score < 80;
        if (riskFilter === "low")    return r.compliance_score >= 80;
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
      const a   = document.createElement("a");
      a.href     = url;
      a.download = `GST_Audit_${report.period || report.id.slice(0, 8)}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      alert("PDF download failed. Please try again.");
    } finally {
      setDownloading(null);
    }
  };

  const formatDate = (d?: string) => {
    if (!d) return "—";
    return new Date(d).toLocaleDateString("en-IN", {
      day: "numeric", month: "short", year: "numeric"
    });
  };

  const formatItc = (r: Report) => {
    const v = r.itc_summary?.at_risk ?? r.itc_at_risk ?? 0;
    if (v >= 100000) return `₹${(v / 100000).toFixed(1)}L`;
    if (v >= 1000)   return `₹${(v / 1000).toFixed(0)}K`;
    return `₹${v}`;
  };

  return (
    <div className="p-8 max-w-5xl mx-auto">

      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Reports</h1>
          <p className="text-gray-500 text-sm mt-1">
            {reports.length} audit{reports.length !== 1 ? "s" : ""} total
          </p>
        </div>
        <button
          onClick={() => router.push("/upload")}
          className="flex items-center gap-2 bg-blue-600 text-white text-sm font-semibold px-4 py-2.5 rounded-xl hover:bg-blue-700"
        >
          + New Audit
        </button>
      </div>

      {/* Search + Filters */}
      <div className="flex gap-3 mb-6">
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
        <div className="flex items-center gap-2">
          <Filter size={14} className="text-gray-400" />
          {(["all", "high", "medium", "low"] as const).map(f => (
            <button
              key={f}
              onClick={() => setRiskFilter(f)}
              className={`px-3 py-2 rounded-xl text-xs font-medium border transition-all capitalize ${
                riskFilter === f
                  ? "bg-blue-600 text-white border-blue-600"
                  : "bg-white text-gray-600 border-gray-200 hover:border-gray-300"
              }`}
            >
              {f === "all" ? "All" : `${f} risk`}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      {loading ? (
        <div className="space-y-3">
          {[1,2,3,4,5].map(i => (
            <div key={i} className="h-16 bg-gray-100 rounded-2xl animate-pulse" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-20 bg-white border border-gray-200 rounded-2xl">
          <FileText size={40} className="text-gray-200 mx-auto mb-3" />
          <p className="text-gray-500 font-medium">
            {reports.length === 0 ? "No audits yet" : "No results found"}
          </p>
          {reports.length === 0 && (
            <button
              onClick={() => router.push("/upload")}
              className="text-blue-600 text-sm mt-2 hover:underline"
            >
              Run your first audit →
            </button>
          )}
        </div>
      ) : (
        <div className="bg-white border border-gray-200 rounded-2xl overflow-hidden">
          {/* Table header */}
          <div className="grid grid-cols-12 gap-4 px-5 py-3 bg-gray-50 border-b border-gray-100 text-xs font-medium text-gray-500 uppercase tracking-wide">
            <div className="col-span-3">Client / Period</div>
            <div className="col-span-2">Score</div>
            <div className="col-span-2">Risk</div>
            <div className="col-span-2">ITC at Risk</div>
            <div className="col-span-2">Date</div>
            <div className="col-span-1"></div>
          </div>

          {/* Rows */}
          {filtered.map((r, i) => (
            <div
              key={r.id}
              onClick={() => router.push(`/reports/${r.id}`)}
              className={`grid grid-cols-12 gap-4 px-5 py-4 items-center cursor-pointer hover:bg-gray-50 transition-colors ${
                i < filtered.length - 1 ? "border-b border-gray-100" : ""
              }`}
            >
              {/* Client / Period */}
              <div className="col-span-3 min-w-0">
                <p className="text-sm font-medium text-gray-900 truncate">
                  {r.client_name || "Audit"}
                </p>
                <p className="text-xs text-gray-400 mt-0.5">
                  {r.period || "—"}
                  {r.sector ? ` · ${r.sector.replace("_", " ")}` : ""}
                </p>
              </div>

              {/* Score */}
              <div className="col-span-2">
                <p className={`text-lg font-bold ${scoreColor(r.compliance_score)}`}>
                  {r.compliance_score}
                </p>
                <div className="w-full bg-gray-100 rounded-full h-1 mt-1">
                  <div
                    className={`h-1 rounded-full ${r.compliance_score >= 80 ? "bg-green-500" : r.compliance_score >= 60 ? "bg-yellow-500" : "bg-red-500"}`}
                    style={{ width: `${r.compliance_score}%` }}
                  />
                </div>
              </div>

              {/* Risk */}
              <div className="col-span-2">
                <span className={`px-2.5 py-1 rounded-full text-xs font-semibold ${riskBadge(r.compliance_score)}`}>
                  {riskLabel(r.compliance_score)} Risk
                </span>
              </div>

              {/* ITC at Risk */}
              <div className="col-span-2">
                <p className="text-sm font-semibold text-orange-600">{formatItc(r)}</p>
                <p className="text-xs text-gray-400">
                  {(r.total_invoices ?? r.total_invoices_scanned ?? 0)} invoices
                </p>
              </div>

              {/* Date */}
              <div className="col-span-2">
                <p className="text-xs text-gray-500">{formatDate(r.created_at)}</p>
              </div>

              {/* Actions */}
              <div className="col-span-1 flex items-center justify-end gap-1">
                <button
                  onClick={(e) => handleDownload(r, e)}
                  disabled={downloading === r.id}
                  className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-400 hover:text-gray-600 transition-colors"
                  title="Download PDF"
                >
                  <Download size={14} className={downloading === r.id ? "animate-bounce" : ""} />
                </button>
                <ArrowRight size={14} className="text-gray-300" />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Summary footer */}
      {filtered.length > 0 && (
        <div className="mt-4 flex gap-6 text-xs text-gray-400 px-1">
          <span>{filtered.length} reports shown</span>
          <span>
            Avg score: {Math.round(filtered.reduce((s, r) => s + r.compliance_score, 0) / filtered.length)}
          </span>
          <span>
            Total ITC at risk: ₹{(
              filtered.reduce((s, r) => s + (r.itc_summary?.at_risk ?? r.itc_at_risk ?? 0), 0) / 1000
            ).toFixed(0)}K
          </span>
        </div>
      )}
    </div>
  );
}
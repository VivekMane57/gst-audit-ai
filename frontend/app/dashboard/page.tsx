"use client";
import { useEffect, useState } from "react";
import { useUser } from "@clerk/nextjs";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Upload, Users, TrendingUp, AlertTriangle, ArrowRight, RefreshCw } from "lucide-react";
import { getClients, getReports, setAuthHeader } from "@/lib/api";

interface Client {
  id:             string;
  business_name:  string;
  gstin_masked?:  string;
  sector?:        string;
  last_score?:    number;
  last_audit_at?: string;
}

interface Report {
  id:               string;
  period?:          string;
  compliance_score: number;
  risk_level?:      string;
  total_invoices?:  number;
  itc_at_risk?:     number;
  itc_summary?:     { at_risk?: number };
  created_at?:      string;
  client_name?:     string;
  sector?:          string;
}

const scoreColor = (s: number) =>
  s >= 80 ? "text-green-600" : s >= 60 ? "text-yellow-600" : "text-red-600";

const scoreBg = (s: number) =>
  s >= 80 ? "bg-green-100" : s >= 60 ? "bg-yellow-100" : "bg-red-100";

const riskBadge = (s: number) =>
  s >= 80
    ? "bg-green-100 text-green-700"
    : s >= 60
    ? "bg-yellow-100 text-yellow-700"
    : "bg-red-100 text-red-700";

const riskLabel = (s: number) =>
  s >= 80 ? "Low Risk" : s >= 60 ? "Medium" : "High Risk";

function ScoreBar({ score }: { score: number }) {
  return (
    <div className="w-full bg-gray-100 rounded-full h-1.5 mt-1">
      <div
        className={`h-1.5 rounded-full ${score >= 80 ? "bg-green-500" : score >= 60 ? "bg-yellow-500" : "bg-red-500"}`}
        style={{ width: `${score}%` }}
      />
    </div>
  );
}

export default function DashboardPage() {
  const { user, isLoaded } = useUser();
  const router = useRouter();

  const [clients,  setClients]  = useState<Client[]>([]);
  const [reports,  setReports]  = useState<Report[]>([]);
  const [loading,  setLoading]  = useState(true);
  const [refresh,  setRefresh]  = useState(0);

  useEffect(() => {
    if (!isLoaded || !user) return;

    setAuthHeader(user.id);
    setLoading(true);

    Promise.all([
      getClients().catch(() => ({ data: { clients: [] } })),
      getReports().catch(() => ({ data: { reports: [] } })),
    ]).then(([c, r]) => {
      setClients(Array.isArray(c.data) ? c.data : c.data?.clients ?? []);
      const rList = Array.isArray(r.data) ? r.data : r.data?.reports ?? [];
      setReports(rList.sort((a: Report, b: Report) =>
        new Date(b.created_at || 0).getTime() - new Date(a.created_at || 0).getTime()
      ));
    }).finally(() => setLoading(false));
  }, [isLoaded, user, refresh]);

  const totalClients  = clients.length;
  const avgScore      = reports.length
    ? Math.round(reports.reduce((s, r) => s + r.compliance_score, 0) / reports.length)
    : null;
  const highRiskCount = reports.filter(r => r.compliance_score < 60).length;
  const totalItcRisk  = reports.reduce((s, r) =>
    s + (r.itc_summary?.at_risk ?? r.itc_at_risk ?? 0), 0
  );
  const recentReports = reports.slice(0, 5);

  if (!isLoaded) return (
    <div className="flex items-center justify-center min-h-64">
      <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
    </div>
  );

  const formatItc = () => {
    if (loading) return "—";
    if (totalItcRisk >= 100000) return `₹${(totalItcRisk / 100000).toFixed(1)}L`;
    if (totalItcRisk >= 1000) return `₹${(totalItcRisk / 1000).toFixed(0)}K`;
    return `₹${totalItcRisk}`;
  };

  return (
    <div className="px-4 py-5 lg:p-8 max-w-5xl mx-auto">

      {/* ── Header ── */}
      <div className="flex items-start justify-between mb-5 lg:mb-8">
        <div>
          <h1 className="text-xl lg:text-2xl font-bold text-gray-900">
            Welcome back, {user?.firstName || "CA"} 👋
          </h1>
          <p className="text-gray-500 mt-0.5 text-xs lg:text-sm">GST compliance overview</p>
        </div>
        <button
          onClick={() => setRefresh(r => r + 1)}
          className="flex items-center gap-1.5 text-gray-400 hover:text-gray-600 text-xs mt-1"
        >
          <RefreshCw size={13} className={loading ? "animate-spin" : ""} />
          <span className="hidden sm:inline">Refresh</span>
        </button>
      </div>

      {/* ── Stats: Vertical list on mobile, 4-col grid on desktop ── */}

      {/* MOBILE — vertical list inside one card */}
      <div className="lg:hidden bg-white border border-gray-200 rounded-xl mb-5 divide-y divide-gray-100">
        <div className="flex items-center justify-between px-4 py-3.5">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-blue-50 rounded-lg flex items-center justify-center">
              <Users size={15} className="text-blue-600" />
            </div>
            <span className="text-sm text-gray-700 font-medium">Total Clients</span>
          </div>
          <span className="text-lg font-bold text-gray-900">{loading ? "—" : totalClients}</span>
        </div>

        <div className="flex items-center justify-between px-4 py-3.5">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-green-50 rounded-lg flex items-center justify-center">
              <TrendingUp size={15} className="text-green-600" />
            </div>
            <span className="text-sm text-gray-700 font-medium">Avg Score</span>
          </div>
          <span className={`text-lg font-bold ${avgScore ? scoreColor(avgScore) : "text-gray-400"}`}>
            {loading ? "—" : avgScore ?? "N/A"}
          </span>
        </div>

        <div className="flex items-center justify-between px-4 py-3.5">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-red-50 rounded-lg flex items-center justify-center">
              <AlertTriangle size={15} className="text-red-500" />
            </div>
            <span className="text-sm text-gray-700 font-medium">High Risk</span>
          </div>
          <span className={`text-lg font-bold ${highRiskCount > 0 ? "text-red-600" : "text-green-600"}`}>
            {loading ? "—" : highRiskCount}
          </span>
        </div>

        <div className="flex items-center justify-between px-4 py-3.5">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-orange-50 rounded-lg flex items-center justify-center">
              <span className="text-orange-600 font-bold text-xs">₹</span>
            </div>
            <span className="text-sm text-gray-700 font-medium">ITC at Risk</span>
          </div>
          <span className="text-lg font-bold text-orange-600">{formatItc()}</span>
        </div>
      </div>

      {/* DESKTOP — 4-col grid (same as original) */}
      <div className="hidden lg:grid grid-cols-4 gap-4 mb-8">
        <div className="bg-white border border-gray-200 rounded-2xl p-5">
          <div className="flex items-center justify-between mb-3">
            <p className="text-sm text-gray-500">Total Clients</p>
            <div className="w-8 h-8 bg-blue-50 rounded-xl flex items-center justify-center">
              <Users size={16} className="text-blue-600" />
            </div>
          </div>
          <p className="text-3xl font-bold text-gray-900">{loading ? "—" : totalClients}</p>
          <Link href="/clients" className="text-xs text-blue-600 mt-2 inline-block hover:underline">
            View all clients →
          </Link>
        </div>

        <div className="bg-white border border-gray-200 rounded-2xl p-5">
          <div className="flex items-center justify-between mb-3">
            <p className="text-sm text-gray-500">Avg Compliance Score</p>
            <div className="w-8 h-8 bg-green-50 rounded-xl flex items-center justify-center">
              <TrendingUp size={16} className="text-green-600" />
            </div>
          </div>
          <p className={`text-3xl font-bold ${avgScore ? scoreColor(avgScore) : "text-gray-400"}`}>
            {loading ? "—" : avgScore ?? "N/A"}
          </p>
          <p className="text-xs text-gray-400 mt-2">
            {reports.length > 0 ? `Based on ${reports.length} audits` : "No audits yet"}
          </p>
        </div>

        <div className="bg-white border border-gray-200 rounded-2xl p-5">
          <div className="flex items-center justify-between mb-3">
            <p className="text-sm text-gray-500">High Risk Clients</p>
            <div className="w-8 h-8 bg-red-50 rounded-xl flex items-center justify-center">
              <AlertTriangle size={16} className="text-red-500" />
            </div>
          </div>
          <p className={`text-3xl font-bold ${highRiskCount > 0 ? "text-red-600" : "text-green-600"}`}>
            {loading ? "—" : highRiskCount}
          </p>
          <p className="text-xs text-gray-400 mt-2">
            {highRiskCount > 0 ? "Score below 60 — action needed" : "All clients healthy 🎉"}
          </p>
        </div>

        <div className="bg-white border border-gray-200 rounded-2xl p-5">
          <div className="flex items-center justify-between mb-3">
            <p className="text-sm text-gray-500">Total ITC at Risk</p>
            <div className="w-8 h-8 bg-orange-50 rounded-xl flex items-center justify-center">
              <span className="text-orange-600 font-bold text-xs">₹</span>
            </div>
          </div>
          <p className="text-3xl font-bold text-orange-600">{formatItc()}</p>
          <p className="text-xs text-gray-400 mt-2">Across all clients</p>
        </div>
      </div>

      {/* ── CTA Banner ── */}
      <div className="bg-blue-600 rounded-xl lg:rounded-2xl p-4 lg:p-5 mb-5 lg:mb-8 flex items-center justify-between gap-3">
        <div className="min-w-0">
          <p className="font-bold text-white text-sm lg:text-base">Run a New Audit</p>
          <p className="text-blue-200 text-xs mt-0.5">Upload Excel — results in 2 min</p>
        </div>
        <button
          onClick={() => router.push("/upload")}
          className="flex items-center gap-1.5 bg-white text-blue-600 font-semibold px-4 py-2.5 rounded-xl text-xs lg:text-sm hover:bg-blue-50 shrink-0 active:scale-95 transition-transform"
        >
          <Upload size={14} /> Upload
        </button>
      </div>

      {/* ── Recent Audits + Clients — stacked on mobile, side-by-side desktop ── */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4 lg:gap-6">

        {/* Recent audits */}
        <div className="lg:col-span-3 bg-white border border-gray-200 rounded-xl lg:rounded-2xl p-4 lg:p-5">
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-bold text-sm lg:text-base text-gray-900">Recent Audits</h2>
            <Link href="/reports" className="text-[10px] lg:text-xs text-blue-600 hover:underline">View all →</Link>
          </div>

          {loading ? (
            <div className="space-y-2">
              {[1,2,3].map(i => <div key={i} className="h-12 bg-gray-100 rounded-xl animate-pulse" />)}
            </div>
          ) : recentReports.length === 0 ? (
            <div className="text-center py-8">
              <p className="text-gray-400 text-xs">No audits yet</p>
              <button onClick={() => router.push("/upload")} className="text-blue-600 text-xs mt-2 hover:underline">
                Run your first audit →
              </button>
            </div>
          ) : (
            <div className="space-y-1.5">
              {recentReports.map((r) => (
                <div
                  key={r.id}
                  onClick={() => router.push(`/reports/${r.id}`)}
                  className="flex items-center gap-2.5 p-2.5 rounded-xl hover:bg-gray-50 cursor-pointer active:bg-gray-100 transition-colors"
                >
                  <div className={`w-9 h-9 rounded-xl flex items-center justify-center font-bold text-xs ${scoreBg(r.compliance_score)} ${scoreColor(r.compliance_score)}`}>
                    {r.compliance_score}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-medium text-gray-900 truncate">
                      {r.client_name || "Audit"} · {r.period || "—"}
                    </p>
                    <ScoreBar score={r.compliance_score} />
                  </div>
                  <span className={`px-1.5 py-0.5 rounded-full text-[10px] font-medium shrink-0 ${riskBadge(r.compliance_score)}`}>
                    {riskLabel(r.compliance_score)}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Clients */}
        <div className="lg:col-span-2 bg-white border border-gray-200 rounded-xl lg:rounded-2xl p-4 lg:p-5">
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-bold text-sm lg:text-base text-gray-900">Clients</h2>
            <Link href="/clients" className="text-[10px] lg:text-xs text-blue-600 hover:underline">View all →</Link>
          </div>

          {loading ? (
            <div className="space-y-2">
              {[1,2,3].map(i => <div key={i} className="h-10 bg-gray-100 rounded-xl animate-pulse" />)}
            </div>
          ) : clients.length === 0 ? (
            <div className="text-center py-8">
              <p className="text-gray-400 text-xs">No clients added yet</p>
              <Link href="/clients" className="text-blue-600 text-xs mt-2 inline-block hover:underline">
                Add your first client →
              </Link>
            </div>
          ) : (
            <div className="space-y-1.5">
              {clients.slice(0, 5).map((c) => {
                const initials = c.business_name
                  .split(" ").slice(0, 2).map(w => w[0]).join("").toUpperCase();
                return (
                  <div
                    key={c.id}
                    className="flex items-center gap-2.5 p-2 rounded-xl hover:bg-gray-50 cursor-pointer active:bg-gray-100 transition-colors"
                    onClick={() => router.push(`/upload?client_id=${c.id}`)}
                  >
                    <div className="w-7 h-7 bg-blue-100 text-blue-700 rounded-full flex items-center justify-center text-[10px] font-bold shrink-0">
                      {initials}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-medium text-gray-900 truncate">{c.business_name}</p>
                      {c.sector && (
                        <p className="text-[10px] text-gray-400 truncate capitalize">{c.sector.replace("_", " ")}</p>
                      )}
                    </div>
                    {c.last_score != null ? (
                      <span className={`text-[10px] font-bold ${scoreColor(c.last_score)}`}>{c.last_score}</span>
                    ) : (
                      <span className="text-[10px] text-gray-300">—</span>
                    )}
                  </div>
                );
              })}
            </div>
          )}

          <button
            onClick={() => router.push("/upload")}
            className="w-full mt-3 py-2 border-2 border-dashed border-gray-200 rounded-xl text-[10px] text-gray-400 hover:border-blue-300 hover:text-blue-500 active:scale-[0.98] transition-all"
          >
            + Run new audit
          </button>
        </div>
      </div>
    </div>
  );
}
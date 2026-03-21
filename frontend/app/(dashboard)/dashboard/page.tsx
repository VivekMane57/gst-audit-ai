"use client";
import { useEffect, useState } from "react";
import { useUser } from "@clerk/nextjs";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Upload, Users, TrendingUp, AlertTriangle, RefreshCw, ArrowUpRight, Zap } from "lucide-react";
import { getClients, getReports, setAuthHeader } from "@/lib/api";

interface Client {
  id: string;
  business_name: string;
  gstin_masked?: string;
  sector?: string;
  last_score?: number;
  last_audit_at?: string;
}

interface Report {
  id: string;
  period?: string;
  compliance_score: number;
  risk_level?: string;
  itc_at_risk?: number;
  itc_summary?: { at_risk?: number };
  created_at?: string;
  client_name?: string;
  sector?: string;
}

const scoreColor = (s: number) =>
  s >= 80 ? "text-emerald-600" : s >= 60 ? "text-amber-500" : "text-red-500";
const scoreBg = (s: number) =>
  s >= 80 ? "bg-emerald-50 text-emerald-700" : s >= 60 ? "bg-amber-50 text-amber-700" : "bg-red-50 text-red-600";
const riskBadge = (s: number) =>
  s >= 80 ? "bg-emerald-50 text-emerald-700 border-emerald-200" : s >= 60 ? "bg-amber-50 text-amber-700 border-amber-200" : "bg-red-50 text-red-600 border-red-200";
const riskLabel = (s: number) =>
  s >= 80 ? "Low Risk" : s >= 60 ? "Medium" : "High Risk";
const progressColor = (s: number) =>
  s >= 80 ? "bg-emerald-500" : s >= 60 ? "bg-amber-400" : "bg-red-500";

export default function DashboardPage() {
  const { user, isLoaded } = useUser();
  const router = useRouter();
  const [clients, setClients] = useState<Client[]>([]);
  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(true);
  const [refresh, setRefresh] = useState(0);

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

  const totalClients = clients.length;
  const avgScore = reports.length
    ? Math.round(reports.reduce((s, r) => s + r.compliance_score, 0) / reports.length)
    : null;
  const highRiskCount = reports.filter(r => r.compliance_score < 60).length;
  const totalItcRisk = reports.reduce((s, r) =>
    s + (r.itc_summary?.at_risk ?? r.itc_at_risk ?? 0), 0
  );
  const recentReports = reports.slice(0, 5);

  const formatItc = () => {
    if (loading) return "—";
    if (totalItcRisk >= 100000) return `₹${(totalItcRisk / 100000).toFixed(1)}L`;
    if (totalItcRisk >= 1000) return `₹${(totalItcRisk / 1000).toFixed(0)}K`;
    return `₹${totalItcRisk}`;
  };

  if (!isLoaded) return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <div className="w-8 h-8 border-[3px] border-blue-600 border-t-transparent rounded-full animate-spin" />
    </div>
  );

  const statCards = [
    { label: "Total Clients", value: loading ? "—" : String(totalClients), icon: Users, iconBg: "bg-blue-50", iconColor: "text-blue-600", link: "/clients", linkText: "View all →" },
    { label: "Avg Score", value: loading ? "—" : avgScore != null ? String(avgScore) : "N/A", icon: TrendingUp, iconBg: "bg-emerald-50", iconColor: "text-emerald-600", valueColor: avgScore ? scoreColor(avgScore) : "text-slate-400", sub: reports.length > 0 ? `${reports.length} audits` : "No audits yet" },
    { label: "High Risk", value: loading ? "—" : String(highRiskCount), icon: AlertTriangle, iconBg: "bg-red-50", iconColor: "text-red-500", valueColor: highRiskCount > 0 ? "text-red-500" : "text-emerald-600", sub: highRiskCount > 0 ? "Action needed" : "All healthy" },
    { label: "ITC at Risk", value: formatItc(), icon: () => <span className="text-amber-600 font-bold text-xs">₹</span>, iconBg: "bg-amber-50", iconColor: "text-amber-600", valueColor: "text-amber-600", sub: "Across all clients" },
  ];

  return (
    <div className="px-4 py-5 lg:px-8 lg:py-8 max-w-6xl mx-auto">

      {/* Header */}
      <div className="flex items-start justify-between mb-6 lg:mb-8 animate-fade-in">
        <div>
          <h1 className="text-2xl lg:text-3xl font-bold text-slate-900 tracking-tight">
            Welcome back, {user?.firstName || "CA"}
          </h1>
          <p className="text-slate-500 mt-1 text-sm">GST compliance overview</p>
        </div>
        <button onClick={() => setRefresh(r => r + 1)}
          className="flex items-center gap-1.5 text-slate-400 hover:text-slate-600 text-xs mt-2 transition-colors">
          <RefreshCw size={13} className={loading ? "animate-spin" : ""} />
          <span className="hidden sm:inline">Refresh</span>
        </button>
      </div>

      {/* Stat Cards — Mobile: vertical list, Desktop: 4-col grid */}
      <div className="lg:hidden bg-white rounded-2xl border border-slate-200/80 mb-5 divide-y divide-slate-100 shadow-sm animate-slide-up">
        {statCards.map((card, i) => {
          const Icon = card.icon;
          return (
            <div key={i} className="flex items-center justify-between px-4 py-4">
              <div className="flex items-center gap-3">
                <div className={`w-9 h-9 ${card.iconBg} rounded-xl flex items-center justify-center`}>
                  {typeof Icon === 'function' && Icon.length === 0 ? <Icon /> : <Icon size={16} className={card.iconColor} />}
                </div>
                <div>
                  <span className="text-sm text-slate-600 font-medium">{card.label}</span>
                  {card.sub && <p className="text-[10px] text-slate-400">{card.sub}</p>}
                </div>
              </div>
              <span className={`text-xl font-bold ${card.valueColor || "text-slate-900"}`}>{card.value}</span>
            </div>
          );
        })}
      </div>

      <div className="hidden lg:grid grid-cols-4 gap-5 mb-8">
        {statCards.map((card, i) => {
          const Icon = card.icon;
          return (
            <div key={i} className="stat-card p-5 animate-slide-up" style={{ animationDelay: `${i * 80}ms` }}>
              <div className="flex items-center justify-between mb-4">
                <p className="text-sm text-slate-500 font-medium">{card.label}</p>
                <div className={`w-9 h-9 ${card.iconBg} rounded-xl flex items-center justify-center`}>
                  {typeof Icon === 'function' && Icon.length === 0 ? <Icon /> : <Icon size={16} className={card.iconColor} />}
                </div>
              </div>
              <p className={`text-3xl font-bold ${card.valueColor || "text-slate-900"} tracking-tight`}>{card.value}</p>
              <div className="mt-2">
                {card.link ? (
                  <Link href={card.link} className="text-xs text-blue-600 hover:underline font-medium">{card.linkText}</Link>
                ) : (
                  <p className="text-xs text-slate-400">{card.sub}</p>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* CTA Banner */}
      <div className="brand-gradient rounded-2xl p-5 lg:p-6 mb-6 lg:mb-8 flex items-center justify-between gap-4 animate-slide-up shadow-lg shadow-blue-600/10"
           style={{ animationDelay: "300ms" }}>
        <div className="min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <Zap size={16} className="text-yellow-300" />
            <p className="font-bold text-white text-sm lg:text-base">Run a New Audit</p>
          </div>
          <p className="text-blue-200 text-xs">Upload Excel, PDF, images, or Tally XML — results in 2 min</p>
        </div>
        <button onClick={() => router.push("/upload")}
          className="flex items-center gap-2 bg-white text-blue-600 font-semibold px-5 py-2.5 rounded-xl text-sm hover:bg-blue-50 shrink-0 btn-press transition-all shadow-sm">
          <Upload size={15} /> Upload
        </button>
      </div>

      {/* Recent Audits + Clients */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-5 lg:gap-6">

        {/* Recent Audits */}
        <div className="lg:col-span-3 bg-white border border-slate-200/80 rounded-2xl p-5 shadow-sm animate-slide-up"
             style={{ animationDelay: "400ms" }}>
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-bold text-base text-slate-900">Recent Audits</h2>
            <Link href="/reports" className="text-xs text-blue-600 hover:underline font-medium flex items-center gap-1">
              View all <ArrowUpRight size={11} />
            </Link>
          </div>

          {loading ? (
            <div className="space-y-3">
              {[1,2,3].map(i => <div key={i} className="h-14 animate-shimmer rounded-xl" />)}
            </div>
          ) : recentReports.length === 0 ? (
            <div className="text-center py-10">
              <div className="w-12 h-12 bg-slate-100 rounded-2xl flex items-center justify-center mx-auto mb-3">
                <TrendingUp size={20} className="text-slate-300" />
              </div>
              <p className="text-slate-400 text-sm">No audits yet</p>
              <button onClick={() => router.push("/upload")} className="text-blue-600 text-xs mt-2 hover:underline font-medium">
                Run your first audit →
              </button>
            </div>
          ) : (
            <div className="space-y-2">
              {recentReports.map((r) => (
                <div key={r.id} onClick={() => router.push(`/reports/${r.id}`)}
                  className="flex items-center gap-3 p-3 rounded-xl hover:bg-slate-50 cursor-pointer active:bg-slate-100 transition-all group">
                  <div className={`w-10 h-10 rounded-xl flex items-center justify-center font-bold text-sm score-ring ${scoreBg(r.compliance_score)}`}>
                    {r.compliance_score}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-slate-900 truncate group-hover:text-blue-600 transition-colors">
                      {r.client_name || "Audit"} · {r.period || "—"}
                    </p>
                    <div className="w-full bg-slate-100 rounded-full h-1 mt-1.5">
                      <div className={`h-1 rounded-full ${progressColor(r.compliance_score)} transition-all`}
                        style={{ width: `${r.compliance_score}%` }} />
                    </div>
                  </div>
                  <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold border shrink-0 ${riskBadge(r.compliance_score)}`}>
                    {riskLabel(r.compliance_score)}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Clients */}
        <div className="lg:col-span-2 bg-white border border-slate-200/80 rounded-2xl p-5 shadow-sm animate-slide-up"
             style={{ animationDelay: "500ms" }}>
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-bold text-base text-slate-900">Clients</h2>
            <Link href="/clients" className="text-xs text-blue-600 hover:underline font-medium flex items-center gap-1">
              View all <ArrowUpRight size={11} />
            </Link>
          </div>

          {loading ? (
            <div className="space-y-3">
              {[1,2,3].map(i => <div key={i} className="h-11 animate-shimmer rounded-xl" />)}
            </div>
          ) : clients.length === 0 ? (
            <div className="text-center py-10">
              <div className="w-12 h-12 bg-slate-100 rounded-2xl flex items-center justify-center mx-auto mb-3">
                <Users size={20} className="text-slate-300" />
              </div>
              <p className="text-slate-400 text-sm">No clients added yet</p>
              <Link href="/clients" className="text-blue-600 text-xs mt-2 inline-block hover:underline font-medium">
                Add your first client →
              </Link>
            </div>
          ) : (
            <div className="space-y-1.5">
              {clients.slice(0, 5).map((c) => {
                const initials = c.business_name.split(" ").slice(0, 2).map(w => w[0]).join("").toUpperCase();
                return (
                  <div key={c.id} onClick={() => router.push(`/upload?client_id=${c.id}`)}
                    className="flex items-center gap-3 p-2.5 rounded-xl hover:bg-slate-50 cursor-pointer active:bg-slate-100 transition-all">
                    <div className="w-8 h-8 bg-blue-100 text-blue-700 rounded-lg flex items-center justify-center text-[10px] font-bold shrink-0">
                      {initials}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-medium text-slate-900 truncate">{c.business_name}</p>
                      {c.sector && <p className="text-[10px] text-slate-400 truncate capitalize">{c.sector.replace("_", " ")}</p>}
                    </div>
                    {c.last_score != null ? (
                      <span className={`text-xs font-bold ${scoreColor(c.last_score)}`}>{c.last_score}</span>
                    ) : (
                      <span className="text-[10px] text-slate-300">—</span>
                    )}
                  </div>
                );
              })}
            </div>
          )}

          <button onClick={() => router.push("/upload")}
            className="w-full mt-4 py-2.5 border-2 border-dashed border-slate-200 rounded-xl text-xs text-slate-400 hover:border-blue-300 hover:text-blue-500 btn-press transition-all">
            + Run new audit
          </button>
        </div>
      </div>
    </div>
  );
}
"use client";

import { useEffect, useState } from "react";
import { rulesApi, lawsApi, thresholdsApi } from "@/lib/adminApi";
import { BookOpen, Scale, SlidersHorizontal, ShieldAlert, TrendingUp, Activity } from "lucide-react";

interface Stats {
  totalRules: number;
  activeRules: number;
  totalLaws: number;
  totalThresholds: number;
}

export default function AdminDashboard() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [rulesRes, lawsRes, threshRes] = await Promise.all([
          rulesApi.list(),
          lawsApi.list({ active_only: false }),
          thresholdsApi.list(),
        ]);
        setStats({
          totalRules:      rulesRes.data.total,
          activeRules:     rulesRes.data.active_count,
          totalLaws:       lawsRes.data.total,
          totalThresholds: threshRes.data.thresholds.length,
        });
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const cards = [
    { label: "Total Rules",      value: stats?.totalRules,      icon: BookOpen,         color: "text-indigo-400",  bg: "bg-indigo-500/10" },
    { label: "Active Rules",     value: stats?.activeRules,     icon: Activity,         color: "text-emerald-400", bg: "bg-emerald-500/10" },
    { label: "Laws Catalogued",  value: stats?.totalLaws,       icon: Scale,            color: "text-violet-400",  bg: "bg-violet-500/10" },
    { label: "Threshold Configs",value: stats?.totalThresholds, icon: SlidersHorizontal,color: "text-amber-400",   bg: "bg-amber-500/10" },
  ];

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white tracking-tight">Admin Dashboard</h1>
        <p className="text-gray-400 text-sm mt-1">GST Rule Engine — Production Control Panel</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {cards.map(({ label, value, icon: Icon, color, bg }) => (
          <div key={label} className="bg-white/[0.03] border border-white/[0.06] rounded-xl p-5">
            <div className="flex items-center justify-between mb-3">
              <p className="text-gray-400 text-sm">{label}</p>
              <div className={`w-8 h-8 rounded-lg ${bg} flex items-center justify-center`}>
                <Icon className={`w-4 h-4 ${color}`} />
              </div>
            </div>
            {loading ? (
              <div className="h-8 w-16 bg-white/[0.06] rounded animate-pulse" />
            ) : (
              <p className="text-3xl font-bold text-white">{value ?? "—"}</p>
            )}
          </div>
        ))}
      </div>

      {/* Info */}
      <div className="bg-indigo-500/10 border border-indigo-500/20 rounded-xl p-5">
        <div className="flex items-start gap-3">
          <ShieldAlert className="w-5 h-5 text-indigo-400 mt-0.5 shrink-0" />
          <div>
            <p className="text-indigo-300 font-medium text-sm">Rule Engine Status</p>
            <p className="text-indigo-400/70 text-sm mt-1">
              <code className="bg-indigo-500/20 px-1.5 py-0.5 rounded text-xs">USE_DB_RULES=false</code>
              {" "}— System is using hardcoded rules. Enable DB rules after seeding compliance_rules table.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
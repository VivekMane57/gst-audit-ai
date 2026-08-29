"use client";

/**
 * DashboardCore.tsx
 * Premium GST Audit AI Dashboard
 * Stack: Next.js 14, Tailwind CSS, Shadcn/UI, Framer Motion
 *
 * Drop-in replacement for the existing dashboard page.
 * Requires:
 *   npm install framer-motion
 *   npx shadcn-ui@latest add card badge scroll-area separator skeleton
 */

import { useEffect, useRef, useState, useMemo } from "react";
import { motion, useSpring, useTransform, animate, AnimatePresence, stagger } from "framer-motion";
import {
  Card, CardContent, CardHeader, CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import {
  Upload, Users, TrendingUp, AlertTriangle, RefreshCw,
  ArrowUpRight, Zap, BarChart3, ShieldAlert, Bell, IndianRupee,
  ChevronRight, Activity,
} from "lucide-react";
import {
  AreaChart, Area, PieChart, Pie, Cell,
  XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
} from "recharts";

// ─── Types (mirror your existing interfaces) ──────────────────────────────────

interface Client {
  id: string; business_name: string; gstin_masked?: string;
  sector?: string; last_score?: number; last_audit_at?: string;
}
interface Report {
  id: string; period?: string; compliance_score: number; risk_level?: string;
  itc_at_risk?: number; itc_summary?: { at_risk?: number }; created_at?: string;
  client_name?: string; sector?: string; critical_count?: number; high_count?: number;
  medium_count?: number; low_count?: number;
}
interface QueueItem {
  audit_id: string; client_name: string; client_gstin_masked: string;
  period: string; compliance_score: number; notice_probability: number;
  notice_risk_level: string; itc_at_risk: number; critical_count: number;
  top_reason: string; recommended_action: string;
  estimated_penalty: number; urgency_score: number;
}
interface QueueSummary {
  total_clients_audited: number;
  by_risk_level: { very_high: number; high: number; medium: number; low: number };
  total_itc_at_risk: number; total_estimated_penalty: number;
  average_notice_probability: number; clients_needing_action: number;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

const scoreColor    = (s: number) => s >= 80 ? "text-emerald-500" : s >= 60 ? "text-amber-500" : "text-rose-500";
const scoreBg       = (s: number) => s >= 80 ? "bg-emerald-50 text-emerald-700" : s >= 60 ? "bg-amber-50 text-amber-700" : "bg-rose-50 text-rose-600";
const progressColor = (s: number) => s >= 80 ? "#10b981" : s >= 60 ? "#f59e0b" : "#f43f5e";
const noticeLevelColor = (level: string) =>
  ({ VERY_HIGH: "bg-rose-100 text-rose-700 border-rose-200", HIGH: "bg-orange-100 text-orange-700 border-orange-200", MEDIUM: "bg-amber-100 text-amber-700 border-amber-200", LOW: "bg-emerald-100 text-emerald-700 border-emerald-200" }[level] || "bg-slate-100 text-slate-500 border-slate-200");
const noticeProbColor = (p: number) => p >= 70 ? "#f43f5e" : p >= 50 ? "#f97316" : p >= 25 ? "#f59e0b" : "#10b981";

const formatCurrency = (v: number) =>
  v >= 10_000_000 ? `₹${(v / 10_000_000).toFixed(1)}Cr`
  : v >= 100_000  ? `₹${(v / 100_000).toFixed(1)}L`
  : v >= 1_000    ? `₹${(v / 1_000).toFixed(0)}K`
  : `₹${v.toFixed(0)}`;

// ─── Animation variants ───────────────────────────────────────────────────────

const fadeUp = {
  hidden: { opacity: 0, y: 16 },
  show:   { opacity: 1, y: 0, transition: { type: "spring", stiffness: 300, damping: 28 } },
};

const staggerContainer = (delayChildren = 0, staggerChildren = 0.07) => ({
  hidden: {},
  show:   { transition: { delayChildren, staggerChildren } },
});

// ─── Count-up hook ────────────────────────────────────────────────────────────

function useCountUp(target: number, duration = 1.2, decimals = 0) {
  const [value, setValue] = useState(0);
  useEffect(() => {
    const controls = animate(0, target, {
      duration,
      ease: "easeOut",
      onUpdate: (v) => setValue(parseFloat(v.toFixed(decimals))),
    });
    return controls.stop;
  }, [target, duration, decimals]);
  return value;
}

// ─── Radial Score Indicator ───────────────────────────────────────────────────

export function RadialScore({ score, size = 96 }: { score: number; size?: number }) {
  const radius    = (size - 12) / 2;
  const circ      = 2 * Math.PI * radius;
  const animScore = useSpring(0, { stiffness: 80, damping: 18 });
  const offset    = useTransform(animScore, [0, 100], [circ, 0]);

  useEffect(() => { animScore.set(score); }, [score, animScore]);

  const color = progressColor(score);
  const displayed = useCountUp(score, 1.1);

  return (
    <div className="relative flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="#e2e8f0" strokeWidth={6} />
        <motion.circle
          cx={size / 2} cy={size / 2} r={radius}
          fill="none" stroke={color} strokeWidth={6}
          strokeLinecap="round"
          strokeDasharray={circ}
          style={{ strokeDashoffset: offset }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className={`text-xl font-black leading-none ${scoreColor(score)}`}>{displayed}</span>
        <span className="text-[9px] text-slate-400 font-medium mt-0.5">SCORE</span>
      </div>
    </div>
  );
}

// ─── Stat Card ────────────────────────────────────────────────────────────────

interface StatCardProps {
  label: string;
  value: string | number;
  icon: React.ElementType;
  iconBg: string;
  iconColor: string;
  valueColor?: string;
  sub?: string;
  link?: string;
  linkText?: string;
  loading?: boolean;
  index?: number;
}

export function AnimatedStatCard({
  label, value, icon: Icon, iconBg, iconColor,
  valueColor = "text-slate-900", sub, loading, index = 0,
}: StatCardProps) {
  return (
    <motion.div
      variants={fadeUp}
      whileHover={{ y: -2, boxShadow: "0 8px 30px rgba(0,0,0,0.06)" }}
      transition={{ type: "spring", stiffness: 400, damping: 24 }}
    >
      <Card className="border border-slate-200/70 bg-white shadow-sm rounded-2xl overflow-hidden">
        <CardContent className="p-4">
          <div className="flex items-center justify-between mb-3">
            <p className="text-xs text-slate-500 font-semibold tracking-wide uppercase">{label}</p>
            <div className={`w-8 h-8 ${iconBg} rounded-xl flex items-center justify-center`}>
              <Icon size={14} className={iconColor} />
            </div>
          </div>
          {loading ? (
            <Skeleton className="h-7 w-20 mb-2 rounded-lg" />
          ) : (
            <p className={`text-2xl font-black tracking-tight ${valueColor}`}>{value}</p>
          )}
          <p className="text-[11px] text-slate-400 mt-1 font-medium">{sub}</p>
        </CardContent>
      </Card>
    </motion.div>
  );
}

// ─── Shimmer Skeleton Card ────────────────────────────────────────────────────

export function ShimmerCard({ className = "" }: { className?: string }) {
  return (
    <motion.div
      className={`rounded-2xl bg-slate-100 overflow-hidden ${className}`}
      animate={{ opacity: [0.5, 1, 0.5] }}
      transition={{ duration: 1.6, repeat: Infinity, ease: "easeInOut" }}
    >
      <div className="h-full w-full" style={{
        background: "linear-gradient(90deg, #f1f5f9 25%, #e2e8f0 50%, #f1f5f9 75%)",
        backgroundSize: "200% 100%",
        animation: "shimmer 1.5s infinite",
      }} />
    </motion.div>
  );
}

// Add shimmer keyframes via inline style tag (inject once in layout)
export function ShimmerStyles() {
  return (
    <style>{`
      @keyframes shimmer {
        0%   { background-position: 200% 0; }
        100% { background-position: -200% 0; }
      }
    `}</style>
  );
}

// ─── Skeleton Row ─────────────────────────────────────────────────────────────

export function SkeletonRow() {
  return (
    <div className="flex items-center gap-3 px-3 py-3">
      <Skeleton className="w-10 h-10 rounded-xl shrink-0" />
      <div className="flex-1 space-y-1.5">
        <Skeleton className="h-3.5 w-3/4 rounded" />
        <Skeleton className="h-2.5 w-1/2 rounded" />
      </div>
      <Skeleton className="h-5 w-16 rounded-full" />
    </div>
  );
}

// ─── Notice Risk Queue Item ───────────────────────────────────────────────────

function QueueItemCard({ item, index }: { item: QueueItem; index: number }) {
  return (
    <motion.div
      variants={fadeUp}
      whileHover={{ x: 6, backgroundColor: "rgba(248,250,252,1)" }}
      transition={{ type: "spring", stiffness: 400, damping: 24 }}
      className="flex items-start gap-3 p-3 rounded-xl cursor-pointer transition-colors border border-transparent hover:border-slate-100"
    >
      {/* Probability badge */}
      <div className={`w-11 h-11 rounded-xl flex items-center justify-center font-black text-xs border-2 shrink-0 ${noticeLevelColor(item.notice_risk_level)}`}>
        {item.notice_probability}%
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between gap-2 mb-1">
          <p className="text-sm font-bold text-slate-900 truncate">{item.client_name}</p>
          <Badge variant="outline" className={`text-[10px] font-bold shrink-0 ${noticeLevelColor(item.notice_risk_level)}`}>
            {item.notice_risk_level.replace("_", " ")}
          </Badge>
        </div>

        {/* Probability bar */}
        <div className="w-full bg-slate-100 rounded-full h-1.5 mb-1.5 overflow-hidden">
          <motion.div
            className="h-full rounded-full"
            style={{ background: noticeProbColor(item.notice_probability) }}
            initial={{ width: 0 }}
            animate={{ width: `${item.notice_probability}%` }}
            transition={{ delay: 0.1 + index * 0.05, duration: 0.6, ease: "easeOut" }}
          />
        </div>

        <div className="flex items-center justify-between">
          <p className="text-[11px] text-slate-400 truncate max-w-[170px]">{item.top_reason}</p>
          <div className="flex items-center gap-2 shrink-0">
            {item.itc_at_risk > 0 && (
              <span className="text-[10px] font-bold text-amber-600">{formatCurrency(item.itc_at_risk)}</span>
            )}
            {item.critical_count > 0 && (
              <span className="text-[10px] font-black text-rose-600 bg-rose-50 px-1.5 py-0.5 rounded-md">
                {item.critical_count} crit
              </span>
            )}
          </div>
        </div>
      </div>
    </motion.div>
  );
}

// ─── Custom Tooltip ───────────────────────────────────────────────────────────

function ChartTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-white border border-slate-200 rounded-xl px-3 py-2 shadow-xl text-xs">
      <p className="text-slate-500 mb-1 font-semibold">{label}</p>
      {payload.map((p: any, i: number) => (
        <p key={i} style={{ color: p.color }} className="font-black">{p.name}: {p.value}</p>
      ))}
    </div>
  );
}

// ─── Score Trend Chart ────────────────────────────────────────────────────────

function ScoreTrendChart({ reports }: { reports: Report[] }) {
  const data = useMemo(() => {
    const byMonth: Record<string, number[]> = {};
    reports.forEach(r => {
      const key = r.period || r.created_at?.slice(0, 7);
      if (!key) return;
      if (!byMonth[key]) byMonth[key] = [];
      byMonth[key].push(r.compliance_score);
    });
    return Object.entries(byMonth)
      .sort(([a], [b]) => a.localeCompare(b))
      .slice(-6)
      .map(([month, scores]) => ({
        month: month.length === 7 ? month.slice(5) + "/" + month.slice(2, 4) : month,
        avg: Math.round(scores.reduce((s, v) => s + v, 0) / scores.length),
      }));
  }, [reports]);

  if (data.length < 2) return (
    <div className="flex items-center justify-center h-36 text-slate-300 text-xs font-medium">
      Need 2+ months of data
    </div>
  );

  return (
    <ResponsiveContainer width="100%" height={140}>
      <AreaChart data={data} margin={{ top: 4, right: 4, left: -24, bottom: 0 }}>
        <defs>
          <linearGradient id="scoreGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%"  stopColor="#3b82f6" stopOpacity={0.18} />
            <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
        <XAxis dataKey="month" tick={{ fontSize: 10, fill: "#94a3b8" }} axisLine={false} tickLine={false} />
        <YAxis domain={[0, 100]} tick={{ fontSize: 10, fill: "#94a3b8" }} axisLine={false} tickLine={false} />
        <Tooltip content={<ChartTooltip />} />
        <Area type="monotone" dataKey="avg" name="Avg Score" stroke="#3b82f6" strokeWidth={2.5}
          fill="url(#scoreGrad)" dot={{ fill: "#3b82f6", r: 3.5, strokeWidth: 0 }}
          activeDot={{ r: 5, fill: "#2563eb", strokeWidth: 2, stroke: "#fff" }} />
      </AreaChart>
    </ResponsiveContainer>
  );
}

// ─── Risk Pie Chart ───────────────────────────────────────────────────────────

function RiskPieChart({ reports }: { reports: Report[] }) {
  const data = useMemo(() => [
    { name: "Critical", value: reports.filter(r => r.compliance_score < 40).length,  color: "#f43f5e" },
    { name: "High",     value: reports.filter(r => r.compliance_score >= 40 && r.compliance_score < 60).length, color: "#f97316" },
    { name: "Medium",   value: reports.filter(r => r.compliance_score >= 60 && r.compliance_score < 80).length, color: "#f59e0b" },
    { name: "Low",      value: reports.filter(r => r.compliance_score >= 80).length, color: "#10b981" },
  ].filter(d => d.value > 0), [reports]);

  if (!data.length) return (
    <div className="flex items-center justify-center h-36 text-slate-300 text-xs">No data yet</div>
  );

  return (
    <div className="flex items-center gap-4 pt-2">
      <ResponsiveContainer width={120} height={120}>
        <PieChart>
          <Pie data={data} cx="50%" cy="50%" innerRadius={30} outerRadius={52}
            dataKey="value" paddingAngle={3} strokeWidth={0}>
            {data.map((e, i) => <Cell key={i} fill={e.color} />)}
          </Pie>
          <Tooltip content={<ChartTooltip />} />
        </PieChart>
      </ResponsiveContainer>
      <div className="space-y-2">
        {data.map((d, i) => (
          <div key={i} className="flex items-center gap-2 text-xs">
            <div className="w-2.5 h-2.5 rounded-full shrink-0" style={{ background: d.color }} />
            <span className="text-slate-500">{d.name}</span>
            <span className="font-black text-slate-700 ml-auto pl-3">{d.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Alert Bar Chart ──────────────────────────────────────────────────────────

function AlertBarChart({ reports }: { reports: Report[] }) {
  const data = useMemo(() => {
    const t = { critical: 0, high: 0, medium: 0, low: 0 };
    reports.forEach(r => {
      t.critical += r.critical_count ?? 0;
      t.high     += r.high_count ?? 0;
      t.medium   += r.medium_count ?? 0;
      t.low      += r.low_count ?? 0;
    });
    return [
      { label: "Critical", value: t.critical, color: "#f43f5e" },
      { label: "High",     value: t.high,     color: "#f97316" },
      { label: "Medium",   value: t.medium,   color: "#f59e0b" },
      { label: "Low",      value: t.low,       color: "#10b981" },
    ];
  }, [reports]);
  const max = Math.max(...data.map(d => d.value), 1);

  return (
    <div className="space-y-3 pt-1">
      {data.map((d, i) => (
        <div key={i} className="flex items-center gap-3">
          <span className="text-[11px] text-slate-500 w-14 shrink-0 font-semibold">{d.label}</span>
          <div className="flex-1 bg-slate-100 rounded-full h-2 overflow-hidden">
            <motion.div
              className="h-full rounded-full"
              style={{ background: d.color }}
              initial={{ width: 0 }}
              animate={{ width: `${(d.value / max) * 100}%` }}
              transition={{ delay: 0.1 + i * 0.08, duration: 0.6, ease: "easeOut" }}
            />
          </div>
          <span className="text-[11px] font-black text-slate-700 w-6 text-right shrink-0">{d.value}</span>
        </div>
      ))}
    </div>
  );
}

// ─── Main Dashboard ───────────────────────────────────────────────────────────

interface DashboardCoreProps {
  // Pass these in from your page — mirrors your existing state
  clients:      Client[];
  reports:      Report[];
  queue:        QueueItem[];
  queueSummary: QueueSummary | null;
  loading:      boolean;
  queueLoading: boolean;
  userName?:    string;
  onRefresh?:   () => void;
  onUpload?:    () => void;
  onReportClick?: (id: string) => void;
  onClientClick?: (id: string) => void;
}

const chartTabs = [
  { key: "trend",  label: "Score Trend", icon: TrendingUp  },
  { key: "risk",   label: "Risk Split",  icon: BarChart3   },
  { key: "alerts", label: "Alerts",      icon: ShieldAlert },
] as const;

export default function DashboardCore({
  clients, reports, queue, queueSummary,
  loading, queueLoading,
  userName = "CA",
  onRefresh, onUpload,
  onReportClick, onClientClick,
}: DashboardCoreProps) {
  const [activeTab, setActiveTab]   = useState<"trend" | "risk" | "alerts">("trend");
  const [showAllQueue, setShowAllQueue] = useState(false);

  // Derived stats
  const avgScore      = reports.length ? Math.round(reports.reduce((s, r) => s + r.compliance_score, 0) / reports.length) : 0;
  const highRiskCount = reports.filter(r => r.compliance_score < 60).length;
  const totalItcRisk  = reports.reduce((s, r) => s + (r.itc_summary?.at_risk ?? r.itc_at_risk ?? 0), 0);
  const totalPenalty  = queueSummary?.total_estimated_penalty ?? 0;
  const recentReports = reports.slice(0, 5);

  // Count-up animations for currency values
  const animItc     = useCountUp(loading ? 0 : totalItcRisk / 100_000, 1.2, 1);
  const animPenalty = useCountUp(queueLoading ? 0 : totalPenalty / 100_000, 1.2, 1);

  const statCards = [
    {
      label: "Total Clients",   icon: Users,         iconBg: "bg-blue-50",    iconColor: "text-blue-600",
      value: loading ? "—" : String(clients.length), valueColor: "text-slate-900",  sub: "Active portfolios",
    },
    {
      label: "Avg Score",       icon: TrendingUp,    iconBg: "bg-emerald-50", iconColor: "text-emerald-600",
      value: loading ? "—" : String(avgScore),       valueColor: scoreColor(avgScore), sub: `${reports.length} audits`,
    },
    {
      label: "High Risk",       icon: AlertTriangle, iconBg: "bg-rose-50",    iconColor: "text-rose-500",
      value: loading ? "—" : String(highRiskCount),  valueColor: highRiskCount > 0 ? "text-rose-500" : "text-emerald-600", sub: highRiskCount > 0 ? "Need action" : "All healthy",
    },
    {
      label: "ITC at Risk",     icon: ShieldAlert,   iconBg: "bg-amber-50",   iconColor: "text-amber-600",
      value: loading ? "—" : `₹${animItc.toFixed(1)}L`, valueColor: "text-amber-600", sub: "Across all clients",
    },
    {
      label: "Penalty Exposure", icon: IndianRupee,  iconBg: "bg-rose-50",    iconColor: "text-rose-600",
      value: queueLoading ? "—" : totalPenalty === 0 ? "₹0" : `₹${animPenalty.toFixed(1)}L`,
      valueColor: totalPenalty > 0 ? "text-rose-600" : "text-emerald-600", sub: "Estimated total",
    },
  ];

  const visibleQueue = showAllQueue ? queue : queue.slice(0, 2);

  return (
    <div className="px-4 py-6 lg:px-8 lg:py-8 max-w-6xl mx-auto space-y-5">
      <ShimmerStyles />

      {/* ── Header ── */}
      <motion.div
        className="flex items-start justify-between"
        initial={{ opacity: 0, y: -12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ type: "spring", stiffness: 280, damping: 26 }}
      >
        <div>
          <h1 className="text-2xl lg:text-3xl font-black text-slate-900 tracking-tight">
            Welcome back,{" "}
            <span className="bg-gradient-to-r from-blue-600 to-violet-600 bg-clip-text text-transparent">
              {userName}
            </span>
          </h1>
          <p className="text-slate-500 mt-1 text-sm font-medium">GST compliance overview</p>
        </div>
        <motion.button
          onClick={onRefresh}
          whileTap={{ rotate: 360 }}
          transition={{ duration: 0.4 }}
          className="flex items-center gap-1.5 text-slate-400 hover:text-slate-700 text-xs mt-2 transition-colors px-3 py-1.5 rounded-xl hover:bg-slate-100"
        >
          <RefreshCw size={13} className={loading ? "animate-spin" : ""} />
          <span className="hidden sm:inline font-medium">Refresh</span>
        </motion.button>
      </motion.div>

      {/* ── Stat Cards ── */}
      <motion.div
        className="grid grid-cols-2 lg:grid-cols-5 gap-3"
        variants={staggerContainer(0.05, 0.08)}
        initial="hidden"
        animate="show"
      >
        {statCards.map((card, i) => (
          <AnimatedStatCard key={i} index={i} loading={loading} {...card} />
        ))}
      </motion.div>

      {/* ── Notice Queue + Analytics ── */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-5">

        {/* Notice queue — 3/5 cols */}
        <motion.div
          className="lg:col-span-3"
          variants={fadeUp}
          initial="hidden"
          animate="show"
          transition={{ delay: 0.25 }}
        >
          <Card className="border border-slate-200/70 shadow-sm rounded-2xl h-full">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <div className="w-8 h-8 bg-rose-50 rounded-xl flex items-center justify-center">
                    <Bell size={14} className="text-rose-500" />
                  </div>
                  <div>
                    <CardTitle className="text-sm font-black text-slate-900">Action Required</CardTitle>
                    {queueSummary && queueSummary.clients_needing_action > 0 && (
                      <p className="text-[10px] text-rose-500 font-bold">
                        {queueSummary.clients_needing_action} client{queueSummary.clients_needing_action > 1 ? "s" : ""} need attention
                      </p>
                    )}
                  </div>
                </div>
                {queueSummary && (
                  <div className="hidden sm:flex gap-1.5">
                    {queueSummary.by_risk_level.very_high > 0 && (
                      <Badge variant="outline" className="text-[10px] font-bold bg-rose-50 text-rose-600 border-rose-200">
                        {queueSummary.by_risk_level.very_high} V.High
                      </Badge>
                    )}
                    {queueSummary.by_risk_level.high > 0 && (
                      <Badge variant="outline" className="text-[10px] font-bold bg-orange-50 text-orange-600 border-orange-200">
                        {queueSummary.by_risk_level.high} High
                      </Badge>
                    )}
                  </div>
                )}
              </div>
            </CardHeader>

            <CardContent>
              {queueLoading ? (
                <div className="space-y-2">
                  {[1, 2].map(i => <SkeletonRow key={i} />)}
                </div>
              ) : queue.length === 0 ? (
                <div className="text-center py-8">
                  <div className="w-10 h-10 bg-emerald-50 rounded-2xl flex items-center justify-center mx-auto mb-3">
                    <ShieldAlert size={18} className="text-emerald-500" />
                  </div>
                  <p className="text-slate-400 text-sm font-semibold">All clients in good shape</p>
                  <p className="text-slate-300 text-xs mt-1">No high-risk notices detected</p>
                </div>
              ) : (
                <>
                  <motion.div
                    className="space-y-1"
                    variants={staggerContainer(0, 0.06)}
                    initial="hidden"
                    animate="show"
                  >
                    <AnimatePresence>
                      {visibleQueue.map((item, i) => (
                        <div key={item.audit_id} onClick={() => onReportClick?.(item.audit_id)}>
                          <QueueItemCard item={item} index={i} />
                        </div>
                      ))}
                    </AnimatePresence>
                  </motion.div>

                  {queue.length > 2 && (
                    <motion.button
                      whileTap={{ scale: 0.97 }}
                      onClick={() => setShowAllQueue(v => !v)}
                      className="w-full mt-2 py-2 text-xs font-bold text-blue-600 hover:text-blue-700 hover:bg-blue-50 rounded-xl transition-all border border-dashed border-blue-200 hover:border-blue-300"
                    >
                      {showAllQueue ? "Show less ↑" : `Show ${queue.length - 2} more ↓`}
                    </motion.button>
                  )}
                </>
              )}
            </CardContent>
          </Card>
        </motion.div>

        {/* Analytics — 2/5 cols */}
        {reports.length > 0 && (
          <motion.div
            className="lg:col-span-2"
            variants={fadeUp}
            initial="hidden"
            animate="show"
            transition={{ delay: 0.32 }}
          >
            <Card className="border border-slate-200/70 shadow-sm rounded-2xl h-full">
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-sm font-black text-slate-900">Analytics</CardTitle>
                  <div className="flex gap-1">
                    {chartTabs.map(tab => {
                      const Icon = tab.icon;
                      const active = activeTab === tab.key;
                      return (
                        <motion.button
                          key={tab.key}
                          onClick={() => setActiveTab(tab.key)}
                          whileTap={{ scale: 0.92 }}
                          className={`flex items-center gap-1 px-2 py-1.5 rounded-lg text-[10px] font-bold transition-all ${
                            active ? "bg-blue-600 text-white shadow" : "text-slate-500 hover:bg-slate-100"
                          }`}
                        >
                          <Icon size={10} />
                          <span className="hidden xl:inline">{tab.label.split(" ")[0]}</span>
                        </motion.button>
                      );
                    })}
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="min-h-[140px]">
                  {loading
                    ? <ShimmerCard className="h-36" />
                    : (
                      <AnimatePresence mode="wait">
                        <motion.div
                          key={activeTab}
                          initial={{ opacity: 0, y: 6 }}
                          animate={{ opacity: 1, y: 0 }}
                          exit={{ opacity: 0, y: -6 }}
                          transition={{ duration: 0.2 }}
                        >
                          {activeTab === "trend"  && <ScoreTrendChart reports={reports} />}
                          {activeTab === "risk"   && <RiskPieChart reports={reports} />}
                          {activeTab === "alerts" && <AlertBarChart reports={reports} />}
                        </motion.div>
                      </AnimatePresence>
                    )
                  }
                </div>
              </CardContent>
            </Card>
          </motion.div>
        )}
      </div>

      {/* ── Run New Audit CTA ── */}
      <motion.div
        variants={fadeUp}
        initial="hidden"
        animate="show"
        transition={{ delay: 0.38 }}
        whileHover={{ scale: 1.005 }}
        className="relative overflow-hidden rounded-2xl p-5 lg:p-6 flex items-center justify-between gap-4"
        style={{ background: "linear-gradient(135deg, #1d4ed8 0%, #4f46e5 100%)" }}
      >
        {/* Decorative blob */}
        <div className="absolute right-24 top-[-20px] w-40 h-40 rounded-full opacity-10"
          style={{ background: "radial-gradient(circle, #fff 0%, transparent 70%)" }} />

        <div className="min-w-0 relative z-10">
          <div className="flex items-center gap-2 mb-1">
            <Zap size={16} className="text-yellow-300" />
            <p className="font-black text-white text-sm lg:text-base">Run a New Audit</p>
          </div>
          <p className="text-blue-200 text-xs font-medium">
            Upload Excel, PDF, images, or Tally XML — results in 2 min
          </p>
        </div>
        <motion.button
          onClick={onUpload}
          whileHover={{ scale: 1.04 }}
          whileTap={{ scale: 0.97 }}
          className="flex items-center gap-2 bg-white text-blue-700 font-black px-5 py-2.5 rounded-xl text-sm shrink-0 shadow-lg relative z-10"
        >
          <Upload size={15} /> Upload
        </motion.button>
      </motion.div>

      {/* ── Recent Audits + Clients ── */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-5">

        {/* Recent Audits — 3/5 */}
        <motion.div
          className="lg:col-span-3"
          variants={fadeUp}
          initial="hidden"
          animate="show"
          transition={{ delay: 0.44 }}
        >
          <Card className="border border-slate-200/70 shadow-sm rounded-2xl">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-base font-black text-slate-900">Recent Audits</CardTitle>
                <button className="text-xs text-blue-600 hover:underline font-bold flex items-center gap-1">
                  View all <ArrowUpRight size={11} />
                </button>
              </div>
            </CardHeader>
            <CardContent className="pt-0">
              {loading ? (
                <div className="space-y-2">
                  {[1, 2, 3].map(i => <SkeletonRow key={i} />)}
                </div>
              ) : recentReports.length === 0 ? (
                <div className="text-center py-10">
                  <div className="w-12 h-12 bg-slate-100 rounded-2xl flex items-center justify-center mx-auto mb-3">
                    <Activity size={20} className="text-slate-300" />
                  </div>
                  <p className="text-slate-400 text-sm font-semibold">No audits yet</p>
                  <button onClick={onUpload} className="text-blue-600 text-xs mt-2 hover:underline font-bold">
                    Run your first audit →
                  </button>
                </div>
              ) : (
                <motion.div
                  className="space-y-1"
                  variants={staggerContainer(0, 0.05)}
                  initial="hidden"
                  animate="show"
                >
                  {recentReports.map(r => (
                    <motion.div
                      key={r.id}
                      variants={fadeUp}
                      whileHover={{ x: 4, backgroundColor: "rgba(248,250,252,1)" }}
                      transition={{ type: "spring", stiffness: 400, damping: 28 }}
                      onClick={() => onReportClick?.(r.id)}
                      className="flex items-center gap-3 p-3 rounded-xl cursor-pointer transition-colors"
                    >
                      <div className={`w-11 h-11 rounded-xl flex items-center justify-center font-black text-sm shrink-0 ${scoreBg(r.compliance_score)}`}>
                        {r.compliance_score}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-bold text-slate-900 truncate">
                          {r.client_name || "Audit"} · {r.period || "—"}
                        </p>
                        <div className="w-full bg-slate-100 rounded-full h-1.5 mt-1.5 overflow-hidden">
                          <motion.div
                            className="h-full rounded-full"
                            style={{ background: progressColor(r.compliance_score) }}
                            initial={{ width: 0 }}
                            animate={{ width: `${r.compliance_score}%` }}
                            transition={{ duration: 0.5, ease: "easeOut" }}
                          />
                        </div>
                      </div>
                      <Badge
                        variant="outline"
                        className={`text-[10px] font-bold shrink-0 ${
                          r.compliance_score >= 80 ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                          : r.compliance_score >= 60 ? "bg-amber-50 text-amber-700 border-amber-200"
                          : "bg-rose-50 text-rose-600 border-rose-200"
                        }`}
                      >
                        {r.compliance_score >= 80 ? "Low Risk" : r.compliance_score >= 60 ? "Medium" : "High Risk"}
                      </Badge>
                    </motion.div>
                  ))}
                </motion.div>
              )}
            </CardContent>
          </Card>
        </motion.div>

        {/* Clients — 2/5 */}
        <motion.div
          className="lg:col-span-2"
          variants={fadeUp}
          initial="hidden"
          animate="show"
          transition={{ delay: 0.5 }}
        >
          <Card className="border border-slate-200/70 shadow-sm rounded-2xl">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-base font-black text-slate-900">Clients</CardTitle>
                <button className="text-xs text-blue-600 hover:underline font-bold flex items-center gap-1">
                  View all <ArrowUpRight size={11} />
                </button>
              </div>
            </CardHeader>
            <CardContent className="pt-0">
              {loading ? (
                <div className="space-y-2">
                  {[1, 2, 3].map(i => <SkeletonRow key={i} />)}
                </div>
              ) : clients.length === 0 ? (
                <div className="text-center py-10">
                  <div className="w-12 h-12 bg-slate-100 rounded-2xl flex items-center justify-center mx-auto mb-3">
                    <Users size={20} className="text-slate-300" />
                  </div>
                  <p className="text-slate-400 text-sm font-semibold">No clients added yet</p>
                </div>
              ) : (
                <motion.div
                  className="space-y-1"
                  variants={staggerContainer(0, 0.06)}
                  initial="hidden"
                  animate="show"
                >
                  {clients.slice(0, 5).map(c => {
                    const initials = c.business_name.split(" ").slice(0, 2).map(w => w[0]).join("").toUpperCase();
                    return (
                      <motion.div
                        key={c.id}
                        variants={fadeUp}
                        whileHover={{ x: 4, backgroundColor: "rgba(248,250,252,1)" }}
                        transition={{ type: "spring", stiffness: 400, damping: 28 }}
                        onClick={() => onClientClick?.(c.id)}
                        className="flex items-center gap-3 p-2.5 rounded-xl cursor-pointer transition-colors"
                      >
                        <div className="w-9 h-9 bg-gradient-to-br from-blue-100 to-violet-100 text-blue-700 rounded-xl flex items-center justify-center text-[10px] font-black shrink-0">
                          {initials}
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-xs font-bold text-slate-900 truncate">{c.business_name}</p>
                          {c.sector && (
                            <p className="text-[10px] text-slate-400 truncate capitalize font-medium">
                              {c.sector.replace("_", " ")}
                            </p>
                          )}
                        </div>
                        {c.last_score != null
                          ? <span className={`text-sm font-black ${scoreColor(c.last_score)}`}>{c.last_score}</span>
                          : <span className="text-xs text-slate-300">—</span>}
                      </motion.div>
                    );
                  })}
                </motion.div>
              )}

              <motion.button
                whileHover={{ borderColor: "#93c5fd", color: "#3b82f6" }}
                whileTap={{ scale: 0.97 }}
                onClick={onUpload}
                className="w-full mt-4 py-2.5 border-2 border-dashed border-slate-200 rounded-xl text-xs text-slate-400 transition-all font-semibold"
              >
                + Run new audit
              </motion.button>
            </CardContent>
          </Card>
        </motion.div>
      </div>
    </div>
  );
}

// "use client";
// import { useEffect, useState, useMemo } from "react";
// import { useUser } from "@clerk/nextjs";
// import { useRouter } from "next/navigation";
// import Link from "next/link";
// import {
//   Upload, Users, TrendingUp, AlertTriangle, RefreshCw,
//   ArrowUpRight, Zap, BarChart3, ShieldAlert, Bell, IndianRupee,
// } from "lucide-react";
// import {
//   AreaChart, Area, PieChart, Pie, Cell,
//   XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
// } from "recharts";
// import { getClients, getReports, getNoticeQueue, getNoticeQueueSummary, setAuthHeader } from "@/lib/api";

// interface Client {
//   id: string; business_name: string; gstin_masked?: string;
//   sector?: string; last_score?: number; last_audit_at?: string;
// }
// interface Report {
//   id: string; period?: string; compliance_score: number; risk_level?: string;
//   itc_at_risk?: number; itc_summary?: { at_risk?: number }; created_at?: string;
//   client_name?: string; sector?: string; critical_count?: number; high_count?: number;
//   medium_count?: number; low_count?: number; issues_json?: { severity?: string }[];
// }
// interface QueueItem {
//   audit_id: string; client_id?: string; client_name: string; client_gstin_masked: string;
//   period: string; compliance_score: number; notice_probability: number; notice_risk_level: string;
//   itc_at_risk: number; critical_count: number; unresolved_issue_count: number;
//   last_audit_date: string; top_reason: string; recommended_action: string;
//   estimated_penalty: number; urgency_score: number;
// }
// interface QueueSummary {
//   total_clients_audited: number; by_risk_level: { very_high: number; high: number; medium: number; low: number };
//   total_itc_at_risk: number; total_estimated_penalty: number;
//   average_notice_probability: number; clients_needing_action: number;
// }

// const scoreColor    = (s: number) => s >= 80 ? "text-emerald-600" : s >= 60 ? "text-amber-500" : "text-red-500";
// const scoreBg       = (s: number) => s >= 80 ? "bg-emerald-50 text-emerald-700" : s >= 60 ? "bg-amber-50 text-amber-700" : "bg-red-50 text-red-600";
// const riskBadge     = (s: number) => s >= 80 ? "bg-emerald-50 text-emerald-700 border-emerald-200" : s >= 60 ? "bg-amber-50 text-amber-700 border-amber-200" : "bg-red-50 text-red-600 border-red-200";
// const riskLabel     = (s: number) => s >= 80 ? "Low Risk" : s >= 60 ? "Medium" : "High Risk";
// const progressColor = (s: number) => s >= 80 ? "bg-emerald-500" : s >= 60 ? "bg-amber-400" : "bg-red-500";
// const noticeLevelColor = (level: string) => ({ VERY_HIGH: "text-red-600 bg-red-50 border-red-200", HIGH: "text-orange-600 bg-orange-50 border-orange-200", MEDIUM: "text-amber-600 bg-amber-50 border-amber-200", LOW: "text-emerald-600 bg-emerald-50 border-emerald-200" }[level] || "text-slate-500 bg-slate-50 border-slate-200");
// const noticeProbBar = (p: number) => p >= 70 ? "bg-red-500" : p >= 50 ? "bg-orange-500" : p >= 25 ? "bg-amber-400" : "bg-emerald-500";
// const formatCurrency = (v: number) => v >= 10000000 ? `₹${(v/10000000).toFixed(1)}Cr` : v >= 100000 ? `₹${(v/100000).toFixed(1)}L` : v >= 1000 ? `₹${(v/1000).toFixed(0)}K` : `₹${v.toFixed(0)}`;

// function CustomTooltip({ active, payload, label }: any) {
//   if (!active || !payload?.length) return null;
//   return (
//     <div className="bg-white border border-slate-200 rounded-xl px-3 py-2 shadow-lg text-xs">
//       <p className="text-slate-500 mb-1 font-medium">{label}</p>
//       {payload.map((p: any, i: number) => <p key={i} style={{ color: p.color }} className="font-bold">{p.name}: {p.value}</p>)}
//     </div>
//   );
// }

// function ScoreTrendChart({ reports }: { reports: Report[] }) {
//   const data = useMemo(() => {
//     const byMonth: Record<string, number[]> = {};
//     reports.forEach(r => { const key = r.period || r.created_at?.slice(0,7); if (!key) return; if (!byMonth[key]) byMonth[key] = []; byMonth[key].push(r.compliance_score); });
//     return Object.entries(byMonth).sort(([a],[b]) => a.localeCompare(b)).slice(-6).map(([month, scores]) => ({ month: month.length===7 ? month.slice(5)+"/"+month.slice(2,4) : month, avg: Math.round(scores.reduce((s,v)=>s+v,0)/scores.length) }));
//   }, [reports]);
//   if (data.length < 2) return <div className="flex items-center justify-center h-32 text-slate-300 text-xs">Need 2+ months data</div>;
//   return (
//     <ResponsiveContainer width="100%" height={140}>
//       <AreaChart data={data} margin={{ top:4, right:4, left:-20, bottom:0 }}>
//         <defs><linearGradient id="scoreGrad" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#3b82f6" stopOpacity={0.15}/><stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/></linearGradient></defs>
//         <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false}/>
//         <XAxis dataKey="month" tick={{fontSize:10,fill:"#94a3b8"}} axisLine={false} tickLine={false}/>
//         <YAxis domain={[0,100]} tick={{fontSize:10,fill:"#94a3b8"}} axisLine={false} tickLine={false}/>
//         <Tooltip content={<CustomTooltip/>}/>
//         <Area type="monotone" dataKey="avg" name="Avg Score" stroke="#3b82f6" strokeWidth={2} fill="url(#scoreGrad)" dot={{fill:"#3b82f6",r:3,strokeWidth:0}} activeDot={{r:5,fill:"#2563eb"}}/>
//       </AreaChart>
//     </ResponsiveContainer>
//   );
// }

// function RiskPieChart({ reports }: { reports: Report[] }) {
//   const data = useMemo(() => [
//     { name:"Critical", value:reports.filter(r=>r.compliance_score<40).length, color:"#ef4444" },
//     { name:"High",     value:reports.filter(r=>r.compliance_score>=40&&r.compliance_score<60).length, color:"#f97316" },
//     { name:"Medium",   value:reports.filter(r=>r.compliance_score>=60&&r.compliance_score<80).length, color:"#f59e0b" },
//     { name:"Low",      value:reports.filter(r=>r.compliance_score>=80).length, color:"#10b981" },
//   ].filter(d=>d.value>0), [reports]);
//   if (!data.length) return <div className="flex items-center justify-center h-32 text-slate-300 text-xs">No data yet</div>;
//   return (
//     <div className="flex items-center gap-4">
//       <ResponsiveContainer width={120} height={120}>
//         <PieChart><Pie data={data} cx="50%" cy="50%" innerRadius={32} outerRadius={52} dataKey="value" paddingAngle={3} strokeWidth={0}>{data.map((e,i)=><Cell key={i} fill={e.color}/>)}</Pie><Tooltip content={<CustomTooltip/>}/></PieChart>
//       </ResponsiveContainer>
//       <div className="space-y-1.5">{data.map((d,i)=><div key={i} className="flex items-center gap-2 text-xs"><div className="w-2.5 h-2.5 rounded-full shrink-0" style={{background:d.color}}/><span className="text-slate-500">{d.name}</span><span className="font-bold text-slate-700 ml-auto pl-3">{d.value}</span></div>)}</div>
//     </div>
//   );
// }

// function AlertBarChart({ reports }: { reports: Report[] }) {
//   const data = useMemo(() => { const t={critical:0,high:0,medium:0,low:0}; reports.forEach(r=>{t.critical+=r.critical_count??0;t.high+=r.high_count??0;t.medium+=r.medium_count??0;t.low+=r.low_count??0;}); return [{label:"Critical",value:t.critical,color:"#ef4444"},{label:"High",value:t.high,color:"#f97316"},{label:"Medium",value:t.medium,color:"#f59e0b"},{label:"Low",value:t.low,color:"#10b981"}]; }, [reports]);
//   const max = Math.max(...data.map(d=>d.value),1);
//   return <div className="space-y-2.5">{data.map((d,i)=><div key={i} className="flex items-center gap-3"><span className="text-[11px] text-slate-500 w-14 shrink-0">{d.label}</span><div className="flex-1 bg-slate-100 rounded-full h-2 overflow-hidden"><div className="h-full rounded-full transition-all duration-700" style={{width:`${(d.value/max)*100}%`,background:d.color}}/></div><span className="text-[11px] font-bold text-slate-700 w-6 text-right shrink-0">{d.value}</span></div>)}</div>;
// }

// function NoticeRiskQueue({ queue, loading }: { queue: QueueItem[]; loading: boolean }) {
//   const router = useRouter();
//   const [showAll, setShowAll] = useState(false);

//   if (loading) return <div className="space-y-2.5">{[1,2].map(i=><div key={i} className="h-16 animate-shimmer rounded-xl"/>)}</div>;
//   if (!queue.length) return (
//     <div className="text-center py-8">
//       <div className="w-10 h-10 bg-emerald-50 rounded-2xl flex items-center justify-center mx-auto mb-3"><ShieldAlert size={18} className="text-emerald-500"/></div>
//       <p className="text-slate-400 text-sm font-medium">All clients in good shape</p>
//       <p className="text-slate-300 text-xs mt-1">No high-risk notices detected</p>
//     </div>
//   );

//   const visible   = showAll ? queue : queue.slice(0, 2);
//   const remaining = queue.length - 2;

//   return (
//     <div className="space-y-2">
//       {visible.map(item => (
//         <div key={item.audit_id} onClick={() => router.push(`/reports/${item.audit_id}`)}
//           className="flex items-start gap-3 p-3 rounded-xl hover:bg-slate-50 cursor-pointer transition-all group border border-transparent hover:border-slate-100">
//           <div className={`w-10 h-10 rounded-xl flex items-center justify-center font-bold text-xs border shrink-0 ${noticeLevelColor(item.notice_risk_level)}`}>
//             {item.notice_probability}%
//           </div>
//           <div className="flex-1 min-w-0">
//             <div className="flex items-center justify-between gap-2 mb-1">
//               <p className="text-sm font-semibold text-slate-900 truncate group-hover:text-blue-600 transition-colors">{item.client_name}</p>
//               <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border shrink-0 ${noticeLevelColor(item.notice_risk_level)}`}>
//                 {item.notice_risk_level.replace("_"," ")}
//               </span>
//             </div>
//             <div className="w-full bg-slate-100 rounded-full h-1 mb-1.5">
//               <div className={`h-1 rounded-full transition-all ${noticeProbBar(item.notice_probability)}`} style={{width:`${item.notice_probability}%`}}/>
//             </div>
//             <div className="flex items-center justify-between">
//               <p className="text-[11px] text-slate-400 truncate max-w-[180px]">{item.top_reason}</p>
//               <div className="flex items-center gap-2 shrink-0">
//                 {item.itc_at_risk > 0 && <span className="text-[10px] font-semibold text-amber-600">{formatCurrency(item.itc_at_risk)}</span>}
//                 {item.critical_count > 0 && <span className="text-[10px] font-bold text-red-600 bg-red-50 px-1.5 py-0.5 rounded">{item.critical_count} crit</span>}
//               </div>
//             </div>
//           </div>
//         </div>
//       ))}

//       {queue.length > 2 && (
//         <button
//           onClick={(e) => { e.stopPropagation(); setShowAll(v => !v); }}
//           className="w-full py-2 text-xs font-semibold text-blue-600 hover:text-blue-700 hover:bg-blue-50 rounded-xl transition-all border border-dashed border-blue-200 hover:border-blue-300"
//         >
//           {showAll ? "Show less ↑" : `Show ${remaining} more ↓`}
//         </button>
//       )}
//     </div>
//   );
// }

// export default function DashboardPage() {
//   const { user, isLoaded } = useUser();
//   const router = useRouter();
//   const [clients, setClients]           = useState<Client[]>([]);
//   const [reports, setReports]           = useState<Report[]>([]);
//   const [queue, setQueue]               = useState<QueueItem[]>([]);
//   const [queueSummary, setQueueSummary] = useState<QueueSummary | null>(null);
//   const [loading, setLoading]           = useState(true);
//   const [queueLoading, setQueueLoading] = useState(true);
//   const [refresh, setRefresh]           = useState(0);
//   const [activeTab, setActiveTab]       = useState<"trend"|"risk"|"alerts">("trend");

//   useEffect(() => {
//     if (!isLoaded || !user) return;
//     setAuthHeader(user.id);
//     setLoading(true); setQueueLoading(true);
//     Promise.all([
//       getClients().catch(()  => ({ data: { clients: [] } })),
//       getReports().catch(()  => ({ data: { reports: [] } })),
//     ]).then(([c, r]) => {
//       setClients(Array.isArray(c.data) ? c.data : c.data?.clients ?? []);
//       const rList = Array.isArray(r.data) ? r.data : r.data?.reports ?? [];
//       setReports(rList.sort((a: Report, b: Report) => new Date(b.created_at||0).getTime() - new Date(a.created_at||0).getTime()));
//     }).finally(() => setLoading(false));
//     Promise.all([
//       getNoticeQueue({ min_prob: 25, limit: 8 }).catch(() => ({ data: { queue: [] } })),
//       getNoticeQueueSummary().catch(() => ({ data: null })),
//     ]).then(([q, s]) => { setQueue(q.data?.queue ?? []); setQueueSummary(s.data ?? null); }).finally(() => setQueueLoading(false));
//   }, [isLoaded, user, refresh]);

//   const avgScore      = reports.length ? Math.round(reports.reduce((s,r)=>s+r.compliance_score,0)/reports.length) : null;
//   const highRiskCount = reports.filter(r=>r.compliance_score<60).length;
//   const totalItcRisk  = reports.reduce((s,r)=>s+(r.itc_summary?.at_risk??r.itc_at_risk??0),0);
//   const totalPenalty  = queueSummary?.total_estimated_penalty ?? 0;
//   const recentReports = reports.slice(0,5);
//   const formatItc = () => loading ? "—" : formatCurrency(totalItcRisk);

//   if (!isLoaded) return <div className="flex items-center justify-center min-h-[60vh]"><div className="w-8 h-8 border-[3px] border-blue-600 border-t-transparent rounded-full animate-spin"/></div>;

//   const statCards = [
//     { label:"Total Clients",    value:loading?"—":String(clients.length),                    icon:Users,         iconBg:"bg-blue-50",    iconColor:"text-blue-600",    link:"/clients", linkText:"View all →" },
//     { label:"Avg Score",        value:loading?"—":avgScore!=null?String(avgScore):"N/A",      icon:TrendingUp,    iconBg:"bg-emerald-50", iconColor:"text-emerald-600", valueColor:avgScore?scoreColor(avgScore):"text-slate-400", sub:`${reports.length} audits` },
//     { label:"High Risk",        value:loading?"—":String(highRiskCount),                      icon:AlertTriangle, iconBg:"bg-red-50",     iconColor:"text-red-500",     valueColor:highRiskCount>0?"text-red-500":"text-emerald-600", sub:highRiskCount>0?"Action needed":"All healthy" },
//     { label:"ITC at Risk",      value:formatItc(),                                             icon:ShieldAlert,   iconBg:"bg-amber-50",   iconColor:"text-amber-600",   valueColor:"text-amber-600", sub:"Across all clients" },
//     { label:"Penalty Exposure", value:queueLoading?"—":formatCurrency(totalPenalty),          icon:IndianRupee,   iconBg:"bg-rose-50",    iconColor:"text-rose-600",    valueColor:totalPenalty>0?"text-rose-600":"text-emerald-600", sub:"Estimated total" },
//   ];
//   const chartTabs = [{key:"trend",label:"Score Trend",icon:TrendingUp},{key:"risk",label:"Risk Split",icon:BarChart3},{key:"alerts",label:"Alert Summary",icon:ShieldAlert}] as const;

//   return (
//     <div className="px-4 py-5 lg:px-8 lg:py-8 max-w-6xl mx-auto">
//       {/* Header */}
//       <div className="flex items-start justify-between mb-6 lg:mb-8 animate-fade-in">
//         <div>
//           <h1 className="text-2xl lg:text-3xl font-bold text-slate-900 tracking-tight">Welcome back, {user?.firstName||"CA"}</h1>
//           <p className="text-slate-500 mt-1 text-sm">GST compliance overview</p>
//         </div>
//         <button onClick={()=>setRefresh(r=>r+1)} className="flex items-center gap-1.5 text-slate-400 hover:text-slate-600 text-xs mt-2 transition-colors">
//           <RefreshCw size={13} className={loading?"animate-spin":""}/><span className="hidden sm:inline">Refresh</span>
//         </button>
//       </div>

//       {/* Mobile stat list */}
//       <div className="lg:hidden bg-white rounded-2xl border border-slate-200/80 mb-5 divide-y divide-slate-100 shadow-sm animate-slide-up">
//         {statCards.map((card,i)=>{ const Icon=card.icon; return (
//           <div key={i} className="flex items-center justify-between px-4 py-3.5">
//             <div className="flex items-center gap-3">
//               <div className={`w-9 h-9 ${card.iconBg} rounded-xl flex items-center justify-center`}><Icon size={16} className={card.iconColor}/></div>
//               <div><span className="text-sm text-slate-600 font-medium">{card.label}</span>{card.sub&&<p className="text-[10px] text-slate-400">{card.sub}</p>}</div>
//             </div>
//             <span className={`text-xl font-bold ${(card as any).valueColor||"text-slate-900"}`}>{card.value}</span>
//           </div>
//         );})}
//       </div>

//       {/* Desktop stat grid */}
//       <div className="hidden lg:grid grid-cols-5 gap-4 mb-6">
//         {statCards.map((card,i)=>{ const Icon=card.icon; return (
//           <div key={i} className="stat-card p-4 animate-slide-up" style={{animationDelay:`${i*60}ms`}}>
//             <div className="flex items-center justify-between mb-3">
//               <p className="text-xs text-slate-500 font-medium">{card.label}</p>
//               <div className={`w-8 h-8 ${card.iconBg} rounded-xl flex items-center justify-center`}><Icon size={14} className={card.iconColor}/></div>
//             </div>
//             <p className={`text-2xl font-bold ${(card as any).valueColor||"text-slate-900"} tracking-tight`}>{card.value}</p>
//             <div className="mt-1.5">{card.link ? <Link href={card.link} className="text-xs text-blue-600 hover:underline font-medium">{card.linkText}</Link> : <p className="text-xs text-slate-400">{card.sub}</p>}</div>
//           </div>
//         );})}
//       </div>

//       {/* Notice Queue + Analytics */}
//       <div className="grid grid-cols-1 lg:grid-cols-5 gap-5 mb-5">
//         <div className="lg:col-span-3 bg-white border border-slate-200/80 rounded-2xl p-5 shadow-sm animate-slide-up" style={{animationDelay:"180ms"}}>
//           <div className="flex items-center justify-between mb-4">
//             <div className="flex items-center gap-2">
//               <div className="w-7 h-7 bg-red-50 rounded-lg flex items-center justify-center"><Bell size={13} className="text-red-500"/></div>
//               <div>
//                 <h2 className="font-bold text-sm text-slate-900">Action Required</h2>
//                 {queueSummary&&queueSummary.clients_needing_action>0&&<p className="text-[10px] text-red-500 font-semibold">{queueSummary.clients_needing_action} client{queueSummary.clients_needing_action>1?"s":""} need attention</p>}
//               </div>
//             </div>
//             {queueSummary&&(
//               <div className="hidden sm:flex items-center gap-1.5">
//                 {queueSummary.by_risk_level.very_high>0&&<span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-red-50 text-red-600 border border-red-200">{queueSummary.by_risk_level.very_high} V.High</span>}
//                 {queueSummary.by_risk_level.high>0&&<span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-orange-50 text-orange-600 border border-orange-200">{queueSummary.by_risk_level.high} High</span>}
//               </div>
//             )}
//           </div>
//           <NoticeRiskQueue queue={queue} loading={queueLoading}/>
//         </div>

//         {reports.length>0&&(
//           <div className="lg:col-span-2 bg-white border border-slate-200/80 rounded-2xl p-5 shadow-sm animate-slide-up" style={{animationDelay:"220ms"}}>
//             <div className="flex items-center justify-between mb-4">
//               <h2 className="font-bold text-sm text-slate-900">Analytics</h2>
//               <div className="flex gap-1">
//                 {chartTabs.map(tab=>{ const Icon=tab.icon; return (
//                   <button key={tab.key} onClick={()=>setActiveTab(tab.key)} className={`flex items-center gap-1 px-2 py-1.5 rounded-lg text-[10px] font-semibold transition-all ${activeTab===tab.key?"bg-blue-600 text-white shadow-sm":"text-slate-500 hover:bg-slate-100"}`}>
//                     <Icon size={10}/><span className="hidden xl:inline">{tab.label.split(" ")[0]}</span>
//                   </button>
//                 );})}
//               </div>
//             </div>
//             <div className="min-h-[140px]">
//               {loading ? <div className="h-36 animate-shimmer rounded-xl"/> : activeTab==="trend" ? <ScoreTrendChart reports={reports}/> : activeTab==="risk" ? <RiskPieChart reports={reports}/> : <AlertBarChart reports={reports}/>}
//             </div>
//           </div>
//         )}
//       </div>

//       {/* CTA */}
//       <div className="brand-gradient rounded-2xl p-5 lg:p-6 mb-5 flex items-center justify-between gap-4 animate-slide-up shadow-lg shadow-blue-600/10" style={{animationDelay:"280ms"}}>
//         <div className="min-w-0">
//           <div className="flex items-center gap-2 mb-1"><Zap size={16} className="text-yellow-300"/><p className="font-bold text-white text-sm lg:text-base">Run a New Audit</p></div>
//           <p className="text-blue-200 text-xs">Upload Excel, PDF, images, or Tally XML — results in 2 min</p>
//         </div>
//         <button onClick={()=>router.push("/upload")} className="flex items-center gap-2 bg-white text-blue-600 font-semibold px-5 py-2.5 rounded-xl text-sm hover:bg-blue-50 shrink-0 btn-press transition-all shadow-sm">
//           <Upload size={15}/> Upload
//         </button>
//       </div>

//       {/* Recent Audits + Clients */}
//       <div className="grid grid-cols-1 lg:grid-cols-5 gap-5 lg:gap-6">
//         <div className="lg:col-span-3 bg-white border border-slate-200/80 rounded-2xl p-5 shadow-sm animate-slide-up" style={{animationDelay:"360ms"}}>
//           <div className="flex items-center justify-between mb-4">
//             <h2 className="font-bold text-base text-slate-900">Recent Audits</h2>
//             <Link href="/reports" className="text-xs text-blue-600 hover:underline font-medium flex items-center gap-1">View all <ArrowUpRight size={11}/></Link>
//           </div>
//           {loading ? <div className="space-y-3">{[1,2,3].map(i=><div key={i} className="h-14 animate-shimmer rounded-xl"/>)}</div>
//           : recentReports.length===0 ? (
//             <div className="text-center py-10">
//               <div className="w-12 h-12 bg-slate-100 rounded-2xl flex items-center justify-center mx-auto mb-3"><TrendingUp size={20} className="text-slate-300"/></div>
//               <p className="text-slate-400 text-sm">No audits yet</p>
//               <button onClick={()=>router.push("/upload")} className="text-blue-600 text-xs mt-2 hover:underline font-medium">Run your first audit →</button>
//             </div>
//           ) : (
//             <div className="space-y-2">
//               {recentReports.map(r=>(
//                 <div key={r.id} onClick={()=>router.push(`/reports/${r.id}`)} className="flex items-center gap-3 p-3 rounded-xl hover:bg-slate-50 cursor-pointer active:bg-slate-100 transition-all group">
//                   <div className={`w-10 h-10 rounded-xl flex items-center justify-center font-bold text-sm score-ring ${scoreBg(r.compliance_score)}`}>{r.compliance_score}</div>
//                   <div className="flex-1 min-w-0">
//                     <p className="text-sm font-medium text-slate-900 truncate group-hover:text-blue-600 transition-colors">{r.client_name||"Audit"} · {r.period||"—"}</p>
//                     <div className="w-full bg-slate-100 rounded-full h-1 mt-1.5"><div className={`h-1 rounded-full ${progressColor(r.compliance_score)} transition-all`} style={{width:`${r.compliance_score}%`}}/></div>
//                   </div>
//                   <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold border shrink-0 ${riskBadge(r.compliance_score)}`}>{riskLabel(r.compliance_score)}</span>
//                 </div>
//               ))}
//             </div>
//           )}
//         </div>

//         <div className="lg:col-span-2 bg-white border border-slate-200/80 rounded-2xl p-5 shadow-sm animate-slide-up" style={{animationDelay:"440ms"}}>
//           <div className="flex items-center justify-between mb-4">
//             <h2 className="font-bold text-base text-slate-900">Clients</h2>
//             <Link href="/clients" className="text-xs text-blue-600 hover:underline font-medium flex items-center gap-1">View all <ArrowUpRight size={11}/></Link>
//           </div>
//           {loading ? <div className="space-y-3">{[1,2,3].map(i=><div key={i} className="h-11 animate-shimmer rounded-xl"/>)}</div>
//           : clients.length===0 ? (
//             <div className="text-center py-10">
//               <div className="w-12 h-12 bg-slate-100 rounded-2xl flex items-center justify-center mx-auto mb-3"><Users size={20} className="text-slate-300"/></div>
//               <p className="text-slate-400 text-sm">No clients added yet</p>
//               <Link href="/clients" className="text-blue-600 text-xs mt-2 inline-block hover:underline font-medium">Add your first client →</Link>
//             </div>
//           ) : (
//             <div className="space-y-1.5">
//               {clients.slice(0,5).map(c=>{ const initials=c.business_name.split(" ").slice(0,2).map(w=>w[0]).join("").toUpperCase(); return (
//                 <div key={c.id} onClick={()=>router.push(`/upload?client_id=${c.id}`)} className="flex items-center gap-3 p-2.5 rounded-xl hover:bg-slate-50 cursor-pointer active:bg-slate-100 transition-all">
//                   <div className="w-8 h-8 bg-blue-100 text-blue-700 rounded-lg flex items-center justify-center text-[10px] font-bold shrink-0">{initials}</div>
//                   <div className="flex-1 min-w-0">
//                     <p className="text-xs font-medium text-slate-900 truncate">{c.business_name}</p>
//                     {c.sector&&<p className="text-[10px] text-slate-400 truncate capitalize">{c.sector.replace("_"," ")}</p>}
//                   </div>
//                   {c.last_score!=null ? <span className={`text-xs font-bold ${scoreColor(c.last_score)}`}>{c.last_score}</span> : <span className="text-[10px] text-slate-300">—</span>}
//                 </div>
//               );})}
//             </div>
//           )}
//           <button onClick={()=>router.push("/upload")} className="w-full mt-4 py-2.5 border-2 border-dashed border-slate-200 rounded-xl text-xs text-slate-400 hover:border-blue-300 hover:text-blue-500 btn-press transition-all">+ Run new audit</button>
//         </div>
//       </div>
//     </div>
//   );
// }
"use client";

import { useEffect, useState } from "react";
import { useUser }   from "@clerk/nextjs";
import { useRouter } from "next/navigation";

import DashboardCore from "@/components/dashboard/DashboardCore";
import { setAuthHeader, getClients, getReports, getNoticeQueue, getNoticeQueueSummary } from "@/lib/api";

type Client       = Parameters<typeof DashboardCore>[0]["clients"][number];
type Report       = Parameters<typeof DashboardCore>[0]["reports"][number];
type QueueItem    = Parameters<typeof DashboardCore>[0]["queue"][number];
type QueueSummary = Parameters<typeof DashboardCore>[0]["queueSummary"];

export default function DashboardPage() {
  const { user, isLoaded } = useUser();
  const router = useRouter();

  const [clients,      setClients]      = useState<Client[]>([]);
  const [reports,      setReports]      = useState<Report[]>([]);
  const [queue,        setQueue]        = useState<QueueItem[]>([]);
  const [queueSummary, setQueueSummary] = useState<QueueSummary>(null);
  const [loading,      setLoading]      = useState(true);
  const [queueLoading, setQueueLoading] = useState(true);
  const [refresh,      setRefresh]      = useState(0);

  useEffect(() => {
    if (!isLoaded || !user) return;
    setAuthHeader(user.id);

    setLoading(true);
    setQueueLoading(true);

    Promise.all([
      getClients().catch(() => ({ data: { clients: [] } })),
      getReports().catch(() => ({ data: { reports: [] } })),
    ]).then(([c, r]) => {
      setClients(Array.isArray(c.data) ? c.data : c.data?.clients ?? []);
      const rList = Array.isArray(r.data) ? r.data : r.data?.reports ?? [];
      setReports(
        rList.sort((a: Report, b: Report) =>
          new Date(b.created_at ?? 0).getTime() - new Date(a.created_at ?? 0).getTime()
        )
      );
    }).finally(() => setLoading(false));

    Promise.all([
      getNoticeQueue({ min_prob: 25, limit: 8 }).catch(() => ({ data: { queue: [] } })),
      getNoticeQueueSummary().catch(() => ({ data: null })),
    ]).then(([q, s]) => {
      setQueue(q.data?.queue ?? []);
      setQueueSummary(s.data ?? null);
    }).finally(() => setQueueLoading(false));
  }, [isLoaded, user, refresh]);

  if (!isLoaded) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="w-8 h-8 border-[3px] border-blue-600 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <DashboardCore
      clients={clients}
      reports={reports}
      queue={queue}
      queueSummary={queueSummary}
      loading={loading}
      queueLoading={queueLoading}
      userName={user?.firstName ?? "CA"}
      onRefresh={() => setRefresh(r => r + 1)}
      onUpload={() => router.push("/upload")}
      onReportClick={(id) => router.push(`/reports/${id}`)}
      onClientClick={(id) => router.push(`/upload?client_id=${id}`)}
    />
  );
}
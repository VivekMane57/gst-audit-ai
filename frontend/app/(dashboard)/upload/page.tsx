"use client";
import { useState, useEffect, useRef } from "react";
import { useUser } from "@clerk/nextjs";
import { useRouter, useSearchParams } from "next/navigation";
import {
  FileSpreadsheet, CheckCircle, Loader2, ChevronRight,
  FileText, Camera, FileCode, Plus, X, File as FileIcon, Sparkles,
} from "lucide-react";
import { runAudit, getClient, getAuditStatus, setAuthHeader, api } from "@/lib/api";

const SECTORS = [
  { value: "",              label: "General",          icon: "📊" },
  { value: "healthcare",    label: "Healthcare",       icon: "🏥" },
  { value: "retail",        label: "Retail / Trading", icon: "🛒" },
  { value: "manufacturing", label: "Manufacturing",    icon: "🏭" },
  { value: "it_services",   label: "IT / Services",    icon: "💻" },
  { value: "real_estate",   label: "Real Estate",      icon: "🏢" },
  { value: "restaurant",    label: "Restaurant",       icon: "🍽️" },
  { value: "export_import", label: "Export / Import",  icon: "🚢" },
];

const LANGUAGES = [
  { value: "en", label: "English", flag: "🇬🇧" },
  { value: "hi", label: "हिन्दी",  flag: "🇮🇳" },
  { value: "mr", label: "मराठी",   flag: "🇮🇳" },
];

const FILE_BADGES: Record<string, { icon: any; bg: string; text: string; label: string }> = {
  xlsx: { icon: FileSpreadsheet, bg: "bg-emerald-50", text: "text-emerald-600", label: "Excel" },
  xls:  { icon: FileSpreadsheet, bg: "bg-emerald-50", text: "text-emerald-600", label: "Excel" },
  csv:  { icon: FileSpreadsheet, bg: "bg-emerald-50", text: "text-emerald-600", label: "CSV" },
  pdf:  { icon: FileText,        bg: "bg-red-50",     text: "text-red-500",     label: "PDF" },
  jpg:  { icon: Camera,          bg: "bg-sky-50",     text: "text-sky-500",     label: "Photo" },
  jpeg: { icon: Camera,          bg: "bg-sky-50",     text: "text-sky-500",     label: "Photo" },
  png:  { icon: Camera,          bg: "bg-sky-50",     text: "text-sky-500",     label: "Photo" },
  webp: { icon: Camera,          bg: "bg-sky-50",     text: "text-sky-500",     label: "Photo" },
  xml:  { icon: FileCode,        bg: "bg-violet-50",  text: "text-violet-500",  label: "Tally XML" },
};

function getFileBadge(name: string) {
  const ext = name.split(".").pop()?.toLowerCase() || "";
  return FILE_BADGES[ext] || { icon: FileIcon, bg: "bg-slate-50", text: "text-slate-500", label: ext.toUpperCase() };
}
function formatSize(b: number) {
  if (b < 1024) return `${b} B`;
  if (b < 1048576) return `${(b / 1024).toFixed(0)} KB`;
  return `${(b / 1048576).toFixed(1)} MB`;
}

type Step = 1 | 2 | 3;

export default function UploadPage() {
  const { user, isLoaded }    = useUser();
  const router                = useRouter();
  const params                = useSearchParams();
  const prefilledClientId     = params.get("client_id") || "";

  const [step, setStep]               = useState<Step>(1);
  const [salesFile, setSalesFile]     = useState<File | null>(null);
  const [purchaseFile, setPurchaseFile] = useState<File | null>(null);
  const [extraFiles, setExtraFiles]   = useState<File[]>([]);
  const [gstin, setGstin]             = useState("");
  const [period, setPeriod]           = useState("");
  const [language, setLanguage]       = useState("en");
  const [sector, setSector]           = useState("");
  const [clientId, setClientId]       = useState(prefilledClientId);
  const [clientName, setClientName]   = useState("");
  const [loading, setLoading]         = useState(false);
  const [error, setError]             = useState("");
  const [auditId, setAuditId]         = useState("");
  const [statusMsg, setStatusMsg]     = useState("Uploading files...");

  const salesRef    = useRef<HTMLInputElement>(null);
  const purchaseRef = useRef<HTMLInputElement>(null);
  const extraRef    = useRef<HTMLInputElement>(null);
  const ACCEPTED    = ".xlsx,.xls,.csv,.pdf,.jpg,.jpeg,.png,.webp,.xml";

  useEffect(() => {
    if (!prefilledClientId || !isLoaded || !user) return;
    setAuthHeader(user.id);
    getClient(prefilledClientId).then((r) => {
      const c = r.data;
      setClientName(c.business_name || "");
      if (c.sector) setSector(c.sector);
      if (c.gstin)  setGstin(c.gstin);
    }).catch(() => {});
  }, [prefilledClientId, isLoaded, user]);

  // ── Safely extract audit_id from ANY response shape ────────
  const extractAuditId = (data: any): string | null => {
    const candidates = [
      data?.audit_id,
      data?.result?.audit_id,
      data?.info?.audit_id,
      data?.data?.audit_id,
    ];
    for (const id of candidates) {
      if (id && typeof id === "string" && id !== "undefined" && id.length > 8) {
        return id;
      }
    }
    return null;
  };

  // ── Poll every 3s until audit_id mila ─────────────────────
  const pollUntilDone = async (taskId: string): Promise<string> => {
    const MAX = 60; // 60 × 3s = 3 min

    for (let i = 0; i < MAX; i++) {
      await new Promise(r => setTimeout(r, 3000));
      const pct = Math.min(Math.round(((i + 1) / MAX) * 90) + 5, 95);
      setStatusMsg(`Analysing files... ${pct}%`);

      try {
        const res  = await getAuditStatus(taskId);
        const data = res.data;
        const st   = (data.status || "").toLowerCase();

        console.log(`[Poll ${i + 1}] status=${st}`, data);

        // ── Completed ────────────────────────────────────────
        if (["completed", "complete", "success"].includes(st)) {
          const id = extractAuditId(data);
          if (id) return id;
          // Retry once — DB might need 1s
          await new Promise(r => setTimeout(r, 2000));
          const r2   = await getAuditStatus(taskId);
          const id2  = extractAuditId(r2.data);
          if (id2) return id2;
          throw new Error("Audit done but report ID nahi mila. Reports page check karo.");
        }

        // ── Failed ───────────────────────────────────────────
        if (["failed", "failure"].includes(st)) {
          throw new Error(data.error || data.info || "Background audit failed. Retry karo.");
        }

        // ── Still running → keep polling ─────────────────────

      } catch (err: any) {
        if (err?.message && !err?.response) continue; // network glitch
        throw err;
      }
    }
    throw new Error("Audit 3 minute mein complete nahi hua. Reports page check karo.");
  };

  // ── Submit handler ────────────────────────────────────────
  const handleRunAudit = async () => {
    if (!salesFile && !purchaseFile && extraFiles.length === 0)
      return setError("Upload at least one file");
    if (!gstin || gstin.length !== 15)
      return setError("Enter valid 15-char GSTIN");
    if (!period)
      return setError("Select period");
    if (!isLoaded || !user)
      return setError("Please wait...");

    setError(""); setLoading(true); setStatusMsg("Uploading files..."); setStep(3);

    try {
      setAuthHeader(user.id);
      api.defaults.headers.common["x-user-email"] = user.primaryEmailAddress?.emailAddress || "";
      api.defaults.headers.common["x-user-name"]  = user.fullName || user.firstName || "CA";

      const form = new FormData();
      if (salesFile)    form.append("sales_file", salesFile);
      if (purchaseFile) form.append("purchase_file", purchaseFile);
      extraFiles.forEach(f => form.append("extra_files", f));
      form.append("our_gstin", gstin.toUpperCase());
      form.append("period", period);
      form.append("language", language);
      if (sector)   form.append("sector", sector);
      if (clientId) form.append("client_id", clientId);

      // Submit
      const res     = await runAudit(form);
      const resData = res.data;
      console.log("[Submit Response]", resData);

      // Case A: Sync result (Redis nahi tha — direct audit_id)
      const directId = extractAuditId(resData);
      if (directId && resData.status !== "queued") {
        setAuditId(directId);
        setLoading(false);
        return;
      }

      // Case B: Async — task_id se poll karo
      const taskId = resData?.task_id;
      if (!taskId || taskId === "undefined") {
        throw new Error("Server se task_id nahi mila. Please retry.");
      }

      setStatusMsg("Audit queued, processing...");
      const finalId = await pollUntilDone(taskId);
      setStatusMsg("Complete! ✅");
      setAuditId(finalId);

    } catch (e: any) {
      const detail = e?.response?.data?.detail;
      const msg =
        typeof detail === "string" ? detail :
        Array.isArray(detail)      ? detail.map((d: any) => d?.msg || "Error").join(", ") :
        e?.message                 || "Audit failed. Please retry.";
      setError(msg);
      setStep(2);
    } finally {
      setLoading(false);
    }
  };

  const totalFiles  = (salesFile ? 1 : 0) + (purchaseFile ? 1 : 0) + extraFiles.length;
  const totalChecks = 6 + (sector ? 4 : 0);
  const steps       = [{ n: 1, l: "Upload" }, { n: 2, l: "Configure" }, { n: 3, l: "Results" }];

  const FileCard = ({ file, onRemove }: { file: File; onRemove?: () => void }) => {
    const b = getFileBadge(file.name);
    const Icon = b.icon;
    return (
      <div className="flex items-center gap-3 bg-white border border-slate-200 rounded-xl px-3 py-2.5">
        <div className={`w-9 h-9 rounded-lg flex items-center justify-center ${b.bg}`}>
          <Icon size={15} className={b.text} />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-xs font-semibold text-slate-900 truncate">{file.name}</p>
          <p className="text-[10px] text-slate-400">{b.label} · {formatSize(file.size)}</p>
        </div>
        {onRemove && (
          <button onClick={(e) => { e.stopPropagation(); onRemove(); }}
            className="p-1.5 hover:bg-red-50 rounded-lg text-slate-300 hover:text-red-400 transition-colors">
            <X size={13} />
          </button>
        )}
      </div>
    );
  };

  return (
    <div className="px-4 py-5 lg:px-8 lg:py-8 max-w-2xl mx-auto">

      {/* Header */}
      <div className="mb-5 lg:mb-8">
        <h1 className="text-2xl lg:text-3xl font-bold text-slate-900 tracking-tight">New Audit</h1>
        {clientName && <p className="text-blue-600 font-medium mt-1 text-sm">📁 {clientName}</p>}
        <p className="text-slate-500 text-xs lg:text-sm mt-1">
          Upload Excel, PDF, images, or Tally XML → {totalChecks} checks → 2 minutes
        </p>
      </div>

      {/* Stepper */}
      <div className="flex items-center gap-0 mb-6 lg:mb-8">
        {steps.map((s, i) => (
          <div key={s.n} className="flex items-center flex-1">
            <div className="flex items-center gap-1.5">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold transition-all
                ${step > s.n  ? "bg-emerald-500 text-white" :
                  step === s.n ? "brand-gradient text-white" :
                  "bg-slate-100 text-slate-400"}`}>
                {step > s.n ? "✓" : s.n}
              </div>
              <span className={`text-xs font-semibold hidden sm:block ${step === s.n ? "text-blue-600" : "text-slate-400"}`}>
                {s.l}
              </span>
            </div>
            {i < steps.length - 1 && (
              <div className={`flex-1 h-[2px] mx-3 rounded-full ${step > s.n ? "bg-emerald-400" : "bg-slate-200"}`} />
            )}
          </div>
        ))}
      </div>

      {/* STEP 1 */}
      {step === 1 && (
        <div className="space-y-3">
          <div className="flex flex-wrap gap-1.5 mb-2">
            {[
              { label: "Excel",     bg: "bg-emerald-50", text: "text-emerald-600" },
              { label: "PDF",       bg: "bg-red-50",     text: "text-red-500" },
              { label: "Images",    bg: "bg-sky-50",     text: "text-sky-500" },
              { label: "Tally XML", bg: "bg-violet-50",  text: "text-violet-500" },
            ].map(f => (
              <span key={f.label} className={`px-2.5 py-1 ${f.bg} ${f.text} text-[10px] font-semibold rounded-full`}>
                {f.label}
              </span>
            ))}
          </div>

          <div onClick={() => salesRef.current?.click()}
            className={`border-2 border-dashed rounded-2xl p-5 cursor-pointer transition-all
              ${salesFile ? "border-emerald-300 bg-emerald-50/50" : "border-slate-200 hover:border-blue-300 hover:bg-blue-50/30"}`}>
            <input ref={salesRef} type="file" accept={ACCEPTED} className="hidden"
              onChange={e => setSalesFile(e.target.files?.[0] || null)} />
            {salesFile ? <FileCard file={salesFile} onRemove={() => setSalesFile(null)} /> : (
              <div className="text-center py-2">
                <FileSpreadsheet className="text-slate-300 mx-auto mb-2" size={24} />
                <p className="font-semibold text-slate-700 text-sm">Sales Register</p>
                <p className="text-[11px] text-slate-400 mt-0.5">GSTR-1 data · Any format</p>
              </div>
            )}
          </div>

          <div onClick={() => purchaseRef.current?.click()}
            className={`border-2 border-dashed rounded-2xl p-5 cursor-pointer transition-all
              ${purchaseFile ? "border-emerald-300 bg-emerald-50/50" : "border-slate-200 hover:border-blue-300 hover:bg-blue-50/30"}`}>
            <input ref={purchaseRef} type="file" accept={ACCEPTED} className="hidden"
              onChange={e => setPurchaseFile(e.target.files?.[0] || null)} />
            {purchaseFile ? <FileCard file={purchaseFile} onRemove={() => setPurchaseFile(null)} /> : (
              <div className="text-center py-2">
                <FileSpreadsheet className="text-slate-300 mx-auto mb-2" size={24} />
                <p className="font-semibold text-slate-700 text-sm">Purchase Register</p>
                <p className="text-[11px] text-slate-400 mt-0.5">GSTR-2B data · Any format</p>
              </div>
            )}
          </div>

          <div className="bg-slate-50/80 rounded-2xl p-4 border border-slate-100">
            <div className="flex items-center justify-between mb-2">
              <p className="text-xs font-semibold text-slate-700">
                Additional Files
                {extraFiles.length > 0 && (
                  <span className="ml-1.5 px-1.5 py-0.5 bg-blue-100 text-blue-600 rounded-full text-[10px] font-bold">
                    {extraFiles.length}
                  </span>
                )}
              </p>
              <button onClick={() => extraRef.current?.click()}
                className="flex items-center gap-1 text-blue-600 text-[11px] font-semibold hover:underline">
                <Plus size={12} /> Add Files
              </button>
            </div>
            <input ref={extraRef} type="file" accept={ACCEPTED} multiple className="hidden"
              onChange={e => e.target.files && setExtraFiles(prev => [...prev, ...Array.from(e.target.files!)])} />
            {extraFiles.length === 0 ? (
              <p className="text-[11px] text-slate-400 text-center py-4">Add invoices, bills, photos</p>
            ) : (
              <div className="space-y-1.5 max-h-44 overflow-y-auto">
                {extraFiles.map((f, i) => (
                  <FileCard key={i} file={f} onRemove={() => setExtraFiles(prev => prev.filter((_, j) => j !== i))} />
                ))}
              </div>
            )}
          </div>

          {totalFiles > 0 && (
            <p className="text-xs text-slate-500 text-center font-medium">
              {totalFiles} file{totalFiles > 1 ? "s" : ""} selected
            </p>
          )}

          <button onClick={() => setStep(2)} disabled={totalFiles === 0}
            className="w-full py-3.5 brand-gradient text-white font-semibold rounded-xl disabled:opacity-40 flex items-center justify-center gap-2 text-sm shadow-sm shadow-blue-600/20">
            Next: Configure <ChevronRight size={16} />
          </button>
        </div>
      )}

      {/* STEP 2 */}
      {step === 2 && (
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-semibold text-slate-700 mb-1.5">
              GSTIN <span className="text-red-400">*</span>
            </label>
            <input type="text" value={gstin} onChange={e => setGstin(e.target.value.toUpperCase())}
              placeholder="27AABCS1234R1Z5" maxLength={15}
              className="w-full border border-slate-200 rounded-xl px-4 py-3 text-sm font-mono bg-white focus:outline-none" />
            <p className="text-[10px] text-slate-400 mt-1">{gstin.length}/15 characters</p>
          </div>

          <div>
            <label className="block text-sm font-semibold text-slate-700 mb-1.5">
              Period <span className="text-red-400">*</span>
            </label>
            <input type="month" value={period} onChange={e => setPeriod(e.target.value)}
              className="w-full border border-slate-200 rounded-xl px-4 py-3 text-sm bg-white focus:outline-none" />
          </div>

          <div>
            <label className="block text-sm font-semibold text-slate-700 mb-2">Report Language</label>
            <div className="flex gap-2">
              {LANGUAGES.map(l => (
                <button key={l.value} onClick={() => setLanguage(l.value)}
                  className={`flex-1 py-2.5 rounded-xl text-sm font-semibold border-2 transition-all
                    ${language === l.value ? "border-blue-500 bg-blue-50 text-blue-700" : "border-slate-200 text-slate-500"}`}>
                  <span className="mr-1">{l.flag}</span> {l.label}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-sm font-semibold text-slate-700 mb-2">
              Business Sector
              <span className="text-xs text-slate-400 font-normal ml-2">
                {sector ? "✅ 4 extra checks" : "optional"}
              </span>
            </label>
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-2">
              {SECTORS.map(s => (
                <button key={s.value} onClick={() => setSector(s.value)}
                  className={`p-3 rounded-xl border-2 text-center transition-all
                    ${sector === s.value ? "border-blue-500 bg-blue-50 shadow-sm" : "border-slate-200 hover:border-slate-300"}`}>
                  <div className="text-lg mb-0.5">{s.icon}</div>
                  <div className="text-[11px] font-semibold text-slate-700 leading-tight">{s.label}</div>
                </button>
              ))}
            </div>
          </div>

          {error && (
            <p className="text-sm text-red-500 bg-red-50 px-4 py-3 rounded-xl border border-red-100">{error}</p>
          )}

          <div className="flex gap-3 pt-2">
            <button onClick={() => setStep(1)}
              className="flex-1 py-3 border border-slate-200 rounded-xl text-sm font-semibold text-slate-600 hover:bg-slate-50">
              Back
            </button>
            <button onClick={handleRunAudit} disabled={loading}
              className="flex-grow-[2] py-3 brand-gradient text-white font-semibold rounded-xl disabled:opacity-50 flex items-center justify-center gap-2 text-sm shadow-sm shadow-blue-600/20">
              <Sparkles size={15} /> Run {totalChecks} Checks
            </button>
          </div>
        </div>
      )}

      {/* STEP 3 */}
      {step === 3 && (
        <div className="text-center py-8">
          {loading ? (
            <>
              <div className="w-16 h-16 brand-gradient rounded-2xl flex items-center justify-center mx-auto mb-5 shadow-lg shadow-blue-600/20">
                <Loader2 className="text-white animate-spin" size={28} />
              </div>
              <p className="text-lg font-bold text-slate-900">{statusMsg}</p>
              <p className="text-slate-400 text-xs mt-1">Running {totalChecks} GST checks</p>
              <div className="mt-6 space-y-2 text-xs text-slate-400 text-left bg-slate-50 rounded-xl p-4 border border-slate-100">
                <p>✓ Smart file detection</p>
                <p>✓ GSTIN validation</p>
                <p>✓ Tax type check</p>
                <p>✓ Duplicate invoice detection</p>
                <p>✓ GSTR-2B missing invoices</p>
                <p>✓ Notice probability calculation</p>
                {sector && <p>✓ {SECTORS.find(s => s.value === sector)?.label} sector checks</p>}
              </div>
              <p className="text-[10px] text-slate-300 mt-3">Usually 30–90 seconds...</p>
            </>
          ) : error ? (
            <>
              <div className="w-16 h-16 bg-red-50 rounded-2xl flex items-center justify-center mx-auto mb-5">
                <X className="text-red-500" size={28} />
              </div>
              <p className="text-lg font-bold text-red-600">Audit Failed</p>
              <p className="text-sm text-slate-500 mt-2 mb-6">{error}</p>
              <button onClick={() => { setStep(2); setError(""); }}
                className="px-6 py-3 brand-gradient text-white rounded-xl font-semibold text-sm shadow-sm">
                Try Again
              </button>
            </>
          ) : (
            <>
              <div className="w-16 h-16 bg-emerald-50 rounded-2xl flex items-center justify-center mx-auto mb-5">
                <CheckCircle className="text-emerald-500" size={32} />
              </div>
              <p className="text-2xl font-bold text-slate-900">Audit Complete!</p>
              <p className="text-slate-500 mt-2 text-sm">
                {clientName ? `${clientName} · ` : ""}{period} · {totalFiles} files
              </p>
              <div className="flex gap-3 mt-8 justify-center">
                <button
                  onClick={() => {
                    if (auditId && auditId !== "undefined" && auditId.length > 8) {
                      router.push(`/reports/${auditId}`);
                    } else {
                      setError("Report ID nahi mila. Reports page check karo.");
                    }
                  }}
                  className="px-6 py-3 brand-gradient text-white rounded-xl font-semibold text-sm shadow-sm shadow-blue-600/20">
                  View Report →
                </button>
                <button onClick={() => {
                  setSalesFile(null); setPurchaseFile(null); setExtraFiles([]);
                  setGstin(clientId ? gstin : ""); setPeriod("");
                  setError(""); setAuditId(""); setStatusMsg("Uploading files..."); setStep(1);
                }} className="px-6 py-3 border border-slate-200 rounded-xl text-sm font-semibold text-slate-600">
                  New Audit
                </button>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
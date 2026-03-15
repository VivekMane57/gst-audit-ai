"use client";
import { useState, useEffect, useRef } from "react";
import { useUser } from "@clerk/nextjs";
import { useRouter, useSearchParams } from "next/navigation";
import { Upload, FileSpreadsheet, CheckCircle, Loader2, ChevronRight } from "lucide-react";
import { runAudit, getClient, setAuthHeader } from "@/lib/api";

const SECTORS = [
  { value: "",              label: "General",          icon: "📊", desc: "All businesses" },
  { value: "healthcare",    label: "Healthcare",       icon: "🏥", desc: "Pharma / Hospital" },
  { value: "retail",        label: "Retail / Trading", icon: "🛒", desc: "Shop / Wholesale" },
  { value: "manufacturing", label: "Manufacturing",    icon: "🏭", desc: "Factory / Production" },
  { value: "it_services",   label: "IT / Services",    icon: "💻", desc: "Software / Consulting" },
  { value: "real_estate",   label: "Real Estate",      icon: "🏢", desc: "Builder / Broker" },
  { value: "restaurant",    label: "Restaurant",       icon: "🍽️", desc: "Food / Hotel" },
  { value: "export_import", label: "Export / Import",  icon: "🚢", desc: "Trading / Logistics" },
];

const LANGUAGES = [
  { value: "en", label: "English" },
  { value: "hi", label: "Hindi" },
  { value: "mr", label: "Marathi" },
];

type Step = 1 | 2 | 3;

export default function UploadPage() {
  // ── FIX: isLoaded add kiya
  const { user, isLoaded } = useUser();
  const router  = useRouter();
  const params  = useSearchParams();

  const prefilledClientId = params.get("client_id") || "";

  const [step,         setStep]         = useState<Step>(1);
  const [salesFile,    setSalesFile]    = useState<File | null>(null);
  const [purchaseFile, setPurchaseFile] = useState<File | null>(null);
  const [gstin,        setGstin]        = useState("");
  const [period,       setPeriod]       = useState("");
  const [language,     setLanguage]     = useState("en");
  const [sector,       setSector]       = useState("");
  const [clientId,     setClientId]     = useState(prefilledClientId);
  const [clientName,   setClientName]   = useState("");
  const [loading,      setLoading]      = useState(false);
  const [error,        setError]        = useState("");
  const [auditId,      setAuditId]      = useState("");

  const salesRef    = useRef<HTMLInputElement>(null);
  const purchaseRef = useRef<HTMLInputElement>(null);

  // ── FIX: isLoaded check add kiya
  useEffect(() => {
    if (!prefilledClientId || !isLoaded || !user) return;
    setAuthHeader(user.id);
    getClient(prefilledClientId)
      .then((r) => {
        const c = r.data;
        setClientName(c.business_name || "");
        if (c.sector) setSector(c.sector);
        if (c.gstin)  setGstin(c.gstin);
      })
      .catch(() => {});
  }, [prefilledClientId, isLoaded, user]);

  const handleRunAudit = async () => {
    if (!salesFile || !purchaseFile) return setError("Both files required");
    if (!gstin || gstin.length !== 15) return setError("Enter valid 15-char GSTIN");
    if (!period) return setError("Select period");
    if (!isLoaded || !user) return setError("Please wait — logging in...");

    setError("");
    setLoading(true);
    setStep(3);

    try {
      setAuthHeader(user.id);

      const form = new FormData();
      form.append("sales_file",    salesFile);
      form.append("purchase_file", purchaseFile);
      form.append("our_gstin",     gstin.toUpperCase());
      form.append("period",        period);
      form.append("language",      language);
      if (sector)   form.append("sector",    sector);
      if (clientId) form.append("client_id", clientId);

      const res = await runAudit(form);
      setAuditId(res.data.audit_id);
    } catch (e: any) {
      // ── FIX: error always string — React object render crash fix
      const detail = e?.response?.data?.detail;
      const msg =
        typeof detail === "string"
          ? detail
          : Array.isArray(detail)
          ? detail.map((d: any) => d?.msg || "Validation error").join(", ")
          : typeof detail === "object" && detail !== null
          ? JSON.stringify(detail)
          : e?.message || "Audit failed. Please retry.";
      setError(msg);
      setStep(2);
    } finally {
      setLoading(false);
    }
  };

  const totalChecks = 6 + (sector ? 4 : 0);

  const steps = [
    { n: 1, label: "Upload Files" },
    { n: 2, label: "Configure" },
    { n: 3, label: "Results" },
  ];

  return (
    <div className="p-8 max-w-2xl mx-auto">

      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">New Audit</h1>
        {clientName && (
          <p className="text-blue-600 font-medium mt-1">📁 {clientName}</p>
        )}
        <p className="text-gray-500 text-sm mt-1">
          Upload sales + purchase Excel files → {totalChecks} checks → 2 minutes
        </p>
      </div>

      {/* Step bar */}
      <div className="flex items-center gap-0 mb-8">
        {steps.map((s, i) => (
          <div key={s.n} className="flex items-center flex-1">
            <div className="flex items-center gap-2">
              <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold transition-all
                ${step > s.n ? "bg-green-500 text-white" :
                  step === s.n ? "bg-blue-600 text-white" :
                  "bg-gray-200 text-gray-400"}`}
              >
                {step > s.n ? "✓" : s.n}
              </div>
              <span className={`text-xs font-medium hidden sm:block ${step === s.n ? "text-blue-600" : "text-gray-400"}`}>
                {s.label}
              </span>
            </div>
            {i < steps.length - 1 && (
              <div className={`flex-1 h-0.5 mx-2 ${step > s.n ? "bg-green-300" : "bg-gray-200"}`} />
            )}
          </div>
        ))}
      </div>

      {/* STEP 1: Upload files */}
      {step === 1 && (
        <div className="space-y-4">
          <div
            onClick={() => salesRef.current?.click()}
            className={`border-2 border-dashed rounded-2xl p-8 text-center cursor-pointer transition-all
              ${salesFile ? "border-green-400 bg-green-50" : "border-gray-200 hover:border-blue-400 hover:bg-blue-50"}`}
          >
            <input ref={salesRef} type="file" accept=".xlsx,.xls,.csv" className="hidden"
              onChange={e => setSalesFile(e.target.files?.[0] || null)} />
            {salesFile ? (
              <>
                <CheckCircle className="text-green-500 mx-auto mb-2" size={28} />
                <p className="font-semibold text-green-700">{salesFile.name}</p>
                <p className="text-xs text-green-500 mt-1">Sales register ready</p>
              </>
            ) : (
              <>
                <FileSpreadsheet className="text-gray-300 mx-auto mb-2" size={28} />
                <p className="font-semibold text-gray-700">Sales Register</p>
                <p className="text-xs text-gray-400 mt-1">GSTR-1 data · .xlsx / .csv</p>
              </>
            )}
          </div>

          <div
            onClick={() => purchaseRef.current?.click()}
            className={`border-2 border-dashed rounded-2xl p-8 text-center cursor-pointer transition-all
              ${purchaseFile ? "border-green-400 bg-green-50" : "border-gray-200 hover:border-blue-400 hover:bg-blue-50"}`}
          >
            <input ref={purchaseRef} type="file" accept=".xlsx,.xls,.csv" className="hidden"
              onChange={e => setPurchaseFile(e.target.files?.[0] || null)} />
            {purchaseFile ? (
              <>
                <CheckCircle className="text-green-500 mx-auto mb-2" size={28} />
                <p className="font-semibold text-green-700">{purchaseFile.name}</p>
                <p className="text-xs text-green-500 mt-1">Purchase register ready</p>
              </>
            ) : (
              <>
                <FileSpreadsheet className="text-gray-300 mx-auto mb-2" size={28} />
                <p className="font-semibold text-gray-700">Purchase Register</p>
                <p className="text-xs text-gray-400 mt-1">GSTR-2B data · .xlsx / .csv</p>
              </>
            )}
          </div>

          <button
            onClick={() => setStep(2)}
            disabled={!salesFile || !purchaseFile}
            className="w-full py-3 bg-blue-600 text-white font-semibold rounded-2xl hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            Next: Configure <ChevronRight size={16} />
          </button>
        </div>
      )}

      {/* STEP 2: Configure */}
      {step === 2 && (
        <div className="space-y-5">

          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-1">
              GSTIN <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={gstin}
              onChange={e => setGstin(e.target.value.toUpperCase())}
              placeholder="27AABCS1234R1Z5"
              maxLength={15}
              className="w-full border border-gray-300 rounded-xl px-4 py-3 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <p className="text-xs text-gray-400 mt-1">{gstin.length}/15 characters</p>
          </div>

          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-1">
              Period <span className="text-red-500">*</span>
            </label>
            <input
              type="month"
              value={period}
              onChange={e => setPeriod(e.target.value)}
              className="w-full border border-gray-300 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-2">Report Language</label>
            <div className="flex gap-2">
              {LANGUAGES.map(l => (
                <button key={l.value} onClick={() => setLanguage(l.value)}
                  className={`flex-1 py-2.5 rounded-xl text-sm font-medium border-2 transition-all
                    ${language === l.value ? "border-blue-500 bg-blue-50 text-blue-700" : "border-gray-200 text-gray-500 hover:border-gray-300"}`}>
                  {l.label}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-2">
              Business Sector
              <span className="text-xs text-gray-400 font-normal ml-2">
                ({sector ? "4 extra checks" : "select for sector-specific checks"})
              </span>
            </label>
            <div className="grid grid-cols-4 gap-2">
              {SECTORS.map(s => (
                <button key={s.value} onClick={() => setSector(s.value)}
                  className={`p-2.5 rounded-xl border-2 text-center transition-all
                    ${sector === s.value ? "border-blue-500 bg-blue-50" : "border-gray-200 hover:border-gray-300"}`}>
                  <div className="text-xl mb-0.5">{s.icon}</div>
                  <div className="text-xs font-medium text-gray-700 leading-tight">{s.label}</div>
                </button>
              ))}
            </div>
          </div>

          {/* ── FIX: error always string — never render object */}
          {error && (
            <p className="text-sm text-red-500 bg-red-50 px-4 py-2.5 rounded-xl">{error}</p>
          )}

          <div className="flex gap-3 pt-2">
            <button onClick={() => setStep(1)}
              className="flex-1 py-3 border border-gray-200 rounded-2xl text-sm font-medium text-gray-600 hover:bg-gray-50">
              Back
            </button>
            <button onClick={handleRunAudit} disabled={loading}
              className="flex-2 flex-grow-[2] py-3 bg-blue-600 text-white font-semibold rounded-2xl hover:bg-blue-700 disabled:opacity-50 flex items-center justify-center gap-2">
              <Upload size={16} />
              Run {totalChecks} Checks
            </button>
          </div>
        </div>
      )}

      {/* STEP 3: Result */}
      {step === 3 && (
        <div className="text-center py-12">
          {loading ? (
            <>
              <Loader2 className="text-blue-600 mx-auto mb-4 animate-spin" size={44} />
              <p className="text-lg font-bold text-gray-900">Running {totalChecks} checks...</p>
              <p className="text-gray-400 text-sm mt-2">
                Analysing {salesFile?.name} + {purchaseFile?.name}
              </p>
              <div className="mt-6 space-y-2 text-xs text-gray-400 text-left bg-gray-50 rounded-2xl p-4">
                <p>✓ GSTIN validation</p>
                <p>✓ Tax type check (IGST vs CGST+SGST)</p>
                <p>✓ Duplicate invoice detection</p>
                <p>✓ GSTR-2B missing invoices</p>
                <p>✓ Amount mismatch (books vs 2B)</p>
                <p>✓ GSTR-1 missing invoices</p>
                {sector && <p>✓ {SECTORS.find(s => s.value === sector)?.label} sector checks</p>}
              </div>
            </>
          ) : error ? (
            <>
              <div className="text-4xl mb-4">❌</div>
              <p className="text-lg font-bold text-red-600">Audit Failed</p>
              <p className="text-sm text-gray-500 mt-2 mb-6">{error}</p>
              <button onClick={() => { setStep(2); setError(""); }}
                className="px-6 py-3 bg-blue-600 text-white rounded-2xl font-semibold hover:bg-blue-700">
                Try Again
              </button>
            </>
          ) : (
            <>
              <CheckCircle className="text-green-500 mx-auto mb-4" size={52} />
              <p className="text-2xl font-bold text-gray-900">Audit Complete! 🎉</p>
              <p className="text-gray-500 mt-2">
                {clientName ? `${clientName} · ` : ""}{period}
              </p>
              <div className="flex gap-3 mt-8 justify-center">
                <button onClick={() => router.push(`/reports/${auditId}`)}
                  className="px-6 py-3 bg-blue-600 text-white rounded-2xl font-semibold hover:bg-blue-700">
                  View Report →
                </button>
                <button
                  onClick={() => {
                    setSalesFile(null); setPurchaseFile(null);
                    setGstin(clientId ? gstin : "");
                    setPeriod(""); setError(""); setAuditId("");
                    setStep(1);
                  }}
                  className="px-6 py-3 border border-gray-200 rounded-2xl text-sm font-medium text-gray-600 hover:bg-gray-50">
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
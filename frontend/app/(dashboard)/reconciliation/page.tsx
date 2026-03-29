"use client";

import { useState } from "react";
import { runReconciliation } from "@/lib/api";
import type {
  ReconciliationResult,
  MatchedInvoice,
  MissingInvoice,
  MismatchedInvoice,
  RiskLevel,
} from "@/lib/type";

const inr = (n: number) =>
  new Intl.NumberFormat("en-IN", {
    style: "currency", currency: "INR", maximumFractionDigits: 0,
  }).format(n);

const RISK_BADGE: Record<RiskLevel, string> = {
  LOW:      "bg-emerald-100 text-emerald-700 ring-emerald-200",
  MEDIUM:   "bg-amber-100 text-amber-700 ring-amber-200",
  HIGH:     "bg-orange-100 text-orange-700 ring-orange-200",
  CRITICAL: "bg-red-100 text-red-700 ring-red-200",
};

const RISK_BORDER: Record<RiskLevel, string> = {
  LOW:      "border-emerald-400",
  MEDIUM:   "border-amber-400",
  HIGH:     "border-orange-400",
  CRITICAL: "border-red-500",
};

type Tab = "missing" | "mismatched" | "matched";

export default function ReconciliationPage() {
  const [purchaseFile, setPurchaseFile] = useState<File | null>(null);
  const [gstr2bFile,   setGstr2bFile]   = useState<File | null>(null);
  const [gstin,        setGstin]        = useState("");
  const [period,       setPeriod]       = useState("");
  const [language,     setLanguage]     = useState<"en" | "hi" | "mr">("en");
  const [loading,      setLoading]      = useState(false);
  const [error,        setError]        = useState<string | null>(null);
  const [result,       setResult]       = useState<ReconciliationResult | null>(null);
  const [activeTab,    setActiveTab]    = useState<Tab>("missing");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!purchaseFile || !gstr2bFile) { setError("Dono files select karo."); return; }
    if (!gstin || !period)            { setError("GSTIN aur Period required hai."); return; }
    setLoading(true); setError(null); setResult(null);
    try {
      const form = new FormData();
      form.append("purchase_file", purchaseFile);
      form.append("gstr2b_file",   gstr2bFile);
      form.append("our_gstin",     gstin.trim().toUpperCase());
      form.append("period",        period);
      form.append("language",      language);
      form.append("amount_tolerance", "1");
      const res = await runReconciliation(form);
      setResult(res.data);
      if      (res.data.summary.missing_count > 0)   setActiveTab("missing");
      else if (res.data.summary.mismatch_count > 0)  setActiveTab("mismatched");
      else                                            setActiveTab("matched");
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Kuch galat hua. Dobara try karo.");
    } finally {
      setLoading(false);
    }
  };

  const risk = (result?.summary?.risk_level ?? "LOW") as RiskLevel;

  return (
    <div className="min-h-screen bg-gray-50">

      {/* Page Header */}
      <div className="bg-white border-b border-gray-200 px-4 sm:px-6 py-4 sticky top-0 z-10">
        <div className="max-w-5xl mx-auto">
          <h1 className="text-xl sm:text-2xl font-bold text-gray-900">GSTR-2B Reconciliation</h1>
          <p className="text-xs text-gray-400 mt-0.5">Purchase Register vs GSTR-2B — ITC at risk instantly jaano</p>
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-4 sm:px-6 py-5 space-y-5">

        {/* Stats Cards — always visible */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <StatCard icon="📄" label="Total Invoices"  value={result?.summary.total_purchase_invoices ?? "—"} sub="Purchase register"  color="text-gray-800"    bg="bg-white" />
          <StatCard icon="✅" label="Matched"          value={result?.summary.matched_count ?? "—"}          sub="Safe to claim"       color="text-emerald-700" bg="bg-emerald-50" />
          <StatCard icon="⚠️" label="Missing in 2B"   value={result?.summary.missing_count ?? "—"}          sub="ITC blocked"         color="text-orange-600"  bg="bg-orange-50" />
          <StatCard icon="🔴" label="Amount Mismatch" value={result?.summary.mismatch_count ?? "—"}         sub="Verify amount"       color="text-red-600"     bg="bg-red-50" />
        </div>

        {/* ITC Impact Banner — after result */}
        {result && (
          <div className={`bg-white rounded-2xl border-l-4 ${RISK_BORDER[risk]} shadow-sm p-4 sm:p-5`}>
            <div className="flex flex-wrap items-center gap-2 mb-3">
              <span className={`text-xs font-bold px-2.5 py-1 rounded-full ring-1 ${RISK_BADGE[risk]}`}>
                {risk} RISK
              </span>
              <span className="text-xs text-gray-400">{result.period}</span>
            </div>
            <p className="text-sm text-gray-600 mb-4 leading-relaxed">
              {language === "hi" ? result.summary.summary_hi
               : language === "mr" ? result.summary.summary_mr
               : result.summary.summary_en}
            </p>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <ITCCard label="Books ITC"     value={inr(result.itc_impact.total_itc_books)}   color="text-gray-800" />
              <ITCCard label="GSTR-2B ITC"   value={inr(result.itc_impact.total_itc_gstr2b)}  color="text-emerald-700" />
              <ITCCard label="ITC at Risk"   value={inr(result.itc_impact.itc_at_risk)}       color="text-orange-600" />
              <ITCCard label="Total Tax Loss" value={inr(result.itc_impact.total_tax_loss)}   color="text-red-600" bold />
            </div>
          </div>
        )}

        {/* Upload Form */}
        <form onSubmit={handleSubmit} className="bg-white rounded-2xl shadow-sm border border-gray-200 p-4 sm:p-6 space-y-4">
          <h2 className="font-semibold text-gray-800 text-sm">Files Upload Karo</h2>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <FileDropZone
              id="purchase-input" label="Purchase Register" hint="Excel / CSV / PDF" emoji="📂"
              accept=".xlsx,.xls,.csv,.pdf" file={purchaseFile}
              activeColor="border-blue-400 bg-blue-50" hoverColor="hover:border-blue-300"
              textColor="text-blue-700" onChange={setPurchaseFile}
            />
            <FileDropZone
              id="gstr2b-input" label="GSTR-2B File" hint="GST Portal se download karo" emoji="🧾"
              accept=".xlsx,.xls,.csv,.pdf" file={gstr2bFile}
              activeColor="border-green-400 bg-green-50" hoverColor="hover:border-green-300"
              textColor="text-green-700" onChange={setGstr2bFile}
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">GSTIN <span className="text-red-500">*</span></label>
              <input type="text" placeholder="27AABC1234D1Z5" maxLength={15}
                value={gstin} onChange={(e) => setGstin(e.target.value.toUpperCase())}
                className="w-full border border-gray-300 rounded-xl px-3 py-2.5 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-400" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Period <span className="text-red-500">*</span></label>
              <input type="month" value={period} onChange={(e) => setPeriod(e.target.value)}
                className="w-full border border-gray-300 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Language</label>
              <select value={language} onChange={(e) => setLanguage(e.target.value as any)}
                className="w-full border border-gray-300 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400">
                <option value="en">English</option>
                <option value="hi">हिंदी</option>
                <option value="mr">मराठी</option>
              </select>
            </div>
          </div>

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-3 text-sm text-red-700 flex gap-2">
              <span>⚠️</span><span>{error}</span>
            </div>
          )}

          <button type="submit" disabled={loading}
            className="w-full bg-blue-600 hover:bg-blue-700 active:scale-[0.99] disabled:bg-blue-300 text-white font-semibold py-3 rounded-xl transition-all text-sm shadow-sm">
            {loading ? (
              <span className="flex items-center justify-center gap-2">
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
                </svg>
                Reconciliation chal rahi hai...
              </span>
            ) : "🔍 Reconcile Karo"}
          </button>
        </form>

        {/* Results */}
        {result && (
          <div className="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden">
            {/* Tabs */}
            <div className="flex border-b border-gray-200 overflow-x-auto">
              <TabBtn label="Missing in 2B"   count={result.summary.missing_count}   badgeColor="bg-orange-100 text-orange-700" active={activeTab === "missing"}    onClick={() => setActiveTab("missing")} />
              <TabBtn label="Amount Mismatch" count={result.summary.mismatch_count}  badgeColor="bg-red-100 text-red-700"       active={activeTab === "mismatched"} onClick={() => setActiveTab("mismatched")} />
              <TabBtn label="Matched"         count={result.summary.matched_count}   badgeColor="bg-emerald-100 text-emerald-700" active={activeTab === "matched"} onClick={() => setActiveTab("matched")} />
            </div>
            <div className="overflow-x-auto">
              {activeTab === "missing"    && <MissingTable    rows={result.missing} />}
              {activeTab === "mismatched" && <MismatchedTable rows={result.mismatched} />}
              {activeTab === "matched"    && <MatchedTable    rows={result.matched} />}
            </div>
          </div>
        )}

        {result?.parse_errors && result.parse_errors.length > 0 && (
          <div className="bg-amber-50 border border-amber-200 rounded-xl p-4">
            <p className="text-xs font-semibold text-amber-800 mb-1">⚠️ Parse Warnings</p>
            {result.parse_errors.map((e, i) => <p key={i} className="text-xs text-amber-700">{e}</p>)}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Components ────────────────────────────────────────────────

function StatCard({ icon, label, value, sub, color, bg }: {
  icon: string; label: string; value: number | string; sub: string; color: string; bg: string;
}) {
  return (
    <div className={`${bg} rounded-2xl border border-gray-200 p-3 sm:p-4`}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs text-gray-500 font-medium">{label}</span>
        <span className="text-base sm:text-lg">{icon}</span>
      </div>
      <p className={`text-xl sm:text-2xl font-bold ${color}`}>{value}</p>
      <p className="text-[11px] text-gray-400 mt-0.5">{sub}</p>
    </div>
  );
}

function ITCCard({ label, value, color, bold }: { label: string; value: string; color: string; bold?: boolean }) {
  return (
    <div className="bg-gray-50 rounded-xl p-3">
      <p className="text-[11px] text-gray-500 mb-1">{label}</p>
      <p className={`text-sm ${bold ? "font-bold" : "font-semibold"} ${color}`}>{value}</p>
    </div>
  );
}

function FileDropZone({ id, label, hint, emoji, accept, file, activeColor, hoverColor, textColor, onChange }: {
  id: string; label: string; hint: string; emoji: string; accept: string;
  file: File | null; activeColor: string; hoverColor: string; textColor: string;
  onChange: (f: File | null) => void;
}) {
  return (
    <div>
      <label className="block text-xs font-medium text-gray-600 mb-1">{label} <span className="text-red-500">*</span></label>
      <div className={`border-2 border-dashed rounded-xl p-4 text-center cursor-pointer transition-all
        ${file ? activeColor : `border-gray-300 ${hoverColor}`}`}
        onClick={() => document.getElementById(id)?.click()}>
        <input id={id} type="file" className="hidden" accept={accept}
          onChange={(e) => onChange(e.target.files?.[0] ?? null)} />
        {file ? (
          <div>
            <p className={`${textColor} font-medium text-sm truncate`}>{file.name}</p>
            <p className="text-xs text-gray-400 mt-0.5">
              {(file.size / 1024).toFixed(1)} KB
              <button className="ml-2 text-red-400 hover:text-red-600 font-bold"
                onClick={(e) => { e.stopPropagation(); onChange(null); }}>✕</button>
            </p>
          </div>
        ) : (
          <>
            <p className="text-2xl mb-1">{emoji}</p>
            <p className="text-xs text-gray-500">{hint}</p>
            <p className="text-[11px] text-gray-400 mt-0.5">Click to select</p>
          </>
        )}
      </div>
    </div>
  );
}

function TabBtn({ label, count, badgeColor, active, onClick }: {
  label: string; count: number; badgeColor: string; active: boolean; onClick: () => void;
}) {
  return (
    <button onClick={onClick}
      className={`flex items-center gap-2 px-4 sm:px-5 py-3 text-sm font-medium whitespace-nowrap border-b-2 transition-all
        ${active ? "border-blue-500 text-blue-600 bg-blue-50/40" : "border-transparent text-gray-500 hover:text-gray-700 hover:bg-gray-50"}`}>
      {label}
      <span className={`text-[11px] font-bold px-1.5 py-0.5 rounded-full ${active ? badgeColor : "bg-gray-100 text-gray-500"}`}>
        {count}
      </span>
    </button>
  );
}

// ── Tables ────────────────────────────────────────────────────

function MissingTable({ rows }: { rows: MissingInvoice[] }) {
  if (!rows.length) return <EmptyState icon="🎉" msg="Sab invoices GSTR-2B mein hain!" />;
  const total = rows.reduce((s, r) => s + r.itc_at_risk, 0);
  return (
    <>
      {/* Mobile */}
      <div className="sm:hidden divide-y divide-gray-100">
        {rows.map((r, i) => (
          <div key={i} className="p-4 space-y-1.5">
            <div className="flex justify-between">
              <span className="font-mono text-xs font-semibold">{r.invoice_number}</span>
              <span className="text-sm font-bold text-orange-600">{inr(r.itc_at_risk)}</span>
            </div>
            <p className="text-xs text-gray-500">{r.party_name || "—"}</p>
            <p className="text-[11px] font-mono text-gray-400">{r.party_gstin || "—"}</p>
          </div>
        ))}
        <div className="p-4 bg-orange-50 flex justify-between font-semibold text-sm">
          <span className="text-orange-800">Total ITC at Risk</span>
          <span className="text-orange-700">{inr(total)}</span>
        </div>
      </div>
      {/* Desktop */}
      <table className="hidden sm:table w-full text-sm">
        <thead className="bg-orange-50 border-b border-orange-100">
          <tr>{["#","Invoice No.","Party Name","GSTIN","Date","Taxable Value","ITC at Risk"].map(h =>
            <th key={h} className="text-left px-4 py-3 text-xs font-semibold text-orange-900 whitespace-nowrap">{h}</th>
          )}</tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {rows.map((r, i) => (
            <tr key={i} className="hover:bg-orange-50/40 transition-colors">
              <td className="px-4 py-3 text-xs text-gray-400">{i+1}</td>
              <td className="px-4 py-3 font-mono text-xs font-medium">{r.invoice_number}</td>
              <td className="px-4 py-3 text-gray-700 max-w-[160px] truncate">{r.party_name || "—"}</td>
              <td className="px-4 py-3 font-mono text-xs text-gray-500">{r.party_gstin || "—"}</td>
              <td className="px-4 py-3 text-xs text-gray-500">{r.invoice_date || "—"}</td>
              <td className="px-4 py-3 text-right text-gray-700">₹{r.taxable_value.toLocaleString("en-IN")}</td>
              <td className="px-4 py-3 text-right font-semibold text-orange-600">₹{r.itc_at_risk.toLocaleString("en-IN")}</td>
            </tr>
          ))}
        </tbody>
        <tfoot className="bg-orange-50 border-t-2 border-orange-200">
          <tr>
            <td colSpan={6} className="px-4 py-3 text-right text-xs font-bold text-orange-900">Total ITC at Risk</td>
            <td className="px-4 py-3 text-right font-bold text-orange-700">₹{total.toLocaleString("en-IN")}</td>
          </tr>
        </tfoot>
      </table>
    </>
  );
}

function MismatchedTable({ rows }: { rows: MismatchedInvoice[] }) {
  if (!rows.length) return <EmptyState icon="✅" msg="Koi amount mismatch nahi." />;
  const total = rows.reduce((s, r) => s + r.excess_itc, 0);
  return (
    <>
      {/* Mobile */}
      <div className="sm:hidden divide-y divide-gray-100">
        {rows.map((r, i) => (
          <div key={i} className="p-4 space-y-1.5">
            <div className="flex justify-between">
              <span className="font-mono text-xs font-semibold">{r.invoice_number}</span>
              <span className="text-xs px-2 py-0.5 bg-red-100 text-red-700 rounded-full font-medium">Excess: {inr(r.excess_itc)}</span>
            </div>
            <p className="text-xs text-gray-500">{r.party_name || "—"}</p>
            <div className="flex gap-3 text-xs text-gray-500">
              <span>Books: <b className="text-gray-800">₹{r.books_tax.toLocaleString("en-IN")}</b></span>
              <span>2B: <b className="text-emerald-700">₹{r.gstr2b_tax.toLocaleString("en-IN")}</b></span>
            </div>
          </div>
        ))}
        <div className="p-4 bg-red-50 flex justify-between font-semibold text-sm">
          <span className="text-red-800">Total Excess ITC</span>
          <span className="text-red-700">{inr(total)}</span>
        </div>
      </div>
      {/* Desktop */}
      <table className="hidden sm:table w-full text-sm">
        <thead className="bg-red-50 border-b border-red-100">
          <tr>{["#","Invoice No.","Party Name","GSTIN","Books Tax","GSTR-2B Tax","Difference","Excess ITC"].map(h =>
            <th key={h} className="text-left px-4 py-3 text-xs font-semibold text-red-900 whitespace-nowrap">{h}</th>
          )}</tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {rows.map((r, i) => (
            <tr key={i} className="hover:bg-red-50/40 transition-colors">
              <td className="px-4 py-3 text-xs text-gray-400">{i+1}</td>
              <td className="px-4 py-3 font-mono text-xs font-medium">{r.invoice_number}</td>
              <td className="px-4 py-3 text-gray-700 max-w-[140px] truncate">{r.party_name || "—"}</td>
              <td className="px-4 py-3 font-mono text-xs text-gray-500">{r.party_gstin || "—"}</td>
              <td className="px-4 py-3 text-right">₹{r.books_tax.toLocaleString("en-IN")}</td>
              <td className="px-4 py-3 text-right text-emerald-700">₹{r.gstr2b_tax.toLocaleString("en-IN")}</td>
              <td className="px-4 py-3 text-right text-red-500">₹{r.diff.toLocaleString("en-IN")}</td>
              <td className="px-4 py-3 text-right font-bold text-red-700">₹{r.excess_itc.toLocaleString("en-IN")}</td>
            </tr>
          ))}
        </tbody>
        <tfoot className="bg-red-50 border-t-2 border-red-200">
          <tr>
            <td colSpan={7} className="px-4 py-3 text-right text-xs font-bold text-red-900">Total Excess ITC</td>
            <td className="px-4 py-3 text-right font-bold text-red-700">₹{total.toLocaleString("en-IN")}</td>
          </tr>
        </tfoot>
      </table>
    </>
  );
}

function MatchedTable({ rows }: { rows: MatchedInvoice[] }) {
  if (!rows.length) return <EmptyState icon="📭" msg="Koi matched invoice nahi mila." />;
  return (
    <>
      {/* Mobile */}
      <div className="sm:hidden divide-y divide-gray-100">
        {rows.map((r, i) => (
          <div key={i} className="p-4 space-y-1.5">
            <div className="flex justify-between">
              <span className="font-mono text-xs font-semibold">{r.invoice_number}</span>
              <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold
                ${r.match_type === "exact" ? "bg-emerald-100 text-emerald-700" : "bg-blue-100 text-blue-700"}`}>
                {r.match_type === "exact" ? "✓ Exact" : "~ Fuzzy"}
              </span>
            </div>
            <p className="text-xs text-gray-500">{r.party_name || "—"}</p>
            <span className="text-xs text-gray-500">Tax: <b className="text-gray-800">₹{r.books_tax.toLocaleString("en-IN")}</b></span>
          </div>
        ))}
      </div>
      {/* Desktop */}
      <table className="hidden sm:table w-full text-sm">
        <thead className="bg-emerald-50 border-b border-emerald-100">
          <tr>{["#","Invoice No.","Party Name","GSTIN","Books Tax","GSTR-2B Tax","Diff","Match"].map(h =>
            <th key={h} className="text-left px-4 py-3 text-xs font-semibold text-emerald-900 whitespace-nowrap">{h}</th>
          )}</tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {rows.map((r, i) => (
            <tr key={i} className="hover:bg-emerald-50/40 transition-colors">
              <td className="px-4 py-3 text-xs text-gray-400">{i+1}</td>
              <td className="px-4 py-3 font-mono text-xs font-medium">{r.invoice_number}</td>
              <td className="px-4 py-3 text-gray-700 max-w-[140px] truncate">{r.party_name || "—"}</td>
              <td className="px-4 py-3 font-mono text-xs text-gray-500">{r.party_gstin || "—"}</td>
              <td className="px-4 py-3 text-right">₹{r.books_tax.toLocaleString("en-IN")}</td>
              <td className="px-4 py-3 text-right text-emerald-700">₹{r.gstr2b_tax.toLocaleString("en-IN")}</td>
              <td className="px-4 py-3 text-right text-xs text-gray-400">₹{r.diff.toLocaleString("en-IN")}</td>
              <td className="px-4 py-3">
                <span className={`text-[11px] px-2 py-0.5 rounded-full font-semibold
                  ${r.match_type === "exact" ? "bg-emerald-100 text-emerald-700" : "bg-blue-100 text-blue-700"}`}>
                  {r.match_type === "exact" ? "✓ Exact" : "~ Fuzzy"}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  );
}

function EmptyState({ icon, msg }: { icon: string; msg: string }) {
  return (
    <div className="py-16 text-center">
      <p className="text-4xl mb-3">{icon}</p>
      <p className="text-sm text-gray-400">{msg}</p>
    </div>
  );
}
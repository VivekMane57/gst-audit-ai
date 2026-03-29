"use client";

import { useState } from "react";
import {
  Search, CheckCircle, XCircle, AlertTriangle,
  Hash, Percent, Info, ArrowRight, Zap,
} from "lucide-react";
import { api, setAuthHeader } from "@/lib/api";
import { useUser } from "@clerk/nextjs";
import { useEffect } from "react";

export default function HSNValidatorPage() {
  const { user, isLoaded } = useUser();

  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [searching, setSearching] = useState(false);

  const [hsnCode, setHsnCode] = useState("");
  const [appliedRate, setAppliedRate] = useState("");
  const [taxableValue, setTaxableValue] = useState("");
  const [validationResult, setValidationResult] = useState<any>(null);
  const [validating, setValidating] = useState(false);

  useEffect(() => {
    if (isLoaded && user) setAuthHeader(user.id);
  }, [isLoaded, user]);

  /* ── Search HSN ────────────────────────────────────────── */
  const handleSearch = async () => {
    if (searchQuery.length < 2) return;
    setSearching(true);
    try {
      const res = await api.get(`/api/hsn/search?q=${encodeURIComponent(searchQuery)}&limit=20`);
      setSearchResults(res.data?.results || []);
    } catch (err) {
      console.error("HSN search failed:", err);
      setSearchResults([]);
    }
    setSearching(false);
  };

  /* ── Validate Rate ─────────────────────────────────────── */
  const handleValidate = async () => {
    if (!hsnCode || !appliedRate) return;
    setValidating(true);
    try {
      const res = await api.post("/api/hsn/validate", {
        hsn_code: hsnCode,
        applied_rate: parseFloat(appliedRate),
        taxable_value: parseFloat(taxableValue) || 0,
      });
      setValidationResult(res.data);
    } catch (err: any) {
      if (err.response?.status === 404) {
        setValidationResult({
          hsn_code: hsnCode,
          is_correct: null,
          severity: "LOW",
          message: `HSN code ${hsnCode} not found in database`,
          description: "Unknown",
        });
      }
    }
    setValidating(false);
  };

  /* ── Select from search ────────────────────────────────── */
  const selectHSN = (item: any) => {
    setHsnCode(item.hsn_code);
    setSearchQuery("");
    setSearchResults([]);
  };

  return (
    <div className="px-4 py-5 lg:p-8 max-w-4xl mx-auto space-y-6">

      {/* Header */}
      <div>
        <h1 className="text-xl lg:text-2xl font-bold text-gray-900 flex items-center gap-2">
          <Hash className="text-blue-600" size={22} />
          HSN Rate Validator
        </h1>
        <p className="text-sm text-gray-500 mt-1">
          Check if correct GST rate is applied — 500+ HSN/SAC codes covered
        </p>
      </div>

      {/* Two Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">

        {/* ── Left: Search HSN ────────────────────────────── */}
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
          <h2 className="font-semibold text-gray-900 text-sm mb-3 flex items-center gap-2">
            <Search size={16} className="text-blue-600" />
            Search HSN / SAC Code
          </h2>

          <div className="flex gap-2">
            <input
              type="text"
              placeholder="e.g. 8471, laptop, cement..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSearch()}
              className="flex-1 px-3 py-2.5 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
            />
            <button
              onClick={handleSearch}
              disabled={searching || searchQuery.length < 2}
              className="px-4 py-2.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 active:scale-95 transition-all"
            >
              {searching ? "..." : "Search"}
            </button>
          </div>

          {/* Search Results */}
          {searchResults.length > 0 && (
            <div className="mt-3 max-h-72 overflow-y-auto space-y-1.5">
              {searchResults.map((item, i) => (
                <button
                  key={i}
                  onClick={() => selectHSN(item)}
                  className="w-full text-left flex items-center justify-between p-3 rounded-lg border border-gray-100 hover:bg-blue-50 hover:border-blue-200 transition-all active:scale-[0.99]"
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-sm font-semibold text-gray-900">
                        {item.hsn_code}
                      </span>
                      <span className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-gray-100 text-gray-600">
                        {item.category}
                      </span>
                    </div>
                    <p className="text-xs text-gray-500 mt-0.5 truncate">
                      {item.description}
                    </p>
                  </div>
                  <span className="shrink-0 ml-3 px-2 py-1 rounded-lg bg-blue-50 text-blue-700 text-sm font-bold">
                    {item.rate}%
                  </span>
                </button>
              ))}
            </div>
          )}

          {searchResults.length === 0 && searchQuery.length >= 2 && !searching && (
            <p className="mt-3 text-xs text-gray-400 text-center py-4">
              No HSN codes found for "{searchQuery}"
            </p>
          )}
        </div>

        {/* ── Right: Validate Rate ────────────────────────── */}
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
          <h2 className="font-semibold text-gray-900 text-sm mb-3 flex items-center gap-2">
            <Percent size={16} className="text-blue-600" />
            Validate GST Rate
          </h2>

          <div className="space-y-3">
            <div>
              <label className="text-xs text-gray-500 font-medium mb-1 block">
                HSN / SAC Code *
              </label>
              <input
                type="text"
                placeholder="e.g. 84715000"
                value={hsnCode}
                onChange={(e) => setHsnCode(e.target.value)}
                className="w-full px-3 py-2.5 border border-gray-200 rounded-lg text-sm font-mono focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-gray-500 font-medium mb-1 block">
                  Applied Rate (%) *
                </label>
                <input
                  type="number"
                  step="0.1"
                  placeholder="e.g. 18"
                  value={appliedRate}
                  onChange={(e) => setAppliedRate(e.target.value)}
                  className="w-full px-3 py-2.5 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                />
              </div>
              <div>
                <label className="text-xs text-gray-500 font-medium mb-1 block">
                  Taxable Value (₹)
                </label>
                <input
                  type="number"
                  placeholder="e.g. 50000"
                  value={taxableValue}
                  onChange={(e) => setTaxableValue(e.target.value)}
                  className="w-full px-3 py-2.5 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                />
              </div>
            </div>

            <button
              onClick={handleValidate}
              disabled={validating || !hsnCode || !appliedRate}
              className="w-full py-2.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 active:scale-95 transition-all flex items-center justify-center gap-2"
            >
              <Zap size={16} />
              {validating ? "Checking..." : "Validate Rate"}
            </button>
          </div>

          {/* Validation Result */}
          {validationResult && (
            <div className={`mt-4 rounded-lg p-4 border ${
              validationResult.is_correct === true
                ? "bg-emerald-50 border-emerald-200"
                : validationResult.is_correct === false
                ? validationResult.severity === "CRITICAL"
                  ? "bg-red-50 border-red-200"
                  : "bg-amber-50 border-amber-200"
                : "bg-gray-50 border-gray-200"
            }`}>
              <div className="flex items-start gap-3">
                {validationResult.is_correct === true ? (
                  <CheckCircle size={20} className="text-emerald-600 mt-0.5 shrink-0" />
                ) : validationResult.is_correct === false ? (
                  <XCircle size={20} className="text-red-600 mt-0.5 shrink-0" />
                ) : (
                  <Info size={20} className="text-gray-400 mt-0.5 shrink-0" />
                )}
                <div className="flex-1">
                  <p className={`font-semibold text-sm ${
                    validationResult.is_correct === true
                      ? "text-emerald-800"
                      : validationResult.is_correct === false
                      ? "text-red-800"
                      : "text-gray-700"
                  }`}>
                    {validationResult.message}
                  </p>

                  {validationResult.description && validationResult.description !== "Unknown" && (
                    <div className="mt-2 space-y-1">
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-gray-500">Product/Service</span>
                        <span className="font-medium text-gray-900">{validationResult.description}</span>
                      </div>
                      {validationResult.category && (
                        <div className="flex items-center justify-between text-xs">
                          <span className="text-gray-500">Category</span>
                          <span className="font-medium text-gray-900">{validationResult.category}</span>
                        </div>
                      )}
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-gray-500">Correct Rate</span>
                        <span className="font-bold text-blue-700">{validationResult.correct_rate}%</span>
                      </div>
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-gray-500">Applied Rate</span>
                        <span className={`font-bold ${
                          validationResult.is_correct ? "text-emerald-700" : "text-red-700"
                        }`}>{validationResult.applied_rate}%</span>
                      </div>
                      {validationResult.tax_difference > 0 && (
                        <div className="flex items-center justify-between text-xs pt-1 border-t border-gray-200 mt-1">
                          <span className="text-gray-500">Tax Difference</span>
                          <span className="font-bold text-red-700">
                            ₹{validationResult.tax_difference.toLocaleString("en-IN")}
                          </span>
                        </div>
                      )}
                    </div>
                  )}

                  {validationResult.severity && validationResult.severity !== "OK" && (
                    <span className={`inline-block mt-2 px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                      validationResult.severity === "CRITICAL" ? "bg-red-100 text-red-700" :
                      validationResult.severity === "HIGH" ? "bg-amber-100 text-amber-700" :
                      validationResult.severity === "MEDIUM" ? "bg-yellow-100 text-yellow-700" :
                      "bg-gray-100 text-gray-600"
                    }`}>
                      {validationResult.severity}
                    </span>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ── Quick Reference ───────────────────────────────── */}
      <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
        <h2 className="font-semibold text-gray-900 text-sm mb-3 flex items-center gap-2">
          <Info size={16} className="text-blue-600" />
          Common GST Rates — Quick Reference
        </h2>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            { rate: "0%", items: "Milk, Wheat, Rice, Books, Salt, Honey", color: "emerald" },
            { rate: "5%", items: "Tea, Coffee, Oil, Sugar, Coal, Spices", color: "blue" },
            { rate: "12%", items: "Medicines, Pasta, Bicycles, Garments", color: "amber" },
            { rate: "18%", items: "Computers, Steel, Soap, Services", color: "orange" },
          ].map((slab) => (
            <div key={slab.rate} className={`rounded-lg p-3 border bg-${slab.color}-50 border-${slab.color}-100`}>
              <p className={`text-lg font-bold text-${slab.color}-700`}>{slab.rate}</p>
              <p className="text-xs text-gray-600 mt-1 leading-relaxed">{slab.items}</p>
            </div>
          ))}
        </div>
        <p className="text-xs text-gray-400 mt-3">
          28% GST: Cars, Tobacco, Aerated Drinks, AC, Cement, Tyres
        </p>
      </div>
    </div>
  );
}
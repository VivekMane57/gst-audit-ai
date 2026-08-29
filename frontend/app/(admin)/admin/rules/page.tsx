"use client";

import { useEffect, useState, useCallback } from "react";
import { rulesApi, Rule } from "@/lib/adminApi";
import { Plus, Search, CheckCircle, XCircle, RefreshCw, Edit2, Filter } from "lucide-react";
import RuleModal from "@/components/admin/RuleModal";
import toast from "react-hot-toast";

const CATEGORIES = ["All", "itc", "gstr", "gstin", "invoice", "payment", "reconciliation", "sector"];
const SEVERITIES = ["All", "low", "medium", "high", "critical"];

export default function RulesPage() {
  const [rules, setRules]           = useState<Rule[]>([]);
  const [loading, setLoading]       = useState(true);
  const [search, setSearch]         = useState("");
  const [category, setCategory]     = useState("All");
  const [severity, setSeverity]     = useState("All");
  const [activeOnly, setActiveOnly] = useState(false);
  const [modalOpen, setModalOpen]   = useState(false);
  const [editing, setEditing]       = useState<Rule | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await rulesApi.list({
        active_only: activeOnly,
        category: category !== "All" ? category : undefined,
        limit: 200,
      });
      setRules(res.data.rules);
    } catch {
      toast.error("Failed to load rules");
    } finally {
      setLoading(false);
    }
  }, [activeOnly, category]);

  useEffect(() => { load(); }, [load]);

  const filtered = rules.filter(r => {
    const matchSearch   = !search || r.rule_code.toLowerCase().includes(search.toLowerCase()) || r.title.toLowerCase().includes(search.toLowerCase());
    const matchSeverity = severity === "All" || r.severity === severity;
    return matchSearch && matchSeverity;
  });

  const toggleActive = async (rule: Rule) => {
    try {
      if (rule.is_active) {
        await rulesApi.deactivate(rule.id);
        toast.success(`Rule ${rule.rule_code} deactivated`);
      } else {
        await rulesApi.activate(rule.id);
        toast.success(`Rule ${rule.rule_code} activated`);
      }
      load();
    } catch {
      toast.error("Failed to update rule status");
    }
  };

  const severityColor: Record<string, string> = {
    low:      "bg-blue-500/10 text-blue-400",
    medium:   "bg-amber-500/10 text-amber-400",
    high:     "bg-orange-500/10 text-orange-400",
    critical: "bg-red-500/10 text-red-400",
  };

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Compliance Rules</h1>
          <p className="text-gray-400 text-sm mt-0.5">{filtered.length} rules {activeOnly ? "(active only)" : ""}</p>
        </div>
        <button
          onClick={() => { setEditing(null); setModalOpen(true); }}
          className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors"
        >
          <Plus className="w-4 h-4" /> Add Rule
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-6">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search rules..."
            className="pl-9 pr-4 py-2 bg-white/[0.04] border border-white/[0.08] rounded-lg text-sm text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500/50 w-64"
          />
        </div>

        <select
          value={category}
          onChange={e => setCategory(e.target.value)}
          className="px-3 py-2 bg-white/[0.04] border border-white/[0.08] rounded-lg text-sm text-gray-300 focus:outline-none focus:border-indigo-500/50"
        >
          {CATEGORIES.map(c => <option key={c} value={c}>{c === "All" ? "All Categories" : c}</option>)}
        </select>

        <select
          value={severity}
          onChange={e => setSeverity(e.target.value)}
          className="px-3 py-2 bg-white/[0.04] border border-white/[0.08] rounded-lg text-sm text-gray-300 focus:outline-none focus:border-indigo-500/50"
        >
          {SEVERITIES.map(s => <option key={s} value={s}>{s === "All" ? "All Severities" : s}</option>)}
        </select>

        <label className="flex items-center gap-2 px-3 py-2 bg-white/[0.04] border border-white/[0.08] rounded-lg cursor-pointer">
          <input
            type="checkbox"
            checked={activeOnly}
            onChange={e => setActiveOnly(e.target.checked)}
            className="accent-indigo-500"
          />
          <span className="text-sm text-gray-300">Active only</span>
        </label>

        <button onClick={load} className="p-2 bg-white/[0.04] border border-white/[0.08] rounded-lg text-gray-400 hover:text-white transition-colors">
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      {/* Table */}
      <div className="bg-white/[0.02] border border-white/[0.06] rounded-xl overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-white/[0.06]">
              {["Rule Code", "Title", "Category", "Severity", "Risk Weight", "Status", "Actions"].map(h => (
                <th key={h} className="text-left text-xs text-gray-500 font-medium px-4 py-3 uppercase tracking-wider">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              Array.from({ length: 5 }).map((_, i) => (
                <tr key={i} className="border-b border-white/[0.04]">
                  {Array.from({ length: 7 }).map((_, j) => (
                    <td key={j} className="px-4 py-3">
                      <div className="h-4 bg-white/[0.06] rounded animate-pulse" />
                    </td>
                  ))}
                </tr>
              ))
            ) : filtered.length === 0 ? (
              <tr>
                <td colSpan={7} className="text-center text-gray-500 py-12">No rules found</td>
              </tr>
            ) : (
              filtered.map(rule => (
                <tr key={rule.id} className="border-b border-white/[0.04] hover:bg-white/[0.02] transition-colors">
                  <td className="px-4 py-3">
                    <code className="text-indigo-300 text-xs bg-indigo-500/10 px-2 py-0.5 rounded">{rule.rule_code}</code>
                  </td>
                  <td className="px-4 py-3 text-gray-200 max-w-xs truncate">{rule.title}</td>
                  <td className="px-4 py-3">
                    <span className="text-xs text-gray-400 bg-white/[0.05] px-2 py-0.5 rounded">{rule.category}</span>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`text-xs px-2 py-0.5 rounded font-medium ${severityColor[rule.severity] || "text-gray-400"}`}>
                      {rule.severity}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-300">{rule.notice_risk_weight}</td>
                  <td className="px-4 py-3">
                    {rule.is_active
                      ? <span className="flex items-center gap-1 text-emerald-400 text-xs"><CheckCircle className="w-3.5 h-3.5" /> Active</span>
                      : <span className="flex items-center gap-1 text-gray-500 text-xs"><XCircle className="w-3.5 h-3.5" /> Inactive</span>}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => { setEditing(rule); setModalOpen(true); }}
                        className="p-1.5 text-gray-400 hover:text-white hover:bg-white/[0.06] rounded transition-colors"
                        title="Edit"
                      >
                        <Edit2 className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={() => toggleActive(rule)}
                        className={`text-xs px-2 py-1 rounded transition-colors ${
                          rule.is_active
                            ? "text-red-400 hover:bg-red-500/10"
                            : "text-emerald-400 hover:bg-emerald-500/10"
                        }`}
                      >
                        {rule.is_active ? "Deactivate" : "Activate"}
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Modal */}
      {modalOpen && (
        <RuleModal
          rule={editing}
          onClose={() => setModalOpen(false)}
          onSaved={() => { setModalOpen(false); load(); }}
        />
      )}
    </div>
  );
}
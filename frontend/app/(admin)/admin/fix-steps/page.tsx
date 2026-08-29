"use client";

import { useState } from "react";
import { fixStepsApi, FixStep } from "@/lib/adminApi";
import { Search, Plus, Trash2, Edit2, X, GripVertical } from "lucide-react";
import toast from "react-hot-toast";

export default function FixStepsPage() {
  const [ruleCode, setRuleCode]   = useState("");
  const [searching, setSearching] = useState(false);
  const [steps, setSteps]         = useState<{ en: string[]; hi: string[]; mr: string[] } | null>(null);
  const [addOpen, setAddOpen]     = useState(false);

  const search = async () => {
    if (!ruleCode.trim()) return;
    setSearching(true);
    try {
      const res = await fixStepsApi.getByRule(ruleCode.trim().toUpperCase());
      setSteps(res.data.steps);
    } catch {
      toast.error("Rule not found or no steps");
      setSteps(null);
    } finally { setSearching(false); }
  };

  const deleteStep = async (idx: number) => {
    toast.error("Delete requires step ID — use API directly for now");
  };

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Fix Steps</h1>
          <p className="text-gray-400 text-sm mt-0.5">Search by Rule Code to view and manage fix steps</p>
        </div>
        <button
          onClick={() => setAddOpen(true)}
          className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors"
        >
          <Plus className="w-4 h-4" /> Add Step
        </button>
      </div>

      {/* Search bar */}
      <div className="flex gap-3 mb-6">
        <input
          value={ruleCode}
          onChange={e => setRuleCode(e.target.value.toUpperCase())}
          onKeyDown={e => e.key === "Enter" && search()}
          placeholder="Enter Rule Code e.g. ITC_MISMATCH_01"
          className="flex-1 bg-white/[0.04] border border-white/[0.08] rounded-lg px-4 py-2.5 text-white text-sm placeholder-gray-500 outline-none focus:border-indigo-500/50"
        />
        <button
          onClick={search}
          disabled={searching}
          className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-sm font-medium px-5 py-2.5 rounded-lg transition-colors"
        >
          <Search className="w-4 h-4" />
          {searching ? "Searching..." : "Search"}
        </button>
      </div>

      {/* Results */}
      {steps && (
        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <code className="text-indigo-300 bg-indigo-500/10 px-3 py-1 rounded text-sm">{ruleCode}</code>
            <span className="text-gray-400 text-sm">— {steps.en.length} steps</span>
          </div>

          {steps.en.length === 0 ? (
            <div className="text-center text-gray-500 py-12 bg-white/[0.02] border border-white/[0.06] rounded-xl">
              No fix steps for this rule. Add one.
            </div>
          ) : (
            <div className="bg-white/[0.02] border border-white/[0.06] rounded-xl overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-white/[0.06]">
                    <th className="text-left text-xs text-gray-500 font-medium px-4 py-3 w-8">#</th>
                    <th className="text-left text-xs text-gray-500 font-medium px-4 py-3">English</th>
                    <th className="text-left text-xs text-gray-500 font-medium px-4 py-3">Hindi</th>
                    <th className="text-left text-xs text-gray-500 font-medium px-4 py-3">Marathi</th>
                  </tr>
                </thead>
                <tbody>
                  {steps.en.map((en, i) => (
                    <tr key={i} className="border-b border-white/[0.04] hover:bg-white/[0.02]">
                      <td className="px-4 py-3 text-gray-500 text-xs">{i + 1}</td>
                      <td className="px-4 py-3 text-gray-200">{en}</td>
                      <td className="px-4 py-3 text-gray-400">{steps.hi[i] || "—"}</td>
                      <td className="px-4 py-3 text-gray-400">{steps.mr[i] || "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {addOpen && (
        <AddStepModal
          defaultRuleCode={ruleCode}
          onClose={() => setAddOpen(false)}
          onSaved={() => { setAddOpen(false); search(); }}
        />
      )}
    </div>
  );
}

function AddStepModal({ defaultRuleCode, onClose, onSaved }: { defaultRuleCode: string; onClose: () => void; onSaved: () => void }) {
  const [form, setForm] = useState({
    rule_code:    defaultRuleCode,
    step_order:   1,
    step_text_en: "",
    step_text_hi: "",
    step_text_mr: "",
  });
  const [saving, setSaving] = useState(false);
  const set = (k: string, v: string | number) => setForm(f => ({ ...f, [k]: v }));

  const handleSubmit = async () => {
    if (!form.rule_code || !form.step_text_en) {
      toast.error("Rule Code and English text are required");
      return;
    }
    setSaving(true);
    try {
      await fixStepsApi.add({ ...form, rule_code: form.rule_code.toUpperCase() });
      toast.success("Fix step added");
      onSaved();
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || "Save failed");
    } finally { setSaving(false); }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
      <div className="bg-[#0f0f1a] border border-white/[0.08] rounded-2xl w-full max-w-lg">
        <div className="flex items-center justify-between px-6 py-4 border-b border-white/[0.06]">
          <h2 className="text-white font-semibold">Add Fix Step</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-white"><X className="w-5 h-5" /></button>
        </div>
        <div className="px-6 py-4 space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-gray-400 font-medium mb-1.5">Rule Code *</label>
              <input value={form.rule_code} onChange={e => set("rule_code", e.target.value.toUpperCase())} className="w-full bg-white/[0.04] border border-white/[0.08] rounded-lg px-3 py-2 text-white text-sm outline-none focus:border-indigo-500/50" />
            </div>
            <div>
              <label className="block text-xs text-gray-400 font-medium mb-1.5">Step Order</label>
              <input type="number" min={1} value={form.step_order} onChange={e => set("step_order", Number(e.target.value))} className="w-full bg-white/[0.04] border border-white/[0.08] rounded-lg px-3 py-2 text-white text-sm outline-none focus:border-indigo-500/50" />
            </div>
          </div>
          {[
            { label: "Step Text (English) *", key: "step_text_en", placeholder: "Reconcile ITC with GSTR-2B..." },
            { label: "Step Text (Hindi)",     key: "step_text_hi", placeholder: "ITC को GSTR-2B से मिलान करें..." },
            { label: "Step Text (Marathi)",   key: "step_text_mr", placeholder: "ITC GSTR-2B शी जुळवा..." },
          ].map(({ label, key, placeholder }) => (
            <div key={key}>
              <label className="block text-xs text-gray-400 font-medium mb-1.5">{label}</label>
              <textarea value={(form as any)[key]} onChange={e => set(key, e.target.value)} placeholder={placeholder} rows={2} className="w-full bg-white/[0.04] border border-white/[0.08] rounded-lg px-3 py-2 text-white text-sm outline-none focus:border-indigo-500/50 resize-none" />
            </div>
          ))}
        </div>
        <div className="px-6 py-4 border-t border-white/[0.06] flex justify-end gap-3">
          <button onClick={onClose} className="px-4 py-2 text-sm text-gray-400 hover:text-white">Cancel</button>
          <button onClick={handleSubmit} disabled={saving} className="px-5 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-colors">
            {saving ? "Saving..." : "Add Step"}
          </button>
        </div>
      </div>
    </div>
  );
}
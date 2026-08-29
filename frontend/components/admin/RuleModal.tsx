"use client";

import { useState } from "react";
import { Rule, rulesApi } from "@/lib/adminApi";
import { X } from "lucide-react";
import toast from "react-hot-toast";

interface Props {
  rule: Rule | null;
  onClose: () => void;
  onSaved: () => void;
}

const CATEGORIES  = ["itc", "gstr", "gstin", "invoice", "payment", "reconciliation", "sector"];
const SEVERITIES  = ["low", "medium", "high", "critical"];
const FORMULA_TYPES = ["flat", "percentage", "tiered", "none"];
const CONDITION_TYPES = ["always_flag", "threshold", "comparison", "composite"];

export default function RuleModal({ rule, onClose, onSaved }: Props) {
  const isEdit = !!rule;

  const [form, setForm] = useState({
    rule_code:           rule?.rule_code           || "",
    title:               rule?.title               || "",
    description:         rule?.description         || "",
    category:            rule?.category            || "itc",
    severity:            rule?.severity            || "medium",
    condition_type:      rule?.condition_type      || "always_flag",
    condition_config:    JSON.stringify(rule?.condition_config || {}, null, 2),
    law_code:            rule?.law_code            || "",
    plain_explanation:   rule?.plain_explanation   || "",
    penalty_formula_type:rule?.penalty_formula_type|| "none",
    penalty_formula_config: JSON.stringify(rule?.penalty_formula_config || {}, null, 2),
    notice_risk_weight:  rule?.notice_risk_weight  ?? 5,
    notice_risk_max:     rule?.notice_risk_max     ?? 10,
    effective_from:      rule?.effective_from      || "",
    effective_to:        rule?.effective_to        || "",
  });

  const [saving, setSaving] = useState(false);
  const [jsonError, setJsonError] = useState("");

  const set = (k: string, v: string | number) => setForm(f => ({ ...f, [k]: v }));

  const validateJson = (val: string, field: string) => {
    try { JSON.parse(val); setJsonError(""); }
    catch { setJsonError(`Invalid JSON in ${field}`); }
  };

  const handleSubmit = async () => {
    // Validate JSON fields
    try {
      JSON.parse(form.condition_config);
      JSON.parse(form.penalty_formula_config);
    } catch {
      setJsonError("Invalid JSON — fix before saving");
      return;
    }

    setSaving(true);
    try {
      const payload = {
        ...form,
        condition_config:      JSON.parse(form.condition_config),
        penalty_formula_config: JSON.parse(form.penalty_formula_config),
        notice_risk_weight:    Number(form.notice_risk_weight),
        notice_risk_max:       Number(form.notice_risk_max),
        effective_from:        form.effective_from || undefined,
        effective_to:          form.effective_to   || undefined,
      };

      if (isEdit) {
        await rulesApi.update(rule!.id, payload);
        toast.success("Rule updated");
      } else {
        await rulesApi.create(payload);
        toast.success("Rule created");
      }
      onSaved();
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || "Save failed");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
      <div className="bg-[#0f0f1a] border border-white/[0.08] rounded-2xl w-full max-w-2xl max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-white/[0.06]">
          <h2 className="text-white font-semibold">{isEdit ? `Edit Rule — ${rule.rule_code}` : "Create Rule"}</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-white transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="overflow-y-auto flex-1 px-6 py-4 space-y-4">
          {/* Row 1 */}
          <div className="grid grid-cols-2 gap-4">
            <Field label="Rule Code *">
              <input
                value={form.rule_code}
                onChange={e => set("rule_code", e.target.value.toUpperCase())}
                disabled={isEdit}
                placeholder="ITC_MISMATCH_01"
                className="input"
              />
            </Field>
            <Field label="Category *">
              <select value={form.category} onChange={e => set("category", e.target.value)} className="input">
                {CATEGORIES.map(c => <option key={c}>{c}</option>)}
              </select>
            </Field>
          </div>

          {/* Title */}
          <Field label="Title *">
            <input value={form.title} onChange={e => set("title", e.target.value)} placeholder="ITC Mismatch with GSTR-2B" className="input" />
          </Field>

          {/* Description */}
          <Field label="Description">
            <textarea value={form.description} onChange={e => set("description", e.target.value)} rows={2} placeholder="Brief description..." className="input resize-none" />
          </Field>

          {/* Row 2 */}
          <div className="grid grid-cols-2 gap-4">
            <Field label="Severity">
              <select value={form.severity} onChange={e => set("severity", e.target.value)} className="input">
                {SEVERITIES.map(s => <option key={s}>{s}</option>)}
              </select>
            </Field>
            <Field label="Condition Type">
              <select value={form.condition_type} onChange={e => set("condition_type", e.target.value)} className="input">
                {CONDITION_TYPES.map(c => <option key={c}>{c}</option>)}
              </select>
            </Field>
          </div>

          {/* Condition Config JSON */}
          <Field label="Condition Config (JSON)">
            <textarea
              value={form.condition_config}
              onChange={e => { set("condition_config", e.target.value); validateJson(e.target.value, "condition_config"); }}
              rows={4}
              className="input resize-none font-mono text-xs"
              placeholder='{"type": "always_flag"}'
            />
          </Field>

          {/* Row 3 */}
          <div className="grid grid-cols-2 gap-4">
            <Field label="Risk Weight (0–100)">
              <input type="number" min={0} max={100} value={form.notice_risk_weight} onChange={e => set("notice_risk_weight", e.target.value)} className="input" />
            </Field>
            <Field label="Risk Max (0–100)">
              <input type="number" min={0} max={100} value={form.notice_risk_max} onChange={e => set("notice_risk_max", e.target.value)} className="input" />
            </Field>
          </div>

          {/* Law code + explanation */}
          <div className="grid grid-cols-2 gap-4">
            <Field label="Law Code (optional)">
              <input value={form.law_code} onChange={e => set("law_code", e.target.value.toUpperCase())} placeholder="CGST_16_2" className="input" />
            </Field>
            <Field label="Penalty Formula Type">
              <select value={form.penalty_formula_type} onChange={e => set("penalty_formula_type", e.target.value)} className="input">
                {FORMULA_TYPES.map(f => <option key={f}>{f}</option>)}
              </select>
            </Field>
          </div>

          {/* Penalty config */}
          <Field label="Penalty Formula Config (JSON)">
            <textarea
              value={form.penalty_formula_config}
              onChange={e => { set("penalty_formula_config", e.target.value); validateJson(e.target.value, "penalty_formula_config"); }}
              rows={3}
              className="input resize-none font-mono text-xs"
              placeholder='{"rate": 0.18, "cap": 50000}'
            />
          </Field>

          {/* Plain explanation */}
          <Field label="Plain Explanation (shown to CA)">
            <textarea value={form.plain_explanation} onChange={e => set("plain_explanation", e.target.value)} rows={2} className="input resize-none" />
          </Field>

          {/* Effective dates */}
          <div className="grid grid-cols-2 gap-4">
            <Field label="Effective From">
              <input type="date" value={form.effective_from} onChange={e => set("effective_from", e.target.value)} className="input" />
            </Field>
            <Field label="Effective To">
              <input type="date" value={form.effective_to} onChange={e => set("effective_to", e.target.value)} className="input" />
            </Field>
          </div>

          {jsonError && (
            <p className="text-red-400 text-xs bg-red-500/10 px-3 py-2 rounded-lg">{jsonError}</p>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-white/[0.06] flex items-center justify-end gap-3">
          <button onClick={onClose} className="px-4 py-2 text-sm text-gray-400 hover:text-white transition-colors">Cancel</button>
          <button
            onClick={handleSubmit}
            disabled={saving || !!jsonError}
            className="px-5 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-medium rounded-lg transition-colors"
          >
            {saving ? "Saving..." : isEdit ? "Update Rule" : "Create Rule"}
          </button>
        </div>
      </div>

      <style jsx>{`
        .input {
          width: 100%;
          background: rgba(255,255,255,0.04);
          border: 1px solid rgba(255,255,255,0.08);
          border-radius: 0.5rem;
          padding: 0.5rem 0.75rem;
          color: white;
          font-size: 0.875rem;
          outline: none;
          transition: border-color 0.15s;
        }
        .input:focus { border-color: rgba(99,102,241,0.5); }
        .input::placeholder { color: rgba(156,163,175,0.6); }
        .input option { background: #1a1a2e; }
      `}</style>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-xs text-gray-400 font-medium mb-1.5">{label}</label>
      {children}
    </div>
  );
}
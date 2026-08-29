"use client";

import { useEffect, useState, useCallback } from "react";
import { lawsApi, Law } from "@/lib/adminApi";
import { Plus, Edit2, RefreshCw, X } from "lucide-react";
import toast from "react-hot-toast";

export default function LawsPage() {
  const [laws, setLaws]         = useState<Law[]>([]);
  const [loading, setLoading]   = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing]   = useState<Law | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await lawsApi.list({ active_only: false });
      setLaws(res.data.laws);
    } catch { toast.error("Failed to load laws"); }
    finally   { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">GST Law Catalog</h1>
          <p className="text-gray-400 text-sm mt-0.5">{laws.length} laws</p>
        </div>
        <div className="flex gap-2">
          <button onClick={load} className="p-2 bg-white/[0.04] border border-white/[0.08] rounded-lg text-gray-400 hover:text-white transition-colors">
            <RefreshCw className="w-4 h-4" />
          </button>
          <button
            onClick={() => { setEditing(null); setModalOpen(true); }}
            className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors"
          >
            <Plus className="w-4 h-4" /> Add Law
          </button>
        </div>
      </div>

      <div className="bg-white/[0.02] border border-white/[0.06] rounded-xl overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-white/[0.06]">
              {["Law Code", "Act Name", "Section", "Short Text", "Status", "Actions"].map(h => (
                <th key={h} className="text-left text-xs text-gray-500 font-medium px-4 py-3 uppercase tracking-wider">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              Array.from({ length: 4 }).map((_, i) => (
                <tr key={i} className="border-b border-white/[0.04]">
                  {Array.from({ length: 6 }).map((_, j) => (
                    <td key={j} className="px-4 py-3"><div className="h-4 bg-white/[0.06] rounded animate-pulse" /></td>
                  ))}
                </tr>
              ))
            ) : laws.length === 0 ? (
              <tr><td colSpan={6} className="text-center text-gray-500 py-12">No laws found. Add one.</td></tr>
            ) : (
              laws.map(law => (
                <tr key={law.id} className="border-b border-white/[0.04] hover:bg-white/[0.02] transition-colors">
                  <td className="px-4 py-3">
                    <code className="text-violet-300 text-xs bg-violet-500/10 px-2 py-0.5 rounded">{law.law_code}</code>
                  </td>
                  <td className="px-4 py-3 text-gray-200">{law.act_name}</td>
                  <td className="px-4 py-3 text-gray-400">{law.section}</td>
                  <td className="px-4 py-3 text-gray-400 max-w-xs truncate">{law.short_text}</td>
                  <td className="px-4 py-3">
                    <span className={`text-xs px-2 py-0.5 rounded ${law.is_active ? "bg-emerald-500/10 text-emerald-400" : "bg-gray-500/10 text-gray-500"}`}>
                      {law.is_active ? "Active" : "Inactive"}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() => { setEditing(law); setModalOpen(true); }}
                      className="p-1.5 text-gray-400 hover:text-white hover:bg-white/[0.06] rounded transition-colors"
                    >
                      <Edit2 className="w-3.5 h-3.5" />
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {modalOpen && (
        <LawModal
          law={editing}
          onClose={() => setModalOpen(false)}
          onSaved={() => { setModalOpen(false); load(); }}
        />
      )}
    </div>
  );
}

function LawModal({ law, onClose, onSaved }: { law: Law | null; onClose: () => void; onSaved: () => void }) {
  const [form, setForm] = useState({
    law_code:            law?.law_code            || "",
    act_name:            law?.act_name            || "",
    section:             law?.section             || "",
    short_text:          law?.short_text          || "",
    official_source_url: law?.official_source_url || "",
    is_active:           law?.is_active           ?? true,
  });
  const [saving, setSaving] = useState(false);
  const set = (k: string, v: string | boolean) => setForm(f => ({ ...f, [k]: v }));

  const handleSubmit = async () => {
    setSaving(true);
    try {
      if (law) {
        await lawsApi.update(law.id, form);
        toast.success("Law updated");
      } else {
        await lawsApi.create(form);
        toast.success("Law created");
      }
      onSaved();
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || "Save failed");
    } finally { setSaving(false); }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
      <div className="bg-[#0f0f1a] border border-white/[0.08] rounded-2xl w-full max-w-lg">
        <div className="flex items-center justify-between px-6 py-4 border-b border-white/[0.06]">
          <h2 className="text-white font-semibold">{law ? "Edit Law" : "Add Law"}</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-white"><X className="w-5 h-5" /></button>
        </div>
        <div className="px-6 py-4 space-y-4">
          {[
            { label: "Law Code *", key: "law_code", placeholder: "CGST_16_2" },
            { label: "Act Name *", key: "act_name", placeholder: "Central GST Act 2017" },
            { label: "Section *",  key: "section",  placeholder: "Section 16(2)" },
            { label: "Short Text", key: "short_text", placeholder: "ITC eligibility conditions..." },
            { label: "Source URL", key: "official_source_url", placeholder: "https://..." },
          ].map(({ label, key, placeholder }) => (
            <div key={key}>
              <label className="block text-xs text-gray-400 font-medium mb-1.5">{label}</label>
              <input
                value={(form as any)[key]}
                onChange={e => set(key, key === "law_code" ? e.target.value.toUpperCase() : e.target.value)}
                placeholder={placeholder}
                className="w-full bg-white/[0.04] border border-white/[0.08] rounded-lg px-3 py-2 text-white text-sm outline-none focus:border-indigo-500/50"
              />
            </div>
          ))}
          <label className="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" checked={form.is_active} onChange={e => set("is_active", e.target.checked)} className="accent-indigo-500" />
            <span className="text-sm text-gray-300">Active</span>
          </label>
        </div>
        <div className="px-6 py-4 border-t border-white/[0.06] flex justify-end gap-3">
          <button onClick={onClose} className="px-4 py-2 text-sm text-gray-400 hover:text-white">Cancel</button>
          <button onClick={handleSubmit} disabled={saving} className="px-5 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-colors">
            {saving ? "Saving..." : law ? "Update" : "Create"}
          </button>
        </div>
      </div>
    </div>
  );
}
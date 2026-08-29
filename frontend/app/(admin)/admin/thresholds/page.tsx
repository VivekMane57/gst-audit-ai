"use client";

import { useEffect, useState, useCallback } from "react";
import { thresholdsApi, Threshold } from "@/lib/adminApi";
import { Plus, Edit2, RefreshCw, X, CheckCircle } from "lucide-react";
import toast from "react-hot-toast";

export default function ThresholdsPage() {
  const [thresholds, setThresholds] = useState<Threshold[]>([]);
  const [loading, setLoading]       = useState(true);
  const [modalOpen, setModalOpen]   = useState(false);
  const [editing, setEditing]       = useState<Threshold | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await thresholdsApi.list();
      setThresholds(res.data.thresholds);
    } catch { toast.error("Failed to load thresholds"); }
    finally   { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Risk Thresholds</h1>
          <p className="text-gray-400 text-sm mt-0.5">Configure notice probability band boundaries</p>
        </div>
        <div className="flex gap-2">
          <button onClick={load} className="p-2 bg-white/[0.04] border border-white/[0.08] rounded-lg text-gray-400 hover:text-white transition-colors">
            <RefreshCw className="w-4 h-4" />
          </button>
          <button
            onClick={() => { setEditing(null); setModalOpen(true); }}
            className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors"
          >
            <Plus className="w-4 h-4" /> Add Profile
          </button>
        </div>
      </div>

      {/* Threshold cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {loading ? (
          Array.from({ length: 2 }).map((_, i) => (
            <div key={i} className="bg-white/[0.02] border border-white/[0.06] rounded-xl p-5 h-40 animate-pulse" />
          ))
        ) : thresholds.length === 0 ? (
          <div className="col-span-2 text-center text-gray-500 py-12 bg-white/[0.02] border border-white/[0.06] rounded-xl">
            No threshold profiles. Create one.
          </div>
        ) : (
          thresholds.map(t => (
            <div key={t.id} className="bg-white/[0.02] border border-white/[0.06] rounded-xl p-5">
              <div className="flex items-start justify-between mb-4">
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-white font-semibold">{t.profile_name}</h3>
                    {t.is_default && (
                      <span className="flex items-center gap-1 text-xs text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded">
                        <CheckCircle className="w-3 h-3" /> Default
                      </span>
                    )}
                  </div>
                </div>
                <button
                  onClick={() => { setEditing(t); setModalOpen(true); }}
                  className="p-1.5 text-gray-400 hover:text-white hover:bg-white/[0.06] rounded transition-colors"
                >
                  <Edit2 className="w-4 h-4" />
                </button>
              </div>

              {/* Band visualization */}
              <div className="space-y-2">
                {[
                  { label: "Low",      range: `0 – ${t.low_max}`,              color: "bg-blue-500" },
                  { label: "Medium",   range: `${t.low_max} – ${t.medium_max}`,color: "bg-amber-500" },
                  { label: "High",     range: `${t.medium_max} – ${t.high_max}`,color: "bg-orange-500" },
                  { label: "Critical", range: `${t.critical_min}+`,            color: "bg-red-500" },
                ].map(({ label, range, color }) => (
                  <div key={label} className="flex items-center gap-3">
                    <div className={`w-2 h-2 rounded-full ${color}`} />
                    <span className="text-gray-400 text-sm w-16">{label}</span>
                    <span className="text-gray-300 text-sm font-mono">{range}</span>
                  </div>
                ))}
              </div>
            </div>
          ))
        )}
      </div>

      {modalOpen && (
        <ThresholdModal
          threshold={editing}
          onClose={() => setModalOpen(false)}
          onSaved={() => { setModalOpen(false); load(); }}
        />
      )}
    </div>
  );
}

function ThresholdModal({ threshold, onClose, onSaved }: { threshold: Threshold | null; onClose: () => void; onSaved: () => void }) {
  const [form, setForm] = useState({
    profile_name: threshold?.profile_name || "",
    low_max:      threshold?.low_max      ?? 30,
    medium_max:   threshold?.medium_max   ?? 60,
    high_max:     threshold?.high_max     ?? 85,
    critical_min: threshold?.critical_min ?? 85,
    is_default:   threshold?.is_default   ?? false,
  });
  const [saving, setSaving] = useState(false);
  const [error, setError]   = useState("");

  const set = (k: string, v: string | number | boolean) => {
    setForm(f => ({ ...f, [k]: v }));
    setError("");
  };

  const handleSubmit = async () => {
    if (form.low_max >= form.medium_max || form.medium_max >= form.high_max) {
      setError("Bands must be ascending: low < medium < high");
      return;
    }
    setSaving(true);
    try {
      const payload = { ...form, critical_min: form.high_max };
      if (threshold) {
        await thresholdsApi.update(threshold.id, payload);
        toast.success("Threshold updated");
      } else {
        await thresholdsApi.create(payload);
        toast.success("Threshold created");
      }
      onSaved();
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || "Save failed");
    } finally { setSaving(false); }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
      <div className="bg-[#0f0f1a] border border-white/[0.08] rounded-2xl w-full max-w-md">
        <div className="flex items-center justify-between px-6 py-4 border-b border-white/[0.06]">
          <h2 className="text-white font-semibold">{threshold ? "Edit Threshold" : "New Threshold Profile"}</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-white"><X className="w-5 h-5" /></button>
        </div>
        <div className="px-6 py-4 space-y-4">
          <div>
            <label className="block text-xs text-gray-400 font-medium mb-1.5">Profile Name *</label>
            <input value={form.profile_name} onChange={e => set("profile_name", e.target.value)} placeholder="default" className="w-full bg-white/[0.04] border border-white/[0.08] rounded-lg px-3 py-2 text-white text-sm outline-none focus:border-indigo-500/50" />
          </div>
          {[
            { label: "Low Max (%)",    key: "low_max" },
            { label: "Medium Max (%)", key: "medium_max" },
            { label: "High Max (%)",   key: "high_max" },
          ].map(({ label, key }) => (
            <div key={key}>
              <label className="block text-xs text-gray-400 font-medium mb-1.5">{label}</label>
              <input type="number" min={0} max={100} value={(form as any)[key]} onChange={e => set(key, Number(e.target.value))} className="w-full bg-white/[0.04] border border-white/[0.08] rounded-lg px-3 py-2 text-white text-sm outline-none focus:border-indigo-500/50" />
            </div>
          ))}
          <label className="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" checked={form.is_default} onChange={e => set("is_default", e.target.checked)} className="accent-indigo-500" />
            <span className="text-sm text-gray-300">Set as default profile</span>
          </label>
          {error && <p className="text-red-400 text-xs bg-red-500/10 px-3 py-2 rounded-lg">{error}</p>}
        </div>
        <div className="px-6 py-4 border-t border-white/[0.06] flex justify-end gap-3">
          <button onClick={onClose} className="px-4 py-2 text-sm text-gray-400 hover:text-white">Cancel</button>
          <button onClick={handleSubmit} disabled={saving} className="px-5 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-colors">
            {saving ? "Saving..." : threshold ? "Update" : "Create"}
          </button>
        </div>
      </div>
    </div>
  );
}
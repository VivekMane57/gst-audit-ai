"use client";
import { useEffect, useState } from "react";
import { useUser } from "@clerk/nextjs";
import { useRouter } from "next/navigation";
import { Search, Plus, Upload, Trash2, Building2, ChevronRight } from "lucide-react";
import { getClients, addClient, deleteClient, setAuthHeader } from "@/lib/api";

interface Client {
  id:             string;
  business_name:  string;
  gstin_masked?:  string;
  gstin?:         string;
  sector?:        string;
  last_score?:    number;
  last_audit_at?: string;
  created_at?:    string;
}

const SECTORS = [
  { value: "",              label: "General" },
  { value: "healthcare",    label: "Healthcare / Pharma" },
  { value: "retail",        label: "Retail / Trading" },
  { value: "manufacturing", label: "Manufacturing" },
  { value: "it_services",   label: "IT / Services" },
  { value: "real_estate",   label: "Real Estate" },
  { value: "restaurant",    label: "Restaurant / Food" },
  { value: "export_import", label: "Export / Import" },
];

const scoreColor = (s: number) =>
  s >= 80 ? "text-green-600" : s >= 60 ? "text-yellow-600" : "text-red-600";

const scoreBg = (s: number) =>
  s >= 80 ? "bg-green-100" : s >= 60 ? "bg-yellow-100" : "bg-red-100";

export default function ClientsPage() {
  const { user }   = useUser();
  const router     = useRouter();

  const [clients,  setClients]  = useState<Client[]>([]);
  const [filtered, setFiltered] = useState<Client[]>([]);
  const [loading,  setLoading]  = useState(true);
  const [search,   setSearch]   = useState("");
  const [showAdd,  setShowAdd]  = useState(false);
  const [deleting, setDeleting] = useState<string | null>(null);

  // Add client form state
  const [form, setForm] = useState({
    business_name: "",
    gstin:         "",
    sector:        "",
  });
  const [adding, setAdding] = useState(false);
  const [formErr, setFormErr] = useState("");

  useEffect(() => {
    if (!user) return;
    setAuthHeader(user.id);
    fetchClients();
  }, [user]);

  useEffect(() => {
    const q = search.toLowerCase();
    setFiltered(
      clients.filter(c =>
        c.business_name.toLowerCase().includes(q) ||
        (c.gstin_masked || c.gstin || "").toLowerCase().includes(q) ||
        (c.sector || "").toLowerCase().includes(q)
      )
    );
  }, [search, clients]);

  const fetchClients = () => {
    setLoading(true);
    getClients()
      .then(r => {
        const list = Array.isArray(r.data) ? r.data : r.data?.clients ?? [];
        setClients(list);
        setFiltered(list);
      })
      .catch(() => setClients([]))
      .finally(() => setLoading(false));
  };

  const handleAdd = async () => {
    if (!form.business_name.trim()) return setFormErr("Business name required");
    if (!form.gstin.trim())         return setFormErr("GSTIN required");
    if (form.gstin.length !== 15)   return setFormErr("GSTIN must be 15 characters");

    setFormErr("");
    setAdding(true);
    try {
      await addClient({
        business_name: form.business_name.trim(),
        gstin:         form.gstin.toUpperCase(),
        sector:        form.sector || null,
      });
      setForm({ business_name: "", gstin: "", sector: "" });
      setShowAdd(false);
      fetchClients();
    } catch (e: any) {
      setFormErr(e?.response?.data?.detail || "Failed to add client");
    } finally {
      setAdding(false);
    }
  };

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm("Delete this client?")) return;
    setDeleting(id);
    try {
      await deleteClient(id);
      setClients(prev => prev.filter(c => c.id !== id));
    } catch {
      alert("Failed to delete client");
    } finally {
      setDeleting(null);
    }
  };

  const getInitials = (name: string) =>
    name.split(" ").slice(0, 2).map(w => w[0]).join("").toUpperCase();

  const getSectorLabel = (val?: string) =>
    SECTORS.find(s => s.value === val)?.label || "General";

  const formatDate = (d?: string) => {
    if (!d) return null;
    return new Date(d).toLocaleDateString("en-IN", { day: "numeric", month: "short" });
  };

  return (
    <div className="p-8 max-w-4xl mx-auto">

      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Clients</h1>
          <p className="text-gray-500 text-sm mt-1">
            {clients.length} client{clients.length !== 1 ? "s" : ""} registered
          </p>
        </div>
        <button
          onClick={() => setShowAdd(true)}
          className="flex items-center gap-2 bg-blue-600 text-white text-sm font-semibold px-4 py-2.5 rounded-xl hover:bg-blue-700"
        >
          <Plus size={16} /> Add Client
        </button>
      </div>

      {/* Add client modal */}
      {showAdd && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6">
            <h2 className="text-lg font-bold text-gray-900 mb-5">Add New Client</h2>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Business Name <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={form.business_name}
                  onChange={e => setForm(f => ({ ...f, business_name: e.target.value }))}
                  placeholder="e.g. Sharma Traders"
                  className="w-full border border-gray-300 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  GSTIN <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={form.gstin}
                  onChange={e => setForm(f => ({ ...f, gstin: e.target.value.toUpperCase() }))}
                  placeholder="27AABCS1234R1Z5"
                  maxLength={15}
                  className="w-full border border-gray-300 rounded-xl px-4 py-2.5 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <p className="text-xs text-gray-400 mt-1">{form.gstin.length}/15</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Business Sector
                </label>
                <select
                  value={form.sector}
                  onChange={e => setForm(f => ({ ...f, sector: e.target.value }))}
                  className="w-full border border-gray-300 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  {SECTORS.map(s => (
                    <option key={s.value} value={s.value}>{s.label}</option>
                  ))}
                </select>
              </div>

              {formErr && (
                <p className="text-sm text-red-500">{formErr}</p>
              )}
            </div>

            <div className="flex gap-3 mt-6">
              <button
                onClick={() => { setShowAdd(false); setFormErr(""); }}
                className="flex-1 py-2.5 border border-gray-200 rounded-xl text-sm text-gray-600 hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={handleAdd}
                disabled={adding}
                className="flex-1 py-2.5 bg-blue-600 text-white rounded-xl text-sm font-semibold hover:bg-blue-700 disabled:opacity-50"
              >
                {adding ? "Adding..." : "Add Client"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Search */}
      <div className="relative mb-5">
        <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
        <input
          type="text"
          placeholder="Search by name, GSTIN, or sector..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="w-full pl-9 pr-4 py-2.5 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      {/* Clients list */}
      {loading ? (
        <div className="space-y-3">
          {[1,2,3].map(i => (
            <div key={i} className="h-20 bg-gray-100 rounded-2xl animate-pulse" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-20 bg-white border border-gray-200 rounded-2xl">
          <Building2 size={40} className="text-gray-200 mx-auto mb-3" />
          <p className="text-gray-500 font-medium">
            {clients.length === 0 ? "No clients added yet" : "No results found"}
          </p>
          {clients.length === 0 && (
            <button
              onClick={() => setShowAdd(true)}
              className="text-blue-600 text-sm mt-2 hover:underline"
            >
              Add your first client →
            </button>
          )}
        </div>
      ) : (
        <div className="bg-white border border-gray-200 rounded-2xl overflow-hidden">
          {filtered.map((c, i) => (
            <div
              key={c.id}
              className={`flex items-center gap-4 px-5 py-4 hover:bg-gray-50 transition-colors ${
                i < filtered.length - 1 ? "border-b border-gray-100" : ""
              }`}
            >
              {/* Avatar */}
              <div className="w-10 h-10 rounded-xl bg-blue-100 text-blue-700 flex items-center justify-center font-bold text-sm shrink-0">
                {getInitials(c.business_name)}
              </div>

              {/* Info */}
              <div className="flex-1 min-w-0">
                <p className="font-semibold text-gray-900 text-sm">{c.business_name}</p>
                <p className="text-xs text-gray-400 mt-0.5">
                  {c.gstin_masked || c.gstin || "No GSTIN"} · {getSectorLabel(c.sector)}
                </p>
              </div>

              {/* Last score */}
              <div className="text-center shrink-0">
                {c.last_score != null ? (
                  <>
                    <div className={`w-10 h-10 rounded-xl flex items-center justify-center font-bold text-sm ${scoreBg(c.last_score)} ${scoreColor(c.last_score)}`}>
                      {c.last_score}
                    </div>
                    <p className="text-xs text-gray-400 mt-1">
                      {formatDate(c.last_audit_at) || "last audit"}
                    </p>
                  </>
                ) : (
                  <div className="w-10 h-10 rounded-xl bg-gray-100 flex items-center justify-center">
                    <span className="text-xs text-gray-400">—</span>
                  </div>
                )}
              </div>

              {/* Actions */}
              <div className="flex items-center gap-2 shrink-0">
                <button
                  onClick={() => router.push(`/upload?client_id=${c.id}`)}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 text-white rounded-lg text-xs font-medium hover:bg-blue-700"
                >
                  <Upload size={12} />
                  {c.last_score != null ? "Re-audit" : "Run Audit"}
                </button>
                <button
                  onClick={(e) => handleDelete(c.id, e)}
                  disabled={deleting === c.id}
                  className="p-1.5 rounded-lg hover:bg-red-50 text-gray-300 hover:text-red-500 transition-colors"
                >
                  <Trash2 size={14} />
                </button>
                <ChevronRight size={14} className="text-gray-300" />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
"use client";
import { useEffect, useState } from "react";
import { useUser } from "@clerk/nextjs";
import { useRouter } from "next/navigation";
import {
  Search, Plus, Upload, Trash2, Building2, Pencil, X,
  ChevronRight, Filter, ArrowUpRight, Phone, Mail, MapPin,
} from "lucide-react";
// ✅ FIX: updateClient import add kiya
import { getClients, addClient, updateClient, deleteClient, getReports, setAuthHeader } from "@/lib/api";

interface Client {
  id: string;
  business_name: string;
  gstin_masked?: string;
  gstin?: string;
  sector?: string;
  last_score?: number;
  last_audit_at?: string;
  created_at?: string;
  contact_person?: string;
  phone?: string;
  email?: string;
  address?: string;
}

interface Report {
  id: string;
  period?: string;
  compliance_score: number;
  created_at?: string;
  client_id?: string;
  itc_at_risk?: number;
  itc_summary?: { at_risk?: number };
}

const SECTORS = [
  { value: "", label: "All Sectors", icon: "📊" },
  { value: "healthcare", label: "Healthcare", icon: "🏥" },
  { value: "retail", label: "Retail / Trading", icon: "🛒" },
  { value: "manufacturing", label: "Manufacturing", icon: "🏭" },
  { value: "it_services", label: "IT / Services", icon: "💻" },
  { value: "real_estate", label: "Real Estate", icon: "🏢" },
  { value: "restaurant", label: "Restaurant", icon: "🍽️" },
  { value: "export_import", label: "Export / Import", icon: "🚢" },
];

const scoreColor = (s: number) =>
  s >= 80 ? "text-emerald-600" : s >= 60 ? "text-amber-500" : "text-red-500";
const scoreBg = (s: number) =>
  s >= 80 ? "bg-emerald-50 text-emerald-700" : s >= 60 ? "bg-amber-50 text-amber-700" : "bg-red-50 text-red-600";
const riskBadge = (s: number) =>
  s >= 80 ? "bg-emerald-50 text-emerald-700 border-emerald-200" : s >= 60 ? "bg-amber-50 text-amber-700 border-amber-200" : "bg-red-50 text-red-600 border-red-200";
const riskLabel = (s: number) =>
  s >= 80 ? "Low" : s >= 60 ? "Medium" : "High";

export default function ClientsPage() {
  const { user } = useUser();
  const router = useRouter();

  const [clients, setClients] = useState<Client[]>([]);
  const [reports, setReports] = useState<Report[]>([]);
  const [filtered, setFiltered] = useState<Client[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [sectorFilter, setSectorFilter] = useState("");
  const [showModal, setShowModal] = useState(false);
  const [editingClient, setEditingClient] = useState<Client | null>(null);
  const [selectedClient, setSelectedClient] = useState<Client | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);

  const [form, setForm] = useState({
    business_name: "", gstin: "", sector: "",
    contact_person: "", phone: "", email: "", address: "",
  });
  const [saving, setSaving] = useState(false);
  const [formErr, setFormErr] = useState("");

  useEffect(() => {
    if (!user) return;
    setAuthHeader(user.id);
    fetchData();
  }, [user]);

  useEffect(() => {
    let result = [...clients];
    if (search.trim()) {
      const q = search.toLowerCase();
      result = result.filter(c =>
        c.business_name.toLowerCase().includes(q) ||
        (c.gstin_masked || c.gstin || "").toLowerCase().includes(q) ||
        (c.sector || "").toLowerCase().includes(q) ||
        (c.contact_person || "").toLowerCase().includes(q)
      );
    }
    if (sectorFilter) {
      result = result.filter(c => c.sector === sectorFilter);
    }
    setFiltered(result);
  }, [search, sectorFilter, clients]);

  const fetchData = () => {
    setLoading(true);
    Promise.all([
      getClients().catch(() => ({ data: [] })),
      getReports().catch(() => ({ data: [] })),
    ]).then(([c, r]) => {
      const clientList = Array.isArray(c.data) ? c.data : c.data?.clients ?? [];
      const reportList = Array.isArray(r.data) ? r.data : r.data?.reports ?? [];
      setClients(clientList);
      setFiltered(clientList);
      setReports(reportList);
    }).finally(() => setLoading(false));
  };

  const openAddModal = () => {
    setEditingClient(null);
    setForm({ business_name: "", gstin: "", sector: "", contact_person: "", phone: "", email: "", address: "" });
    setFormErr("");
    setShowModal(true);
  };

  const openEditModal = (client: Client, e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingClient(client);
    setForm({
      business_name: client.business_name,
      gstin: client.gstin || client.gstin_masked?.replace(/\*/g, "") || "",
      sector: client.sector || "",
      contact_person: client.contact_person || "",
      phone: client.phone || "",
      email: client.email || "",
      address: client.address || "",
    });
    setFormErr("");
    setShowModal(true);
  };

  // ✅ FIX: handleSave — edit vs add dono handle hota hai ab
  const handleSave = async () => {
    if (!form.business_name.trim()) return setFormErr("Business name required");
    if (!form.gstin.trim()) return setFormErr("GSTIN required");
    if (form.gstin.length !== 15) return setFormErr("GSTIN must be 15 characters");
    setFormErr("");
    setSaving(true);
    try {
      if (editingClient) {
        // ✅ EDIT MODE — updateClient call
        await updateClient(editingClient.id, {
          business_name:  form.business_name.trim(),
          gstin:          form.gstin.toUpperCase(),
          sector:         form.sector || null,
          contact_person: form.contact_person.trim() || null,
          phone:          form.phone.trim() || null,
          email:          form.email.trim() || null,
          address:        form.address.trim() || null,
        });
        // ✅ selectedClient bhi update karo taaki detail panel refresh ho
        setSelectedClient(prev =>
          prev?.id === editingClient.id
            ? {
                ...prev,
                business_name:  form.business_name.trim(),
                gstin:          form.gstin.toUpperCase(),
                sector:         form.sector || undefined,
                contact_person: form.contact_person.trim() || undefined,
                phone:          form.phone.trim() || undefined,
                email:          form.email.trim() || undefined,
                address:        form.address.trim() || undefined,
              }
            : prev
        );
      } else {
        // ✅ ADD MODE — addClient call
        await addClient({
          business_name: form.business_name.trim(),
          gstin:         form.gstin.toUpperCase(),
          sector:        form.sector || null,
        });
      }
      setShowModal(false);
      fetchData();
    } catch (e: any) {
      setFormErr(e?.response?.data?.detail || "Failed to save client");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm("Delete this client? All audit history will remain.")) return;
    setDeleting(id);
    try {
      await deleteClient(id);
      setClients(prev => prev.filter(c => c.id !== id));
      if (selectedClient?.id === id) setSelectedClient(null);
    } catch { alert("Failed to delete"); }
    finally { setDeleting(null); }
  };

  const getInitials = (name: string) =>
    name.split(" ").slice(0, 2).map(w => w[0]).join("").toUpperCase();
  const getSectorInfo = (val?: string) =>
    SECTORS.find(s => s.value === val) || SECTORS[0];
  const getClientReports = (clientId: string) =>
    reports.filter(r => r.client_id === clientId).sort((a, b) =>
      new Date(b.created_at || 0).getTime() - new Date(a.created_at || 0).getTime()
    );
  const formatDate = (d?: string) =>
    d ? new Date(d).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" }) : "—";

  return (
    <div className="px-4 py-5 lg:px-8 lg:py-8 max-w-5xl mx-auto">

      {/* Header */}
      <div className="flex items-center justify-between mb-5 lg:mb-6 animate-fade-in">
        <div>
          <h1 className="text-2xl lg:text-3xl font-bold text-slate-900 tracking-tight">Clients</h1>
          <p className="text-slate-500 text-xs lg:text-sm mt-0.5">
            {clients.length} client{clients.length !== 1 ? "s" : ""} registered
          </p>
        </div>
        <button onClick={openAddModal}
          className="flex items-center gap-1.5 brand-gradient text-white text-xs lg:text-sm font-semibold px-4 py-2.5 rounded-xl btn-press shadow-sm shadow-blue-600/20">
          <Plus size={15} /> Add Client
        </button>
      </div>

      {/* Search + Sector Filter */}
      <div className="flex flex-col sm:flex-row gap-3 mb-5 animate-slide-up">
        <div className="flex-1 relative">
          <Search size={15} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
          <input type="text" placeholder="Search by name, GSTIN, contact..."
            value={search} onChange={e => setSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 border border-slate-200 rounded-xl text-sm bg-white focus:outline-none transition-all" />
        </div>
        <div className="flex items-center gap-1.5 overflow-x-auto scrollbar-hide">
          <Filter size={14} className="text-slate-400 shrink-0 ml-0.5" />
          {SECTORS.slice(0, 5).map(s => (
            <button key={s.value} onClick={() => setSectorFilter(sectorFilter === s.value ? "" : s.value)}
              className={`px-3 py-2 rounded-xl text-xs font-semibold border transition-all shrink-0 btn-press
                ${sectorFilter === s.value ? "brand-gradient text-white border-blue-600 shadow-sm" : "bg-white text-slate-600 border-slate-200 hover:border-slate-300"}`}>
              {s.icon} {s.value ? s.label.split("/")[0].trim() : "All"}
            </button>
          ))}
        </div>
      </div>

      {/* Stats Bar */}
      {clients.length > 0 && (
        <div className="flex gap-4 mb-5 text-xs text-slate-500 px-1 font-medium animate-fade-in">
          <span>{filtered.length} showing</span>
          <span>{clients.filter(c => c.last_score && c.last_score < 60).length} high risk</span>
          <span>{clients.filter(c => !c.last_score).length} not audited</span>
        </div>
      )}

      {/* Content — List + Detail Split on Desktop */}
      <div className="flex gap-5">

        {/* Client List */}
        <div className={`${selectedClient ? "hidden lg:block lg:w-2/5" : "w-full"} animate-slide-up`}>
          {loading ? (
            <div className="space-y-2.5">{[1,2,3].map(i => <div key={i} className="h-16 animate-shimmer rounded-xl" />)}</div>
          ) : filtered.length === 0 ? (
            <div className="text-center py-16 bg-white border border-slate-200 rounded-2xl shadow-sm">
              <div className="w-14 h-14 bg-slate-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
                <Building2 size={24} className="text-slate-300" />
              </div>
              <p className="text-slate-500 font-medium">{clients.length === 0 ? "No clients added yet" : "No results found"}</p>
              {clients.length === 0 && (
                <button onClick={openAddModal} className="text-blue-600 text-xs mt-2 hover:underline font-medium">Add your first client →</button>
              )}
            </div>
          ) : (
            <div className="space-y-2">
              {filtered.map(c => {
                const sector = getSectorInfo(c.sector);
                const isSelected = selectedClient?.id === c.id;
                return (
                  <div key={c.id} onClick={() => setSelectedClient(c)}
                    className={`bg-white border rounded-2xl p-4 cursor-pointer transition-all active:bg-slate-50 group
                      ${isSelected ? "border-blue-400 shadow-md shadow-blue-500/10" : "border-slate-200 hover:border-slate-300 shadow-sm"}`}>
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-xl bg-blue-100 text-blue-700 flex items-center justify-center font-bold text-sm shrink-0">
                        {getInitials(c.business_name)}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="font-semibold text-slate-900 text-sm truncate group-hover:text-blue-600 transition-colors">
                          {c.business_name}
                        </p>
                        <p className="text-[11px] text-slate-400 mt-0.5 truncate">
                          {c.gstin_masked || c.gstin || "No GSTIN"} · {sector.icon} {sector.label}
                        </p>
                      </div>
                      {c.last_score != null ? (
                        <div className={`w-10 h-10 rounded-xl flex items-center justify-center font-bold text-sm score-ring ${scoreBg(c.last_score)}`}>
                          {c.last_score}
                        </div>
                      ) : (
                        <div className="w-10 h-10 rounded-xl bg-slate-100 flex items-center justify-center">
                          <span className="text-[10px] text-slate-400">N/A</span>
                        </div>
                      )}
                      <ChevronRight size={16} className="text-slate-300 shrink-0 hidden lg:block" />
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Client Detail Panel */}
        {selectedClient && (
          <div className={`${selectedClient ? "w-full lg:w-3/5" : "hidden"} animate-scale-in`}>
            <div className="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden">

              {/* Detail Header */}
              <div className="p-5 border-b border-slate-100">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-12 h-12 rounded-xl bg-blue-100 text-blue-700 flex items-center justify-center font-bold text-lg">
                      {getInitials(selectedClient.business_name)}
                    </div>
                    <div>
                      <h2 className="font-bold text-lg text-slate-900">{selectedClient.business_name}</h2>
                      <p className="text-xs text-slate-400 font-mono mt-0.5">
                        {selectedClient.gstin_masked || selectedClient.gstin || "No GSTIN"}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <button onClick={(e) => openEditModal(selectedClient, e)}
                      className="p-2 rounded-lg hover:bg-slate-100 text-slate-400 hover:text-slate-600 transition-colors">
                      <Pencil size={15} />
                    </button>
                    <button onClick={() => setSelectedClient(null)}
                      className="p-2 rounded-lg hover:bg-slate-100 text-slate-400 hover:text-slate-600 transition-colors lg:hidden">
                      <X size={15} />
                    </button>
                  </div>
                </div>

                {/* Quick Info */}
                <div className="flex flex-wrap gap-2 mt-4">
                  {selectedClient.sector && (
                    <span className="px-2.5 py-1 bg-blue-50 text-blue-600 text-[11px] font-semibold rounded-full">
                      {getSectorInfo(selectedClient.sector).icon} {getSectorInfo(selectedClient.sector).label}
                    </span>
                  )}
                  {selectedClient.last_score != null && (
                    <span className={`px-2.5 py-1 text-[11px] font-bold rounded-full border ${riskBadge(selectedClient.last_score)}`}>
                      Score: {selectedClient.last_score} · {riskLabel(selectedClient.last_score)} Risk
                    </span>
                  )}
                  <span className="px-2.5 py-1 bg-slate-100 text-slate-500 text-[11px] font-medium rounded-full">
                    Added {formatDate(selectedClient.created_at)}
                  </span>
                </div>

                {/* Contact Info */}
                {(selectedClient.contact_person || selectedClient.phone || selectedClient.email) && (
                  <div className="mt-4 flex flex-wrap gap-3 text-xs text-slate-500">
                    {selectedClient.contact_person && <span className="flex items-center gap-1"><Building2 size={12} /> {selectedClient.contact_person}</span>}
                    {selectedClient.phone && <span className="flex items-center gap-1"><Phone size={12} /> {selectedClient.phone}</span>}
                    {selectedClient.email && <span className="flex items-center gap-1"><Mail size={12} /> {selectedClient.email}</span>}
                  </div>
                )}
              </div>

              {/* Actions */}
              <div className="p-4 border-b border-slate-100 flex gap-2">
                <button onClick={() => router.push(`/upload?client_id=${selectedClient.id}`)}
                  className="flex-1 flex items-center justify-center gap-2 py-2.5 brand-gradient text-white font-semibold rounded-xl text-sm btn-press shadow-sm shadow-blue-600/20">
                  <Upload size={15} /> Run Audit
                </button>
                <button onClick={(e) => handleDelete(selectedClient.id, e)}
                  disabled={deleting === selectedClient.id}
                  className="px-4 py-2.5 border border-red-200 text-red-500 rounded-xl text-sm font-medium hover:bg-red-50 btn-press">
                  <Trash2 size={15} />
                </button>
              </div>

              {/* Audit History */}
              <div className="p-5">
                <h3 className="font-bold text-sm text-slate-900 mb-3">Audit History</h3>
                {(() => {
                  const clientReports = getClientReports(selectedClient.id);
                  if (clientReports.length === 0) return (
                    <div className="text-center py-8">
                      <p className="text-slate-400 text-xs">No audits yet for this client</p>
                      <button onClick={() => router.push(`/upload?client_id=${selectedClient.id}`)}
                        className="text-blue-600 text-xs mt-2 hover:underline font-medium">Run first audit →</button>
                    </div>
                  );
                  return (
                    <div className="space-y-2">
                      {clientReports.map(r => (
                        <div key={r.id} onClick={() => router.push(`/reports/${r.id}`)}
                          className="flex items-center gap-3 p-3 rounded-xl hover:bg-slate-50 cursor-pointer active:bg-slate-100 transition-all group">
                          <div className={`w-10 h-10 rounded-xl flex items-center justify-center font-bold text-sm score-ring ${scoreBg(r.compliance_score)}`}>
                            {r.compliance_score}
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium text-slate-900 group-hover:text-blue-600 transition-colors">
                              {r.period || "—"}
                            </p>
                            <p className="text-[11px] text-slate-400">{formatDate(r.created_at)}</p>
                          </div>
                          <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold border ${riskBadge(r.compliance_score)}`}>
                            {riskLabel(r.compliance_score)}
                          </span>
                          <ArrowUpRight size={14} className="text-slate-300" />
                        </div>
                      ))}
                    </div>
                  );
                })()}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Add/Edit Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-50 flex items-end sm:items-center justify-center p-0 sm:p-4"
          onClick={() => setShowModal(false)}>
          <div className="bg-white rounded-t-2xl sm:rounded-2xl shadow-xl w-full sm:max-w-lg p-5 sm:p-6 animate-slide-up"
            onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-lg font-bold text-slate-900">
                {editingClient ? "Edit Client" : "Add New Client"}
              </h2>
              <button onClick={() => setShowModal(false)} className="p-1.5 rounded-lg hover:bg-slate-100 text-slate-400">
                <X size={18} />
              </button>
            </div>
            <div className="space-y-3">
              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-1">Business Name *</label>
                <input type="text" value={form.business_name}
                  onChange={e => setForm(f => ({ ...f, business_name: e.target.value }))}
                  placeholder="e.g. Sharma Traders Pvt. Ltd."
                  className="w-full border border-slate-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none transition-all" />
              </div>
              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-1">GSTIN *</label>
                <input type="text" value={form.gstin}
                  onChange={e => setForm(f => ({ ...f, gstin: e.target.value.toUpperCase() }))}
                  placeholder="27AABCS1234R1Z5" maxLength={15}
                  className="w-full border border-slate-200 rounded-xl px-4 py-2.5 text-sm font-mono focus:outline-none transition-all" />
                <p className="text-[10px] text-slate-400 mt-1">{form.gstin.length}/15 characters</p>
              </div>
              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-1">Sector</label>
                <div className="grid grid-cols-4 gap-1.5">
                  {SECTORS.filter(s => s.value).map(s => (
                    <button key={s.value} onClick={() => setForm(f => ({ ...f, sector: f.sector === s.value ? "" : s.value }))}
                      className={`p-2 rounded-xl border text-center transition-all btn-press text-[10px] font-semibold
                        ${form.sector === s.value ? "border-blue-500 bg-blue-50 text-blue-700" : "border-slate-200 text-slate-600"}`}>
                      <div className="text-sm mb-0.5">{s.icon}</div>
                      {s.label.split("/")[0].trim()}
                    </button>
                  ))}
                </div>
              </div>

              {/* Optional Contact Fields */}
              <details className="group">
                <summary className="text-xs text-blue-600 font-medium cursor-pointer hover:underline">
                  + Contact Details (optional)
                </summary>
                <div className="space-y-2 mt-3">
                  <input type="text" value={form.contact_person}
                    onChange={e => setForm(f => ({ ...f, contact_person: e.target.value }))}
                    placeholder="Contact Person Name"
                    className="w-full border border-slate-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none" />
                  <div className="grid grid-cols-2 gap-2">
                    <input type="tel" value={form.phone}
                      onChange={e => setForm(f => ({ ...f, phone: e.target.value }))}
                      placeholder="Phone"
                      className="border border-slate-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none" />
                    <input type="email" value={form.email}
                      onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
                      placeholder="Email"
                      className="border border-slate-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none" />
                  </div>
                  <input type="text" value={form.address}
                    onChange={e => setForm(f => ({ ...f, address: e.target.value }))}
                    placeholder="Address"
                    className="w-full border border-slate-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none" />
                </div>
              </details>

              {formErr && <p className="text-sm text-red-500 bg-red-50 px-4 py-2.5 rounded-xl border border-red-100">{formErr}</p>}
            </div>
            <div className="flex gap-3 mt-5">
              <button onClick={() => setShowModal(false)}
                className="flex-1 py-3 border border-slate-200 rounded-xl text-sm font-semibold text-slate-600 hover:bg-slate-50 btn-press">
                Cancel
              </button>
              <button onClick={handleSave} disabled={saving}
                className="flex-grow-[2] py-3 brand-gradient text-white rounded-xl text-sm font-semibold disabled:opacity-50 btn-press shadow-sm shadow-blue-600/20">
                {saving ? "Saving..." : editingClient ? "Update Client" : "Add Client"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
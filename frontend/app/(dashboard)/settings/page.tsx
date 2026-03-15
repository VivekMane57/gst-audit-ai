"use client";
import { useState } from "react";
import { useUser } from "@clerk/nextjs";
import { CheckCircle2, User, Globe, Bell, Shield, CreditCard } from "lucide-react";

const LANGUAGES = [
  { value: "en", label: "English",  desc: "Audit reports in English" },
  { value: "hi", label: "Hindi",    desc: "Audit reports in Hindi" },
  { value: "mr", label: "Marathi",  desc: "Audit reports in Marathi" },
];

const PLANS = [
  { id: "free",  name: "Free",  price: "₹0/mo",     audits: "3 audits/month",      highlight: false },
  { id: "pro",   name: "Pro",   price: "₹999/mo",   audits: "Unlimited audits",    highlight: true  },
  { id: "firm",  name: "Firm",  price: "₹2,499/mo", audits: "5 users + unlimited", highlight: false },
];

export default function SettingsPage() {
  const { user }                        = useUser();
  const [language, setLanguage]         = useState("en");
  const [emailAlerts, setEmailAlerts]   = useState(true);
  const [saved, setSaved]               = useState(false);

  const handleSave = () => {
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <div className="p-8 max-w-2xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
        <p className="text-gray-500 mt-1">Manage your account and preferences</p>
      </div>

      <div className="space-y-6">

        {/* ── Profile ─────────────────────────────── */}
        <section className="bg-white rounded-2xl border border-gray-200 p-6">
          <div className="flex items-center gap-3 mb-5">
            <div className="w-8 h-8 bg-blue-50 rounded-lg flex items-center justify-center">
              <User size={16} className="text-blue-600" />
            </div>
            <h2 className="font-semibold text-gray-900">Profile</h2>
          </div>
          <div className="flex items-center gap-4">
            {user?.imageUrl ? (
              <img src={user.imageUrl} alt="avatar" className="w-14 h-14 rounded-full object-cover" />
            ) : (
              <div className="w-14 h-14 rounded-full bg-blue-600 flex items-center justify-center text-white text-xl font-bold">
                {user?.firstName?.charAt(0) ?? "U"}
              </div>
            )}
            <div>
              <p className="font-semibold text-gray-900">{user?.fullName ?? "User"}</p>
              <p className="text-sm text-gray-400">{user?.primaryEmailAddress?.emailAddress}</p>
              <p className="text-xs text-blue-500 mt-1">Managed via Clerk</p>
            </div>
          </div>
        </section>

        {/* ── Report Language ───────────────────────── */}
        <section className="bg-white rounded-2xl border border-gray-200 p-6">
          <div className="flex items-center gap-3 mb-5">
            <div className="w-8 h-8 bg-green-50 rounded-lg flex items-center justify-center">
              <Globe size={16} className="text-green-600" />
            </div>
            <div>
              <h2 className="font-semibold text-gray-900">Report Language</h2>
              <p className="text-xs text-gray-400 mt-0.5">Language used in generated audit reports</p>
            </div>
          </div>
          <div className="space-y-2">
            {LANGUAGES.map((l) => (
              <button
                key={l.value}
                onClick={() => setLanguage(l.value)}
                className={`w-full flex items-center justify-between p-4 rounded-xl border-2 text-left transition-all
                  ${language === l.value
                    ? "border-blue-500 bg-blue-50"
                    : "border-gray-200 hover:border-gray-300 bg-white"}`}
              >
                <div>
                  <p className={`font-medium text-sm ${language === l.value ? "text-blue-700" : "text-gray-900"}`}>
                    {l.label}
                  </p>
                  <p className="text-xs text-gray-400 mt-0.5">{l.desc}</p>
                </div>
                {language === l.value && <CheckCircle2 size={18} className="text-blue-500 shrink-0" />}
              </button>
            ))}
          </div>
        </section>

        {/* ── Notifications ────────────────────────── */}
        <section className="bg-white rounded-2xl border border-gray-200 p-6">
          <div className="flex items-center gap-3 mb-5">
            <div className="w-8 h-8 bg-yellow-50 rounded-lg flex items-center justify-center">
              <Bell size={16} className="text-yellow-600" />
            </div>
            <h2 className="font-semibold text-gray-900">Notifications</h2>
          </div>
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium text-gray-900 text-sm">Email Alerts</p>
              <p className="text-xs text-gray-400 mt-0.5">Get notified when high-risk issues are detected</p>
            </div>
            <button
              onClick={() => setEmailAlerts(!emailAlerts)}
              aria-label="Toggle email alerts"
              className={`relative w-11 h-6 rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-400
                ${emailAlerts ? "bg-blue-500" : "bg-gray-200"}`}
            >
              <div className={`absolute top-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform
                ${emailAlerts ? "translate-x-5" : "translate-x-0.5"}`}
              />
            </button>
          </div>
        </section>

        {/* ── Plan ─────────────────────────────────── */}
        <section className="bg-white rounded-2xl border border-gray-200 p-6">
          <div className="flex items-center gap-3 mb-5">
            <div className="w-8 h-8 bg-purple-50 rounded-lg flex items-center justify-center">
              <CreditCard size={16} className="text-purple-600" />
            </div>
            <div>
              <h2 className="font-semibold text-gray-900">Billing Plan</h2>
              <p className="text-xs text-gray-400 mt-0.5">Currently on Free plan</p>
            </div>
          </div>
          <div className="grid grid-cols-3 gap-3">
            {PLANS.map((p) => (
              <div
                key={p.id}
                className={`rounded-xl border-2 p-4 ${p.highlight
                  ? "border-blue-500 bg-blue-50"
                  : "border-gray-200 bg-white"}`}
              >
                <p className="font-bold text-gray-900 text-sm">{p.name}</p>
                <p className={`text-base font-bold mt-1 ${p.highlight ? "text-blue-600" : "text-gray-700"}`}>
                  {p.price}
                </p>
                <p className="text-xs text-gray-400 mt-1">{p.audits}</p>
                {p.id !== "free" ? (
                  <button className="mt-3 w-full bg-blue-600 text-white text-xs py-1.5 rounded-lg hover:bg-blue-700 transition-colors font-medium">
                    Upgrade
                  </button>
                ) : (
                  <p className="mt-3 text-xs text-green-600 font-semibold">Active</p>
                )}
              </div>
            ))}
          </div>
        </section>

        {/* ── Security ─────────────────────────────── */}
        <section className="bg-white rounded-2xl border border-gray-200 p-6">
          <div className="flex items-center gap-3 mb-5">
            <div className="w-8 h-8 bg-red-50 rounded-lg flex items-center justify-center">
              <Shield size={16} className="text-red-500" />
            </div>
            <h2 className="font-semibold text-gray-900">Security</h2>
          </div>
          <div className="space-y-0 divide-y divide-gray-100">
            {[
              { label: "GSTIN Encryption",  detail: "All GSTINs stored with AES-256 encryption",      badge: "Active",    color: "bg-green-100 text-green-700" },
              { label: "Data Isolation",    detail: "Row-level security — only your data is visible",  badge: "Active",    color: "bg-green-100 text-green-700" },
              { label: "Storage Region",    detail: "Asia Pacific (Singapore) — closest to India",     badge: "IN Region", color: "bg-blue-100 text-blue-700"   },
            ].map((row) => (
              <div key={row.label} className="flex items-center justify-between py-3">
                <div>
                  <p className="font-medium text-gray-900 text-sm">{row.label}</p>
                  <p className="text-xs text-gray-400 mt-0.5">{row.detail}</p>
                </div>
                <span className={`px-2.5 py-1 text-xs font-semibold rounded-full shrink-0 ${row.color}`}>
                  {row.badge}
                </span>
              </div>
            ))}
          </div>
        </section>

        {/* ── Save ─────────────────────────────────── */}
        <button
          onClick={handleSave}
          className="w-full bg-blue-600 text-white font-semibold py-3.5 rounded-xl
                     hover:bg-blue-700 transition-colors flex items-center justify-center gap-2"
        >
          {saved
            ? <><CheckCircle2 size={18} /> Preferences Saved</>
            : "Save Preferences"}
        </button>

      </div>
    </div>
  );
}
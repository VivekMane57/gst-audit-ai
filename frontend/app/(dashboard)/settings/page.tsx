"use client";
import { useState } from "react";
import { useUser } from "@clerk/nextjs";
import {
  CheckCircle2, User, Globe, Bell, Shield,
  CreditCard, Zap, Lock, Server, Check, X, AlertCircle
} from "lucide-react";

const LANGUAGES = [
  { value: "en", label: "English", flag: "🇬🇧", desc: "Reports in English" },
  { value: "hi", label: "हिंदी",   flag: "🇮🇳", desc: "रिपोर्ट हिंदी में"  },
  { value: "mr", label: "मराठी",  flag: "🇮🇳", desc: "अहवाल मराठीत"      },
];

const PLANS = [
  {
    id:        "free",
    name:      "Starter",
    price:     "₹0",
    period:    "/month",
    audits:    "3 audits/month",
    features:  ["3 GST audits/month", "PDF reports", "EN/HI/MR language", "Email support"],
    missing:   ["Unlimited audits", "Bulk upload", "Priority support", "API access"],
    highlight: false,
    badge:     null,
    plan_id:   null,
  },
  {
    id:        "pro",
    name:      "Pro",
    price:     "₹999",
    period:    "/month",
    audits:    "Unlimited audits",
    features:  ["Unlimited audits", "PDF + Excel reports", "EN/HI/MR language", "Notice Simulator", "OCR image scanning", "Priority email support"],
    missing:   ["Multi-user access", "API access"],
    highlight: true,
    badge:     "Most Popular",
    plan_id:   "plan_SUnDUixyhRB0ic", // Pro ₹999/month
  },
  {
    id:        "firm",
    name:      "Firm",
    price:     "₹2,499",
    period:    "/month",
    audits:    "5 users + unlimited",
    features:  ["5 user accounts", "Unlimited audits", "All Pro features", "Bulk client upload", "Dedicated support", "API access"],
    missing:   [],
    highlight: false,
    badge:     "For CA Firms",
    plan_id:   "plan_SUnEYNhFhZiClX", // Firm ₹2499/month
  },
];

function loadRazorpay(): Promise<boolean> {
  return new Promise((resolve) => {
    if (typeof window === "undefined") return resolve(false);
    if ((window as any).Razorpay)      return resolve(true);
    const script    = document.createElement("script");
    script.src      = "https://checkout.razorpay.com/v1/checkout.js";
    script.onload   = () => resolve(true);
    script.onerror  = () => resolve(false);
    document.body.appendChild(script);
  });
}

export default function SettingsPage() {
  const { user }                      = useUser();
  const [language, setLanguage]       = useState("en");
  const [emailAlerts, setEmailAlerts] = useState(true);
  const [saved, setSaved]             = useState(false);
  const [currentPlan, setCurrentPlan] = useState("free");
  const [payLoading, setPayLoading]   = useState<string | null>(null);
  const [payError, setPayError]       = useState<string | null>(null);

  const handleSave = () => {
    setSaved(true);
    setTimeout(() => setSaved(false), 2500);
  };

  const handleUpgrade = async (planId: string, planName: string, rzpPlanId: string) => {
    setPayLoading(planId);
    setPayError(null);

    try {
      // Step 1: Razorpay JS load karo
      const loaded = await loadRazorpay();
      if (!loaded) throw new Error("Razorpay load nahi hua. Internet check karo.");

      // Step 2: Backend se subscription_id lo
      const res = await fetch("/api/create-subscription", {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          plan_id: rzpPlanId,
          user_id: user?.id                                || "",
          email:   user?.primaryEmailAddress?.emailAddress || "",
          name:    user?.fullName                          || "",
        }),
      });

      const data = await res.json();
      if (!res.ok || !data.subscription_id) {
        throw new Error(data.error || "Subscription create nahi hua");
      }

      // Step 3: Razorpay modal — subscription_id pass karo (amount nahi)
      const options = {
        key:             process.env.NEXT_PUBLIC_RAZORPAY_KEY_ID || "",
        subscription_id: data.subscription_id, // ← yahi real subscription flow hai
        name:            "AuditAI",
        description:     `${planName} Plan — Monthly Subscription`,
        image:           "/logo.png",
        prefill: {
          name:  user?.fullName                              || "",
          email: user?.primaryEmailAddress?.emailAddress     || "",
        },
        theme: { color: "#2563EB" },

        handler: async (response: any) => {
          // TODO: /api/verify-subscription call karke DB update karo
          // await fetch("/api/verify-subscription", { method: "POST", body: JSON.stringify(response) });
          setCurrentPlan(planId);
          setPayLoading(null);
          alert(
            `✅ Subscription active! Welcome to ${planName}.\n\n` +
            `Payment ID: ${response.razorpay_payment_id}\n` +
            `Subscription ID: ${response.razorpay_subscription_id}`
          );
        },

        modal: { ondismiss: () => setPayLoading(null) },
      };

      const rzp = new (window as any).Razorpay(options);
      rzp.on("payment.failed", (response: any) => {
        setPayError(response.error?.description || "Payment fail hua");
        setPayLoading(null);
      });
      rzp.open();

    } catch (err: any) {
      setPayError(err.message || "Kuch galat hua, dobara try karo");
      setPayLoading(null);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-2xl mx-auto px-4 py-6 lg:py-8">

        <div className="mb-8">
          <h1 className="text-2xl font-bold text-gray-900 tracking-tight">Settings</h1>
          <p className="text-gray-500 mt-1 text-sm">Manage your account, preferences, and billing</p>
        </div>

        <div className="space-y-5">

          {/* Profile */}
          <section className="bg-white rounded-2xl border border-gray-200 p-5 lg:p-6">
            <div className="flex items-center gap-3 mb-5">
              <div className="w-8 h-8 bg-blue-50 rounded-lg flex items-center justify-center">
                <User size={15} className="text-blue-600" />
              </div>
              <h2 className="font-semibold text-gray-900">Profile</h2>
            </div>
            <div className="flex items-center gap-4">
              {user?.imageUrl ? (
                <img src={user.imageUrl} alt="avatar" className="w-12 h-12 lg:w-14 lg:h-14 rounded-full object-cover" />
              ) : (
                <div className="w-12 h-12 lg:w-14 lg:h-14 rounded-full bg-gradient-to-br from-blue-500 to-blue-700 flex items-center justify-center text-white text-lg font-bold">
                  {user?.firstName?.charAt(0) ?? "U"}
                </div>
              )}
              <div>
                <p className="font-semibold text-gray-900 text-sm lg:text-base">{user?.fullName ?? "User"}</p>
                <p className="text-xs lg:text-sm text-gray-400">{user?.primaryEmailAddress?.emailAddress}</p>
                <span className="mt-1 inline-flex items-center gap-1 text-xs text-blue-500 bg-blue-50 px-2 py-0.5 rounded-full">
                  <Lock size={10} /> Managed via Clerk
                </span>
              </div>
            </div>
          </section>

          {/* Billing */}
          <section className="bg-white rounded-2xl border border-gray-200 overflow-hidden">
            <div className="p-5 lg:p-6 border-b border-gray-100">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 bg-purple-50 rounded-lg flex items-center justify-center">
                  <CreditCard size={15} className="text-purple-600" />
                </div>
                <div>
                  <h2 className="font-semibold text-gray-900">Billing Plan</h2>
                  <p className="text-xs text-gray-400 mt-0.5">
                    Currently on <span className="font-semibold text-blue-600 capitalize">{currentPlan}</span> plan
                  </p>
                </div>
              </div>
            </div>

            <div className="p-5 lg:p-6 space-y-4">
              {payError && (
                <div className="flex items-start gap-2 bg-red-50 border border-red-200 text-red-700 text-xs rounded-xl px-4 py-3">
                  <AlertCircle size={14} className="shrink-0 mt-0.5" />
                  <span>{payError}</span>
                  <button onClick={() => setPayError(null)} className="ml-auto shrink-0 opacity-60 hover:opacity-100">
                    <X size={13} />
                  </button>
                </div>
              )}

              {PLANS.map((plan) => {
                const isActive  = currentPlan === plan.id;
                const isLoading = payLoading  === plan.id;
                return (
                  <div
                    key={plan.id}
                    className={`relative rounded-xl border-2 p-4 transition-all ${
                      plan.highlight
                        ? "border-blue-500 bg-gradient-to-br from-blue-50 to-indigo-50"
                        : isActive
                        ? "border-green-400 bg-green-50"
                        : "border-gray-200 bg-white hover:border-gray-300"
                    }`}
                  >
                    {plan.badge && (
                      <span className={`absolute -top-3 left-4 text-xs font-bold px-3 py-1 rounded-full ${
                        plan.highlight ? "bg-blue-600 text-white" : "bg-gray-700 text-white"
                      }`}>
                        {plan.badge}
                      </span>
                    )}
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1">
                        <div className="flex items-baseline gap-1 mb-1">
                          <span className="font-bold text-gray-900 text-base">{plan.name}</span>
                          <span className={`text-xl font-black ml-2 ${plan.highlight ? "text-blue-700" : "text-gray-800"}`}>
                            {plan.price}
                          </span>
                          <span className="text-xs text-gray-400">{plan.period}</span>
                        </div>
                        <p className="text-xs text-gray-500 mb-3">{plan.audits}</p>
                        <div className="space-y-1.5">
                          {plan.features.map((f, i) => (
                            <div key={i} className="flex items-center gap-2">
                              <Check size={12} className={`shrink-0 ${plan.highlight ? "text-blue-600" : "text-green-500"}`} />
                              <span className="text-xs text-gray-600">{f}</span>
                            </div>
                          ))}
                          {plan.missing.map((f, i) => (
                            <div key={i} className="flex items-center gap-2 opacity-40">
                              <X size={12} className="shrink-0 text-gray-400" />
                              <span className="text-xs text-gray-400 line-through">{f}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                      <div className="shrink-0 mt-1">
                        {isActive ? (
                          <div className="flex items-center gap-1.5 text-green-600 bg-green-100 px-3 py-1.5 rounded-lg">
                            <CheckCircle2 size={14} />
                            <span className="text-xs font-semibold">Active</span>
                          </div>
                        ) : plan.id === "free" ? (
                          <button className="px-3 py-1.5 text-xs text-gray-400 bg-gray-100 rounded-lg cursor-not-allowed">
                            Downgrade
                          </button>
                        ) : (
                          <button
                            onClick={() => handleUpgrade(plan.id, plan.name, plan.plan_id!)}
                            disabled={!!payLoading}
                            className={`flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-bold transition-all active:scale-95 ${
                              plan.highlight
                                ? "bg-blue-600 hover:bg-blue-700 text-white shadow-md shadow-blue-200"
                                : "bg-gray-900 hover:bg-gray-800 text-white"
                            } disabled:opacity-60`}
                          >
                            {isLoading ? (
                              <>
                                <div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" />
                                Loading...
                              </>
                            ) : (
                              <><Zap size={12} /> Upgrade</>
                            )}
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}

              <p className="text-xs text-gray-400 text-center pt-2">
                🔒 Secure payment via Razorpay · Auto-renews monthly · Cancel anytime · GST invoice provided
              </p>
            </div>
          </section>

          {/* Language */}
          <section className="bg-white rounded-2xl border border-gray-200 p-5 lg:p-6">
            <div className="flex items-center gap-3 mb-5">
              <div className="w-8 h-8 bg-green-50 rounded-lg flex items-center justify-center">
                <Globe size={15} className="text-green-600" />
              </div>
              <div>
                <h2 className="font-semibold text-gray-900">Report Language</h2>
                <p className="text-xs text-gray-400 mt-0.5">Language for generated audit reports</p>
              </div>
            </div>
            <div className="grid grid-cols-3 gap-2">
              {LANGUAGES.map((l) => (
                <button
                  key={l.value}
                  onClick={() => setLanguage(l.value)}
                  className={`flex flex-col items-center gap-1.5 p-3 rounded-xl border-2 text-center transition-all active:scale-95 ${
                    language === l.value
                      ? "border-blue-500 bg-blue-50"
                      : "border-gray-200 hover:border-gray-300 bg-white"
                  }`}
                >
                  <span className="text-xl">{l.flag}</span>
                  <span className={`font-semibold text-xs ${language === l.value ? "text-blue-700" : "text-gray-700"}`}>
                    {l.label}
                  </span>
                  <span className="text-[10px] text-gray-400 leading-tight">{l.desc}</span>
                  {language === l.value && <CheckCircle2 size={12} className="text-blue-500" />}
                </button>
              ))}
            </div>
          </section>

          {/* Notifications */}
          <section className="bg-white rounded-2xl border border-gray-200 p-5 lg:p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-8 h-8 bg-amber-50 rounded-lg flex items-center justify-center">
                <Bell size={15} className="text-amber-600" />
              </div>
              <h2 className="font-semibold text-gray-900">Notifications</h2>
            </div>
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium text-gray-900 text-sm">Email Alerts</p>
                <p className="text-xs text-gray-400 mt-0.5">Notify when HIGH risk issues detected</p>
              </div>
              <button
                onClick={() => setEmailAlerts(!emailAlerts)}
                className={`relative w-11 h-6 rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-400 ${
                  emailAlerts ? "bg-blue-500" : "bg-gray-200"
                }`}
              >
                <div className={`absolute top-0.5 w-5 h-5 bg-white rounded-full shadow-sm transition-transform ${
                  emailAlerts ? "translate-x-5" : "translate-x-0.5"
                }`} />
              </button>
            </div>
          </section>

          {/* Security */}
          <section className="bg-white rounded-2xl border border-gray-200 p-5 lg:p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-8 h-8 bg-red-50 rounded-lg flex items-center justify-center">
                <Shield size={15} className="text-red-500" />
              </div>
              <h2 className="font-semibold text-gray-900">Security</h2>
            </div>
            <div className="divide-y divide-gray-100">
              {[
                { icon: Lock,   label: "GSTIN Encryption", detail: "AES-256 encryption at rest",  badge: "Active",    color: "bg-green-100 text-green-700" },
                { icon: Shield, label: "Data Isolation",   detail: "Row-level security per user", badge: "Active",    color: "bg-green-100 text-green-700" },
                { icon: Server, label: "Storage Region",   detail: "Asia Pacific (Singapore)",    badge: "IN Region", color: "bg-blue-100 text-blue-700"   },
              ].map((row) => (
                <div key={row.label} className="flex items-center justify-between py-3">
                  <div className="flex items-center gap-2.5">
                    <row.icon size={14} className="text-gray-400 shrink-0" />
                    <div>
                      <p className="font-medium text-gray-900 text-sm">{row.label}</p>
                      <p className="text-xs text-gray-400 mt-0.5">{row.detail}</p>
                    </div>
                  </div>
                  <span className={`px-2.5 py-1 text-xs font-semibold rounded-full shrink-0 ${row.color}`}>
                    {row.badge}
                  </span>
                </div>
              ))}
            </div>
          </section>

          {/* Save */}
          <button
            onClick={handleSave}
            className="w-full bg-blue-600 text-white font-semibold py-3.5 rounded-xl hover:bg-blue-700 active:scale-[0.98] transition-all flex items-center justify-center gap-2"
          >
            {saved ? <><CheckCircle2 size={17} /> Preferences Saved!</> : "Save Preferences"}
          </button>

        </div>
      </div>
    </div>
  );
}
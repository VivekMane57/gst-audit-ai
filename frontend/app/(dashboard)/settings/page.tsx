"use client";
import { useState, useEffect } from "react";
import { useUser } from "@clerk/nextjs";
import { useSearchParams } from "next/navigation";
import {
  CheckCircle2, User, Globe, Bell, Shield,
  CreditCard, Zap, Lock, Server, Check, X,
  AlertCircle, Star, ArrowRight, Sparkles,
} from "lucide-react";

// ── Data ──────────────────────────────────────────────────────
const LANGUAGES = [
  { value: "en", label: "English", flag: "🇬🇧", desc: "Reports in English" },
  { value: "hi", label: "हिंदी",   flag: "🇮🇳", desc: "रिपोर्ट हिंदी में"  },
  { value: "mr", label: "मराठी",  flag: "🇮🇳", desc: "अहवाल मराठीत"      },
];

const PLANS = [
  {
    id:       "free",
    name:     "Starter",
    price:    0,
    period:   "forever",
    tagline:  "Get started for free",
    color:    "gray",
    badge:    null,
    plan_id:  null,
    features: [
      "3 GST audits / month",
      "PDF reports",
      "EN / HI / MR language",
      "Email support",
    ],
    locked: ["Unlimited audits", "OCR scanning", "Notice Simulator", "API access"],
  },
  {
    id:       "pro",
    name:     "Pro",
    price:    999,
    period:   "/ mo",
    tagline:  "For individual CAs",
    color:    "blue",
    badge:    "Most Popular",
    plan_id:  "plan_SUnDUixyhRB0ic",
    features: [
      "Unlimited audits",
      "OCR image & PDF scanning",
      "Notice Simulator",
      "GSTR-2B reconciliation",
      "Supplier trust scores",
      "Priority email support",
      "PDF + Excel exports",
    ],
    locked: ["5 team members", "API access"],
  },
  {
    id:       "firm",
    name:     "Firm",
    price:    2499,
    period:   "/ mo",
    tagline:  "For CA firms & teams",
    color:    "violet",
    badge:    "For Firms",
    plan_id:  "plan_SUnEYNhFhZiClX",
    features: [
      "Everything in Pro",
      "5 team members",
      "Bulk client upload",
      "White-label PDF reports",
      "API access",
      "Dedicated account manager",
    ],
    locked: [],
  },
];

// ── Razorpay loader ───────────────────────────────────────────
declare global { interface Window { Razorpay: any } }

function loadRazorpay(): Promise<boolean> {
  return new Promise(resolve => {
    if (typeof window === "undefined") return resolve(false);
    if (window.Razorpay) return resolve(true);
    const s   = document.createElement("script");
    s.src     = "https://checkout.razorpay.com/v1/checkout.js";
    s.onload  = () => resolve(true);
    s.onerror = () => resolve(false);
    document.body.appendChild(s);
  });
}

// ── Plan card colors ──────────────────────────────────────────
const PLAN_THEME: Record<string, {
  card: string; header: string; badge: string;
  btn: string; check: string; price: string;
}> = {
  gray: {
    card:   "border-slate-200",
    header: "bg-slate-50",
    badge:  "bg-slate-200 text-slate-600",
    btn:    "bg-slate-100 text-slate-500 cursor-not-allowed",
    check:  "text-slate-400",
    price:  "text-slate-800",
  },
  blue: {
    card:   "border-blue-500 ring-2 ring-blue-500/20",
    header: "bg-gradient-to-br from-blue-600 to-blue-700",
    badge:  "bg-yellow-400 text-yellow-900",
    btn:    "bg-blue-600 hover:bg-blue-700 text-white shadow-lg shadow-blue-600/30",
    check:  "text-blue-500",
    price:  "text-blue-700",
  },
  violet: {
    card:   "border-violet-300 ring-1 ring-violet-200",
    header: "bg-gradient-to-br from-violet-600 to-violet-700",
    badge:  "bg-violet-100 text-violet-700",
    btn:    "bg-violet-600 hover:bg-violet-700 text-white shadow-lg shadow-violet-600/30",
    check:  "text-violet-500",
    price:  "text-violet-700",
  },
};

// ── Section wrapper ───────────────────────────────────────────
function Section({ icon, iconBg, iconColor, title, subtitle, children }: {
  icon: any; iconBg: string; iconColor: string;
  title: string; subtitle?: string; children: React.ReactNode;
}) {
  const Icon = icon;
  return (
    <section className="bg-white rounded-2xl border border-gray-200 overflow-hidden shadow-sm">
      <div className="flex items-center gap-3 px-5 py-4 border-b border-gray-100">
        <div className={`w-8 h-8 ${iconBg} rounded-lg flex items-center justify-center`}>
          <Icon size={15} className={iconColor} />
        </div>
        <div>
          <h2 className="font-semibold text-gray-900 text-sm">{title}</h2>
          {subtitle && <p className="text-[11px] text-gray-400 mt-0.5">{subtitle}</p>}
        </div>
      </div>
      <div className="p-5">{children}</div>
    </section>
  );
}

// ── Main ──────────────────────────────────────────────────────
export default function SettingsPage() {
  const { user }                       = useUser();
  const searchParams                   = useSearchParams();
  const [language, setLanguage]        = useState("en");
  const [emailAlerts, setEmailAlerts]  = useState(true);
  const [saved, setSaved]              = useState(false);
  const [currentPlan, setCurrentPlan]  = useState("free");
  const [payLoading, setPayLoading]    = useState<string | null>(null);
  const [payError, setPayError]        = useState<string | null>(null);
  const [successPlan, setSuccessPlan]  = useState<string | null>(null);

  // Show success if redirected after payment
  useEffect(() => {
    const upgraded = searchParams.get("upgraded");
    if (upgraded) {
      setCurrentPlan(upgraded);
      setSuccessPlan(upgraded);
      setTimeout(() => setSuccessPlan(null), 5000);
    }
  }, [searchParams]);

  const handleSave = () => { setSaved(true); setTimeout(() => setSaved(false), 2500); };

  const handleUpgrade = async (plan: typeof PLANS[0]) => {
    if (!plan.plan_id) return;
    setPayLoading(plan.id);
    setPayError(null);

    try {
      const loaded = await loadRazorpay();
      if (!loaded) throw new Error("Razorpay load nahi hua. Internet check karo.");

      const res = await fetch("/api/create-subscription", {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          plan_id: plan.plan_id,
          user_id: user?.id || "",
          email:   user?.primaryEmailAddress?.emailAddress || "",
          name:    user?.fullName || "",
        }),
      });

      const data = await res.json();
      if (!res.ok || !data.subscription_id) throw new Error(data.error || "Subscription create nahi hua");

      const options = {
        key:             process.env.NEXT_PUBLIC_RAZORPAY_KEY_ID || "",
        subscription_id: data.subscription_id,
        name:            "AuditAI",
        description:     `${plan.name} Plan — Monthly Subscription`,
        image:           "/logo.png",
        prefill: {
          name:  user?.fullName || "",
          email: user?.primaryEmailAddress?.emailAddress || "",
        },
        theme: { color: plan.color === "blue" ? "#2563EB" : "#7C3AED" },
        handler: (response: any) => {
          // Webhook DB update karega — optimistic UI update
          setCurrentPlan(plan.id);
          setSuccessPlan(plan.name);
          setPayLoading(null);
          setTimeout(() => setSuccessPlan(null), 5000);
        },
        modal: { ondismiss: () => setPayLoading(null) },
      };

      const rzp = new window.Razorpay(options);
      rzp.on("payment.failed", (r: any) => {
        setPayError(r.error?.description || "Payment fail hua. Dobara try karo.");
        setPayLoading(null);
      });
      rzp.open();

    } catch (err: any) {
      setPayError(err.message || "Kuch galat hua.");
      setPayLoading(null);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50/50">
      <div className="max-w-2xl mx-auto px-4 py-6 lg:py-10 space-y-5">

        {/* Header */}
        <div className="mb-2">
          <h1 className="text-2xl font-bold text-gray-900 tracking-tight">Settings</h1>
          <p className="text-gray-400 mt-1 text-sm">Manage your account, preferences, and billing</p>
        </div>

        {/* Success banner */}
        {successPlan && (
          <div className="flex items-center gap-3 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-2xl px-5 py-4 animate-slide-up">
            <CheckCircle2 size={20} className="text-emerald-500 shrink-0" />
            <div>
              <p className="font-semibold text-sm">Plan upgraded successfully!</p>
              <p className="text-xs text-emerald-600 mt-0.5">Welcome to <span className="font-bold capitalize">{successPlan}</span>. All features are now active.</p>
            </div>
          </div>
        )}

        {/* Profile */}
        <Section icon={User} iconBg="bg-blue-50" iconColor="text-blue-600" title="Profile" subtitle="Your account details">
          <div className="flex items-center gap-4">
            {user?.imageUrl ? (
              <img src={user.imageUrl} alt="avatar" className="w-14 h-14 rounded-2xl object-cover ring-2 ring-slate-100" />
            ) : (
              <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-blue-500 to-blue-700 flex items-center justify-center text-white text-xl font-bold ring-2 ring-blue-100">
                {user?.firstName?.charAt(0) ?? "U"}
              </div>
            )}
            <div>
              <p className="font-semibold text-gray-900">{user?.fullName ?? "User"}</p>
              <p className="text-sm text-gray-400">{user?.primaryEmailAddress?.emailAddress}</p>
              <span className="mt-1.5 inline-flex items-center gap-1 text-[11px] text-blue-500 bg-blue-50 px-2.5 py-1 rounded-full border border-blue-100">
                <Lock size={9} /> Managed via Clerk
              </span>
            </div>
          </div>
        </Section>

        {/* ── Billing ─────────────────────────────────────────── */}
        <section className="bg-white rounded-2xl border border-gray-200 overflow-hidden shadow-sm">
          <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 bg-purple-50 rounded-lg flex items-center justify-center">
                <CreditCard size={15} className="text-purple-600" />
              </div>
              <div>
                <h2 className="font-semibold text-gray-900 text-sm">Billing & Plans</h2>
                <p className="text-[11px] text-gray-400 mt-0.5">
                  Current plan:{" "}
                  <span className={`font-bold capitalize ${currentPlan === "free" ? "text-gray-600" : currentPlan === "pro" ? "text-blue-600" : "text-violet-600"}`}>
                    {currentPlan}
                  </span>
                </p>
              </div>
            </div>
            <span className="text-[10px] text-gray-400 bg-gray-50 border border-gray-100 px-2.5 py-1 rounded-full">
              🔒 Razorpay secured
            </span>
          </div>

          <div className="p-5 space-y-3">

            {/* Error */}
            {payError && (
              <div className="flex items-start gap-2.5 bg-red-50 border border-red-200 text-red-700 text-xs rounded-xl px-4 py-3">
                <AlertCircle size={14} className="shrink-0 mt-0.5" />
                <span className="flex-1">{payError}</span>
                <button onClick={() => setPayError(null)} className="shrink-0 opacity-50 hover:opacity-100"><X size={13} /></button>
              </div>
            )}

            {/* Plan Cards */}
            <div className="grid grid-cols-1 gap-3">
              {PLANS.map(plan => {
                const theme     = PLAN_THEME[plan.color];
                const isActive  = currentPlan === plan.id;
                const isLoading = payLoading === plan.id;
                const isFree    = plan.price === 0;

                return (
                  <div key={plan.id} className={`relative rounded-xl border-2 overflow-hidden transition-all ${theme.card} ${isActive && !plan.color.includes("blue") && !plan.color.includes("violet") ? "border-emerald-400" : ""}`}>

                    {/* Plan header */}
                    <div className={`px-4 py-3 flex items-center justify-between ${
                      plan.color === "gray"
                        ? "bg-slate-50"
                        : theme.header
                    }`}>
                      <div className="flex items-center gap-2.5">
                        {plan.color !== "gray" && (
                          <div className="w-7 h-7 bg-white/20 rounded-lg flex items-center justify-center">
                            {plan.color === "blue" ? <Zap size={14} className="text-white" /> : <Sparkles size={14} className="text-white" />}
                          </div>
                        )}
                        <div>
                          <p className={`font-bold text-sm ${plan.color === "gray" ? "text-slate-700" : "text-white"}`}>{plan.name}</p>
                          <p className={`text-[10px] ${plan.color === "gray" ? "text-slate-400" : "text-white/70"}`}>{plan.tagline}</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        {plan.badge && (
                          <span className={`text-[10px] font-bold px-2.5 py-1 rounded-full flex items-center gap-1 ${theme.badge}`}>
                            {plan.color === "blue" && <Star size={8} fill="currentColor" />}
                            {plan.badge}
                          </span>
                        )}
                        <div className="text-right">
                          <p className={`text-lg font-black ${plan.color === "gray" ? "text-slate-800" : "text-white"}`}>
                            {isFree ? "Free" : `₹${plan.price.toLocaleString("en-IN")}`}
                          </p>
                          <p className={`text-[10px] ${plan.color === "gray" ? "text-slate-400" : "text-white/60"}`}>{plan.period}</p>
                        </div>
                      </div>
                    </div>

                    {/* Features + CTA */}
                    <div className="px-4 py-3 flex items-end justify-between gap-4 bg-white">
                      <div className="flex-1 space-y-1.5">
                        {plan.features.slice(0, 4).map((f, i) => (
                          <div key={i} className="flex items-center gap-1.5">
                            <Check size={11} className={theme.check} />
                            <span className="text-[11px] text-gray-600">{f}</span>
                          </div>
                        ))}
                        {plan.features.length > 4 && (
                          <p className="text-[10px] text-gray-400 pl-4">+{plan.features.length - 4} more features</p>
                        )}
                        {plan.locked.slice(0, 2).map((f, i) => (
                          <div key={i} className="flex items-center gap-1.5 opacity-35">
                            <X size={10} className="text-gray-400 shrink-0" />
                            <span className="text-[11px] text-gray-400 line-through">{f}</span>
                          </div>
                        ))}
                      </div>

                      <div className="shrink-0">
                        {isActive ? (
                          <div className="flex items-center gap-1.5 bg-emerald-50 text-emerald-700 border border-emerald-200 px-3 py-2 rounded-xl">
                            <CheckCircle2 size={13} />
                            <span className="text-[11px] font-bold">Active</span>
                          </div>
                        ) : isFree ? (
                          <button disabled className="px-3 py-2 text-[11px] text-gray-300 bg-gray-50 border border-gray-100 rounded-xl cursor-not-allowed">
                            Downgrade
                          </button>
                        ) : (
                          <button
                            onClick={() => handleUpgrade(plan)}
                            disabled={!!payLoading}
                            className={`flex items-center gap-1.5 px-4 py-2 rounded-xl text-[11px] font-bold transition-all active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed ${theme.btn}`}
                          >
                            {isLoading ? (
                              <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                            ) : (
                              <><Zap size={11} /> Upgrade <ArrowRight size={10} /></>
                            )}
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Trust row */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1">
              {[
                { icon: "🔒", text: "256-bit SSL" },
                { icon: "↩️", text: "Cancel anytime" },
                { icon: "🧾", text: "GST invoice" },
                { icon: "💬", text: "WhatsApp support" },
              ].map((t, i) => (
                <div key={i} className="flex items-center gap-1.5 bg-gray-50 border border-gray-100 rounded-xl px-2.5 py-2">
                  <span className="text-sm">{t.icon}</span>
                  <span className="text-[10px] text-gray-500 font-medium">{t.text}</span>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Language */}
        <Section icon={Globe} iconBg="bg-green-50" iconColor="text-green-600" title="Report Language" subtitle="Language for generated audit reports">
          <div className="grid grid-cols-3 gap-2">
            {LANGUAGES.map(l => (
              <button key={l.value} onClick={() => setLanguage(l.value)}
                className={`flex flex-col items-center gap-1.5 p-3 rounded-xl border-2 text-center transition-all active:scale-95 ${
                  language === l.value ? "border-blue-500 bg-blue-50" : "border-gray-200 hover:border-gray-300 bg-white"
                }`}>
                <span className="text-xl">{l.flag}</span>
                <span className={`font-semibold text-xs ${language === l.value ? "text-blue-700" : "text-gray-700"}`}>{l.label}</span>
                <span className="text-[10px] text-gray-400 leading-tight">{l.desc}</span>
                {language === l.value && <CheckCircle2 size={11} className="text-blue-500" />}
              </button>
            ))}
          </div>
        </Section>

        {/* Notifications */}
        <Section icon={Bell} iconBg="bg-amber-50" iconColor="text-amber-600" title="Notifications">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium text-gray-900 text-sm">Email Alerts</p>
              <p className="text-xs text-gray-400 mt-0.5">Notify when HIGH risk issues detected</p>
            </div>
            <button onClick={() => setEmailAlerts(!emailAlerts)}
              className={`relative w-11 h-6 rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-300 ${emailAlerts ? "bg-blue-500" : "bg-gray-200"}`}>
              <div className={`absolute top-0.5 w-5 h-5 bg-white rounded-full shadow-sm transition-transform ${emailAlerts ? "translate-x-5" : "translate-x-0.5"}`} />
            </button>
          </div>
        </Section>

        {/* Security */}
        <Section icon={Shield} iconBg="bg-red-50" iconColor="text-red-500" title="Security">
          <div className="divide-y divide-gray-100">
            {[
              { icon: Lock,   label: "GSTIN Encryption", detail: "AES-256 encryption at rest",  badge: "Active",    color: "bg-emerald-100 text-emerald-700" },
              { icon: Shield, label: "Data Isolation",   detail: "Row-level security per user", badge: "Active",    color: "bg-emerald-100 text-emerald-700" },
              { icon: Server, label: "Storage Region",   detail: "Asia Pacific (Singapore)",    badge: "IN Region", color: "bg-blue-100 text-blue-700"       },
            ].map(row => (
              <div key={row.label} className="flex items-center justify-between py-3">
                <div className="flex items-center gap-2.5">
                  <row.icon size={13} className="text-gray-400 shrink-0" />
                  <div>
                    <p className="font-medium text-gray-900 text-sm">{row.label}</p>
                    <p className="text-xs text-gray-400 mt-0.5">{row.detail}</p>
                  </div>
                </div>
                <span className={`px-2.5 py-1 text-[11px] font-semibold rounded-full shrink-0 ${row.color}`}>{row.badge}</span>
              </div>
            ))}
          </div>
        </Section>

        {/* Save */}
        <button onClick={handleSave}
          className="w-full bg-blue-600 text-white font-semibold py-3.5 rounded-2xl hover:bg-blue-700 active:scale-[0.98] transition-all flex items-center justify-center gap-2 shadow-lg shadow-blue-600/20">
          {saved ? <><CheckCircle2 size={16} /> Preferences Saved!</> : "Save Preferences"}
        </button>

      </div>
    </div>
  );
}
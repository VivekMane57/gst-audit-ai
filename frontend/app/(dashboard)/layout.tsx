"use client";
import { UserButton } from "@clerk/nextjs";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import {
  LayoutDashboard, Users, Upload,
  FileText, Settings, Menu, X, Shield, Hash, GitMerge,
} from "lucide-react";

const NAV = [
  { href: "/dashboard",       label: "Dashboard",       icon: LayoutDashboard },
  { href: "/clients",         label: "Clients",         icon: Users },
  { href: "/upload",          label: "New Audit",       icon: Upload },
  { href: "/reports",         label: "Reports",         icon: FileText },
  { href: "/reconciliation",  label: "Reconciliation",  icon: GitMerge },  // ← Added
  { href: "/suppliers",       label: "Suppliers",       icon: Shield },
  { href: "/hsn",             label: "HSN Rates",       icon: Hash },
  { href: "/settings",        label: "Settings",        icon: Settings },
];

const BOTTOM_NAV = [
  { href: "/dashboard",      label: "Home",       icon: LayoutDashboard },
  { href: "/upload",         label: "Audit",      icon: Upload },
  { href: "/reconciliation", label: "Recon",      icon: GitMerge },       // ← Added
  { href: "/suppliers",      label: "Suppliers",  icon: Shield },
  { href: "/reports",        label: "Reports",    icon: FileText },
];

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const path = usePathname();
  const [open, setOpen] = useState(false);

  return (
    <div className="flex h-[100dvh] bg-gray-50">
      {open && <div className="fixed inset-0 bg-black/50 z-30 lg:hidden backdrop-blur-sm" onClick={() => setOpen(false)} />}

      <aside className={`fixed lg:static inset-y-0 left-0 z-40 w-64 bg-white border-r border-gray-200 flex flex-col transform transition-transform duration-300 ease-in-out ${open ? "translate-x-0" : "-translate-x-full lg:translate-x-0"}`}>
        <div className="p-5 border-b border-gray-100">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <img src="/logo.png" alt="AuditAI" className="w-9 h-9 rounded-lg" />
              <div>
                <h1 className="font-bold text-gray-900 text-sm">AuditAI</h1>
                <p className="text-[11px] text-gray-400">Smart GST Compliance</p>
              </div>
            </div>
            <button onClick={() => setOpen(false)} className="lg:hidden p-1.5 rounded-lg hover:bg-gray-100 text-gray-400"><X size={18} /></button>
          </div>
        </div>

        <nav className="flex-1 p-3 space-y-0.5">
          {NAV.map(({ href, label, icon: Icon }) => {
            const active = path === href || path.startsWith(href + "/");
            return (
              <Link key={href} href={href} onClick={() => setOpen(false)}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${active ? "bg-blue-50 text-blue-700 border border-blue-100" : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"}`}
              ><Icon size={18} />{label}</Link>
            );
          })}
        </nav>

        <div className="p-4 border-t border-gray-100 flex items-center gap-3">
          <UserButton afterSignOutUrl="/login" />
          <span className="text-sm text-gray-600">Account</span>
        </div>
      </aside>

      <main className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <header className="lg:hidden sticky top-0 z-20 bg-white/95 backdrop-blur-md border-b border-gray-100 px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button onClick={() => setOpen(true)} className="p-2 -ml-2 rounded-xl hover:bg-gray-100 text-gray-700 active:scale-95 transition-transform"><Menu size={22} /></button>
            <div className="flex items-center gap-2">
              <img src="/logo.png" alt="AuditAI" className="w-7 h-7 rounded-md" />
              <span className="font-bold text-sm text-gray-900">AuditAI</span>
            </div>
          </div>
          <UserButton afterSignOutUrl="/login" />
        </header>

        <div className="flex-1 overflow-y-auto pb-20 lg:pb-0">{children}</div>

        <nav className="lg:hidden fixed bottom-0 left-0 right-0 z-20 bg-white/95 backdrop-blur-md border-t border-gray-200">
          <div className="flex items-center justify-around py-1.5">
            {BOTTOM_NAV.map(({ href, label, icon: Icon }) => {
              const active = path === href || path.startsWith(href + "/");
              return (
                <Link key={href} href={href}
                  className={`flex flex-col items-center gap-0.5 px-2 py-1.5 rounded-xl transition-all active:scale-95 ${active ? "text-blue-600" : "text-gray-400"}`}
                ><Icon size={20} strokeWidth={active ? 2.5 : 1.5} />
                  <span className={`text-[10px] font-medium ${active ? "font-bold" : ""}`}>{label}</span>
                </Link>
              );
            })}
          </div>
        </nav>
      </main>
    </div>
  );
}
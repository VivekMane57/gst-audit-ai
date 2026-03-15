"use client";
import { UserButton } from "@clerk/nextjs";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import {
  LayoutDashboard, Users, Upload,
  FileText, Settings, Menu, X,
} from "lucide-react";

const NAV = [
  { href: "/dashboard", label: "Dashboard",  icon: LayoutDashboard },
  { href: "/clients",   label: "Clients",    icon: Users },
  { href: "/upload",    label: "New Audit",  icon: Upload },
  { href: "/reports",   label: "Reports",    icon: FileText },
  { href: "/settings",  label: "Settings",   icon: Settings },
];

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const path = usePathname();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="flex h-screen bg-gray-50">

      {/* ── Mobile overlay backdrop ── */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/40 z-30 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* ── Sidebar ── */}
      <aside
        className={`
          fixed lg:static inset-y-0 left-0 z-40
          w-64 bg-white border-r border-gray-200 flex flex-col
          transform transition-transform duration-300 ease-in-out
          ${sidebarOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"}
        `}
      >
        {/* Logo + close button (mobile) */}
        <div className="p-6 border-b border-gray-100">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <img
                src="/logo.png"
                alt="AuditAI"
                className="w-9 h-9 rounded-lg"
              />
              <div>
                <h1 className="font-bold text-gray-900 text-sm">AuditAI</h1>
                <p className="text-xs text-gray-400">Smart GST Compliance</p>
              </div>
            </div>
            {/* Close button — only on mobile */}
            <button
              onClick={() => setSidebarOpen(false)}
              className="lg:hidden p-1 rounded-lg hover:bg-gray-100 text-gray-500"
            >
              <X size={20} />
            </button>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 p-4 space-y-1">
          {NAV.map(({ href, label, icon: Icon }) => {
            const active = path === href || path.startsWith(href + "/");
            return (
              <Link
                key={href}
                href={href}
                onClick={() => setSidebarOpen(false)}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${
                  active
                    ? "bg-blue-50 text-blue-700 border border-blue-100"
                    : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
                }`}
              >
                <Icon size={18} />
                {label}
              </Link>
            );
          })}
        </nav>

        {/* User */}
        <div className="p-4 border-t border-gray-100 flex items-center gap-3">
          <UserButton afterSignOutUrl="/login" />
          <span className="text-sm text-gray-600">Account</span>
        </div>
      </aside>

      {/* ── Main content ── */}
      <main className="flex-1 overflow-auto flex flex-col min-w-0">

        {/* Mobile top bar */}
        <div className="lg:hidden sticky top-0 z-20 bg-white border-b border-gray-200 px-4 py-3 flex items-center gap-3">
          <button
            onClick={() => setSidebarOpen(true)}
            className="p-2 rounded-lg hover:bg-gray-100 text-gray-700"
          >
            <Menu size={22} />
          </button>
          <img
            src="/logo.png"
            alt="AuditAI"
            className="w-7 h-7 rounded-md"
          />
          <span className="font-bold text-sm text-gray-900">AuditAI</span>
        </div>

        {/* Page content */}
        <div className="flex-1">
          {children}
        </div>
      </main>
    </div>
  );
}
"use client";
import { UserButton } from "@clerk/nextjs";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard, Users, Upload,
  FileText, Settings,
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

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <aside className="w-64 bg-white border-r border-gray-200 flex flex-col">
        {/* Logo */}
        <div className="p-6 border-b border-gray-100">
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
        </div>

        {/* Nav */}
        <nav className="flex-1 p-4 space-y-1">
          {NAV.map(({ href, label, icon: Icon }) => {
            const active = path === href || path.startsWith(href + "/");
            return (
              <Link
                key={href}
                href={href}
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

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        {children}
      </main>
    </div>
  );
}
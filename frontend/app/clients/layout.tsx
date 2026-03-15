"use client";
import { UserButton } from "@clerk/nextjs";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard, Users, Upload,
  FileText, Settings, Shield,
} from "lucide-react";

const NAV = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/clients",   label: "Clients",   icon: Users },
  { href: "/upload",    label: "New Audit", icon: Upload },
  { href: "/reports",   label: "Reports",   icon: FileText },
  { href: "/settings",  label: "Settings",  icon: Settings },
];

function Sidebar() {
  const path = usePathname();
  return (
    <aside className="w-64 bg-white border-r border-gray-200 flex flex-col h-screen fixed left-0 top-0">
      <div className="p-6 border-b border-gray-100">
        <div className="flex items-center gap-2">
          <Shield className="text-blue-600" size={22} />
          <div>
            <h1 className="font-bold text-gray-900 text-sm">GST Audit AI</h1>
            <p className="text-xs text-gray-400">Smart Compliance</p>
          </div>
        </div>
      </div>
      <nav className="flex-1 p-4 space-y-1">
        {NAV.map(({ href, label, icon: Icon }) => {
          const active = path === href || path.startsWith(href + "/");
          return (
            <Link
              key={href}
              href={href}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium ${
                active
                  ? "bg-blue-50 text-blue-700 border border-blue-100"
                  : "text-gray-600 hover:bg-gray-50"
              }`}
            >
              <Icon size={17} />
              {label}
            </Link>
          );
        })}
      </nav>
      <div className="p-4 border-t border-gray-100 flex items-center gap-3">
        <UserButton afterSignOutUrl="/login" />
        <span className="text-sm text-gray-500">Account</span>
      </div>
    </aside>
  );
}

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex">
      <Sidebar />
      <main className="ml-64 flex-1 min-h-screen bg-gray-50">
        {children}
      </main>
    </div>
  );
}
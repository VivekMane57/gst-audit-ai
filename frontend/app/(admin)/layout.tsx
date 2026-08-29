"use client";

import { usePathname } from "next/navigation";
import Link from "next/link";
import {
  LayoutDashboard,
  BookOpen,
  Scale,
  SlidersHorizontal,
  Wrench,
  Shield,
  ChevronRight,
} from "lucide-react";
import { UserButton } from "@clerk/nextjs";

const NAV = [
  { label: "Dashboard",  href: "/admin",           icon: LayoutDashboard },
  { label: "Rules",      href: "/admin/rules",      icon: BookOpen },
  { label: "Laws",       href: "/admin/laws",       icon: Scale },
  { label: "Thresholds", href: "/admin/thresholds", icon: SlidersHorizontal },
  { label: "Fix Steps",  href: "/admin/fix-steps",  icon: Wrench },
];

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="min-h-screen bg-[#0a0a0f] flex">
      {/* Sidebar */}
      <aside className="w-64 border-r border-white/[0.06] flex flex-col bg-[#0d0d14]">
        {/* Logo */}
        <div className="px-6 py-5 border-b border-white/[0.06]">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center">
              <Shield className="w-4 h-4 text-white" />
            </div>
            <div>
              <p className="text-white font-semibold text-sm tracking-tight">GST Audit AI</p>
              <p className="text-indigo-400 text-xs">Admin Panel</p>
            </div>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 py-4 space-y-0.5">
          {NAV.map(({ label, href, icon: Icon }) => {
            const active = pathname === href || (href !== "/admin" && pathname.startsWith(href));
            return (
              <Link
                key={href}
                href={href}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all group ${
                  active
                    ? "bg-indigo-600/20 text-indigo-300 font-medium"
                    : "text-gray-400 hover:text-white hover:bg-white/[0.04]"
                }`}
              >
                <Icon className={`w-4 h-4 ${active ? "text-indigo-400" : "text-gray-500 group-hover:text-gray-300"}`} />
                {label}
                {active && <ChevronRight className="w-3 h-3 ml-auto text-indigo-400" />}
              </Link>
            );
          })}
        </nav>

        {/* Bottom */}
        <div className="px-4 py-4 border-t border-white/[0.06]">
          <div className="flex items-center gap-3">
            <UserButton afterSignOutUrl="/login" />
            <div className="flex-1 min-w-0">
              <p className="text-white text-xs font-medium truncate">Admin</p>
              <p className="text-gray-500 text-xs">Super access</p>
            </div>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        {children}
      </main>
    </div>
  );
}
"use client";

/**
 * AnimatedSidebar.tsx
 * Responsive animated sidebar for AuditAI
 * Works with Next.js 14 App Router + Shadcn/UI + Framer Motion
 *
 * Usage:
 *   <AnimatedSidebar pathname={pathname} onNavigate={(href) => router.push(href)} />
 */

import { useState } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import { Separator } from "@/components/ui/separator";
import {
  LayoutDashboard, Users, Upload, FileBarChart2,
  GitMerge, Truck, Hash, Settings, ChevronLeft, ChevronRight,
  LogOut, Sparkles,
} from "lucide-react";

// ─── Nav config ───────────────────────────────────────────────────────────────

const NAV_ITEMS = [
  { label: "Dashboard",      href: "/dashboard",     icon: LayoutDashboard },
  { label: "Clients",        href: "/clients",        icon: Users           },
  { label: "New Audit",      href: "/upload",         icon: Upload          },
  { label: "Reports",        href: "/reports",        icon: FileBarChart2   },
  { label: "Reconciliation", href: "/reconciliation", icon: GitMerge        },
  { label: "Suppliers",      href: "/suppliers",      icon: Truck           },
  { label: "HSN Rates",      href: "/hsn-rates",      icon: Hash            },
] as const;

const BOTTOM_ITEMS = [
  { label: "Settings", href: "/settings", icon: Settings },
] as const;

// ─── Animation variants ───────────────────────────────────────────────────────

const sidebarVariants = {
  expanded: { width: 220, transition: { type: "spring", stiffness: 260, damping: 26 } },
  collapsed: { width: 64,  transition: { type: "spring", stiffness: 260, damping: 26 } },
};

const navListVariants = {
  hidden: {},
  show: {
    transition: {
      delayChildren: 0.15,
      staggerChildren: 0.055,
    },
  },
};

const navItemVariants = {
  hidden: { opacity: 0, x: -14 },
  show:   { opacity: 1, x: 0, transition: { type: "spring", stiffness: 320, damping: 26 } },
};

const labelVariants = {
  hidden:  { opacity: 0, x: -6, width: 0   },
  visible: { opacity: 1, x: 0,  width: "auto", transition: { duration: 0.18 } },
};

// ─── Nav Item ─────────────────────────────────────────────────────────────────

interface NavItemProps {
  href:      string;
  label:     string;
  icon:      React.ElementType;
  active:    boolean;
  collapsed: boolean;
  onClick?:  () => void;
}

function NavItem({ href, label, icon: Icon, active, collapsed, onClick }: NavItemProps) {
  return (
    <motion.div variants={navItemVariants}>
      <Link
        href={href}
        onClick={onClick}
        title={collapsed ? label : undefined}
        className={`
          relative flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-semibold
          transition-colors group
          ${active
            ? "bg-blue-600 text-white shadow-md shadow-blue-600/20"
            : "text-slate-500 hover:bg-slate-100 hover:text-slate-900"}
        `}
      >
        {/* Active pill indicator */}
        {active && (
          <motion.div
            layoutId="activeNav"
            className="absolute inset-0 bg-blue-600 rounded-xl -z-10"
            transition={{ type: "spring", stiffness: 380, damping: 30 }}
          />
        )}

        <Icon size={17} className="shrink-0" />

        <AnimatePresence>
          {!collapsed && (
            <motion.span
              variants={labelVariants}
              initial="hidden"
              animate="visible"
              exit="hidden"
              className="overflow-hidden whitespace-nowrap"
            >
              {label}
            </motion.span>
          )}
        </AnimatePresence>

        {/* Tooltip when collapsed */}
        {collapsed && (
          <div className="
            absolute left-full ml-2.5 px-2 py-1 bg-slate-900 text-white text-xs
            rounded-lg whitespace-nowrap opacity-0 pointer-events-none
            group-hover:opacity-100 transition-opacity z-50 shadow-xl
          ">
            {label}
            <div className="absolute right-full top-1/2 -translate-y-1/2 border-4 border-transparent border-r-slate-900" />
          </div>
        )}
      </Link>
    </motion.div>
  );
}

// ─── Sidebar ──────────────────────────────────────────────────────────────────

interface AnimatedSidebarProps {
  pathname?:   string;
  userName?:   string;
  userEmail?:  string;
  userAvatar?: string;
  onNavigate?: (href: string) => void;
  onSignOut?:  () => void;
}

export default function AnimatedSidebar({
  pathname = "/dashboard",
  userName = "CA User",
  userEmail,
  userAvatar,
  onSignOut,
}: AnimatedSidebarProps) {
  const [collapsed, setCollapsed] = useState(false);

  const initials = userName
    .split(" ").slice(0, 2).map(w => w[0]).join("").toUpperCase();

  return (
    <motion.aside
      variants={sidebarVariants}
      initial="expanded"
      animate={collapsed ? "collapsed" : "expanded"}
      className="
        relative flex flex-col h-screen bg-white border-r border-slate-200/80
        shadow-[2px_0_12px_rgba(0,0,0,0.04)] overflow-hidden
      "
    >
      {/* ── Logo ── */}
      <div className="flex items-center gap-3 px-4 py-5 shrink-0">
        <div className="w-9 h-9 bg-gradient-to-br from-blue-600 to-violet-600 rounded-xl flex items-center justify-center shrink-0 shadow-md shadow-blue-600/20">
          <Sparkles size={16} className="text-white" />
        </div>
        <AnimatePresence>
          {!collapsed && (
            <motion.div
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -8 }}
              transition={{ duration: 0.18 }}
              className="overflow-hidden"
            >
              <p className="text-sm font-black text-slate-900 leading-tight">AuditAI</p>
              <p className="text-[10px] text-slate-400 font-medium">Smart GST Compliance</p>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <Separator className="mx-3 w-auto" />

      {/* ── Nav Items ── */}
      <ScrollAreaCompat className="flex-1 py-3 px-2 overflow-y-auto">
        <motion.nav
          className="space-y-0.5"
          variants={navListVariants}
          initial="hidden"
          animate="show"
        >
          {NAV_ITEMS.map(item => (
            <NavItem
              key={item.href}
              href={item.href}
              label={item.label}
              icon={item.icon}
              active={pathname === item.href}
              collapsed={collapsed}
            />
          ))}
        </motion.nav>
      </ScrollAreaCompat>

      {/* ── Bottom section ── */}
      <div className="px-2 py-3 space-y-0.5 shrink-0">
        <Separator className="mb-3 mx-1 w-auto" />

        {BOTTOM_ITEMS.map(item => (
          <NavItem
            key={item.href}
            href={item.href}
            label={item.label}
            icon={item.icon}
            active={pathname === item.href}
            collapsed={collapsed}
          />
        ))}

        {/* Sign out */}
        <motion.button
          variants={navItemVariants}
          whileHover={{ x: 2 }}
          onClick={onSignOut}
          className="
            w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-semibold
            text-slate-400 hover:text-rose-500 hover:bg-rose-50 transition-colors
          "
          title={collapsed ? "Sign out" : undefined}
        >
          <LogOut size={17} className="shrink-0" />
          <AnimatePresence>
            {!collapsed && (
              <motion.span
                variants={labelVariants}
                initial="hidden"
                animate="visible"
                exit="hidden"
                className="overflow-hidden whitespace-nowrap"
              >
                Sign out
              </motion.span>
            )}
          </AnimatePresence>
        </motion.button>

        <Separator className="my-3 mx-1 w-auto" />

        {/* User chip */}
        <div className="flex items-center gap-2.5 px-2 py-1.5">
          {userAvatar ? (
            <img src={userAvatar} alt={userName}
              className="w-8 h-8 rounded-full object-cover shrink-0 ring-2 ring-blue-100" />
          ) : (
            <div className="w-8 h-8 bg-gradient-to-br from-blue-100 to-violet-100 text-blue-700 rounded-full flex items-center justify-center text-[10px] font-black shrink-0">
              {initials}
            </div>
          )}
          <AnimatePresence>
            {!collapsed && (
              <motion.div
                initial={{ opacity: 0, x: -6 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -6 }}
                transition={{ duration: 0.16 }}
                className="min-w-0 overflow-hidden"
              >
                <p className="text-xs font-bold text-slate-800 truncate leading-tight">{userName}</p>
                {userEmail && (
                  <p className="text-[10px] text-slate-400 truncate">{userEmail}</p>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* ── Collapse toggle ── */}
      <motion.button
        onClick={() => setCollapsed(v => !v)}
        whileHover={{ scale: 1.1 }}
        whileTap={{ scale: 0.92 }}
        className="
          absolute top-[72px] -right-3 z-50
          w-6 h-6 bg-white border border-slate-200 rounded-full shadow-md
          flex items-center justify-center text-slate-400 hover:text-slate-700
          hover:border-slate-300 transition-colors
        "
      >
        {collapsed
          ? <ChevronRight size={12} />
          : <ChevronLeft  size={12} />}
      </motion.button>
    </motion.aside>
  );
}

// ─── Tiny scroll-area compat (avoids import if Shadcn not installed) ──────────

function ScrollAreaCompat({ children, className }: { children: React.ReactNode; className?: string }) {
  return <div className={className}>{children}</div>;
}
"use client";

/**
 * animated-ui.tsx
 * Reusable animated UI primitives for AuditAI
 *
 * Exports:
 *  - AnimatedStatCard      — count-up metric card
 *  - RadialScore           — animated SVG compliance score ring
 *  - ShimmerCard           — skeleton shimmer placeholder
 *  - SkeletonRow           — list-item skeleton
 *  - ShimmerStyles         — <style> tag for shimmer keyframe (inject in layout)
 *  - FadeInList            — staggered fade-in list wrapper
 *  - SlideInItem           — individual list item with whileHover slide
 *  - AnimatedBadge         — pill badge with entry animation
 *  - AnimatedProgressBar   — horizontal bar animated from 0
 *  - PageTransition        — page-level fade-up wrapper
 */

import { useEffect, useState, ReactNode } from "react";
import { motion, useSpring, useTransform, animate, AnimatePresence } from "framer-motion";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface StatCardProps {
  label:       string;
  value:       string | number;
  icon:        React.ElementType;
  iconBg:      string;
  iconColor:   string;
  valueColor?: string;
  sub?:        string;
  loading?:    boolean;
}

// ─── Shared spring presets ────────────────────────────────────────────────────

export const SPRING_SNAPPY = { type: "spring", stiffness: 380, damping: 28 } as const;
export const SPRING_SOFT   = { type: "spring", stiffness: 200, damping: 22 } as const;

// ─── Count-up hook ────────────────────────────────────────────────────────────

export function useCountUp(target: number, duration = 1.2, decimals = 0) {
  const [value, setValue] = useState(0);
  useEffect(() => {
    const controls = animate(0, target, {
      duration,
      ease: "easeOut",
      onUpdate: (v) => setValue(parseFloat(v.toFixed(decimals))),
    });
    return controls.stop;
  }, [target, duration, decimals]);
  return value;
}

// ─── Radial Score ─────────────────────────────────────────────────────────────

/**
 * Animated SVG compliance score ring.
 * Animates both the arc and the number from 0 → score on mount.
 */
export function RadialScore({
  score,
  size = 96,
  strokeWidth = 6,
}: {
  score: number;
  size?: number;
  strokeWidth?: number;
}) {
  const radius  = (size - strokeWidth * 2) / 2;
  const circ    = 2 * Math.PI * radius;
  const spring  = useSpring(0, { stiffness: 70, damping: 16 });
  const dashOffset = useTransform(spring, [0, 100], [circ, 0]);

  useEffect(() => { spring.set(score); }, [score, spring]);

  const displayed = useCountUp(score, 1.1);
  const color = score >= 80 ? "#10b981" : score >= 60 ? "#f59e0b" : "#f43f5e";

  return (
    <div className="relative flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2} cy={size / 2} r={radius}
          fill="none" stroke="#e2e8f0" strokeWidth={strokeWidth}
        />
        <motion.circle
          cx={size / 2} cy={size / 2} r={radius}
          fill="none" stroke={color} strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circ}
          style={{ strokeDashoffset: dashOffset }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-xl font-black leading-none" style={{ color }}>
          {displayed}
        </span>
        <span className="text-[9px] text-slate-400 font-semibold mt-0.5 tracking-wider uppercase">
          Score
        </span>
      </div>
    </div>
  );
}

// ─── Animated Stat Card ───────────────────────────────────────────────────────

/**
 * Shadcn Card wrapper with lift-on-hover and skeleton loading state.
 * Pass loading=true while data is fetching.
 */
export function AnimatedStatCard({
  label, value, icon: Icon, iconBg, iconColor,
  valueColor = "text-slate-900", sub, loading,
}: StatCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={SPRING_SOFT}
      whileHover={{ y: -3, boxShadow: "0 10px 32px rgba(0,0,0,0.07)" }}
    >
      <Card className="border border-slate-200/70 bg-white shadow-sm rounded-2xl overflow-hidden h-full">
        <CardContent className="p-4">
          <div className="flex items-center justify-between mb-3">
            <p className="text-[11px] text-slate-500 font-bold uppercase tracking-wide">{label}</p>
            <div className={`w-8 h-8 ${iconBg} rounded-xl flex items-center justify-center`}>
              <Icon size={14} className={iconColor} />
            </div>
          </div>
          {loading
            ? <Skeleton className="h-7 w-20 rounded-lg mb-1" />
            : <p className={`text-2xl font-black tracking-tight ${valueColor}`}>{value}</p>
          }
          {sub && <p className="text-[11px] text-slate-400 mt-1 font-medium">{sub}</p>}
        </CardContent>
      </Card>
    </motion.div>
  );
}

// ─── Shimmer Skeleton ─────────────────────────────────────────────────────────

/**
 * Pulse shimmer placeholder. Inject <ShimmerStyles /> once in your layout.
 */
export function ShimmerCard({ className = "" }: { className?: string }) {
  return (
    <div
      className={`rounded-2xl overflow-hidden ${className}`}
      style={{
        background: "linear-gradient(90deg, #f1f5f9 25%, #e2e8f0 50%, #f1f5f9 75%)",
        backgroundSize: "200% 100%",
        animation: "shimmer 1.5s infinite linear",
      }}
    />
  );
}

export function ShimmerStyles() {
  return (
    <style>{`
      @keyframes shimmer {
        0%   { background-position: 200% 0; }
        100% { background-position: -200% 0; }
      }
    `}</style>
  );
}

// ─── Skeleton Row ─────────────────────────────────────────────────────────────

/** Placeholder row for list items while loading. */
export function SkeletonRow() {
  return (
    <div className="flex items-center gap-3 px-3 py-3">
      <Skeleton className="w-10 h-10 rounded-xl shrink-0" />
      <div className="flex-1 space-y-1.5">
        <Skeleton className="h-3.5 w-3/4 rounded" />
        <Skeleton className="h-2.5 w-1/2 rounded" />
      </div>
      <Skeleton className="h-5 w-16 rounded-full" />
    </div>
  );
}

// ─── Fade-in staggered list ───────────────────────────────────────────────────

/**
 * Wrapper that staggers children with fade+slide.
 *
 * Usage:
 *   <FadeInList>
 *     {items.map(i => <SlideInItem key={i.id}>{…}</SlideInItem>)}
 *   </FadeInList>
 */
export function FadeInList({
  children,
  delayChildren = 0,
  staggerChildren = 0.07,
  className = "",
}: {
  children: ReactNode;
  delayChildren?: number;
  staggerChildren?: number;
  className?: string;
}) {
  return (
    <motion.div
      className={className}
      initial="hidden"
      animate="show"
      variants={{
        hidden: {},
        show:   { transition: { delayChildren, staggerChildren } },
      }}
    >
      {children}
    </motion.div>
  );
}

/**
 * Individual item inside <FadeInList>.
 * Fades + slides in. On hover slides right by `hoverX` px.
 */
export function SlideInItem({
  children,
  hoverX = 6,
  className = "",
  onClick,
}: {
  children: ReactNode;
  hoverX?: number;
  className?: string;
  onClick?: () => void;
}) {
  return (
    <motion.div
      variants={{
        hidden: { opacity: 0, y: 10 },
        show:   { opacity: 1, y: 0, transition: { type: "spring", stiffness: 300, damping: 26 } },
      }}
      whileHover={{ x: hoverX, transition: { type: "spring", stiffness: 400, damping: 24 } }}
      className={className}
      onClick={onClick}
    >
      {children}
    </motion.div>
  );
}

// ─── Animated Badge ───────────────────────────────────────────────────────────

/**
 * Badge with scale+fade entry animation.
 */
export function AnimatedBadge({
  children,
  className = "",
  delay = 0,
}: {
  children: ReactNode;
  className?: string;
  delay?: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.75 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ delay, type: "spring", stiffness: 400, damping: 24 }}
    >
      <Badge variant="outline" className={className}>
        {children}
      </Badge>
    </motion.div>
  );
}

// ─── Animated Progress Bar ────────────────────────────────────────────────────

/**
 * Horizontal progress bar that animates from 0 → value on mount.
 *
 * @param value    0–100
 * @param color    CSS color string
 * @param delay    Framer Motion delay (seconds)
 */
export function AnimatedProgressBar({
  value,
  color = "#3b82f6",
  delay = 0,
  height = "h-1.5",
  className = "",
}: {
  value:     number;
  color?:    string;
  delay?:    number;
  height?:   string;
  className?: string;
}) {
  return (
    <div className={`w-full bg-slate-100 rounded-full overflow-hidden ${height} ${className}`}>
      <motion.div
        className="h-full rounded-full"
        style={{ background: color }}
        initial={{ width: 0 }}
        animate={{ width: `${Math.min(100, Math.max(0, value))}%` }}
        transition={{ delay, duration: 0.55, ease: "easeOut" }}
      />
    </div>
  );
}

// ─── Page Transition ──────────────────────────────────────────────────────────

/**
 * Wrap page content to get a smooth fade+up entry.
 *
 * Usage in layout / page:
 *   <PageTransition>
 *     <YourPageContent />
 *   </PageTransition>
 */
export function PageTransition({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <motion.div
      className={className}
      initial={{ opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      transition={{ type: "spring", stiffness: 260, damping: 26 }}
    >
      {children}
    </motion.div>
  );
}
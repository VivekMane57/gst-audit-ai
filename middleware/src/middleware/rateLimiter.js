// const rateLimit = require("express-rate-limit");

// // Global — sab routes pe
// const globalLimiter = rateLimit({
//   windowMs: 15 * 60 * 1000,   // 15 min
//   max: 100,
//   message: { error: "Bahut zyada requests. 15 minute baad try karo." },
//   standardHeaders: true,
//   legacyHeaders: false,
// });

// // Upload route — 10 per minute
// const uploadLimiter = rateLimit({
//   windowMs: 60 * 1000,
//   max: 10,
//   message: { error: "Upload limit: 10 per minute." },
// });

// // Audit route — 20 per hour
// const auditLimiter = rateLimit({
//   windowMs: 60 * 60 * 1000,
//   max: 20,
//   message: { error: "Audit limit: 20 per hour. Pro plan mein upgrade karo." },
// });

// module.exports = { globalLimiter, uploadLimiter, auditLimiter };

/**
 * middleware/src/middleware/rateLimiter.js
 * 
 * Layer  : Infrastructure
 * Role   : SIRF request throttling — kuch aur nahi
 * Scale  : ENV variables se 10,000 users tak adjust karo
 */

const rateLimit = require("express-rate-limit");

// ── ENV-driven config (production mein .env change karo, code nahi) ──────────
const GLOBAL_MAX  = parseInt(process.env.RATE_GLOBAL_MAX)  || 500;  // 500 req/15min
const AUDIT_MAX   = parseInt(process.env.RATE_AUDIT_MAX)   || 50;   // 50  req/hour
const UPLOAD_MAX  = parseInt(process.env.RATE_UPLOAD_MAX)  || 30;   // 30  req/min

// ── IP extractor — Vercel/Railway/Nginx proxy ke peeche bhi kaam karta hai ───
const keyGenerator = (req) =>
  req.headers["x-forwarded-for"]?.split(",")[0]?.trim() ||
  req.ip ||
  "unknown";

// ── Global limiter — har route pe lagta hai ───────────────────────────────────
const globalLimiter = rateLimit({
  windowMs:        15 * 60 * 1000,   // 15 minutes
  max:             GLOBAL_MAX,
  standardHeaders: true,
  legacyHeaders:   false,
  keyGenerator,
  message: { error: "Bahut zyada requests. 15 minute baad try karo." },
});

// ── Audit limiter — heavy processing route ke liye ────────────────────────────
const auditLimiter = rateLimit({
  windowMs:        60 * 60 * 1000,   // 1 hour
  max:             AUDIT_MAX,
  standardHeaders: true,
  legacyHeaders:   false,
  keyGenerator,
  message: { error: "Audit limit: 50 per hour." },
});

// ── Upload limiter — file upload burst rokne ke liye ─────────────────────────
const uploadLimiter = rateLimit({
  windowMs:        60 * 1000,         // 1 minute
  max:             UPLOAD_MAX,
  standardHeaders: true,
  legacyHeaders:   false,
  keyGenerator,
  message: { error: "Upload limit: 30 per minute." },
});

module.exports = { globalLimiter, auditLimiter, uploadLimiter };
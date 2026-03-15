const rateLimit = require("express-rate-limit");

// Global — sab routes pe
const globalLimiter = rateLimit({
  windowMs: 15 * 60 * 1000,   // 15 min
  max: 100,
  message: { error: "Bahut zyada requests. 15 minute baad try karo." },
  standardHeaders: true,
  legacyHeaders: false,
});

// Upload route — 10 per minute
const uploadLimiter = rateLimit({
  windowMs: 60 * 1000,
  max: 10,
  message: { error: "Upload limit: 10 per minute." },
});

// Audit route — 20 per hour
const auditLimiter = rateLimit({
  windowMs: 60 * 60 * 1000,
  max: 20,
  message: { error: "Audit limit: 20 per hour. Pro plan mein upgrade karo." },
});

module.exports = { globalLimiter, uploadLimiter, auditLimiter };
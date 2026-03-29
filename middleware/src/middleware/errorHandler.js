// const { isDev } = require("../config");

// // Global error handler — sab unhandled errors yahan aate hain
// const errorHandler = (err, req, res, next) => {
//   console.error(`[ERROR] ${req.method} ${req.path}:`, err.message);

//   const status = err.status || err.statusCode || 500;
//   const message = err.message || "Kuch problem aa gayi. Please retry.";

//   res.status(status).json({
//     error: message,
//     ...(isDev && { stack: err.stack }),  // Dev mein stack dikhao
//   });
// };

// // 404 handler
// const notFound = (req, res) => {
//   res.status(404).json({ error: `Route not found: ${req.method} ${req.path}` });
// };

// module.exports = { errorHandler, notFound };

/**
 * middleware/src/middleware/errorHandler.js
 *
 * Layer  : Infrastructure
 * Role   : SIRF error handling — kuch aur nahi
 */

const isDev = process.env.NODE_ENV !== "production";

// ── Global error handler — sab unhandled errors yahan aate hain ──────────────
const errorHandler = (err, req, res, _next) => {
  console.error(`[ERROR] ${req.method} ${req.path}:`, err.message);

  // Multer file size error
  if (err.code === "LIMIT_FILE_SIZE") {
    return res.status(413).json({ error: "File 20MB se badi hai. Chhoti file upload karo." });
  }

  const status  = err.status || err.statusCode || 500;
  const message = err.message || "Kuch problem aa gayi. Please retry.";

  res.status(status).json({
    error: message,
    ...(isDev && { stack: err.stack }),
  });
};

// ── 404 handler ───────────────────────────────────────────────────────────────
const notFound = (req, res) => {
  res.status(404).json({ error: `Route not found: ${req.method} ${req.path}` });
};

module.exports = { errorHandler, notFound };
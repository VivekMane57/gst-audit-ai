const { isDev } = require("../config");

// Global error handler — sab unhandled errors yahan aate hain
const errorHandler = (err, req, res, next) => {
  console.error(`[ERROR] ${req.method} ${req.path}:`, err.message);

  const status = err.status || err.statusCode || 500;
  const message = err.message || "Kuch problem aa gayi. Please retry.";

  res.status(status).json({
    error: message,
    ...(isDev && { stack: err.stack }),  // Dev mein stack dikhao
  });
};

// 404 handler
const notFound = (req, res) => {
  res.status(404).json({ error: `Route not found: ${req.method} ${req.path}` });
};

module.exports = { errorHandler, notFound };
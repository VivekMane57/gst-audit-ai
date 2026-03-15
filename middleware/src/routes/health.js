const router = require("express").Router();
const axios = require("axios");
const { pythonUrl } = require("../config");

router.get("/health", async (req, res) => {
  let pythonStatus = "unknown";
  try {
    await axios.get(`${pythonUrl}/health`, { timeout: 3000 });
    pythonStatus = "connected";
  } catch {
    pythonStatus = "error";
  }

  res.json({
    status: pythonStatus === "connected" ? "healthy" : "degraded",
    service: "GST Audit AI — Middleware",
    version: "1.0.0",
    python_backend: pythonStatus,
    timestamp: new Date().toISOString(),
  });
});

module.exports = router;
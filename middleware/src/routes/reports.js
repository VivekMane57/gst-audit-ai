const router = require("express").Router();
const axios = require("axios");
const { pythonUrl } = require("../config");

// GET /api/reports
router.get("/", async (req, res, next) => {
  try {
    // FIX: backend expects x-user-id, not x-clerk-id
    const userId = req.headers["x-user-id"] || req.headers["x-clerk-id"] || "dev-user";

    const response = await axios.get(`${pythonUrl}/reports`, {
      headers: { "x-user-id": userId },   // ← FIX: was x-clerk-id
      timeout: 10000,
    });
    res.json(response.data);
  } catch (err) {
    if (err.response) return res.status(err.response.status).json(err.response.data);
    next(err);
  }
});

// GET /api/reports/:id/pdf — PDF download proxy
router.get("/:id/pdf", async (req, res, next) => {
  try {
    const userId = req.headers["x-user-id"] || req.headers["x-clerk-id"] || "dev-user";
    const { lang = "en", ca_name = "CA", client_name = "Client" } = req.query;

    const response = await axios.get(
      `${pythonUrl}/reports/${req.params.id}/pdf`,
      {
        headers: { "x-user-id": userId },  // ← FIX: was x-clerk-id
        params: { lang, ca_name, client_name },
        responseType: "stream",
        timeout: 15000,
      }
    );

    res.setHeader("Content-Type", "application/pdf");
    res.setHeader(
      "Content-Disposition",
      response.headers["content-disposition"] || `attachment; filename=audit_report.pdf`
    );

    response.data.pipe(res);
  } catch (err) {
    if (err.response) return res.status(err.response.status).json({ error: "PDF generate nahi hua" });
    next(err);
  }
});

// GET /api/reports/:id — Single report
router.get("/:id", async (req, res, next) => {
  try {
    const userId = req.headers["x-user-id"] || req.headers["x-clerk-id"] || "dev-user";

    const response = await axios.get(`${pythonUrl}/reports/${req.params.id}`, {
      headers: { "x-user-id": userId },
      timeout: 10000,
    });
    res.json(response.data);
  } catch (err) {
    if (err.response) return res.status(err.response.status).json(err.response.data);
    next(err);
  }
});

module.exports = router;
const router = require("express").Router();
const axios = require("axios");
const { pythonUrl } = require("../config");

// Helper — Python pe request forward karo
const forward = (method, path) => async (req, res, next) => {
  try {
    // FIX: backend expects x-user-id, not x-clerk-id
    const userId = req.headers["x-user-id"] || req.headers["x-clerk-id"] || "dev-user";

    const response = await axios({
      method,
      url: `${pythonUrl}${path(req)}`,
      headers: { "x-user-id": userId },   // ← FIX: was x-clerk-id
      data: method !== "get" && method !== "delete" ? req.body : undefined,
      timeout: 10000,
    });

    res.json(response.data);
  } catch (err) {
    if (err.response) {
      return res.status(err.response.status).json(err.response.data);
    }
    next(err);
  }
};

// GET /api/clients
router.get("/",       forward("get",    () => "/clients"));

// POST /api/clients
router.post("/",      forward("post",   () => "/clients"));

// GET /api/clients/:id
router.get("/:id",    forward("get",    (r) => `/clients/${r.params.id}`));

// DELETE /api/clients/:id
router.delete("/:id", forward("delete", (r) => `/clients/${r.params.id}`));

module.exports = router;
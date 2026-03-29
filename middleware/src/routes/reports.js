const router = require("express").Router();
const axios  = require("axios");
const { pythonUrl } = require("../config");

const forward = (method, path) => async (req, res, next) => {
  try {
    const userId = req.headers["x-user-id"] || req.headers["x-clerk-id"] || "dev-user";

    const response = await axios({
      method,
      url:     `${pythonUrl}${path(req)}`,
      headers: {
        "x-user-id":    userId,
        "Content-Type": "application/json",
      },
      data: ["post", "put", "patch"].includes(method) ? req.body : undefined,
      timeout: 15000,
    });

    res.json(response.data);
  } catch (err) {
    if (err.response) {
      return res.status(err.response.status).json(err.response.data);
    }
    next(err);
  }
};

// GET /api/reports/suppliers — MUST be before /:id to avoid conflict
router.get("/suppliers", forward("get", () => "/reports/suppliers"));

// GET /api/reports
router.get("/",          forward("get",  () => "/reports"));

// GET /api/reports/:id
router.get("/:id",       forward("get",  (r) => `/reports/${r.params.id}`));

// GET /api/reports/:id/pdf
router.get("/:id/pdf",   forward("get",  (r) => `/reports/${r.params.id}/pdf`));

module.exports = router;
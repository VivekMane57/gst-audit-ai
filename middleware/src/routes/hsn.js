const router = require("express").Router();
const axios  = require("axios");
const { pythonUrl } = require("../config");

const forward = (method, path) => async (req, res, next) => {
  try {
    const userId = req.headers["x-user-id"] || req.headers["x-clerk-id"] || "dev-user";
    const response = await axios({
      method,
      url:     `${pythonUrl}${path(req)}`,
      headers: { "x-user-id": userId, "Content-Type": "application/json" },
      data: ["post", "put"].includes(method) ? req.body : undefined,
      params: method === "get" ? req.query : undefined,
      timeout: 10000,
    });
    res.json(response.data);
  } catch (err) {
    if (err.response) return res.status(err.response.status).json(err.response.data);
    next(err);
  }
};

// GET /api/hsn/search?q=laptop
router.get("/search",       forward("get",  () => "/hsn/search"));

// GET /api/hsn/lookup/:code
router.get("/lookup/:code",  forward("get",  (r) => `/hsn/lookup/${r.params.code}`));

// POST /api/hsn/validate
router.post("/validate",     forward("post", () => "/hsn/validate"));

module.exports = router;
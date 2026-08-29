/**
 * routes/noticeQueue.js
 * ---------------------
 * Proxy routes for Notice Risk Queue API.
 * Forwards to Python FastAPI /api/notice-queue endpoints.
 */
const router = require("express").Router();
const axios  = require("axios");
const { pythonUrl } = require("../config");

const forward = (method, pathFn) => async (req, res, next) => {
  try {
    const userId    = req.headers["x-user-id"]    || req.headers["x-clerk-id"] || "dev-user";
    const userEmail = req.headers["x-user-email"] || "";
    const userName  = req.headers["x-user-name"]  || "";

    const response = await axios({
      method,
      url: `${pythonUrl}${pathFn(req)}`,
      headers: {
        "x-user-id":    userId,
        "x-user-email": userEmail,
        "x-user-name":  userName,
        "Content-Type": "application/json",
      },
      params: method === "get" ? req.query : undefined,
      data:   ["post", "put", "patch"].includes(method) ? req.body : undefined,
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

// GET /api/notice-queue/summary  — MUST be before /:id pattern
router.get("/summary", forward("get", () => "/api/notice-queue/summary"));

// GET /api/notice-queue?min_prob=25&limit=8
router.get("/",        forward("get", () => "/api/notice-queue"));

module.exports = router;
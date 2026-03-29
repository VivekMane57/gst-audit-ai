const router = require("express").Router();
const axios  = require("axios");
const { pythonUrl } = require("../config");

/**
 * Helper — Python FastAPI pe request forward karo.
 * x-user-id, x-user-email, x-user-name — sab headers forward hote hain.
 */
const forward = (method, pathFn) => async (req, res, next) => {
  try {
    const userId    = req.headers["x-user-id"]    || req.headers["x-clerk-id"] || "dev-user";
    const userEmail = req.headers["x-user-email"]  || "";
    const userName  = req.headers["x-user-name"]   || "";

    const response = await axios({
      method,
      url: `${pythonUrl}${pathFn(req)}`,
      headers: {
        "x-user-id":    userId,
        "x-user-email": userEmail,
        "x-user-name":  userName,
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

// GET    /api/clients          — All clients
router.get(   "/",    forward("get",    ()  => "/clients"));

// POST   /api/clients          — Add new client
router.post(  "/",    forward("post",   ()  => "/clients"));

// GET    /api/clients/:id      — Single client detail
router.get(   "/:id", forward("get",    (r) => `/clients/${r.params.id}`));

// PUT    /api/clients/:id      — Update client ← YE MISSING THA!
router.put(   "/:id", forward("put",    (r) => `/clients/${r.params.id}`));

// DELETE /api/clients/:id      — Delete client
router.delete("/:id", forward("delete", (r) => `/clients/${r.params.id}`));

module.exports = router;
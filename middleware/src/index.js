const express   = require("express");
const axios     = require("axios");
const multer    = require("multer");
const cors      = require("cors");
const rateLimit = require("express-rate-limit");
const FormData  = require("form-data");

const app        = express();
const PORT       = process.env.PORT       || 3001;
const PYTHON_URL = process.env.PYTHON_URL || "http://localhost:8000";

const T = {
  DEFAULT:  30_000,
  AUDIT:   120_000,
  PDF:      60_000,
};

const api = axios.create({ baseURL: PYTHON_URL, timeout: T.DEFAULT });

app.set("trust proxy", 1);
app.use(cors({ origin: "*" }));
app.use(express.json());
app.use(rateLimit({ windowMs: 15 * 60 * 1000, max: 300 }));

const upload = multer({
  storage: multer.memoryStorage(),
  limits:  { fileSize: 10 * 1024 * 1024 },
}).any();

const getUserId = (req) =>
  req.headers["x-user-id"] ||
  req.headers["x-clerk-id"] ||
  "";

const proxyHeaders = (req) => ({
  "x-user-id": getUserId(req),
});

function handleError(res, err, label) {
  if (err.code === "ECONNABORTED") {
    console.error(`[TIMEOUT] ${label}`);
    return res.status(504).json({ error: `${label} timed out. Please retry.` });
  }
  if (err.response) {
    return res.status(err.response.status).json(err.response.data);
  }
  console.error(`[ERROR] ${label}:`, err.message);
  return res.status(500).json({ error: err.message });
}

app.get("/health", async (_req, res) => {
  try {
    const r = await api.get("/health");
    res.json({ middleware: "ok", backend: r.data });
  } catch {
    res.status(503).json({ middleware: "ok", backend: "unreachable" });
  }
});

app.get("/api/clients", async (req, res) => {
  try {
    const r = await api.get("/clients", {
      timeout: T.DEFAULT,
      headers: proxyHeaders(req),
    });
    res.json(r.data);
  } catch (err) { handleError(res, err, "GET /api/clients"); }
});

app.get("/api/clients/:id", async (req, res) => {
  try {
    const r = await api.get(`/clients/${req.params.id}`, {
      timeout: T.DEFAULT,
      headers: proxyHeaders(req),
    });
    res.json(r.data);
  } catch (err) { handleError(res, err, "GET /api/clients/:id"); }
});

app.post("/api/clients", async (req, res) => {
  try {
    const r = await api.post("/clients", req.body, {
      timeout: T.DEFAULT,
      headers: proxyHeaders(req),
    });
    res.json(r.data);
  } catch (err) { handleError(res, err, "POST /api/clients"); }
});

app.delete("/api/clients/:id", async (req, res) => {
  try {
    const r = await api.delete(`/clients/${req.params.id}`, {
      timeout: T.DEFAULT,
      headers: proxyHeaders(req),
    });
    res.json(r.data);
  } catch (err) { handleError(res, err, "DELETE /api/clients/:id"); }
});

app.post("/api/audit", upload, async (req, res) => {
  try {
    const files = req.files || [];

    const salesFile    = files.find(f => f.fieldname === "sales_file");
    const purchaseFile = files.find(f => f.fieldname === "purchase_file");

    if (!salesFile || !purchaseFile) {
      return res.status(400).json({
        error: `Missing files. Got: ${files.map(f => f.fieldname).join(", ") || "none"}. Need: sales_file + purchase_file`
      });
    }

    const form = new FormData();

    form.append("sales_file", salesFile.buffer, {
      filename:    salesFile.originalname,
      contentType: salesFile.mimetype || "application/octet-stream",
    });
    form.append("purchase_file", purchaseFile.buffer, {
      filename:    purchaseFile.originalname,
      contentType: purchaseFile.mimetype || "application/octet-stream",
    });

    const textFields = ["our_gstin", "period", "language", "client_id", "sector"];
    textFields.forEach((f) => {
      if (req.body[f] !== undefined && req.body[f] !== "") {
        form.append(f, req.body[f]);
      }
    });

    console.log(`[AUDIT] user=${getUserId(req)} gstin=${req.body.our_gstin} period=${req.body.period}`);

    const r = await api.post("/audit", form, {
      timeout: T.AUDIT,
      headers: {
        ...form.getHeaders(),
        "x-user-id": getUserId(req),
      },
    });
    res.json(r.data);
  } catch (err) { handleError(res, err, "POST /api/audit"); }
});

app.get("/api/audit/:id", async (req, res) => {
  try {
    const r = await api.get(`/audit/${req.params.id}`, {
      timeout: T.DEFAULT,
      headers: proxyHeaders(req),
    });
    res.json(r.data);
  } catch (err) { handleError(res, err, "GET /api/audit/:id"); }
});

app.get("/api/reports", async (req, res) => {
  try {
    const r = await api.get("/reports", {
      timeout: T.DEFAULT,
      headers: proxyHeaders(req),
      params:  req.query,
    });
    res.json(r.data);
  } catch (err) { handleError(res, err, "GET /api/reports"); }
});

app.get("/api/reports/:id", async (req, res) => {
  try {
    const r = await api.get(`/reports/${req.params.id}`, {
      timeout: T.DEFAULT,
      headers: proxyHeaders(req),
    });
    res.json(r.data);
  } catch (err) { handleError(res, err, "GET /api/reports/:id"); }
});

app.get("/api/reports/:id/pdf", async (req, res) => {
  try {
    const r = await api.get(`/reports/${req.params.id}/pdf`, {
      timeout:      T.PDF,
      responseType: "arraybuffer",
      headers:      proxyHeaders(req),
      params:       req.query,
    });
    res.setHeader("Content-Type", "application/pdf");
    res.setHeader("Content-Disposition", `attachment; filename=GST_Audit_${req.params.id.slice(0, 8)}.pdf`);
    res.send(Buffer.from(r.data));
  } catch (err) { handleError(res, err, "GET /api/reports/:id/pdf"); }
});

app.listen(PORT, () => {
  console.log(`
  ╔══════════════════════════════════════╗
  ║   GST Audit AI — Middleware v1.0.0   ║
  ║   Port: ${PORT}                        ║
  ║   Python: ${PYTHON_URL}  ║
  ╚══════════════════════════════════════╝
  `);
});
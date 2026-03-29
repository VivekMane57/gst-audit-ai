// const express   = require("express");
// const axios     = require("axios");
// const multer    = require("multer");
// const cors      = require("cors");
// const rateLimit = require("express-rate-limit");
// const FormData  = require("form-data");

// const app        = express();
// const PORT       = process.env.PORT       || 3001;
// const PYTHON_URL = process.env.PYTHON_URL || "http://localhost:8000";

// const T = {
//   DEFAULT:  30_000,
//   AUDIT:   120_000,
//   PDF:      60_000,
// };

// const api = axios.create({ baseURL: PYTHON_URL, timeout: T.DEFAULT });

// app.set("trust proxy", 1);
// app.use(cors({ origin: "*" }));
// app.use(express.json());
// app.use(rateLimit({ windowMs: 15 * 60 * 1000, max: 300 }));

// const upload = multer({
//   storage: multer.memoryStorage(),
//   limits:  { fileSize: 10 * 1024 * 1024 },
// }).any();

// const getUserId = (req) =>
//   req.headers["x-user-id"] ||
//   req.headers["x-clerk-id"] ||
//   "";

// const proxyHeaders = (req) => ({
//   "x-user-id":    getUserId(req),
//   "x-user-email": req.headers["x-user-email"] || "",
//   "x-user-name":  req.headers["x-user-name"]  || "",
// });

// function handleError(res, err, label) {
//   if (err.code === "ECONNABORTED") {
//     console.error(`[TIMEOUT] ${label}`);
//     return res.status(504).json({ error: `${label} timed out. Please retry.` });
//   }
//   if (err.response) {
//     return res.status(err.response.status).json(err.response.data);
//   }
//   console.error(`[ERROR] ${label}:`, err.message);
//   return res.status(500).json({ error: err.message });
// }

// // ── Health ───────────────────────────────────────────────────
// app.get("/health", async (_req, res) => {
//   try {
//     const r = await api.get("/health");
//     res.json({ middleware: "ok", backend: r.data });
//   } catch {
//     res.status(503).json({ middleware: "ok", backend: "unreachable" });
//   }
// });

// // ── Clients ──────────────────────────────────────────────────
// app.get("/api/clients", async (req, res) => {
//   try {
//     const r = await api.get("/clients", {
//       timeout: T.DEFAULT,
//       headers: proxyHeaders(req),
//     });
//     res.json(r.data);
//   } catch (err) { handleError(res, err, "GET /api/clients"); }
// });

// app.get("/api/clients/:id", async (req, res) => {
//   try {
//     const r = await api.get(`/clients/${req.params.id}`, {
//       timeout: T.DEFAULT,
//       headers: proxyHeaders(req),
//     });
//     res.json(r.data);
//   } catch (err) { handleError(res, err, "GET /api/clients/:id"); }
// });

// app.post("/api/clients", async (req, res) => {
//   try {
//     const r = await api.post("/clients", req.body, {
//       timeout: T.DEFAULT,
//       headers: proxyHeaders(req),
//     });
//     res.json(r.data);
//   } catch (err) { handleError(res, err, "POST /api/clients"); }
// });

// app.put("/api/clients/:id", async (req, res) => {
//   try {
//     const r = await api.put(`/clients/${req.params.id}`, req.body, {
//       timeout: T.DEFAULT,
//       headers: proxyHeaders(req),
//     });
//     res.json(r.data);
//   } catch (err) { handleError(res, err, "PUT /api/clients/:id"); }
// });

// app.delete("/api/clients/:id", async (req, res) => {
//   try {
//     const r = await api.delete(`/clients/${req.params.id}`, {
//       timeout: T.DEFAULT,
//       headers: proxyHeaders(req),
//     });
//     res.json(r.data);
//   } catch (err) { handleError(res, err, "DELETE /api/clients/:id"); }
// });

// // ── Audit ────────────────────────────────────────────────────
// app.post("/api/audit", upload, async (req, res) => {
//   try {
//     const files = req.files || [];

//     const salesFile    = files.find(f => f.fieldname === "sales_file");
//     const purchaseFile = files.find(f => f.fieldname === "purchase_file");
//     const extraFiles   = files.filter(f => f.fieldname === "extra_files");

//     if (!salesFile && !purchaseFile && extraFiles.length === 0) {
//       return res.status(400).json({
//         error: `No files uploaded. Got: ${files.map(f => f.fieldname).join(", ") || "none"}. Need at least one file.`
//       });
//     }

//     const form = new FormData();

//     if (salesFile) {
//       form.append("sales_file", salesFile.buffer, {
//         filename:    salesFile.originalname,
//         contentType: salesFile.mimetype || "application/octet-stream",
//       });
//     }

//     if (purchaseFile) {
//       form.append("purchase_file", purchaseFile.buffer, {
//         filename:    purchaseFile.originalname,
//         contentType: purchaseFile.mimetype || "application/octet-stream",
//       });
//     }

//     extraFiles.forEach((ef) => {
//       form.append("extra_files", ef.buffer, {
//         filename:    ef.originalname,
//         contentType: ef.mimetype || "application/octet-stream",
//       });
//     });

//     const textFields = ["our_gstin", "period", "language", "client_id", "sector"];
//     textFields.forEach((f) => {
//       if (req.body[f] !== undefined && req.body[f] !== "") {
//         form.append(f, req.body[f]);
//       }
//     });

//     const totalFiles = (salesFile ? 1 : 0) + (purchaseFile ? 1 : 0) + extraFiles.length;
//     console.log(`[AUDIT] user=${getUserId(req)} gstin=${req.body.our_gstin} period=${req.body.period} files=${totalFiles}`);

//     const r = await api.post("/audit", form, {
//       timeout: T.AUDIT,
//       headers: {
//         ...form.getHeaders(),
//         "x-user-id": getUserId(req),
//       },
//     });
//     res.json(r.data);
//   } catch (err) { handleError(res, err, "POST /api/audit"); }
// });

// app.get("/api/audit/:id", async (req, res) => {
//   try {
//     const r = await api.get(`/audit/${req.params.id}`, {
//       timeout: T.DEFAULT,
//       headers: proxyHeaders(req),
//     });
//     res.json(r.data);
//   } catch (err) { handleError(res, err, "GET /api/audit/:id"); }
// });

// // ── Reports ──────────────────────────────────────────────────
// // IMPORTANT: /suppliers MUST be before /:id to avoid route conflict
// app.get("/api/reports/suppliers", async (req, res) => {
//   try {
//     const r = await api.get("/reports/suppliers", {
//       timeout: T.DEFAULT,
//       headers: proxyHeaders(req),
//     });
//     res.json(r.data);
//   } catch (err) { handleError(res, err, "GET /api/reports/suppliers"); }
// });

// app.get("/api/reports", async (req, res) => {
//   try {
//     const r = await api.get("/reports", {
//       timeout: T.DEFAULT,
//       headers: proxyHeaders(req),
//       params:  req.query,
//     });
//     res.json(r.data);
//   } catch (err) { handleError(res, err, "GET /api/reports"); }
// });

// app.get("/api/reports/:id", async (req, res) => {
//   try {
//     const r = await api.get(`/reports/${req.params.id}`, {
//       timeout: T.DEFAULT,
//       headers: proxyHeaders(req),
//     });
//     res.json(r.data);
//   } catch (err) { handleError(res, err, "GET /api/reports/:id"); }
// });

// app.get("/api/reports/:id/pdf", async (req, res) => {
//   try {
//     const r = await api.get(`/reports/${req.params.id}/pdf`, {
//       timeout:      T.PDF,
//       responseType: "arraybuffer",
//       headers:      proxyHeaders(req),
//       params:       req.query,
//     });
//     res.setHeader("Content-Type", "application/pdf");
//     res.setHeader("Content-Disposition", `attachment; filename=GST_Audit_${req.params.id.slice(0, 8)}.pdf`);
//     res.send(Buffer.from(r.data));
//   } catch (err) { handleError(res, err, "GET /api/reports/:id/pdf"); }
// });

// // ── HSN ──────────────────────────────────────────────────────
// app.get("/api/hsn/search", async (req, res) => {
//   try {
//     const r = await api.get("/hsn/search", {
//       timeout: T.DEFAULT,
//       headers: proxyHeaders(req),
//       params:  req.query,
//     });
//     res.json(r.data);
//   } catch (err) { handleError(res, err, "GET /api/hsn/search"); }
// });

// app.get("/api/hsn/lookup/:code", async (req, res) => {
//   try {
//     const r = await api.get(`/hsn/lookup/${req.params.code}`, {
//       timeout: T.DEFAULT,
//       headers: proxyHeaders(req),
//     });
//     res.json(r.data);
//   } catch (err) { handleError(res, err, "GET /api/hsn/lookup"); }
// });

// app.post("/api/hsn/validate", async (req, res) => {
//   try {
//     const r = await api.post("/hsn/validate", req.body, {
//       timeout: T.DEFAULT,
//       headers: proxyHeaders(req),
//     });
//     res.json(r.data);
//   } catch (err) { handleError(res, err, "POST /api/hsn/validate"); }
// });

// // ── Start ────────────────────────────────────────────────────
// app.listen(PORT, () => {
//   console.log(`
//   ╔══════════════════════════════════════╗
//   ║   GST Audit AI — Middleware v3.0.0   ║
//   ║   Port: ${PORT}                        ║
//   ║   Python: ${PYTHON_URL}  ║
//   ╚══════════════════════════════════════╝
//   `);
// });


/**
 * middleware/src/index.js
 *
 * Layer  : Entry Point — App bootstrap only
 * Role   : Middleware register karo + routes mount karo
 *          Koi business logic YAHAN NAHI
 *
 * Clean Architecture (diagram ke hisaab se):
 *   Request → globalLimiter → cors → auth headers → routes → Python backend
 */

require("dotenv").config();

const express = require("express");
const cors    = require("cors");

const { globalLimiter }  = require("./middleware/rateLimiter");
const { errorHandler, notFound } = require("./middleware/errorHandler");

// ── Route imports ──────────────────────────────────────────────────────────
const auditRouter        = require("./routes/audit");
const clientsRouter      = require("./routes/clients");
const reportsRouter      = require("./routes/reports");
const hsnRouter          = require("./routes/hsn");
const healthRouter       = require("./routes/health");

const app  = express();
const PORT = process.env.PORT || 3001;

// ── Trust proxy — Vercel/Railway/Nginx ke peeche IP sahi mile ─────────────
app.set("trust proxy", 1);

// ── CORS — sirf frontend se requests allow karo ───────────────────────────
app.use(cors({
  origin: process.env.FRONTEND_URL || "http://localhost:3000",
  credentials: true,
}));

// ── Body parser ────────────────────────────────────────────────────────────
app.use(express.json({ limit: "1mb" }));
app.use(express.urlencoded({ extended: true }));

// ── Global rate limiter — sab routes pe pehle lagta hai ───────────────────
app.use(globalLimiter);

// ── Request ID middleware — distributed tracing ke liye ───────────────────
app.use((req, _res, next) => {
  if (!req.headers["x-request-id"]) {
    req.headers["x-request-id"] = `mid-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
  }
  next();
});

// ══════════════════════════════════════════════════════════════════════════
// Routes — thin API layer (auth check + validate + forward to Python)
// ══════════════════════════════════════════════════════════════════════════
app.use("/health",       healthRouter);
app.use("/api/audit",    auditRouter);
app.use("/api/clients",  clientsRouter);
app.use("/api/reports",  reportsRouter);
app.use("/api/hsn",      hsnRouter);

// ── 404 + Global error handler ─────────────────────────────────────────────
app.use(notFound);
app.use(errorHandler);

// ── Start ──────────────────────────────────────────────────────────────────
app.listen(PORT, () => {
  console.log(`
  ╔══════════════════════════════════════════╗
  ║   GST Audit AI — Middleware v4.0.0       ║
  ║   Clean Architecture ✅                  ║
  ║   Port     : ${PORT}                       ║
  ║   Backend  : ${process.env.PYTHON_BACKEND_URL || "http://localhost:8000"} ║
  ║   Env      : ${process.env.NODE_ENV || "development"}                ║
  ╚══════════════════════════════════════════╝
  `);
});

module.exports = app; // testing ke liye
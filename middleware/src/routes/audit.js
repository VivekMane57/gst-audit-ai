/**
 * middleware/src/routes/audit.js
 * 
 * Routes: POST /api/audit, GET /api/audit/status/:taskId, GET /api/audit/:id, POST /api/audit/:id/notice
 */

const router   = require("express").Router();
const axios    = require("axios");
const multer   = require("multer");
const FormData = require("form-data");
const path     = require("path");
const fs       = require("fs");
const os       = require("os");

const { auditLimiter } = require("../middleware/rateLimiter");
const { pythonUrl }    = require("../config");

// ── DiskStorage ──────────────────────────────────────────────
const TMP_DIR = process.env.UPLOAD_TMP_DIR || os.tmpdir();

const storage = multer.diskStorage({
  destination: (_req, _file, cb) => cb(null, TMP_DIR),
  filename:    (_req, file, cb) => {
    const unique = `${Date.now()}-${Math.round(Math.random() * 1e6)}`;
    cb(null, `${unique}${path.extname(file.originalname)}`);
  },
});

const upload = multer({
  storage,
  limits: { fileSize: parseInt(process.env.MAX_FILE_SIZE) || 20 * 1024 * 1024 },
  fileFilter: (_req, file, cb) => {
    const allowed = [".xlsx", ".xls", ".csv", ".pdf", ".png", ".jpg", ".jpeg", ".xml"];
    const ext = path.extname(file.originalname).toLowerCase();
    if (allowed.includes(ext)) return cb(null, true);
    cb(new Error(`File type allowed nahi: ${ext}`));
  },
}).any();

const AUDIT_TIMEOUT = parseInt(process.env.AUDIT_TIMEOUT_MS) || 30_000;

const cleanupFiles = (files = []) => {
  files.forEach((f) => {
    if (f.path) fs.unlink(f.path, () => {});
  });
};

const getForwardHeaders = (req, extraHeaders = {}) => ({
  "x-user-id":    req.headers["x-user-id"]    || req.headers["x-clerk-id"] || "",
  "x-user-email": req.headers["x-user-email"] || "",
  "x-user-name":  req.headers["x-user-name"]  || "",
  "x-real-ip":    req.headers["x-forwarded-for"]?.split(",")[0]?.trim() || req.ip || "",
  "x-request-id": req.headers["x-request-id"] || `mid-${Date.now()}`,
  ...extraHeaders,
});

// ══════════════════════════════════════════════════════════════
// GET /api/audit/status/:taskId — Celery task status polling
// IMPORTANT: YE /:id SE PEHLE HONA CHAHIYE warna "status" ko id samjhega
// ══════════════════════════════════════════════════════════════
router.get("/status/:taskId", async (req, res, next) => {
  try {
    const response = await axios.get(`${pythonUrl}/audit/status/${req.params.taskId}`, {
      timeout: 10_000,
      headers: getForwardHeaders(req),
    });
    res.json(response.data);
  } catch (err) {
    if (err.response) return res.status(err.response.status).json(err.response.data);
    next(err);
  }
});

// ══════════════════════════════════════════════════════════════
// GET /api/audit/formats — Supported file formats
// ══════════════════════════════════════════════════════════════
router.get("/formats", async (req, res, next) => {
  try {
    const response = await axios.get(`${pythonUrl}/audit/formats`, {
      timeout: 5_000,
      headers: getForwardHeaders(req),
    });
    res.json(response.data);
  } catch (err) {
    if (err.response) return res.status(err.response.status).json(err.response.data);
    next(err);
  }
});

// ══════════════════════════════════════════════════════════════
// POST /api/audit — File upload → Python → task_id
// ══════════════════════════════════════════════════════════════
router.post("/", auditLimiter, upload, async (req, res, next) => {
  const files = req.files || [];

  try {
    const userId = req.headers["x-user-id"] || req.headers["x-clerk-id"] || "";
    if (!userId) {
      cleanupFiles(files);
      return res.status(401).json({ error: "Unauthorized — login required" });
    }

    const salesFile    = files.find(f => f.fieldname === "sales_file");
    const purchaseFile = files.find(f => f.fieldname === "purchase_file");
    const extraFiles   = files.filter(f => f.fieldname === "extra_files");

    if (!salesFile && !purchaseFile && extraFiles.length === 0) {
      cleanupFiles(files);
      return res.status(400).json({
        error: `No files uploaded. At least one file chahiye.`,
      });
    }

    const { our_gstin, period, language, sector, client_id } = req.body;
    if (!our_gstin) {
      cleanupFiles(files);
      return res.status(400).json({ error: "GSTIN required" });
    }

    const form = new FormData();

    if (salesFile) {
      form.append("sales_file", fs.createReadStream(salesFile.path), {
        filename:    salesFile.originalname,
        contentType: salesFile.mimetype || "application/octet-stream",
      });
    }

    if (purchaseFile) {
      form.append("purchase_file", fs.createReadStream(purchaseFile.path), {
        filename:    purchaseFile.originalname,
        contentType: purchaseFile.mimetype || "application/octet-stream",
      });
    }

    extraFiles.forEach((ef) => {
      form.append("extra_files", fs.createReadStream(ef.path), {
        filename:    ef.originalname,
        contentType: ef.mimetype || "application/octet-stream",
      });
    });

    ["our_gstin", "period", "language", "sector", "client_id"].forEach((field) => {
      if (req.body[field]) form.append(field, req.body[field]);
    });

    const totalFiles = (salesFile ? 1 : 0) + (purchaseFile ? 1 : 0) + extraFiles.length;
    console.log(`[AUDIT] user=${userId} gstin=${our_gstin} period=${period} files=${totalFiles}`);

    const response = await axios.post(`${pythonUrl}/audit`, form, {
      timeout: AUDIT_TIMEOUT,
      headers: getForwardHeaders(req, form.getHeaders()),
      maxContentLength: Infinity,
      maxBodyLength:    Infinity,
    });

    res.json(response.data);

  } catch (err) {
    if (err.response) {
      return res.status(err.response.status).json(err.response.data);
    }
    if (err.code === "ECONNABORTED") {
      return res.status(504).json({ error: "Backend timed out. Retry karo." });
    }
    console.error("[ERROR] POST /api/audit:", err.message);
    next(err);
  } finally {
    cleanupFiles(files);
  }
});

// ══════════════════════════════════════════════════════════════
// GET /api/audit/:id — Get audit result by audit_id
// ══════════════════════════════════════════════════════════════
router.get("/:id", async (req, res, next) => {
  try {
    const response = await axios.get(`${pythonUrl}/audit/${req.params.id}`, {
      timeout: 10_000,
      headers: getForwardHeaders(req),
    });
    res.json(response.data);
  } catch (err) {
    if (err.response) return res.status(err.response.status).json(err.response.data);
    next(err);
  }
});

// ══════════════════════════════════════════════════════════════
// POST /api/audit/:id/notice — Re-run notice simulation
// ══════════════════════════════════════════════════════════════
router.post("/:id/notice", async (req, res, next) => {
  try {
    const response = await axios.post(
      `${pythonUrl}/audit/${req.params.id}/notice`,
      req.body,
      {
        timeout: 30_000,
        headers: getForwardHeaders(req),
      }
    );
    res.json(response.data);
  } catch (err) {
    if (err.response) return res.status(err.response.status).json(err.response.data);
    next(err);
  }
});

module.exports = router;
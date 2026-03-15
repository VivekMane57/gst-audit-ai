const router = require("express").Router();
const axios = require("axios");
const FormData = require("form-data");
const { upload, handleMulterError } = require("../middleware/fileValidator");
const { auditLimiter } = require("../middleware/rateLimiter");
const { pythonUrl } = require("../config");

/**
 * POST /api/audit
 * File + form data ko Python FastAPI pe forward karo.
 * Clerk auth middleware pehle se run ho chuka hoga.
 */
router.post(
  "/",
  auditLimiter,
  upload.single("file"),
  handleMulterError,
  async (req, res, next) => {
    try {
      if (!req.file) {
        return res.status(400).json({ error: "File upload karo" });
      }

      const { our_gstin, invoice_type, period, language, client_name } = req.body;

      if (!our_gstin) {
        return res.status(400).json({ error: "our_gstin required hai" });
      }

      // FormData banao — Python ko bhejne ke liye
      const form = new FormData();
      form.append("file", req.file.buffer, {
        filename: req.file.originalname,
        contentType: req.file.mimetype,
      });
      form.append("our_gstin",    our_gstin);
      form.append("invoice_type", invoice_type || "purchase");
      form.append("period",       period || "");
      form.append("language",     language || "en");
      if (client_name) form.append("client_name", client_name);

      // Python FastAPI pe forward karo
      const response = await axios.post(
        `${pythonUrl}/audit`,
        form,
        {
          headers: form.getHeaders(),
          timeout: 30000,   // 30 sec — badi files ke liye
        }
      );

      res.json(response.data);

    } catch (err) {
      if (err.response) {
        // Python se error aaya
        return res.status(err.response.status).json(err.response.data);
      }
      next(err);
    }
  }
);

/**
 * GET /api/audit/:id
 * Stored audit report fetch karo.
 */
router.get("/:id", async (req, res, next) => {
  try {
    const response = await axios.get(
      `${pythonUrl}/audit/${req.params.id}`,
      { timeout: 5000 }
    );
    res.json(response.data);
  } catch (err) {
    if (err.response) {
      return res.status(err.response.status).json(err.response.data);
    }
    next(err);
  }
});

module.exports = router;
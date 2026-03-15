const multer = require("multer");
const path = require("path");

const ALLOWED_TYPES = [
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", // xlsx
  "application/vnd.ms-excel",   // xls
  "text/csv",
  "application/csv",
];
const ALLOWED_EXTS = [".xlsx", ".xls", ".csv"];
const MAX_SIZE = 10 * 1024 * 1024; // 10MB

// Multer memory storage — disk pe save nahi karte
const upload = multer({
  storage: multer.memoryStorage(),
  limits: { fileSize: MAX_SIZE },
  fileFilter: (req, file, cb) => {
    const ext = path.extname(file.originalname).toLowerCase();
    const mime = file.mimetype;

    if (ALLOWED_EXTS.includes(ext) || ALLOWED_TYPES.includes(mime)) {
      cb(null, true);
    } else {
      cb(new Error(`File type allowed nahi: ${ext}. Sirf .xlsx, .xls, .csv upload karo.`));
    }
  },
});

// Multer error handler
const handleMulterError = (err, req, res, next) => {
  if (err instanceof multer.MulterError) {
    if (err.code === "LIMIT_FILE_SIZE") {
      return res.status(400).json({ error: "File 10MB se badi hai" });
    }
    return res.status(400).json({ error: err.message });
  }
  if (err) {
    return res.status(400).json({ error: err.message });
  }
  next();
};

module.exports = { upload, handleMulterError };
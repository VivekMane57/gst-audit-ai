require("dotenv").config();

module.exports = {
  port:           process.env.PORT || 3001,
  pythonUrl:      process.env.PYTHON_BACKEND_URL || "http://localhost:8000",
  frontendUrl:    process.env.FRONTEND_URL || "http://localhost:3000",
  supabaseUrl:    process.env.SUPABASE_URL,
  supabaseKey:    process.env.SUPABASE_KEY,
  nodeEnv:        process.env.NODE_ENV || "development",
  isDev:          process.env.NODE_ENV !== "production",
};
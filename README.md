<div align="center">

# 🧾 GST-AUDIT-AI

### AI-Powered GST Audit & Compliance System for Indian Chartered Accountants

[![Next.js](https://img.shields.io/badge/Next.js-14-black?style=for-the-badge&logo=next.js)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Python-009688?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Supabase](https://img.shields.io/badge/Supabase-Database-3ECF8E?style=for-the-badge&logo=supabase)](https://supabase.com/)
[![Razorpay](https://img.shields.io/badge/Razorpay-Payments-02042B?style=for-the-badge&logo=razorpay)](https://razorpay.com/)

> **Status:** 🟢 Live — 3 real clients onboarded

</div>

---

## 📌 What is GST-AUDIT-AI?

GST-AUDIT-AI is a fintech SaaS platform that automates GST compliance auditing for Indian Chartered Accountants and businesses. It uses AI to detect compliance issues, predict GST notices, score supplier risk, and generate audit reports — replacing hours of manual work with instant, accurate results.

---

## ✨ Features

### 🔍 Audit & Compliance Engine
- Rule-based GST audit engine with 200+ compliance rules across 15 sectors
- Automatic detection of ITC mismatches, HSN errors, filing discrepancies
- GSTR-2A / 2B vs purchase register reconciliation

### 🤖 AI Risk Scoring
- AI-powered risk scoring for each compliance issue
- Predicts likelihood of receiving GST notice
- Risk levels: Low / Medium / High / Critical

### 📊 Supplier Trust Score Dashboard
- Scores suppliers based on filing consistency, ITC claims, and return history
- Flags risky suppliers before ITC is claimed
- Visual dashboard with actionable insights

### 🔢 HSN Rate Validator
- Validates HSN/SAC codes against correct GST rates
- Detects misclassification and rate application errors
- Covers goods and services across all sectors

### 📄 Multilingual OCR Pipeline
- Extracts data from GST documents, invoices, and returns
- Powered by Google Vision API
- Feature-flagged rollout — supports English + regional languages

### 📧 Email Notification System
- Automated alerts for filing deadlines, audit findings, and notice predictions
- SMTP-based reliable delivery
- Configurable per client

### 📑 Automated Audit Reports
- One-click PDF audit reports for clients
- Structured findings with fix recommendations and penalty details
- Ready to share with clients directly

### 💳 Payments & Subscriptions
- Razorpay integration for subscription billing
- Plan-based access control

### 🔐 Authentication
- Clerk-based secure authentication
- Role-based access (CA / Client / Admin)

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────┐
│                  CLIENT BROWSER                  │
└──────────────────────┬──────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────┐
│             Next.js 14 (Frontend)                │
│         Vercel Deployment | Clerk Auth           │
└──────────────────────┬──────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────┐
│           Node.js + Express (API Layer)          │
│         REST APIs | Business Logic               │
└───────────┬──────────────────────┬──────────────┘
            │                      │
┌───────────▼──────┐   ┌───────────▼──────────────┐
│ FastAPI (Python) │   │        Supabase           │
│ AI Rule Engine   │   │   PostgreSQL Database     │
│ OCR Pipeline     │   │   Auth + Storage          │
│ Risk Scoring     │   └──────────────────────────┘
└───────────┬──────┘
            │
┌───────────▼──────┐
│  Celery + Redis  │
│  Async Task Queue│
│  Background Jobs │
└──────────────────┘
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14, React, Tailwind CSS |
| Backend API | Node.js, Express.js |
| AI / ML Engine | Python, FastAPI |
| Database | Supabase (PostgreSQL) |
| Auth | Clerk |
| Payments | Razorpay |
| Task Queue | Celery + Redis |
| OCR | Google Vision API |
| Deployment | Vercel (Frontend), Railway (Backend) |
| Email | SMTP (Nodemailer) |

---

## 📁 Project Structure

```
gst-audit-ai/
├── frontend/                  # Next.js 14 app
│   ├── app/                   # App router pages
│   ├── components/            # Reusable UI components
│   ├── lib/                   # Utilities, API calls
│   └── public/                # Static assets
│
├── backend/                   # Node.js Express API
│   ├── routes/                # API routes
│   ├── controllers/           # Business logic
│   ├── middleware/             # Auth, validation
│   └── models/                # DB models
│
├── ai-engine/                 # Python FastAPI
│   ├── rule_engine/           # GST compliance rules
│   ├── risk_scoring/          # AI risk model
│   ├── ocr/                   # OCR pipeline
│   └── main.py                # FastAPI entry point
│
└── README.md
```

---

## 🚀 Getting Started

### Prerequisites
- Node.js 18+
- Python 3.10+
- Redis
- Supabase account
- Clerk account
- Razorpay account

### 1. Clone the repo
```bash
git clone https://github.com/your-username/gst-audit-ai.git
cd gst-audit-ai
```

### 2. Frontend setup
```bash
cd frontend
npm install
cp .env.example .env.local
# Fill in your env variables
npm run dev
```

### 3. Backend setup
```bash
cd backend
npm install
cp .env.example .env
# Fill in your env variables
npm run dev
```

### 4. AI Engine setup
```bash
cd ai-engine
pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --reload --port 8000
```

### 5. Start Redis + Celery
```bash
redis-server
celery -A ai-engine.tasks worker --loglevel=info
```

---

## 🌍 Environment Variables

### Frontend (`.env.local`)
```env
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=
CLERK_SECRET_KEY=
NEXT_PUBLIC_API_URL=
NEXT_PUBLIC_RAZORPAY_KEY_ID=
```

### Backend (`.env`)
```env
SUPABASE_URL=
SUPABASE_SERVICE_KEY=
CLERK_SECRET_KEY=
RAZORPAY_KEY_ID=
RAZORPAY_KEY_SECRET=
SMTP_HOST=
SMTP_USER=
SMTP_PASS=
AI_ENGINE_URL=
REDIS_URL=
```

### AI Engine (`.env`)
```env
SUPABASE_URL=
SUPABASE_SERVICE_KEY=
GOOGLE_VISION_API_KEY=
REDIS_URL=
```

---

## 📊 GST Rule Coverage

| Category | Rules |
|----------|-------|
| Input Tax Credit (ITC) | 30+ |
| Invoice & Documentation | 25+ |
| Returns & Filing | 25+ |
| HSN Classification | 20+ |
| Reconciliation | 20+ |
| Registration & Compliance | 15+ |
| Supplier Risk | 15+ |
| Tax Calculation | 15+ |
| Payment & Interest | 15+ |
| Penalties & Offences | 15+ |
| **Total** | **200–300** |

**Sectors Covered:** Manufacturing, Trading/Retail, Services, IT/SaaS, Transport & Logistics, Healthcare, Construction/Real Estate, Hospitality, E-commerce, Export/Import, Finance/Banking, Education, Agriculture, Government Contracts, Advertising/Media

---

## 👥 Team

| Name | Role |
|------|------|
| Vivek | Co-Founder, Full Stack + AI Engineer |
| Vaishnavi Powar | Co-Founder, GST Domain Expert |

---

## 📄 License

This project is proprietary and confidential.
© 2025 GST-AUDIT-AI. All rights reserved.

---

<div align="center">
  <b>Built with ❤️ for Indian CAs and businesses</b>
</div>

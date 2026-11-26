# BreatheWise — AI-Powered Urban Air Quality Assistant

**Tagline:** Breathe Smarter. Live Better.

BreatheWise is an environmental intelligence web platform designed for families, students, commuters, and communities navigating urban air pollution and winter smog (with Pune, India as the initial demonstration city).

## Architecture & Tech Stack

- **Frontend:** Next.js (App Router), React, TypeScript, Tailwind CSS, Framer Motion, Lucide React, Recharts
- **Backend:** Python, FastAPI, Pydantic v2, Async API endpoints, Swagger (`/docs`)
- **Database:** MongoDB Atlas via PyMongo Native Async API (`AsyncMongoClient`) with collection schema validators and indexes (plus a development-only in-memory fallback when `MONGODB_URI` is unset in `ENVIRONMENT=development`)
- **AI Engine:** Google Gemini (`gemini-2.5-flash` default via official `google-genai` Python SDK, configurable via `AI_PROVIDER=gemini` and `GEMINI_MODEL`; optional legacy Hugging Face Qwen support retained)
- **Environmental Telemetry:** Live **Open-Meteo Air Quality API**, **Open-Meteo Weather API**, and **Open-Meteo Geocoding API**, plus browser geolocation

## Key Engineering Principles

1. **Separated AQI Standards:** CPCB Indian National AQI (NAQI) is computed from raw pollutant concentrations (`μg/m³`, converting Open-Meteo CO from `μg/m³` to `mg/m³` per CPCB breakpoints) and displayed separately from US EPA AQI — never mixed or conflated.
2. **Strict AI Grounding:** Gemini receives verified Open-Meteo readings, hourly forecast context, and household/family profiles, and outputs Pydantic-validated JSON. If API keys are missing/invalid or rate limits/timeouts occur, BreatheWise surfaces the exact status and falls back to deterministic `rule_based_fallback` guidance derived strictly from live Open-Meteo readings.
3. **Honest Indoor & Impact Modules:** Indoor guidance explicitly states when no indoor sensor is connected; Personal Impact Tracker uses documented emission factors (UK DESNZ/DEFRA transport baselines, CEA India grid factor) and clearly separates factor-based estimates from measured exposure.

---

## Project Structure

```text
breathwise/
├── frontend/
│   ├── app/                # Landing, Dashboard, AI Advisor, Routine, Indoor, Alternatives, Impact, Profile, Auth
│   ├── components/         # AppShell, LocationPickerModal, UI primitives
│   ├── hooks/              # Global BreatheWise context (auth, location, AQI standard, telemetry)
│   ├── lib/                # Typed FastAPI client, AQI label helpers, constants
│   └── types/              # TypeScript interfaces
├── backend/
│   ├── app/
│   │   ├── main.py         # FastAPI entry point & CORS
│   │   ├── config.py       # Environment configuration
│   │   ├── database.py     # PyMongo AsyncMongoClient, validators & indexes
│   │   ├── prompts/        # Centralized 6-template prompt system
│   │   ├── routes/         # auth, environment, ai, users, routines, impact, health
│   │   ├── schemas/        # Pydantic v2 request/response & structured AI schemas
│   │   ├── services/       # aqi_calculator, environmental_provider, ai_service, auth_service, impact_calculator
│   │   ├── middleware/     # Sliding-window rate limiter
│   │   └── utils/          # Input sanitization & ObjectId helpers
│   ├── tests/              # Pytest unit & API integration tests
│   ├── requirements.txt
│   └── .env.example
└── README.md
```

---

## Local Setup Instructions

### 1. Backend Setup (FastAPI + Python)

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Edit `backend/.env` and set:
- `JWT_SECRET_KEY`: Secure random secret string
- `MONGODB_URI`: Your MongoDB Atlas connection string (`mongodb+srv://...`)
- `AI_PROVIDER`: `gemini`
- `GEMINI_API_KEY`: Your Google Gemini API key
- `GEMINI_MODEL`: Desired Gemini model (default: `gemini-2.5-flash`)

Start the API server:

```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Interactive Swagger docs are available at `http://localhost:8000/docs`.

### 2. Frontend Setup (Next.js)

```powershell
cd frontend
npm install
copy .env.example .env.local
npm run dev
```

Open `http://localhost:3000`.

### 3. Running Tests

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -v
```

```powershell
cd frontend
npm run build
```

---

## Deployment Guide

### Database (MongoDB Atlas)
1. Create an M0/dedicated cluster in MongoDB Atlas.
2. Add a database user and allow Render outbound IPs (or `0.0.0.0/0` with strong credentials).
3. Copy the SRV connection string into `MONGODB_URI`. Collections, `$jsonSchema` validators, and indexes are created automatically on startup.

### Backend (Render)
1. Create a new **Web Service** pointing to `backend/`.
2. Build Command: `pip install -r requirements.txt`
3. Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Set environment variables: `ENVIRONMENT=production`, `DEV_MEMORY_DB_FALLBACK=false`, `ALLOWED_ORIGINS=https://your-vercel-domain.vercel.app`, `JWT_SECRET_KEY`, `MONGODB_URI`, `AI_PROVIDER=gemini`, `GEMINI_API_KEY`, `GEMINI_MODEL=gemini-2.5-flash`.

### Frontend (Vercel)
1. Import the repository into Vercel and set **Root Directory** to `frontend`.
2. Set `NEXT_PUBLIC_API_BASE_URL` to your Render backend URL (`https://your-api.onrender.com`).
3. Deploy.

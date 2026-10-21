# Blood Bridge — Real-Time Blood Request & Donor Matching System

Blood Bridge connects patients, hospitals/blood banks and eligible blood donors in real time.
A patient or hospital posts an emergency request; the matching engine finds compatible, available,
nearby donors (red-cell compatibility + Haversine distance + configurable screening rules), alerts
them instantly over WebSockets, and tracks the request through to a hospital-confirmed donation.

> **Medical safety notice.** Blood Bridge is a donor-request coordination platform. Final donor
> eligibility, blood compatibility verification, testing, and transfusion decisions must be confirmed
> by qualified healthcare professionals.

## Contents
- [Architecture](#architecture)
- [Features](#features)
- [Run locally](#run-locally)
- [Environment variables](#environment-variables)
- [Tests](#tests)
- [Deploy (Render + Neon)](#deploy-render--neon)
- [Docker](#docker)
- [API overview](#api-overview)
- [Privacy & security](#privacy--security)
- [Known limitations](#known-limitations)

## Architecture

```
React 18 + Vite + Tailwind + React Router + Axios + Leaflet/OpenStreetMap + Chart.js   (frontend/)
        │  REST  /api/*            │  WebSocket  /ws?token=<JWT>
        ▼                          ▼
FastAPI  ── routers ── matching engine ── notification service ── WebSocket manager   (backend/app/)
        │
SQLAlchemy 2 ──► PostgreSQL (SQLite file only for quick local experiments)
```

```
BloodBridge/
├── backend/
│   ├── app/
│   │   ├── main.py            FastAPI app, CORS, error handlers, /ws, /api/health
│   │   ├── config.py          settings from environment variables
│   │   ├── database.py        engine/session; creates missing tables (never drops)
│   │   ├── auth.py            bcrypt hashing, JWT, role checks, auth rate limit
│   │   ├── models/            users, donor/patient profiles, hospitals, requests, matches,
│   │   │                      donations, inventory (+history), notifications, audit logs
│   │   ├── schemas/           validated request bodies
│   │   ├── routers/           auth, donors, requests, matching, hospitals, notifications, admin, stats
│   │   └── services/          matching, eligibility, distance, notifications, websocket, privacy, audit
│   ├── tests/                 pytest suite (24 tests)
│   ├── create_admin.py        create an administrator (admins cannot self-register)
│   ├── seed.py                OPTIONAL labelled demo data (non-destructive)
│   ├── requirements.txt / requirements-dev.txt / .env.example / Dockerfile
├── frontend/
│   ├── src/  (pages/, components/, context/, lib/, __tests__/)
│   ├── .env.example / vite.config.js / tailwind.config.js / Dockerfile / nginx.conf
├── e2e/e2e_test.py            Playwright end-to-end test
├── docs/PROJECT_BRIEF.md      original project specification
├── render.yaml                Render deployment (website + API as one service)
├── DEPLOY_STEPS.md            simple deployment guide
└── docker-compose.yml         db + backend + frontend
```

## Features

| Area | What works |
|---|---|
| Accounts | Register as **Donor**, **Patient/Seeker** or **Hospital/Blood Bank** (with validation); login with role check; JWT sessions; admins created by script only. |
| Emergency requests | Big **Emergency Blood Request** button on the home page and **Request Blood** in the header. Visitors who aren't logged in submit in **one step** (their requester account is created from the same form). Blood group, units, urgency, date/time, registered hospital *or* manual hospital + map location; edit, cancel, mark fulfilled. |
| Matching engine | Red-cell compatibility (hard filter) → availability → screening (age, interval since last donation, self-screening) → distance ≤ 50 km (or same city if no coordinates) → weighted score. Newly registered/available donors are matched to open requests automatically. |
| Real time | WebSocket push for new matches, donor acceptance, hospital confirmation, cancellations; live feed/map refresh; notification bell with unread count, mark read / all read. |
| Donors | Availability toggle, eligibility status, accept/decline matches, “I can donate” on the urgent feed, nearby requests with filters, donation history, profile & location editing. |
| Find donors | Search by patient blood group (compatible donors), exact group, city, PIN code, availability, screening status and distance — privacy-safe results. |
| Blood banks | Registered hospitals/blood banks with contact, directions (OpenStreetMap) and verification status. Stock is reported per **component** (Whole Blood, Packed Red Cells, Platelets, Plasma) and blood group, never auto-filled, and shown publicly **only after an admin verifies the facility**. |
| Hospitals | Component inventory editor with low/out-of-stock flags and change history, incoming requests, confirm donations, issue red-cell units from stock. |
| Admin | Live metrics, charts (blood groups, requests over time, severity, cities), verify/unverify, block/unblock, flag suspicious requests (hidden from public), audit log. |
| Live statistics | Home page counts of registered donors, available donors, active requests, fulfilled requests and participating facilities, straight from the database. |
| Emergency map | Leaflet/OSM map: requests as ~1 km approximate circles, facilities as pins. |
| Awareness | Donate Blood guide (eligibility, preparation, interval, aftercare) and Emergency Help page (112 / 108 / 102), with disclaimers. |
| Quick navigation | Always-labelled **Request Blood · Emergency Help · My Dashboard** in the header, **Donate Blood · Find Blood Banks** (and the other pages) in the second header row, plus quick-action tiles on the home page and a mobile menu. |

## Run locally

Prerequisites: **Python 3.11+**, **Node 18+ (20 recommended)**, **PostgreSQL 14+**.

### 1. Database
```bash
# psql as a superuser
CREATE USER bloodbridge WITH PASSWORD 'choose-a-password';
CREATE DATABASE bloodbridge OWNER bloodbridge;
```

### 2. Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env                 # then edit DATABASE_URL and JWT_SECRET
python -c "import secrets; print(secrets.token_urlsafe(48))"   # paste as JWT_SECRET
uvicorn app.main:app --reload --port 8000
```
Tables are created automatically on first start (existing tables/data are never dropped).
API docs: http://localhost:8000/docs · health check: http://localhost:8000/api/health

Create an administrator (you will be prompted for the password):
```bash
python create_admin.py --email admin@yourdomain.org --name "Site Admin"
```
Optional, **empty development databases only** — clearly labelled sample data (no inventory is invented):
```bash
python seed.py --demo        # sample accounts use password Demo@1234
```

### Windows shortcut
Double-click `start_bloodbridge.bat` in the project folder: it opens the backend and frontend in two windows and then the site. (`backend/run_backend.bat` starts only the backend.)

### 3. Frontend
```bash
cd frontend
npm install
npm run dev                  # http://localhost:5173  (proxies /api and /ws to :8000)
```

## Environment variables

**Backend** (`backend/.env`, see `backend/.env.example`)

| Variable | Required | Purpose |
|---|---|---|
| `DATABASE_URL` | yes (prod) | PostgreSQL URL. `postgres://` / `postgresql://` URLs from Render/Neon/Supabase are accepted. |
| `JWT_SECRET` | yes (prod) | Long random secret for signing tokens. If unset in development a temporary one is generated (sessions reset on restart). |
| `ENVIRONMENT` | | `production` enforces `JWT_SECRET` and PostgreSQL. |
| `CORS_ORIGINS` | only if the website is hosted separately | Comma-separated frontend URLs. Not needed on Render, where website and API share one address. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | | Default 720. |
| `WEIGHT_*`, `MAX_MATCH_DISTANCE_KM`, `NOTIFY_TOP_N_DONORS` | | Matching engine tuning. |
| `MIN_DONATION_INTERVAL_DAYS`, `MIN_DONOR_AGE`, `MAX_DONOR_AGE` | | System screening criteria (defaults 90 / 18 / 65). |
| `PUBLIC_LOCATION_DECIMALS` | | Precision of public request locations (2 ≈ 1 km). |
| `FRONTEND_DIST` | | Path to `frontend/dist` to serve the SPA from the API (single-service deploy). |

**Frontend** (`frontend/.env.local` or the hosting provider's build settings, see `frontend/.env.example`)

| Variable | Purpose |
|---|---|
| `VITE_API_URL` | Backend base URL **including `/api`**, e.g. `https://bloodbridge-api.onrender.com/api`. Leave unset in local dev. It is read at **build time**. |

## Tests

```bash
# Backend (SQLite by default)
cd backend && python -m pytest -q
# Backend against PostgreSQL (database name must end in _test; it is reset by the tests)
TEST_DATABASE_URL=postgresql://bloodbridge:pw@localhost:5432/bloodbridge_test python -m pytest -q

# Frontend
cd frontend && npm test && npm run build

# Browser end-to-end (3 users, real-time flow) — see the header of e2e/e2e_test.py
python e2e/e2e_test.py ./e2e-screenshots
```

## Deploy (Render + Neon)

The recommended deployment is **one Render web service** that builds the React website and serves it
from the FastAPI backend (same address, so no CORS or API-URL settings), plus a free, permanent
**Neon** PostgreSQL database. `render.yaml` contains the whole Render setup.
**Simple click-by-click instructions: [DEPLOY_STEPS.md](DEPLOY_STEPS.md).**

1. Neon → create a project → copy the connection string.
2. Push this folder to GitHub (`.env` files are git-ignored, so secrets are not uploaded).
3. Render → **New → Blueprint** → choose the repository → paste the Neon string as `DATABASE_URL` → **Apply**.
   Render runs `npm ci && npm run build` for the website and `pip install` for the API, then starts
   `uvicorn` with `FRONTEND_DIST=../frontend/dist`. `JWT_SECRET` is generated automatically.
4. Create the admin from your own computer against Neon: set `DATABASE_URL` and run `python create_admin.py --email …`.

Render's free web service sleeps after 15 minutes without visitors (the next visit takes about a minute).
Render's own free PostgreSQL is deleted after 30 days, which is why Neon is used.

**Alternative (separate hosting):** the frontend can also be hosted on its own static host: build it with
`VITE_API_URL=https://<backend>/api` and set `CORS_ORIGINS` on the backend to the frontend URL. Render alone is simpler.

## Docker

```bash
JWT_SECRET=$(openssl rand -hex 32) docker compose up --build
# http://localhost:8080  (nginx proxies /api and /ws to the backend)
docker compose exec backend python create_admin.py --email admin@example.org
```

## API overview

Interactive documentation is at `/docs`. Main endpoints (all under `/api`):

| Area | Endpoints |
|---|---|
| Auth | `POST /auth/register`, `POST /auth/login`, `GET /auth/me`, `POST /auth/logout` |
| Requests | `GET/POST /requests`, `GET /requests/mine`, `GET/PUT/DELETE /requests/{id}`, `POST /requests/{id}/cancel`, `/fulfilled`, `/respond` |
| Matching | `GET/POST /matching/{request_id}`, `POST /matching/{match_id}/accept`, `/reject`, `/confirm` |
| Donors | `GET /donors` (search), `GET /donors/me`, `PUT /donors/profile`, `PUT /donors/availability`, `GET /donors/matches`, `/requests/nearby`, `/donations` |
| Hospitals | `GET /hospitals`, `GET/PUT /hospitals/me`, `GET /hospitals/{id}`, `GET/PUT/POST /hospitals/{id}/inventory`, `/inventory/history`, `/requests`, `/requests/{rid}/fulfill-from-stock` |
| Notifications | `GET /notifications`, `PUT /notifications/{id}/read`, `PUT /notifications/read-all` |
| Admin | `/admin/dashboard`, `/analytics`, `/users`, `/donors`, `/hospitals`, `/requests`, `/audit-logs`, `PUT /admin/users/{id}/verify`, `/block`, `PUT /admin/requests/{id}/flag-suspicious` |
| Public | `GET /stats/public`, `GET /stats/config`, `GET /health` · WebSocket `/ws?token=<JWT>` |

## Privacy & security

- Passwords hashed with bcrypt; never returned or logged. JWT in the `Authorization` header; the WebSocket requires a valid token.
- Role-based access everywhere: only the requester/linked facility/admin can see matches or cancel a request; only the donor can accept/decline their match; only the facility (or admin) can confirm donations or edit its stock.
- The public feed and map never include patient names, notes or exact coordinates (locations rounded to ~1 km).
- Donor search returns initials, city, PIN prefix, distance and status only. Donor phone numbers are shared with the requester/hospital **only after that donor accepts**; the hospital address is shared with the donor after acceptance.
- Admin accounts cannot be created through public registration. Important actions are written to an audit log.
- Login/registration are rate-limited per IP. Stack traces are never returned to clients.

## Known limitations

- Email/SMS delivery is not integrated; notifications are in-app + WebSocket (hook point: `services/notification_service.py`).
- The WebSocket registry is in memory — run a single backend process, or add Redis pub/sub before scaling out.
- No Alembic migrations yet: `create_all` adds missing tables but does not alter existing ones.
- Address search uses the free OpenStreetMap Nominatim service (fair-use rate limits).
- Screening rules are simple, configurable coordination checks — never a medical determination.

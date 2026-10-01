# SOLANA QUANT RESEARCH LAB

A runnable quantitative research MVP for a two-person Solana hackathon team. This is a research environment, with no wallet connection, trading keys or live execution.

**The included dataset is SYNTHETIC.** Every price, wallet and transaction in the demo is simulated. Performance is calculated by the engine, never hardcoded. The default experiment can lose money.

## Fastest demo: use the included build

The downloadable ZIP includes `frontend/out`, a ready-to-run browser demo. From the extracted `solana-quant-research-lab` folder, with Python 3 installed:

```bash
python3 -m http.server 3000 --bind 127.0.0.1 --directory frontend/out
```

Open **http://localhost:3000**, then click **Run reference experiment**. No dependency installation, API key or external service is required for this packaged demo. The Python research engine runs in your browser; its runtime files are included. Use the full stack below for FastAPI, database persistence and provider ingestion.

## Launch with Docker Compose

Prerequisites: Docker Engine/Desktop with Compose v2. From the extracted project root:

```bash
cp .env.example .env
docker compose up --build
```

Open **http://localhost:3000**. The API is **http://localhost:8000** and interactive REST documentation is **http://localhost:8000/docs**. Migrations and deterministic seeding run automatically. No API credentials are required for the demo. PostgreSQL data persists in the `postgres_data` volume.

Docker was unavailable in the build environment. The Compose/Dockerfiles are supplied; their containers have not been executed there. SQLite, Alembic, FastAPI tests and Next.js builds were executed.

## Launch without Docker: SQLite fallback

Prerequisites: Python 3.12 (3.11+ works for the portable engine), Node.js 22, npm.

Terminal 1, from the project root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
cp .env.example backend/.env
cd backend
alembic upgrade head
uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
```

Terminal 2, from the project root:

```bash
cd frontend
npm ci
NEXT_PUBLIC_EXECUTION_MODE=api NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
```

Open **http://localhost:3000**. SQLite is created at `backend/quantlab.db`. Use one API process: the MVP worker pool and restart recovery assume a single host/process. No external service is needed after dependency installation.

To use your own PostgreSQL instead, set `DATABASE_URL=postgresql+psycopg://USER:PASSWORD@localhost:5432/quantlab` in `backend/.env`, create that database, and run the same migration/start commands. Passwords in URLs must be URL-encoded.

## Browser-only offline demo

The private hosted demonstration uses the **same Python source**, executed by a self-hosted Pyodide Web Worker. Its datasets/configurations/results persist in IndexedDB on the current browser. It does not run FastAPI or PostgreSQL in the cloud. Real provider ingestion is available in the local API deployment.

To run this mode locally:

```bash
cd frontend
npm ci
npm run prepare:browser
NEXT_PUBLIC_EXECUTION_MODE=browser npm run dev
```

To create a portable static build:

```bash
cd frontend
npm run prepare:browser
NEXT_PUBLIC_EXECUTION_MODE=browser STATIC_EXPORT=1 npm run build
python3 -m http.server 3000 --directory out
```

Open http://localhost:3000. All Python/runtime assets are served locally, with no CDN or API calls. The first load downloads about 13 MB of runtime assets. This is network-independent when served locally; there is no service-worker/PWA cache for disconnected visits to the hosted URL. Keep the tab open while a browser experiment runs. Clearing browser data removes that browser workspace. API failures never switch execution modes automatically.

## Demonstration flow

1. Workspace → **Run reference experiment**.
2. Inspect **Out of sample** net return against gross return and execution costs.
3. Switch to **In sample**; compare the chronology, daily Sharpe caveat and trade count.
4. Expand a trade to see its signal-time eligible wallets and factor snapshot.
5. Strategy lab → change fees, liquidity threshold, wallet count, hold time or another control → **Run backtest**.
6. Research report → export Markdown and the full result JSON; optionally print to PDF.

All supported inputs affect engine decisions or execution. No user-supplied Python is evaluated. Strategy configurations are validated on the server and in browser mode by the same Python config validator.

## Tests and reproducibility

From the project root:

```bash
source .venv/bin/activate
cd backend
pytest -q
cd ../frontend
npm ci
npm run typecheck
NEXT_PUBLIC_EXECUTION_MODE=api npm run build
cd ..
node scripts/check-wasm.mjs
python scripts/run_demo.py --output artifacts
```

The tests use a temporary SQLite database and mock provider responses; no paid API calls occur. `scripts/check-wasm.mjs` compares native Python and WebAssembly fingerprints and numerical results. The headless runner produces `artifacts/result.json`, `config.json` and `report.md`.

The canonical deterministic dataset is `data/synthetic_seed33.json`, generated with:

```bash
PYTHONPATH=backend python -m app.demo
```

To reproduce an exported experiment:

```bash
python scripts/run_demo.py --dataset data/synthetic_seed33.json --config artifacts/config.json --output reproduction
```

The run fingerprint hashes the engine version, canonical JSON dataset and full config. Exact run IDs and creation timestamps are operational metadata and do not affect the research fingerprint.

## Real-data integrations

Set `HELIUS_API_KEY` and `BIRDEYE_API_KEY` in the backend environment, restart the API, then use **Datasets → Historical Solana ingestion**. Keys stay on the server. This requests provider credits under your own plan. Requests are bounded to ten wallets, fourteen days, twenty detected tokens and explicit pagination limits. Use a small window first.

- Helius: finalized wallet history; date filters, signature pagination, backoff, deduplication, preserved raw responses and conservative explicit-swap normalization.
- Birdeye: five-minute historical USD price series and one-minute historical token exit-liquidity snapshots. Exact timestamp joins, no interpolation or current-depth substitution. Price observations receive a conservative one-bucket availability lag.
- Missing access, pagination gaps, missing prices or missing historical exit liquidity are disclosed and block performance. No synthetic replacement is made.
- Token age is verified only in the simulated universe; real token creation timestamps remain unknown, so positive age filters are rejected.

Official documentation was reviewed on 2026-09-29; details and supported schemas are in [docs/PROVIDERS.md](docs/PROVIDERS.md). **No provider credentials were available during implementation. No genuine Solana dataset is included, and authenticated live ingestion has not been verified.** Provider tests validate response handling against fixtures, not live coverage.

## What is included

- Next.js + TypeScript + Tailwind + Recharts research terminal with five routes.
- FastAPI + Pydantic REST API, SQLAlchemy models, Alembic migration, PostgreSQL configuration and tested SQLite fallback.
- Modular factors and strategy rule registry; event-driven execution/accounting; chronological validation; Markdown/JSON/CSV exports.
- Immutable datasets, saved strategies, configuration snapshots, persisted jobs/trades/reports and progress/error states.
- Deterministic fourteen-day, four-token, twelve-wallet simulation and automated regression tests.

See [ARCHITECTURE](docs/ARCHITECTURE.md), [API](docs/API.md), [METHODOLOGY](docs/METHODOLOGY.md), [LIMITATIONS](docs/LIMITATIONS.md), and [VERIFICATION](docs/VERIFICATION.md).

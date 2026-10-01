# REST API

Base URL: `http://localhost:8000`. Interactive schemas: `/docs`; machine-readable schema: `/openapi.json` and the included `docs/openapi.json`.

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | Status, engine version and credential-presence flags; never returns keys |
| GET | `/api/datasets` | Dataset metadata and completeness |
| POST | `/api/datasets` | Import a normalized immutable dataset; schema validation, REAL/SYNTHETIC required |
| GET | `/api/datasets/{id}` | Metadata, provenance and quality |
| GET | `/api/datasets/{id}/export` | Full normalized dataset |
| POST | `/api/ingestions/wallets` | Queue bounded Helius/Birdeye ingestion; returns `202` |
| GET | `/api/ingestions/{id}` | Ingestion status, progress, sanitized error and saved dataset |
| GET | `/api/strategies` | Saved research configurations |
| POST | `/api/strategies` | Create a strategy |
| PUT | `/api/strategies/{id}` | Update current config; previous runs keep their snapshots |
| POST | `/api/backtests` | Queue a strategy run; returns `202` |
| GET | `/api/backtests` | Latest 100 runs with summary metrics |
| GET | `/api/backtests/{id}` | Status/progress and full result once completed |
| GET | `/api/backtests/{id}/trades` | `segment`, `offset`, `limit` (1–500) |
| POST | `/api/backtests/{id}/report` | Idempotent Markdown report for a completed run |

Create and run:

```bash
curl -s http://localhost:8000/api/strategies \
  -H 'Content-Type: application/json' \
  -d '{"dataset_id":"synthetic-seed-33","config":{"min_wallet_count":3,"fee_bps":30}}'

# Substitute the returned strategy id:
curl -s http://localhost:8000/api/backtests \
  -H 'Content-Type: application/json' \
  -d '{"strategy_id":"RETURNED_STRATEGY_ID"}'
```

Poll the returned run ID until `completed` or `failed`. Progress is based on processed event count. Runs can fail honestly; errors do not return invented results.

Request historical ingestion only after configuring server environment keys:

```json
{
  "wallets": ["YOUR_VALID_SOLANA_WALLET_ADDRESS"],
  "start_ts": 1767225600,
  "end_ts": 1767312000,
  "max_pages": 20,
  "include_prices": true
}
```

Times are UTC Unix seconds aligned to five-minute boundaries. Inputs are bounded to 10 wallets, 14 days and 200 wallet-history pages. Ingestion may save an **incomplete REAL** dataset when market access fails. A missing Helius key returns `503` immediately; unsupported coverage never becomes synthetic.

## Normalized events

Market event:

```json
{"id":"source:token:timestamp","type":"market","ts":1767225600,"token":"MINT","price_usd":1.25,"liquidity_usd":200000,"volume_usd":null,"provider":"source"}
```

Swap event:

```json
{"id":"signature:wallet:mint:buy","type":"swap","ts":1767225600,"slot":123,"wallet":"WALLET","token":"MINT","side":"buy","quantity":100,"decimals":6,"execution_price_usd":null,"provider":"helius-enhanced-transactions"}
```

Top-level dataset fields are `id`, `name`, `kind`, `start_ts`, `end_ts`, `resolution_seconds`, `tokens`, `wallets`, `events`, `provenance` and `limitations`. See the bundled synthetic JSON for a complete example. Null unknowns remain null. Dataset identity collisions return `409`.

Authentication is optional for local use (`API_TOKEN`); if configured, pass `Authorization: Bearer TOKEN`. The frontend does not store server/API secrets and does not offer a token-entry flow. Put shared deployments behind a trusted authentication proxy or implement application-level sessions before exposing them. Docker binds the frontend/API to localhost by default.

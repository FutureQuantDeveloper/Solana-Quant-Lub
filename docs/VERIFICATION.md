# Verification record

Verified on 2026-09-29 with Python 3.12, Node.js 22 and Chrome in the build environment.

## Automated checks

- `cd backend && ../.venv/bin/python -m pytest -q`: **48 passed**. One upstream Starlette/AnyIO deprecation warning; no failures.
- `cd frontend && NEXT_PUBLIC_EXECUTION_MODE=api npm run build`: **passed**, including TypeScript checking and generation of all five product routes.
- Browser-mode static production build and `npm --prefix frontend run typecheck`: **passed**. The downloadable package contains this built frontend with its local Python runtime.
- `node scripts/check-wasm.mjs`: **passed**. The native and WebAssembly executions have identical dataset/config/engine fingerprints, matching trade counts and return/drawdown/cost values to absolute tolerance `1e-8`.
- Alembic initial migration and the complete FastAPI workflow ran against SQLite. API tests cover saved strategy snapshots, background execution, ordinary-request responsiveness during a running job, result/trade persistence, dataset export/replay, report generation, and incomplete-data rejection.
- Headless demo runner produced the committed configuration, full results and report in `data/reference_run/`.

The engine/provider suite covers swap normalization, raw decimal amounts, unsupported transfers, pagination/deduplication/backoff, factor thresholds, strict prior-time wallet eligibility, FIFO cost basis, chronological ordering, delayed execution, fees/slippage, capital reservations, insufficient liquidity, missing prices/liquidity, chronological holdout separation, undefined statistics, deterministic reproduction and future-data perturbation.

## Browser workflow

Manually exercised the actual Python Web Worker through the interface: load dataset, run reference strategy, inspect IS/OOS results, expand a trade's factor snapshot, edit assumptions and run another saved experiment. This caught and fixed browser UUID compatibility and HTML numeric-step validation issues.

Changing the trading fee from 30 to 100 bps per side, with the same remaining assumptions and all twelve wallets, changed OOS net return from approximately **−1.92% to −6.34%** and execution costs from **$319.68 to $761.04**. Both results had 32 closed trades. These are calculated **SYNTHETIC** results, not genuine market observations.

## Native reference result

Engine/config/dataset fingerprint:

`f9636bda5f8206dd50b61a4ced628ac5568c7e662595bb1c3eb7d166b140e01b`

| Metric | In sample | Out of sample |
| --- | ---: | ---: |
| Closed trades | 83 | 32 |
| Gross return | −4.5303% | +1.2818% |
| Net return | −12.7829% | −1.9150% |
| Execution costs | $825.26 | $319.68 |

Only three complete daily returns occur in the reference test period. Any annualized Sharpe from that period is highly uncertain. The simulation is a software demonstration and cannot establish alpha.

Fingerprints include the full configuration, including experiment names and the explicit wallet list. Selecting every wallet explicitly has the same economic behavior as the default empty list (all wallets), but a different configuration hash.

## Not verified

- Authenticated Helius or Birdeye calls: no credentials were available. Adapter tests use mocks and documented response schemas, not genuine retrieved observations.
- Docker Compose and PostgreSQL execution: Docker was unavailable. The tested local persistence path is SQLite.
- Production authentication, tenancy, distributed jobs and a broad mobile/browser matrix are outside this MVP's implemented boundary.

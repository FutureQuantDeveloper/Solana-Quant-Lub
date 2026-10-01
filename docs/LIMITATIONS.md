# Known limitations and next priorities

## Implemented boundary

The MVP implements one long-only Smart Money Accumulation entry rule with six configurable factors. All performance is event-driven. It is not a strategy optimizer, autonomous trader, or predictor. The included fourteen-day simulation exists to test the system, not establish alpha.

The hosted application is a browser-only synthetic workspace using the same Python engine as FastAPI. PostgreSQL persistence and real ingestion run in the downloadable local stack. No provider keys or real data were available for an authenticated integration smoke test. Docker/PostgreSQL execution was unavailable; those paths are supplied but not runtime verified. SQLite migrations and the full API flow were verified.

## Research limits

- Short sample, single chronological holdout, no significance testing, walk-forward optimization or multiple-hypothesis correction.
- Fixed supplied wallet/token universe may have selection/survivorship bias. No historical universe reconstruction.
- Gross observed FIFO wallet evidence; transfers, missing initial inventory, wallet-level costs and unsupported swaps are not reconstructed.
- Five-minute observations, discrete stops/targets, fixed per-side slippage, fixed network fee assumption and aggregate historical liquidity cap. No AMM reserve replay, venue routing, order book, MEV, chain failures, compute-unit dynamics, transfer fees or Token-2022 extensions.
- No shorts, margin, leverage, limit orders, portfolio optimization or automatic position sizing.
- Missing required data blocks an entire research dataset instead of providing subtly biased partial performance. A future valid-interval research mode needs its own methodology and tests.
- Current real ingestion intentionally does not verify token creation times. Age filtering on unknown dates is blocked.
- Sharpe ratios from a few daily observations are mathematically defined but highly uncertain; the interface states their sample size. No confidence interval is calculated.

## Engineering limits

- Single API process and bounded in-process worker pool. Restarted work is marked failed; there is no automatic resume or distributed queue.
- JSON result storage favors auditability over efficient large-scale analytics. Dataset limit: 250,000 events.
- Authentication/authorization, per-user tenancy and robust quotas are not implemented. Optional API bearer protection does not create a frontend login. Use localhost as configured.
- IndexedDB is browser-local. Browser jobs require the tab to stay open; the hosted URL is not a cached offline PWA.
- Floating point arithmetic is suitable for research fixtures, not exact on-chain settlement.

## Next development priorities

1. With provider credentials, ingest and validate a small genuine historical sample, reconcile transactions against an independent explorer, and verify actual plan-specific price/liquidity coverage.
2. Migrate the Helius legacy decoder to current Parsed Events; build a curated corpus of actual transaction fixtures and token-extension rules.
3. Add verified token-creation history, historical universe construction, robust wallet cost basis and token/pool-level execution models.
4. Add a durable worker queue, authentication/tenancy and atomic admission control before multi-user hosting.
5. Add locked holdouts, walk-forward windows, purging/embargo where factor labels require it, parameter search accounting and bootstrap uncertainty.
6. Run Docker Compose/PostgreSQL and a wider responsive/mobile browser matrix in CI.

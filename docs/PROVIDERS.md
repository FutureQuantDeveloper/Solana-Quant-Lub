# Provider verification

Reviewed against official documentation on **2026-09-29**. No Helius or Birdeye credentials were present; all adapter tests use fixtures. No real provider observations are shipped in the demo.

## Helius

Official references:

- https://www.helius.dev/docs/enhanced-transactions/transaction-history
- https://www.helius.dev/docs/api-reference/enhanced-transactions/gettransactionsbyaddress
- https://www.helius.dev/docs/enhanced-transactions/overview
- Official `helius-sdk` npm package, repository `https://github.com/helius-labs/helius-sdk`; legacy `1.5.2` `SwapEvent` / `TokenBalanceChange` types checked for event structure, and current `3.2.0` checked for history API types.

Implemented request: `GET https://mainnet.helius-rpc.com/v0/addresses/{wallet}/transactions`, with `api-key`, `gte-time`, `lte-time`, `before-signature`, `sort-order=desc`, `limit=100`, `token-accounts=balanceChanged` and `commitment=finalized`.

The current documentation marks Enhanced Transactions as legacy/maintenance mode and recommends the newer transaction/Parsed Events products for new integrations. The still-supported legacy endpoint is used here for a narrow explicit-swap MVP. Migration is a documented next step, not a claimed implemented feature.

All transaction types are retrieved; only explicit `type=SWAP` with unambiguous top-level `events.swap` economic legs for the selected wallet is parsed. We do not infer swaps from transfers or count inner route hops. Native amounts use 9 decimals; SPL amounts use supplied raw decimals. SOL/USDC/USDT quote values remain quote values, without assumed USD conversion. Unsupported records are counted. History is considered complete only when pagination reaches an empty response, not simply a short page.

## Birdeye

Official references:

- https://data.birdeye.so/docs/data-api/price-ohlcv/get-defi-history-price
- https://data.birdeye.so/docs/data-api/price-ohlcv/get-defi-v3-liquidity-history-token
- https://data.birdeye.so/docs/data-api/price-ohlcv

Price: `GET /defi/history_price`, using `address_type=token`, `type=5m`, `time_from`, `time_to` and `ui_amount_mode=raw`. The documented response has `data.items[].unixTime` and `value`. The adapter uses bounded chunks and checks gaps rather than assuming complete provider coverage. Scaled-UI tokens are rejected.

Liquidity: `GET /defi/v3/liquidity/history/token`, using `resolution=1m`, `time`, `direction=back`, `count=100`. Documentation lists historical support from 2024-01-01, with 1m/4h/1D snapshots. The adapter reads `unix_time` and `exit_liquidity_usd`, preserving total `liquidity_usd` separately. It pages backward, samples exact five-minute timestamps, and leaves missing values null.

Both use `X-API-KEY` and `x-chain=solana`. Actual entitlement, supported tokens, retention and missingness still require checking returned observations with the user's plan. Documentation support is not proof of successful retrieval.

## Availability assumptions

Price line-series bucket timing is not treated as an instantaneous executable quote. Each point is available to this research model one five-minute bucket later; its original timestamp is retained. Liquidity snapshot values represent historical candle-open observations. No current endpoint, price interpolation or missing-liquidity substitute is used. These are conservative coarse observations, not full exchange/AMM replay.

Provider errors are sanitized to avoid API keys embedded in URLs. Rate-limit and transient-server failures retry at most five times with bounded delays. Network access is never attempted in synthetic demo mode.

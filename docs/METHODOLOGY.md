# Research methodology

## Information set

Events are sorted by timestamp, market-before-swap type, slot and identity. A market snapshot is available at its declared timestamp. Wallet profitability is computed from observed matched FIFO acquisitions and sales with `sale_timestamp < signal_timestamp`. Same-timestamp sales cannot qualify a wallet. The engine never computes a final wallet leaderboard to choose historical wallets.

Selected wallet IDs define a fixed research universe. This does not cure selection or survivorship bias in the supplied universe. Wallet ROI is aggregate proceeds / matched cost − 1, before wallet-specific costs. Unmatched sells never count as free profit. In real datasets, missing executed USD prices are valued only from available lagged market marks, explicitly as a proxy. Stablecoin quotes are not assumed equal to USD.

## Factors

- **Accumulation:** count distinct eligible selected buyers in an inclusive trailing time window. Repeat buys add volume, not wallet count. Wallet eligibility is rechecked at each potential signal.
- **Profitability:** gross FIFO realized return and a minimum number of prior matched sale observations.
- **Volume:** USD value of those eligible wallet buys, not the token's entire market turnover.
- **Liquidity:** historical depth at the signal and execution observations. The real adapter uses historical `exit_liquidity_usd`; aggregate depth is not an executable venue quote.
- **Age:** signal time minus verified creation time. A positive filter is prohibited for unknown creation times.
- **Momentum:** available price relative to the last observed price at or before the lookback boundary. A threshold of −100 disables the filter; missing required momentum rejects the signal.

## Orders and accounting

There is at most one open or pending position per token. Signal-time cash checks reserve complete position budgets for pending orders. Entries execute at the first later market observation at or after `signal + entry_delay`. Even a zero delay cannot fill on the signal observation.

For budget B, proportional per-side fee f, fixed per-side fee F, adverse slippage s and entry mark P:

```text
entry_notional = (B - F) / (1 + f)
entry_price   = P * (1 + s)
quantity      = entry_notional / entry_price
entry_fee     = entry_notional * f + F
cash          = cash - B
exit_price    = exit_mark * (1 - s)
exit_proceeds = quantity * exit_price
exit_fee      = exit_proceeds * f + F
cash          = cash + exit_proceeds - exit_fee
net_PnL       = exit_proceeds - exit_fee - B
gross_PnL     = quantity * (exit_mark - entry_mark)
total_costs   = gross_PnL - net_PnL
```

The liquidity participation cap is checked again at each fill. A failed entry is logged and canceled. Failed exits remain open and retry on later observations. Stops/targets are observed using the current mark versus the entry fill, then execute on the next market observation, allowing adverse gaps. A known holding deadline executes on the first eligible observation. Segment-end liquidation uses the final known scheduled observation. Inability to liquidate blocks that segment's performance metrics.

Equity is cash plus open quantity at current market marks. Marked equity does not pre-charge hypothetical exit fees; those are charged on closing. Gross equity uses the same actual position quantities/timing, removing costs, rather than a separate zero-cost strategy with different sizing.

## Chronological validation

Warmup is excluded from trading and used to accumulate past wallet evidence. The remaining time grid splits chronologically by the configured training fraction. The in-sample segment ends one observation before test begins. Each segment starts with the same fresh initial capital and liquidates at its end. Pending orders and rolling accumulation do not cross the boundary. Previously observed wallet information may be reused in the test period because it is already public at that time.

There is no automatic parameter fitting. The split is an evaluation protocol, not proof of unbiased model selection. Repeatedly examining and tuning on the holdout invalidates its interpretation as unseen evidence. Walk-forward nested validation and multiple-testing correction are not implemented.

## Metrics and limitations

- Net/gross returns: ending portfolio value / initial capital − 1.
- Maximum drawdown: largest decline from the preceding net marked-equity peak.
- Win rate: proportion of completed trades with strictly positive net P&L; zero-return trades are not wins.
- Average trade return: arithmetic mean of net P&L / original position budget.
- Profit factor: summed positive net P&L / absolute summed negative net P&L. No losses means undefined, not fabricated infinity.
- Sharpe: mean complete UTC daily return / sample standard deviation × √365, with zero risk-free rate. At least two daily returns and positive variance are required. A final partial day is excluded; short samples carry an explicit warning.
- Zero trades: portfolio return can be zero; win rate, average trade return and profit factor remain undefined. No NaN/Infinity is serialized.

Missing required market bars, prices, liquidity or incomplete wallet paging blocks a run before performance calculations. None are forward-filled. The engine is intended for small curated datasets; there is a 250,000-event limit. Numerical accounting uses double precision with test tolerances, not settlement-grade fixed-point arithmetic.

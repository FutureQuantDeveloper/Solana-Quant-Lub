# SOLANA QUANT RESEARCH LAB

**SYNTHETIC DATA — Accumulation research · 14-day simulation**

## Hypothesis
When multiple previously profitable wallets accumulate a token, subsequent returns may exceed execution costs.

## Dataset and provenance
Dataset ID: `synthetic-seed-33`
```json
{
  "provider": "deterministic-simulator",
  "generator_version": "1.0.0",
  "seed": 33,
  "retrieved_at": null,
  "generated_at": "2026-01-01T00:00:00Z (fixed scenario metadata)",
  "coverage": "14 synthetic days; 5-minute market snapshots",
  "price_unit": "simulated USD",
  "liquidity_source": "simulated historical snapshots"
}
```

## Evaluation
Chronological split: 2026-01-11T02:25:00+00:00. Separate initial capital in each segment. No positions or accumulation windows cross the boundary.

| Metric | In sample | Out of sample |
|---|---:|---:|
| Net return (%) | -12.782860 | -1.915024 |
| Gross return (%) | -4.530310 | 1.281806 |
| Closed trades | 83 | 32 |
| Win rate (%) | 33.734940 | 46.875000 |
| Maximum drawdown (%) | 12.782860 | 2.500127 |
| Daily Sharpe (annualized √365) | -47.976883 | -6.195321 |
| Average trade return (%) | -1.540104 | -0.598445 |
| Profit factor | 0.248104 | 0.662088 |
| Execution costs (USD) | 825.255021 | 319.683009 |

## Warnings
- in_sample: Only 8 complete daily returns. Any annualized Sharpe is highly uncertain.
- out_of_sample: Only 3 complete daily returns. Any annualized Sharpe is highly uncertain.

## Configuration
```json
{
  "strategy_type": "smart_money_accumulation",
  "name": "Smart Money Accumulation",
  "hypothesis": "When multiple previously profitable wallets accumulate a token, subsequent returns may exceed execution costs.",
  "wallet_ids": [],
  "min_wallet_count": 3,
  "accumulation_minutes": 30,
  "min_wallet_return_pct": 0.0,
  "min_closed_trades": 2,
  "min_volume_usd": 0.0,
  "min_liquidity_usd": 100000.0,
  "min_token_age_hours": 0.0,
  "min_momentum_pct": -100.0,
  "momentum_minutes": 60,
  "entry_delay_minutes": 5,
  "position_size_usd": 1000.0,
  "initial_capital_usd": 10000.0,
  "holding_minutes": 120,
  "take_profit_pct": 8.0,
  "stop_loss_pct": 5.0,
  "fee_bps": 30.0,
  "slippage_bps": 20.0,
  "fixed_fee_usd": 0.01,
  "max_liquidity_participation_pct": 1.0,
  "train_fraction": 0.7,
  "warmup_hours": 24
}
```

## Assumptions and limitations
- SYNTHETIC DATA: every price, wallet, liquidity observation and transaction is simulated. Returns are not evidence of real Solana alpha.
- Four simulated tokens and twelve wallets are an engineering test universe, not a representative market sample.
- Five-minute observations do not reproduce intrabar execution or sub-minute accumulation.
- Wallet profitability is gross FIFO performance of observed matched lots only; transfer-in inventory, unseen wallets and wallet-level costs are not inferred.
- Fixed slippage and liquidity participation are assumptions, not order-book or AMM execution replay; no MEV, rug-pull or failed-chain-transaction model.
- Signals use only prior information. Stop and target observations execute on the NEXT market observation; holding deadlines execute on the first eligible observation.
- Each chronological segment starts with fresh capital and liquidates at its own end. Historical wallet evidence may warm up the test segment; positions and accumulation windows do not cross the split.
- Gross performance uses the same executed quantities and trade timings, with costs removed; it is not a separately re-sized zero-cost portfolio.
- Changing parameters after inspecting the test period contaminates that holdout. This app does not perform statistical significance testing or automatic model fitting.
- Equity uses current market marks. Fees and slippage are paid on both sides. Position budgets include entry fees; pending orders reserve cash.
- Daily Sharpe uses complete UTC daily close-to-close returns, sample standard deviation, zero risk-free rate and 365-day annualization. Undefined metrics are not zero.

## Reproducibility
Engine: `1.0.0`
Dataset SHA-256: `d1472d81d69983de87dad530d89bf0e1f108552086da79719cae74f71d09107d`
Run fingerprint: `f9636bda5f8206dd50b61a4ced628ac5568c7e662595bb1c3eb7d166b140e01b`
Export the result JSON to preserve every equity observation, trade, factor snapshot, skipped execution and exact configuration.

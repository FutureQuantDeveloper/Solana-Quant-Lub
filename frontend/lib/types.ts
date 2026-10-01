export type Config = {
  strategy_type: string;
  name: string; hypothesis: string; wallet_ids: string[];
  min_wallet_count: number; accumulation_minutes: number; min_wallet_return_pct: number; min_closed_trades: number;
  min_volume_usd: number; min_liquidity_usd: number; min_token_age_hours: number; min_momentum_pct: number; momentum_minutes: number;
  entry_delay_minutes: number; position_size_usd: number; initial_capital_usd: number; holding_minutes: number;
  take_profit_pct: number; stop_loss_pct: number; fee_bps: number; slippage_bps: number; fixed_fee_usd: number;
  max_liquidity_participation_pct: number; train_fraction: number; warmup_hours: number;
};
export type Quality = {performance_ready: boolean; issues: string[]; market_observations: number; swap_events: number; price_coverage_pct: number; liquidity_coverage_pct: number; missing_bars: number; verified_token_ages: number};
export type Dataset = {id: string; name: string; kind: "REAL"|"SYNTHETIC"; start_ts: number; end_ts: number; resolution_seconds: number; wallets: string[]; tokens: {mint: string; symbol: string; created_at?: number}[]; quality: Quality; content_hash: string; provenance: Record<string, unknown>; limitations: string[]; events?: Record<string,unknown>[]};
export type Strategy = {id: string; dataset_id: string; name: string; config: Config; created_at: string};
export type Metrics = {net_return_pct: number|null; gross_return_pct: number|null; trade_count: number; win_rate_pct: number|null; max_drawdown_pct: number|null; sharpe: number|null; sharpe_observations: number; sharpe_reason: string|null; average_trade_return_pct: number|null; profit_factor: number|null; profit_factor_reason?: string; costs_usd: number|null; ending_equity_usd: number|null};
export type Point = {ts: number; net_equity: number; gross_equity: number; drawdown_pct: number; cash: number; open_positions: number; reserved_cash: number};
export type Trade = {id: string; segment: string; token: string; signal_ts: number; entry_ts: number; exit_ts: number; entry_price: number; exit_price: number; quantity: number; budget_usd: number; net_pnl_usd: number; gross_pnl_usd: number; costs_usd: number; entry_fee_usd: number; exit_fee_usd: number; return_pct: number; reason: string; factors: Record<string, unknown>};
export type Segment = {label: string; start_ts: number; end_ts: number; valid: boolean; metrics: Metrics; equity_curve: Point[]; trades: Trade[]; skipped: {ts: number; token: string; reason: string; detail: string}[]; signals: {ts: number;token: string;factors: Record<string,unknown>}[]; warnings: string[]};
export type Result = {engine_version: string; fingerprint: string; dataset_hash: string; dataset_id: string; dataset_kind: "REAL"|"SYNTHETIC"; dataset_name: string; config: Config; split_ts: number; quality: Quality; provenance: Record<string,unknown>; limitations: string[]; in_sample: Segment; out_of_sample: Segment};
export type Run = {id: string; strategy_id: string; dataset_id: string; status: "queued"|"running"|"completed"|"failed"; progress: number; config: Config; error: string|null; created_at: string; result?: Result; summary?: {dataset_kind: string; fingerprint: string; in_sample: Metrics; out_of_sample: Metrics}};

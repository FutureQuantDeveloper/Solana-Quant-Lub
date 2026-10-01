"""Event-driven long-only engine. Standard library only; also runs inside Pyodide."""
from collections import defaultdict
import hashlib
import itertools
import json

from .domain import StrategyConfig, ResearchDataError
from .factors import FactorState
from .strategies import STRATEGY_REGISTRY
from .metrics import calculate_metrics
from .quality import assess

ENGINE_VERSION = "1.0.0"


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def simulate(dataset, config, start, end, label, progress=None):
    events = sorted((e for e in dataset["events"] if e["ts"] <= end), key=lambda e: (e["ts"], 0 if e["type"] == "market" else 1, e.get("slot") or 0, e["id"]))
    state = FactorState(config, dataset["tokens"])
    strategy = STRATEGY_REGISTRY[config.strategy_type]
    markets, positions, pending = {}, {}, {}
    trades, skipped, curve, signals = [], [], [], []
    cash = peak = config.initial_capital_usd
    gross_realized = 0.0
    step = dataset["resolution_seconds"]
    fee, slip = config.fee_bps / 10000, config.slippage_bps / 10000
    participation = config.max_liquidity_participation_pct / 100
    audit_seen = set()
    processed = 0

    def skip(ts, token, reason, detail, signal_ts=None):
        key = (ts, token, reason, signal_ts)
        if key not in audit_seen:
            skipped.append({"ts": ts, "token": token, "reason": reason, "detail": detail, "signal_ts": signal_ts})
            audit_seen.add(key)

    for ts, grouped in itertools.groupby(events, key=lambda e: e["ts"]):
        batch = list(grouped)
        bars = [e for e in batch if e["type"] == "market"]
        for event in bars:
            markets[event["token"]] = event
            state.market(event)
        active = start <= ts <= end
        if active:
            for event in bars:
                token, mid = event["token"], event["price_usd"]
                position = positions.get(token)
                if position:
                    boundary = ts == end
                    timed = ts >= position["entry_ts"] + config.holding_minutes * 60
                    delayed_exit = position.get("exit_due") is not None and ts > position["exit_due"]
                    if boundary or timed or delayed_exit:
                        reason = "segment_end" if boundary else position.get("exit_reason", "holding_period")
                        if position["quantity"] * mid > event["liquidity_usd"] * participation:
                            skip(ts, token, "exit_liquidity", "Exit exceeds the configured historical-liquidity participation cap")
                        else:
                            exit_price = mid * (1 - slip)
                            proceeds = position["quantity"] * exit_price
                            exit_fee = proceeds * fee + config.fixed_fee_usd
                            cash += proceeds - exit_fee
                            gross_pnl = position["quantity"] * (mid - position["entry_mid"])
                            net_pnl = proceeds - exit_fee - position["budget"]
                            gross_realized += gross_pnl
                            trades.append({"id": f"{label}-{len(trades)+1:04d}", "segment": label, "token": token,
                                "signal_ts": position["signal_ts"], "entry_ts": position["entry_ts"], "exit_ts": ts,
                                "entry_mid": position["entry_mid"], "exit_mid": mid,
                                "entry_price": position["entry_price"], "exit_price": exit_price,
                                "quantity": position["quantity"], "budget_usd": position["budget"],
                                "net_pnl_usd": net_pnl, "gross_pnl_usd": gross_pnl,
                                "costs_usd": gross_pnl - net_pnl, "entry_fee_usd": position["entry_fee"], "exit_fee_usd": exit_fee,
                                "return_pct": net_pnl / position["budget"] * 100, "reason": reason, "factors": position["factors"]})
                            del positions[token]
                    elif position.get("exit_due") is None:
                        move = (mid / position["entry_price"] - 1) * 100
                        if move >= config.take_profit_pct or move <= -config.stop_loss_pct:
                            position["exit_due"] = ts
                            position["exit_reason"] = "take_profit" if move >= config.take_profit_pct else "stop_loss"
                order = pending.get(token)
                if order and ts >= order["due"] and ts > order["signal_ts"]:
                    del pending[token]
                    if ts >= end:
                        skip(ts, token, "segment_boundary", "No new position on the segment's liquidation bar", order["signal_ts"])
                        continue
                    budget = config.position_size_usd
                    if ts - order["due"] > step * 2:
                        skip(ts, token, "expired_entry", "No timely executable market observation", order["signal_ts"])
                    elif cash + 1e-8 < budget:
                        skip(ts, token, "insufficient_cash", "Available cash cannot fund entry and its fees", order["signal_ts"])
                    elif budget > event["liquidity_usd"] * participation or event["liquidity_usd"] < config.min_liquidity_usd:
                        skip(ts, token, "entry_liquidity", "Entry fails historical liquidity or participation limits", order["signal_ts"])
                    else:
                        notional = (budget - config.fixed_fee_usd) / (1 + fee)
                        entry_price = mid * (1 + slip)
                        entry_fee = notional * fee + config.fixed_fee_usd
                        positions[token] = {"entry_ts": ts, "entry_mid": mid, "entry_price": entry_price,
                            "quantity": notional / entry_price, "budget": budget, "entry_fee": entry_fee,
                            "signal_ts": order["signal_ts"], "factors": order["factors"]}
                        cash -= budget
            for event in batch:
                if event["type"] != "swap":
                    continue
                token = event["token"]
                market = markets.get(token)
                if not market or ts - market["ts"] > step:
                    skip(ts, token, "missing_price", "No contemporaneous or prior non-stale market price")
                    continue
                snapshot = state.on_swap(event, market, allow_accumulation=ts < end)
                if snapshot and strategy.should_enter(config, snapshot) and ts < end:
                    if token in positions or token in pending:
                        continue
                    reserved = len(pending) * config.position_size_usd
                    if cash - reserved + 1e-8 < config.position_size_usd:
                        skip(ts, token, "insufficient_cash", "Cash is already invested or reserved for pending orders", ts)
                        continue
                    signal = {"ts": ts, "token": token, "factors": snapshot}
                    signals.append(signal)
                    pending[token] = {"signal_ts": ts, "due": ts + config.entry_delay_minutes * 60, "factors": snapshot}
        else:
            for event in batch:
                if event["type"] == "swap":
                    market = markets.get(event["token"])
                    if market and ts - market["ts"] <= step:
                        state.on_swap(event, market, allow_accumulation=False)
        if active and bars:
            marked = sum(p["quantity"] * markets[t]["price_usd"] for t, p in positions.items())
            equity = cash + marked
            gross_equity = config.initial_capital_usd + gross_realized + sum(p["quantity"] * (markets[t]["price_usd"] - p["entry_mid"]) for t, p in positions.items())
            peak = max(peak, equity)
            curve.append({"ts": ts, "net_equity": equity, "gross_equity": gross_equity,
                "drawdown_pct": (equity / peak - 1) * 100, "cash": cash, "open_positions": len(positions), "reserved_cash": len(pending) * config.position_size_usd})
        processed += len(batch)
        if progress and processed % 500 < len(batch):
            progress(min(99, int(processed / max(1, len(events)) * 100)))
    for token, order in pending.items():
        skip(end, token, "unfilled_entry", "Entry delay extends beyond this evaluation segment", order["signal_ts"])
    if positions:
        skip(end, "portfolio", "unclosed_positions", "Unable to liquidate every position; performance metrics are withheld")
    valid = not positions
    metrics = calculate_metrics(curve, trades, config.initial_capital_usd, valid)
    warnings = []
    if len(trades) < 30:
        warnings.append(f"Only {len(trades)} closed trades. The sample is too small for reliable conclusions.")
    if metrics["sharpe_observations"] < 20:
        warnings.append(f"Only {metrics['sharpe_observations']} complete daily returns. Any annualized Sharpe is highly uncertain.")
    if not valid:
        warnings.append("Performance calculations blocked: open positions could not be valued as completed trades.")
    return {"label": label, "start_ts": start, "end_ts": end, "valid": valid, "metrics": metrics,
        "equity_curve": curve, "trades": trades, "skipped": skipped, "signals": signals, "warnings": warnings}


def run_backtest(dataset, config_dict, progress=None):
    c = StrategyConfig.from_dict(config_dict)
    quality = assess(dataset)
    if not quality["performance_ready"]:
        raise ResearchDataError("Performance blocked: " + "; ".join(quality["issues"]))
    if len(dataset["events"]) > 250000:
        raise ResearchDataError("MVP limit: 250,000 events per research dataset")
    step = dataset["resolution_seconds"]
    first = dataset["start_ts"] + c.warmup_hours * 3600
    first = dataset["start_ts"] + ((first - dataset["start_ts"] + step - 1) // step) * step
    end = dataset["end_ts"]
    count = (end - first) // step + 1
    if count < 8:
        raise ResearchDataError("Not enough observations remain after warmup for two evaluation segments")
    split = first + int(count * c.train_fraction) * step
    if c.wallet_ids and any(w not in dataset["wallets"] for w in c.wallet_ids):
        raise ResearchDataError("Selected wallet does not exist in this dataset")
    if c.min_token_age_hours > 0 and any(t.get("created_at") is None for t in dataset["tokens"]):
        raise ResearchDataError("Token-age filtering requires verified creation times for every token")
    results = {}
    for index, (name, a, b) in enumerate((("in_sample", first, split-step), ("out_of_sample", split, end))):
        results[name] = simulate(dataset, c, a, b, name, (lambda pct: progress(index * 50 + pct // 2)) if progress else None)
    fingerprint = digest({"engine": ENGINE_VERSION, "dataset": digest(dataset), "config": c.to_dict()})
    result = {"engine_version": ENGINE_VERSION, "fingerprint": fingerprint, "dataset_hash": digest(dataset),
        "dataset_id": dataset["id"], "dataset_kind": dataset["kind"], "dataset_name": dataset["name"],
        "config": c.to_dict(), "split_ts": split, "quality": quality, "provenance": dataset["provenance"],
        "limitations": dataset.get("limitations", []) + [
            "Wallet profitability is gross FIFO performance of observed matched lots only; transfer-in inventory, unseen wallets and wallet-level costs are not inferred.",
            "Fixed slippage and liquidity participation are assumptions, not order-book or AMM execution replay; no MEV, rug-pull or failed-chain-transaction model.",
            "Signals use only prior information. Stop and target observations execute on the NEXT market observation; holding deadlines execute on the first eligible observation.",
            "Each chronological segment starts with fresh capital and liquidates at its own end. Historical wallet evidence may warm up the test segment; positions and accumulation windows do not cross the split.",
            "Gross performance uses the same executed quantities and trade timings, with costs removed; it is not a separately re-sized zero-cost portfolio.",
            "Changing parameters after inspecting the test period contaminates that holdout. This app does not perform statistical significance testing or automatic model fitting."
        ], **results}
    if progress:
        progress(100)
    return result

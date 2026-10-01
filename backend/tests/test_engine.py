from copy import deepcopy
import json
import random
import pytest
from app.demo import generate_demo
from app.domain import StrategyConfig, ResearchDataError
from app.engine import run_backtest, simulate
from app.factors import WalletLedger, FactorState, passes
from app.metrics import calculate_metrics
from app.quality import assess


def fixture_dataset():
    prices = [100, 110, 105, 100, 110, 120, 115, 118, 116, 120, 120, 120, 120]
    events = [{"id": f"bar-{i}", "type": "market", "token": "T", "ts": i*300, "price_usd": p, "liquidity_usd": 1_000_000} for i, p in enumerate(prices)]
    for i, side in ((0, "buy"), (1, "sell"), (2, "buy")):
        events.append({"id": f"swap-{i}", "type": "swap", "ts": i*300, "wallet": "W", "token": "T", "side": side, "quantity": 10, "execution_price_usd": prices[i]})
    return {"id": "fixture", "name": "SYNTHETIC fixture", "kind": "SYNTHETIC", "start_ts": 0, "end_ts": 3600, "resolution_seconds": 300, "tokens": [{"mint": "T", "symbol": "TEST", "created_at": -86400}], "wallets": ["W"], "events": events, "provenance": {"provider": "test"}}


def config(**overrides):
    return StrategyConfig.from_dict({"min_wallet_count": 1, "min_closed_trades": 1, "min_liquidity_usd": 1000, "holding_minutes": 10, "take_profit_pct": 90, "fee_bps": 0, "slippage_bps": 0, "fixed_fee_usd": 0, **overrides})


def test_entry_follows_signal_and_holding_clock():
    r = simulate(fixture_dataset(), config(), 600, 3000, "test")
    t = r["trades"][0]
    assert (t["signal_ts"], t["entry_ts"], t["exit_ts"]) == (600, 900, 1500)
    assert t["net_pnl_usd"] == pytest.approx(200)


def test_zero_delay_still_waits_for_later_observation():
    t = simulate(fixture_dataset(), config(entry_delay_minutes=0), 600, 3000, "test")["trades"][0]
    assert t["entry_ts"] > t["signal_ts"]


def test_exact_fees_and_slippage_on_both_sides():
    r = simulate(fixture_dataset(), config(fee_bps=100, slippage_bps=200, fixed_fee_usd=1), 600, 3000, "test")
    t = r["trades"][0]
    q = ((1000 - 1) / 1.01) / 102
    proceeds = q * 120 * 0.98
    expected = proceeds * 0.99 - 1 - 1000
    assert t["net_pnl_usd"] == pytest.approx(expected)
    assert t["gross_pnl_usd"] == pytest.approx(q * 20)
    assert t["costs_usd"] == pytest.approx(t["gross_pnl_usd"] - expected)
    assert r["equity_curve"][-1]["net_equity"] == pytest.approx(10000 + expected)


def test_stop_observation_executes_next_bar():
    d = fixture_dataset()
    d["events"][4]["price_usd"] = 80
    d["events"][5]["price_usd"] = 70
    t = simulate(d, config(holding_minutes=100, stop_loss_pct=5), 600, 3000, "test")["trades"][0]
    assert t["exit_ts"] == 1500
    assert t["exit_price"] == 70  # Does not fill at the stop threshold or triggering close.
    assert t["reason"] == "stop_loss"


def test_take_profit_executes_next_bar():
    t = simulate(fixture_dataset(), config(holding_minutes=100, take_profit_pct=5), 600, 3000, "test")["trades"][0]
    assert t["exit_ts"] == 1500 and t["reason"] == "take_profit"


def test_chronological_sorting_independent_of_input_order():
    d = fixture_dataset()
    reference = simulate(d, config(), 600, 3000, "test")
    random.Random(19).shuffle(d["events"])
    assert simulate(d, config(), 600, 3000, "test") == reference


def test_future_wallet_profit_cannot_create_past_signal():
    d = fixture_dataset()
    for e in d["events"]:
        if e["id"] == "swap-1":
            e["execution_price_usd"] = 50
    d["events"].append({"id": "future-sale", "type": "swap", "ts": 2400, "wallet": "W", "token": "T", "side": "sell", "quantity": 10, "execution_price_usd": 10000})
    r = simulate(d, config(), 600, 3000, "test")
    assert r["signals"] == [] and r["trades"] == []


def test_same_timestamp_sale_is_not_prior_profitability():
    ledger = WalletLedger()
    ledger.observe({"wallet": "W", "token": "T", "ts": 0, "side": "buy", "quantity": 1}, 1)
    ledger.observe({"wallet": "W", "token": "T", "ts": 100, "side": "sell", "quantity": 1}, 2)
    assert ledger.score("W", 100)["closed_trades"] == 0
    assert ledger.score("W", 101)["return_pct"] == 100


def test_unmatched_wallet_sales_are_not_free_profit():
    ledger = WalletLedger()
    ledger.observe({"wallet": "W", "token": "T", "ts": 0, "side": "sell", "quantity": 100}, 200)
    assert ledger.score("W", 1)["return_pct"] is None


def test_wallet_fifo_partial_lots():
    ledger = WalletLedger()
    for side, qty, price, ts in (("buy", 2, 10, 1), ("buy", 2, 20, 2), ("sell", 3, 30, 3)):
        ledger.observe({"wallet": "W", "token": "T", "ts": ts, "side": side, "quantity": qty}, price)
    assert ledger.score("W", 4)["return_pct"] == pytest.approx(125)
    assert list(ledger.lots[("W", "T")]) == [[1, 20]]


def test_factor_unique_wallets_and_rolling_expiry():
    c = config(accumulation_minutes=5)
    s = FactorState(c, [{"mint": "T", "created_at": 0}])
    s.ledger.closed["W"] = [(0, 100, 110)]
    market = {"price_usd": 10, "liquidity_usd": 100000}
    def buy(ts):
        return s.on_swap({"wallet": "W", "token": "T", "ts": ts, "side": "buy", "quantity": 2}, market)
    buy(100)
    snap = buy(200)
    assert snap["wallet_count"] == 1 and snap["volume_usd"] == 40
    assert buy(600)["volume_usd"] == 20


def test_factor_thresholds_are_connected():
    snapshot = {"wallet_count": 3, "volume_usd": 200, "liquidity_usd": 200000, "momentum_pct": 2, "token_age_hours": 3}
    assert passes(config(), snapshot)
    assert not passes(config(min_volume_usd=201), snapshot)
    assert not passes(config(min_token_age_hours=4), snapshot)
    assert not passes(config(min_momentum_pct=3), snapshot)
    assert not passes(config(min_wallet_count=4), snapshot)


def test_pending_orders_cannot_overspend_capital():
    d = fixture_dataset()
    copied = deepcopy(d["events"])
    for e in copied:
        e["id"] += "-T2"
        e["token"] = "T2"
    d["tokens"].append({"mint": "T2", "symbol": "T2", "created_at": -86400})
    d["events"].extend(copied)
    r = simulate(d, config(initial_capital_usd=1000, position_size_usd=1000), 600, 3000, "test")
    assert len(r["trades"]) == 1
    assert any(s["reason"] == "insufficient_cash" for s in r["skipped"])
    assert all(p["cash"] >= -1e-8 and p["reserved_cash"] <= p["cash"] + 1e-8 for p in r["equity_curve"])


def test_insufficient_entry_liquidity_is_audited():
    d = fixture_dataset()
    d["events"][3]["liquidity_usd"] = 100
    r = simulate(d, config(), 600, 3000, "test")
    assert not r["trades"]
    assert any(s["reason"] == "entry_liquidity" for s in r["skipped"])


def test_impossible_exit_withholds_metrics():
    d = fixture_dataset()
    for e in d["events"]:
        if e["type"] == "market" and e["ts"] >= 1500:
            e["liquidity_usd"] = 1
    r = simulate(d, config(), 600, 3000, "test")
    assert not r["valid"] and r["metrics"]["net_return_pct"] is None


@pytest.mark.parametrize("field", ["price_usd", "liquidity_usd"])
def test_missing_market_data_blocks_performance(field):
    d = generate_demo(days=3)
    next(e for e in d["events"] if e["type"] == "market")[field] = None
    assert not assess(d)["performance_ready"]
    with pytest.raises(ResearchDataError, match="Performance blocked"):
        run_backtest(d, {})


def test_missing_bar_and_duplicate_ids_detected():
    d = fixture_dataset()
    d["events"].pop(4)
    assert assess(d)["missing_bars"] == 1
    d = fixture_dataset()
    d["events"].append(d["events"][0])
    assert not assess(d)["performance_ready"]


def test_zero_trades_and_undefined_metrics():
    r = simulate(fixture_dataset(), config(min_wallet_count=9), 600, 3000, "test")
    m = r["metrics"]
    assert m["trade_count"] == 0 and m["net_return_pct"] == 0
    assert m["win_rate_pct"] is None and m["sharpe"] is None and m["profit_factor"] is None
    json.dumps(r, allow_nan=False)


def test_train_test_no_position_or_cash_leakage():
    r = run_backtest(generate_demo(days=5), {})
    a, b = r["in_sample"], r["out_of_sample"]
    assert a["end_ts"] < b["start_ts"]
    assert all(t["exit_ts"] <= a["end_ts"] for t in a["trades"])
    assert all(t["signal_ts"] >= b["start_ts"] for t in b["trades"])
    assert a["equity_curve"][-1]["open_positions"] == 0
    assert b["equity_curve"][0]["net_equity"] == 10000


def test_reproducibility_and_future_price_invariance():
    d = generate_demo(days=4)
    r = run_backtest(d, {})
    assert run_backtest(d, {}) == r
    changed = deepcopy(d)
    for e in changed["events"]:
        if e["ts"] >= r["split_ts"]:
            if e["type"] == "market":
                e["price_usd"] *= 2
            elif e.get("execution_price_usd"):
                e["execution_price_usd"] *= 2
    second = run_backtest(changed, {})
    assert second["in_sample"] == r["in_sample"]


@pytest.mark.parametrize("override", [{"fee_bps": -1}, {"slippage_bps": float("nan")}, {"min_wallet_count": 1.5}, {"python": "print(1)"}, {"train_fraction": 1}, {"position_size_usd": 20000}])
def test_invalid_controls_rejected(override):
    with pytest.raises(ValueError):
        StrategyConfig.from_dict(override)


def test_sharpe_uses_daily_returns_not_intrabar_samples():
    curve = [{"ts": i*86400, "net_equity": e, "gross_equity": e, "drawdown_pct": 0} for i, e in enumerate([100, 101, 103, 104, 106])]
    m = calculate_metrics(curve, [], 100)
    assert m["sharpe_observations"] == 3 and m["sharpe"] is not None

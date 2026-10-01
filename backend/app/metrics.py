"""USD returns; 24/7 daily Sharpe, zero risk-free rate, sample standard deviation."""
import math
import statistics


def calculate_metrics(curve, trades, initial, valid=True):
    if not curve or not valid:
        return {k: None for k in ("total_return_pct", "net_return_pct", "gross_return_pct", "win_rate_pct", "max_drawdown_pct", "sharpe", "average_trade_return_pct", "profit_factor", "costs_usd", "ending_equity_usd")} | {"trade_count": len(trades), "sharpe_observations": 0, "sharpe_reason": "Incomplete valuation or unclosed positions"}
    net = (curve[-1]["net_equity"] / initial - 1) * 100
    gross = (curve[-1]["gross_equity"] / initial - 1) * 100
    pnls = [t["net_pnl_usd"] for t in trades]
    wins, losses = sum(p for p in pnls if p > 0), -sum(p for p in pnls if p < 0)
    # Complete UTC days only. Intraday observations are NOT independent daily returns.
    closes = {}
    for row in curve:
        closes[row["ts"] // 86400] = row["net_equity"]
    first_day, last_day = curve[0]["ts"] // 86400, curve[-1]["ts"] // 86400
    returns = []
    for day in sorted(closes):
        if first_day < day < last_day and day - 1 in closes and closes[day - 1] > 0:
            returns.append(closes[day] / closes[day - 1] - 1)
    sd = statistics.stdev(returns) if len(returns) >= 2 else 0.0
    sharpe = statistics.mean(returns) / sd * math.sqrt(365) if sd > 1e-12 else None
    reason = None if sharpe is not None else ("Fewer than two complete daily returns" if len(returns) < 2 else "Zero daily return variance")
    return {"total_return_pct": gross, "net_return_pct": net, "gross_return_pct": gross,
        "win_rate_pct": sum(p > 0 for p in pnls) / len(pnls) * 100 if pnls else None,
        "max_drawdown_pct": max(-r["drawdown_pct"] for r in curve), "sharpe": sharpe,
        "sharpe_observations": len(returns), "sharpe_reason": reason, "trade_count": len(trades),
        "average_trade_return_pct": statistics.mean(t["return_pct"] for t in trades) if trades else None,
        "profit_factor": wins / losses if losses > 1e-10 else None,
        "profit_factor_reason": None if losses > 1e-10 else "No losing trades; ratio undefined",
        "costs_usd": sum(t["costs_usd"] for t in trades), "ending_equity_usd": curve[-1]["net_equity"]}

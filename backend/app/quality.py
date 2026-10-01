import math


def positive(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value > 0


def assess(dataset):
    events = dataset.get("events", [])
    markets = [e for e in events if e.get("type") == "market"]
    swaps = [e for e in events if e.get("type") == "swap"]
    tokens = [t["mint"] for t in dataset.get("tokens", [])]
    start, end, step = dataset.get("start_ts", 0), dataset.get("end_ts", 0), dataset.get("resolution_seconds", 300)
    issues = []
    if not isinstance(step, int) or step < 1 or end <= start or (end - start) / max(step, 1) > 250000:
        return {"performance_ready": False, "issues": ["Invalid or excessive historical coverage"], "market_observations": len(markets), "swap_events": len(swaps), "price_coverage_pct": 0, "liquidity_coverage_pct": 0, "missing_bars": 0}
    expected = set(range(start, end + 1, step))
    present = {(m["token"], m["ts"]) for m in markets}
    missing_bars = sum(len(expected - {ts for token, ts in present if token == t}) for t in tokens)
    missing_prices = sum(not positive(m.get("price_usd")) for m in markets)
    missing_liquidity = sum(not positive(m.get("liquidity_usd")) for m in markets)
    total_expected = len(expected) * len(tokens)
    if not tokens or not markets:
        issues.append("No historical market observations")
    if missing_bars:
        issues.append(f"{missing_bars} required historical market bars are missing")
    if missing_prices:
        issues.append(f"{missing_prices} observations have missing or invalid prices")
    if missing_liquidity:
        issues.append(f"{missing_liquidity} observations have missing or invalid historical liquidity")
    if len(present) != len(markets):
        issues.append("Duplicate token/timestamp market observations")
    if len({e.get('id') for e in events}) != len(events):
        issues.append("Duplicate event IDs")
    if dataset.get("kind") not in ("REAL", "SYNTHETIC"):
        issues.append("Dataset must be explicitly labeled REAL or SYNTHETIC")
    if dataset.get("provenance", {}).get("transaction_coverage_complete") is False:
        issues.append("Wallet history pagination is incomplete; narrow the window or increase the page budget")
    if dataset.get("provenance", {}).get("missing_data"):
        issues.extend(dataset["provenance"]["missing_data"])
    if any(e.get("token") not in tokens for e in events):
        issues.append("Events refer to undeclared tokens")
    if any(not isinstance(e.get("ts"), int) or e["ts"] < start or e["ts"] > end for e in events):
        issues.append("Events fall outside declared coverage or have invalid timestamps")
    if not swaps:
        issues.append("No supported swap events")
    if any(not positive(e.get("quantity")) or e.get("side") not in ("buy", "sell") or not e.get("wallet") for e in swaps):
        issues.append("Invalid normalized swap quantity, side or wallet")
    if any(e.get("execution_price_usd") is not None and not positive(e["execution_price_usd"]) for e in swaps):
        issues.append("Invalid declared USD execution price")
    price_pct = max(0, min(100, 100 * (len(markets) - missing_prices) / total_expected)) if total_expected else 0
    liq_pct = max(0, min(100, 100 * (len(markets) - missing_liquidity) / total_expected)) if total_expected else 0
    return {"performance_ready": not issues, "issues": issues, "market_observations": len(markets), "swap_events": len(swaps),
        "price_coverage_pct": price_pct, "liquidity_coverage_pct": liq_pct, "missing_bars": missing_bars,
        "missing_prices": missing_prices, "missing_liquidity": missing_liquidity,
        "verified_token_ages": sum(t.get("created_at") is not None for t in dataset.get("tokens", []))}

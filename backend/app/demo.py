"""Seeded prices and independently scheduled wallet activity; no fixed return output."""
import json
import math
from pathlib import Path
import random


def generate_demo(seed=33, days=14):
    rng = random.Random(seed)
    start, step = 1767225600, 300  # 2026-01-01 UTC, synthetic scenario time.
    n = days * 86400 // step
    tokens = [{"mint": f"SYNTH_{symbol}", "symbol": symbol, "decimals": 6,
        "created_at": start - (30 + i * 20) * 86400, "age_source": "simulation"}
        for i, symbol in enumerate(("ORBIT", "NOVA", "TIDAL", "EMBER"))]
    wallets = [f"SYNTH_W{i:02d}" for i in range(1, 13)]
    events, paths = [], {}
    for i, token in enumerate(tokens):
        price, prices = [2.5, 0.15, 8.0, 0.04][i], []
        for k in range(n + 1):
            # Regime changes and common shocks exercise drawdowns; no future-driven orders.
            drift = 0.00008 * math.sin(k / 220 + i)
            shock = rng.gauss(0, 0.007) + (-0.055 if rng.random() < 0.001 else 0)
            price *= math.exp(drift + shock)
            liquidity = (180000 + i * 85000) * max(0.15, 1 + 0.35 * math.sin(k / 90 + i) + rng.gauss(0, 0.08))
            if 1550 <= k <= 1560 and i == 0:
                liquidity *= 0.025
            ts = start + k * step
            prices.append(price)
            events.append({"id": f"bar:{i}:{k}", "type": "market", "ts": ts, "token": token["mint"],
                "price_usd": round(price, 10), "liquidity_usd": round(liquidity, 2),
                "volume_usd": round(rng.uniform(1000, 10000), 2), "provider": "deterministic-simulator"})
        paths[token["mint"]] = prices
    serial = 0
    for k in range(1, n - 72, 10):
        token = rng.choice(tokens)["mint"]
        group = rng.sample(wallets, rng.randint(3, 7))
        for wallet in group:
            entry = k + rng.randint(0, 3)
            exit_at = min(n, entry + rng.randint(6, 60))
            quantity = round(rng.uniform(400, 4000) / paths[token][entry], 6)
            for side, at in (("buy", entry), ("sell", exit_at)):
                serial += 1
                events.append({"id": f"sim-swap:{serial}", "signature": f"SYNTH_TX_{serial}", "type": "swap",
                    "ts": start + at * step, "slot": 400000000 + at * 750 + serial % 50,
                    "wallet": wallet, "token": token, "side": side, "quantity": quantity,
                    "decimals": 6, "execution_price_usd": round(paths[token][at], 10), "price_source": "simulation", "provider": "deterministic-simulator"})
    events.sort(key=lambda e: (e["ts"], e["id"]))
    return {"id": f"synthetic-seed-{seed}", "name": "Accumulation research · 14-day simulation" if days == 14 else f"Accumulation research · {days}-day simulation",
        "kind": "SYNTHETIC", "start_ts": start, "end_ts": start + n * step, "resolution_seconds": step,
        "tokens": tokens, "wallets": wallets, "events": events,
        "provenance": {"provider": "deterministic-simulator", "generator_version": "1.0.0", "seed": seed,
            "retrieved_at": None, "generated_at": "2026-01-01T00:00:00Z (fixed scenario metadata)",
            "coverage": "14 synthetic days; 5-minute market snapshots", "price_unit": "simulated USD", "liquidity_source": "simulated historical snapshots"},
        "limitations": ["SYNTHETIC DATA: every price, wallet, liquidity observation and transaction is simulated. Returns are not evidence of real Solana alpha.",
            "Four simulated tokens and twelve wallets are an engineering test universe, not a representative market sample.",
            "Five-minute observations do not reproduce intrabar execution or sub-minute accumulation."]}


if __name__ == "__main__":
    destination = Path(__file__).resolve().parents[2] / "data" / "synthetic_seed33.json"
    destination.parent.mkdir(exist_ok=True)
    destination.write_text(json.dumps(generate_demo(), separators=(",", ":")))
    print(destination)

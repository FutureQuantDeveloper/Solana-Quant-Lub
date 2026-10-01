"""Incremental factors. No full-dataset wallet rankings or future price access."""
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Protocol


class Factor(Protocol):
    name: str
    def evaluate(self, context: dict) -> float | None: ...


@dataclass
class ContextFactor:
    name: str
    def evaluate(self, context):
        return context.get(self.name)


FACTOR_REGISTRY = {name: ContextFactor(name) for name in (
    "wallet_count", "wallet_return_pct", "volume_usd", "liquidity_usd", "token_age_hours", "momentum_pct"
)}


class WalletLedger:
    """FIFO matched lots. Unknown acquisition cost never becomes free inventory."""
    def __init__(self):
        self.lots = defaultdict(deque)
        self.closed = defaultdict(list)

    def score(self, wallet, before_ts):
        observations = [x for x in self.closed[wallet] if x[0] < before_ts]
        cost = sum(x[1] for x in observations)
        proceeds = sum(x[2] for x in observations)
        return {"closed_trades": len(observations), "return_pct": (proceeds / cost - 1) * 100 if cost > 0 else None}

    def observe(self, event, price):
        key = (event["wallet"], event["token"])
        q = event.get("quantity", 0)
        if not isinstance(q, (float, int)) or q <= 0 or price is None or price <= 0:
            return
        if event["side"] == "buy":
            self.lots[key].append([q, price])
        elif event["side"] == "sell":
            matched_cost = matched_proceeds = 0.0
            while q > 1e-10 and self.lots[key]:
                lot = self.lots[key][0]
                matched = min(q, lot[0])
                matched_cost += matched * lot[1]
                matched_proceeds += matched * price
                lot[0] -= matched
                q -= matched
                if lot[0] < 1e-10:
                    self.lots[key].popleft()
            if matched_cost > 0:
                self.closed[event["wallet"]].append((event["ts"], matched_cost, matched_proceeds))


class FactorState:
    def __init__(self, config, tokens):
        self.config = config
        self.tokens = {t["mint"]: t for t in tokens}
        self.ledger = WalletLedger()
        self.buys = defaultdict(deque)
        self.prices = defaultdict(deque)

    def market(self, event):
        history = self.prices[event["token"]]
        history.append((event["ts"], event["price_usd"]))
        cutoff = event["ts"] - self.config.momentum_minutes * 60
        while len(history) > 1 and history[1][0] <= cutoff:
            history.popleft()

    def on_swap(self, event, market, allow_accumulation=True):
        c, ts, token = self.config, event["ts"], event["token"]
        score = self.ledger.score(event["wallet"], ts)
        price = event.get("execution_price_usd") or (market or {}).get("price_usd")
        selected = not c.wallet_ids or event["wallet"] in c.wallet_ids
        eligible = selected and score["closed_trades"] >= c.min_closed_trades and score["return_pct"] is not None and score["return_pct"] >= c.min_wallet_return_pct
        history = self.buys[token]
        while history and history[0]["ts"] < ts - c.accumulation_minutes * 60:
            history.popleft()
        context = None
        if event["side"] == "buy" and eligible and allow_accumulation and price:
            history.append({"wallet": event["wallet"], "ts": ts, "volume": event["quantity"] * price})
            # Re-evaluate every participating wallet at this signal, never at dataset end.
            valid = [b for b in history if (s := self.ledger.score(b["wallet"], ts))["closed_trades"] >= c.min_closed_trades and s["return_pct"] is not None and s["return_pct"] >= c.min_wallet_return_pct]
            wallets = sorted({b["wallet"] for b in valid})
            scores = [self.ledger.score(w, ts)["return_pct"] for w in wallets]
            price_history = self.prices[token]
            old = price_history[0] if price_history and price_history[0][0] <= ts - c.momentum_minutes * 60 else None
            born = self.tokens.get(token, {}).get("created_at")
            context = {"wallet_count": len(wallets), "wallets": wallets,
                "wallet_return_pct": sum(scores) / len(scores) if scores else None,
                "volume_usd": sum(b["volume"] for b in valid),
                "liquidity_usd": (market or {}).get("liquidity_usd"),
                "token_age_hours": (ts - born) / 3600 if born is not None else None,
                "momentum_pct": ((market or {}).get("price_usd", 0) / old[1] - 1) * 100 if old else None}
        # Same-timestamp sales cannot change eligibility: score filters with strict <.
        self.ledger.observe(event, price)
        return context


def passes(config, snapshot):
    tests = {"wallet_count": config.min_wallet_count, "volume_usd": config.min_volume_usd,
        "liquidity_usd": config.min_liquidity_usd}
    if config.min_token_age_hours > 0:
        tests["token_age_hours"] = config.min_token_age_hours
    if config.min_momentum_pct > -100:
        tests["momentum_pct"] = config.min_momentum_pct
    return all(FACTOR_REGISTRY[name].evaluate(snapshot) is not None and FACTOR_REGISTRY[name].evaluate(snapshot) >= minimum for name, minimum in tests.items())

"""Portable domain: shared unchanged by CPython/FastAPI and the browser worker."""
from dataclasses import asdict, dataclass, fields
import math


class ResearchDataError(ValueError):
    pass


@dataclass(frozen=True)
class StrategyConfig:
    strategy_type: str = "smart_money_accumulation"
    name: str = "Smart Money Accumulation"
    hypothesis: str = "When multiple previously profitable wallets accumulate a token, subsequent returns may exceed execution costs."
    wallet_ids: tuple = ()
    min_wallet_count: int = 3
    accumulation_minutes: int = 30
    min_wallet_return_pct: float = 0.0
    min_closed_trades: int = 2
    min_volume_usd: float = 0.0
    min_liquidity_usd: float = 100000.0
    min_token_age_hours: float = 0.0
    min_momentum_pct: float = -100.0
    momentum_minutes: int = 60
    entry_delay_minutes: int = 5
    position_size_usd: float = 1000.0
    initial_capital_usd: float = 10000.0
    holding_minutes: int = 120
    take_profit_pct: float = 8.0
    stop_loss_pct: float = 5.0
    fee_bps: float = 30.0
    slippage_bps: float = 20.0
    fixed_fee_usd: float = 0.01
    max_liquidity_participation_pct: float = 1.0
    train_fraction: float = 0.7
    warmup_hours: int = 24

    @classmethod
    def from_dict(cls, data):
        unknown = set(data) - {f.name for f in fields(cls)}
        if unknown:
            raise ValueError(f"Unsupported controls: {', '.join(sorted(unknown))}")
        clean = dict(data)
        if "wallet_ids" in clean:
            if not isinstance(clean["wallet_ids"], (list, tuple)) or not all(isinstance(w, str) for w in clean["wallet_ids"]):
                raise ValueError("wallet_ids must be a list of wallet identifiers")
            clean["wallet_ids"] = tuple(sorted(set(clean["wallet_ids"])))
        c = cls(**clean)
        if c.strategy_type != "smart_money_accumulation":
            raise ValueError("Unsupported strategy type")
        if not isinstance(c.name, str) or not 1 <= len(c.name) <= 120:
            raise ValueError("Strategy name must contain 1–120 characters")
        if not isinstance(c.hypothesis, str) or len(c.hypothesis) > 4000:
            raise ValueError("Hypothesis must be text, at most 4,000 characters")
        bounds = {
            "min_wallet_count": (1, 100), "accumulation_minutes": (1, 1440),
            "min_wallet_return_pct": (-100, 10000), "min_closed_trades": (1, 10000),
            "min_volume_usd": (0, 1e12), "min_liquidity_usd": (0, 1e12),
            "min_token_age_hours": (0, 1e7), "min_momentum_pct": (-100, 10000),
            "momentum_minutes": (1, 1440), "entry_delay_minutes": (0, 1440),
            "position_size_usd": (1, 1e9), "initial_capital_usd": (1, 1e10),
            "holding_minutes": (1, 10080), "take_profit_pct": (0.01, 10000),
            "stop_loss_pct": (0.01, 99.99), "fee_bps": (0, 1000),
            "slippage_bps": (0, 1000), "fixed_fee_usd": (0, 1000),
            "max_liquidity_participation_pct": (0.001, 10), "train_fraction": (0.2, 0.8),
            "warmup_hours": (1, 720),
        }
        integer_fields = {"min_wallet_count", "accumulation_minutes", "min_closed_trades", "momentum_minutes", "entry_delay_minutes", "holding_minutes", "warmup_hours"}
        for key, (lo, hi) in bounds.items():
            val = getattr(c, key)
            if isinstance(val, bool) or not isinstance(val, (int, float)) or not math.isfinite(val) or not lo <= val <= hi:
                raise ValueError(f"{key} must be a finite number between {lo} and {hi}")
            if key in integer_fields and int(val) != val:
                raise ValueError(f"{key} must be an integer")
        if c.position_size_usd > c.initial_capital_usd:
            raise ValueError("Position size cannot exceed initial capital")
        if c.fixed_fee_usd >= c.position_size_usd:
            raise ValueError("Fixed transaction fee must be smaller than the position budget")
        return c

    def to_dict(self):
        d = asdict(self)
        d["wallet_ids"] = list(self.wallet_ids)
        return d

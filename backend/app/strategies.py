from typing import Protocol
from .factors import passes


class StrategyRule(Protocol):
    def should_enter(self, config, snapshot: dict) -> bool: ...


class SmartMoneyAccumulation:
    def should_enter(self, config, snapshot):
        return passes(config, snapshot)


STRATEGY_REGISTRY = {"smart_money_accumulation": SmartMoneyAccumulation()}

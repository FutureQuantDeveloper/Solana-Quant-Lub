from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from .domain import StrategyConfig
import re


class StrategyInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    dataset_id: str = Field(min_length=1, max_length=80)
    config: dict[str, Any] = Field(default_factory=dict)

    @field_validator("config")
    @classmethod
    def valid_config(cls, v):
        return StrategyConfig.from_dict(v).to_dict()


class BacktestInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    strategy_id: str


class IngestionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    wallets: list[str] = Field(min_length=1, max_length=10)
    start_ts: int = Field(ge=1704067200)
    end_ts: int
    max_pages: int = Field(default=20, ge=1, le=200)
    include_prices: bool = True

    @model_validator(mode="after")
    def bounds(self):
        if not 0 < self.end_ts - self.start_ts <= 14*86400:
            raise ValueError("Select a historical window of at most 14 days")
        if self.start_ts % 300 or self.end_ts % 300:
            raise ValueError("Coverage endpoints must align to five-minute UTC boundaries")
        if len(set(self.wallets)) != len(self.wallets):
            raise ValueError("Wallet addresses must be unique")
        if any(not re.fullmatch(r"[1-9A-HJ-NP-Za-km-z]{32,44}", w) for w in self.wallets):
            raise ValueError("Invalid Solana base58 wallet address")
        return self


class DatasetInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,80}$")
    name: str = Field(min_length=1, max_length=200)
    kind: Literal["REAL", "SYNTHETIC"]
    start_ts: int = Field(ge=0)
    end_ts: int = Field(ge=0)
    resolution_seconds: int = Field(ge=1, le=86400)
    tokens: list[dict] = Field(min_length=1, max_length=100)
    wallets: list[str] = Field(max_length=10000)
    events: list[dict] = Field(max_length=250000)
    provenance: dict
    limitations: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def shape(self):
        if self.end_ts <= self.start_ts:
            raise ValueError("end_ts must be after start_ts")
        if any(not {"mint", "symbol"} <= t.keys() for t in self.tokens):
            raise ValueError("Every token requires mint and symbol")
        ids = set()
        for event in self.events:
            if not {"id", "type", "token", "ts"} <= event.keys() or event["type"] not in ("market", "swap"):
                raise ValueError("Invalid normalized event")
            if not isinstance(event["ts"], int) or event["id"] in ids:
                raise ValueError("Event timestamps must be integers and IDs unique")
            ids.add(event["id"])
            if event["type"] == "swap" and (not {"wallet", "quantity", "side"} <= event.keys() or event["side"] not in ("buy", "sell")):
                raise ValueError("Swap requires wallet, quantity and buy/sell side")
        return self

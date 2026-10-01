from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, JSON, ForeignKey, Text, UniqueConstraint, Index
from .db import Base


def now():
    return datetime.now(timezone.utc).isoformat()


class Dataset(Base):
    __tablename__ = "datasets"
    id = Column(String(80), primary_key=True)
    name = Column(String(200), nullable=False)
    kind = Column(String(12), nullable=False)
    metadata_json = Column(JSON, nullable=False)
    quality = Column(JSON, nullable=False)
    content_hash = Column(String(64), nullable=False)
    created_at = Column(String(40), default=now, nullable=False)


class Event(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True)
    dataset_id = Column(String(80), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True)
    event_id = Column(String(240), nullable=False)
    ts = Column(Integer, nullable=False)
    type = Column(String(20), nullable=False)
    token = Column(String(80), nullable=False)
    wallet = Column(String(80), nullable=True)
    payload = Column(JSON, nullable=False)
    __table_args__ = (UniqueConstraint("dataset_id", "event_id", name="uq_dataset_event"), Index("ix_events_timeline", "dataset_id", "ts"))


class Strategy(Base):
    __tablename__ = "strategies"
    id = Column(String(80), primary_key=True)
    dataset_id = Column(String(80), ForeignKey("datasets.id"), nullable=False)
    name = Column(String(120), nullable=False)
    config = Column(JSON, nullable=False)
    created_at = Column(String(40), default=now, nullable=False)


class Backtest(Base):
    __tablename__ = "backtests"
    id = Column(String(80), primary_key=True)
    strategy_id = Column(String(80), ForeignKey("strategies.id"), nullable=False)
    dataset_id = Column(String(80), ForeignKey("datasets.id"), nullable=False)
    status = Column(String(20), nullable=False, default="queued")
    progress = Column(Integer, nullable=False, default=0)
    config = Column(JSON, nullable=False)
    result = Column(JSON)
    error = Column(Text)
    created_at = Column(String(40), default=now, nullable=False)


class Trade(Base):
    __tablename__ = "trades"
    id = Column(Integer, primary_key=True)
    backtest_id = Column(String(80), ForeignKey("backtests.id", ondelete="CASCADE"), nullable=False, index=True)
    trade_id = Column(String(80), nullable=False)
    segment = Column(String(20), nullable=False)
    payload = Column(JSON, nullable=False)
    __table_args__ = (UniqueConstraint("backtest_id", "trade_id", name="uq_backtest_trade"),)


class Report(Base):
    __tablename__ = "reports"
    id = Column(String(80), primary_key=True)
    backtest_id = Column(String(80), ForeignKey("backtests.id"), unique=True, nullable=False)
    markdown = Column(Text, nullable=False)
    created_at = Column(String(40), default=now, nullable=False)


class Ingestion(Base):
    __tablename__ = "ingestions"
    id = Column(String(80), primary_key=True)
    status = Column(String(20), nullable=False, default="queued")
    progress = Column(Integer, default=0, nullable=False)
    request = Column(JSON, nullable=False)
    result = Column(JSON)
    error = Column(Text)
    created_at = Column(String(40), default=now, nullable=False)

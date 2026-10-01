"""Initial immutable dataset, event, strategy, job, trade and report schema."""
from alembic import op
import sqlalchemy as sa
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("datasets", sa.Column("id", sa.String(80), primary_key=True), sa.Column("name", sa.String(200), nullable=False), sa.Column("kind", sa.String(12), nullable=False), sa.Column("metadata_json", sa.JSON(), nullable=False), sa.Column("quality", sa.JSON(), nullable=False), sa.Column("content_hash", sa.String(64), nullable=False), sa.Column("created_at", sa.String(40), nullable=False))
    op.create_table("events", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("dataset_id", sa.String(80), sa.ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False), sa.Column("event_id", sa.String(240), nullable=False), sa.Column("ts", sa.Integer(), nullable=False), sa.Column("type", sa.String(20), nullable=False), sa.Column("token", sa.String(80), nullable=False), sa.Column("wallet", sa.String(80)), sa.Column("payload", sa.JSON(), nullable=False), sa.UniqueConstraint("dataset_id", "event_id", name="uq_dataset_event"))
    op.create_index("ix_events_dataset_id", "events", ["dataset_id"])
    op.create_index("ix_events_timeline", "events", ["dataset_id", "ts"])
    op.create_table("strategies", sa.Column("id", sa.String(80), primary_key=True), sa.Column("dataset_id", sa.String(80), sa.ForeignKey("datasets.id"), nullable=False), sa.Column("name", sa.String(120), nullable=False), sa.Column("config", sa.JSON(), nullable=False), sa.Column("created_at", sa.String(40), nullable=False))
    op.create_table("backtests", sa.Column("id", sa.String(80), primary_key=True), sa.Column("strategy_id", sa.String(80), sa.ForeignKey("strategies.id"), nullable=False), sa.Column("dataset_id", sa.String(80), sa.ForeignKey("datasets.id"), nullable=False), sa.Column("status", sa.String(20), nullable=False), sa.Column("progress", sa.Integer(), nullable=False), sa.Column("config", sa.JSON(), nullable=False), sa.Column("result", sa.JSON()), sa.Column("error", sa.Text()), sa.Column("created_at", sa.String(40), nullable=False))
    op.create_table("trades", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("backtest_id", sa.String(80), sa.ForeignKey("backtests.id", ondelete="CASCADE"), nullable=False), sa.Column("trade_id", sa.String(80), nullable=False), sa.Column("segment", sa.String(20), nullable=False), sa.Column("payload", sa.JSON(), nullable=False), sa.UniqueConstraint("backtest_id", "trade_id", name="uq_backtest_trade"))
    op.create_index("ix_trades_backtest_id", "trades", ["backtest_id"])
    op.create_table("reports", sa.Column("id", sa.String(80), primary_key=True), sa.Column("backtest_id", sa.String(80), sa.ForeignKey("backtests.id"), unique=True, nullable=False), sa.Column("markdown", sa.Text(), nullable=False), sa.Column("created_at", sa.String(40), nullable=False))
    op.create_table("ingestions", sa.Column("id", sa.String(80), primary_key=True), sa.Column("status", sa.String(20), nullable=False), sa.Column("progress", sa.Integer(), nullable=False), sa.Column("request", sa.JSON(), nullable=False), sa.Column("result", sa.JSON()), sa.Column("error", sa.Text()), sa.Column("created_at", sa.String(40), nullable=False))


def downgrade():
    for name in ("ingestions", "reports", "trades", "backtests", "strategies", "events", "datasets"):
        op.drop_table(name)

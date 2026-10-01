"""A bounded, single-host worker pool. Jobs and progress are persisted, never fabricated."""
from concurrent.futures import ThreadPoolExecutor
import logging
from .db import SessionLocal
from .engine import run_backtest
from .models import Backtest, Trade
from .repository import load_dataset
from .settings import settings

pool = ThreadPoolExecutor(max_workers=settings.max_concurrent_jobs, thread_name_prefix="quant-worker")


def execute_backtest(job_id):
    try:
        with SessionLocal() as db:
            job = db.get(Backtest, job_id)
            if job is None:
                return
            job.status, job.progress = "running", 1
            config = job.config
            dataset = load_dataset(db, job.dataset_id)
            db.commit()
        last = [0]
        def update(percent):
            if percent - last[0] >= 5:
                with SessionLocal() as db:
                    db.get(Backtest, job_id).progress = percent
                    db.commit()
                last[0] = percent
        result = run_backtest(dataset, config, update)
        with SessionLocal() as db:
            job = db.get(Backtest, job_id)
            job.result, job.status, job.progress = result, "completed", 100
            for segment in ("in_sample", "out_of_sample"):
                db.add_all([Trade(backtest_id=job_id, trade_id=t["id"], segment=segment, payload=t) for t in result[segment]["trades"]])
            db.commit()
    except Exception as exc:
        logging.exception("Backtest failed: %s", job_id)
        with SessionLocal() as db:
            job = db.get(Backtest, job_id)
            if job:
                job.status, job.error = "failed", str(exc)
                db.commit()

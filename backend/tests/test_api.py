import time
import threading
from sqlalchemy import select, func
from app.domain import StrategyConfig
from app.engine import run_backtest


def wait(client, job_id):
    for _ in range(500):
        response = client.get("/api/backtests/"+job_id)
        assert response.status_code == 200
        row = response.json()
        if row["status"] in ("completed", "failed"):
            return row
        time.sleep(.01)
    raise AssertionError("Backtest did not finish")


def test_end_to_end_api_persistence_report_and_reproducibility(client):
    datasets = client.get("/api/datasets").json()
    assert datasets[0]["kind"] == "SYNTHETIC" and datasets[0]["quality"]["performance_ready"]
    created = client.post("/api/strategies",json={"dataset_id":"synthetic-seed-33","config":{}})
    assert created.status_code == 201
    strategy = created.json()
    response = client.post("/api/backtests",json={"strategy_id":strategy["id"]})
    assert response.status_code == 202
    run = wait(client,response.json()["id"])
    assert run["status"] == "completed" and run["progress"] == 100
    assert run["result"]["out_of_sample"]["metrics"]["trade_count"] > 0
    report = client.post(f"/api/backtests/{run['id']}/report")
    assert report.status_code == 200 and "SYNTHETIC" in report.text and run["result"]["fingerprint"] in report.text
    assert client.post(f"/api/backtests/{run['id']}/report").text == report.text
    assert len(client.get(f"/api/backtests/{run['id']}/trades?limit=5").json()) == 5
    exported = client.get("/api/datasets/synthetic-seed-33/export").json()
    assert run_backtest(exported,strategy["config"])["fingerprint"] == run["result"]["fingerprint"]
    from app.db import SessionLocal
    from app.models import Trade, Report
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(Trade).where(Trade.backtest_id==run["id"])) == sum(run["result"][s]["metrics"]["trade_count"] for s in ("in_sample","out_of_sample"))
        assert db.scalar(select(func.count()).select_from(Report).where(Report.backtest_id==run["id"])) == 1


def test_configuration_update_and_snapshot_isolation(client):
    s = client.post("/api/strategies",json={"dataset_id":"synthetic-seed-33","config":{"fee_bps":10}}).json()
    r = client.post("/api/backtests",json={"strategy_id":s["id"]}).json()
    changed = client.put("/api/strategies/"+s["id"],json={"dataset_id":"synthetic-seed-33","config":{"fee_bps":80}})
    assert changed.json()["config"]["fee_bps"] == 80
    assert wait(client,r["id"])["config"]["fee_bps"] == 10


def test_incomplete_dataset_stored_but_backtest_blocked(client):
    from app.demo import generate_demo
    d = generate_demo(days=3)
    d["id"] = "incomplete-test"
    next(e for e in d["events"] if e["type"]=="market")["liquidity_usd"] = None
    response = client.post("/api/datasets",json=d)
    assert response.status_code == 201 and not response.json()["quality"]["performance_ready"]
    s = client.post("/api/strategies",json={"dataset_id":d["id"],"config":{}}).json()
    assert client.post("/api/backtests",json={"strategy_id":s["id"]}).status_code == 422
    assert client.post("/api/datasets",json=d).status_code == 409


def test_api_rejects_arbitrary_code_and_invalid_inputs(client):
    assert client.post("/api/strategies",json={"dataset_id":"synthetic-seed-33","config":{"python":"print(1)"}}).status_code == 422
    assert client.post("/api/strategies",json={"dataset_id":"missing","config":{}}).status_code == 404
    assert client.get("/api/backtests/missing").status_code == 404
    assert client.post("/api/ingestions/wallets",json={"wallets":["So11111111111111111111111111111111111111112"],"start_ts":1767225600,"end_ts":1767312000}).status_code == 503


def test_worker_does_not_block_ordinary_api_requests(client,monkeypatch):
    import app.jobs as jobs
    entered, release = threading.Event(), threading.Event()
    original = jobs.run_backtest
    def held(*args,**kwargs):
        entered.set()
        assert release.wait(5)
        return original(*args,**kwargs)
    monkeypatch.setattr(jobs,"run_backtest",held)
    s = client.post("/api/strategies",json={"dataset_id":"synthetic-seed-33","config":{}}).json()
    job = client.post("/api/backtests",json={"strategy_id":s["id"]}).json()
    try:
        assert entered.wait(2)
        start = time.monotonic()
        assert client.get("/health").status_code == 200
        assert client.get("/api/datasets").status_code == 200
        assert time.monotonic()-start < 1.5
    finally:
        release.set()
    assert wait(client,job["id"])["status"] == "completed"

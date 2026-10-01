from collections import Counter
from datetime import datetime, timezone
import uuid
from .db import SessionLocal
from .models import Ingestion
from .providers.helius import HeliusProvider
from .providers.birdeye import BirdeyeProvider
from .providers.base import ProviderError
from .repository import persist_dataset, dataset_summary
from .settings import settings


def ingest(request, progress=None):
    provider = HeliusProvider(settings.helius_api_key)
    events, details, decimals = {}, [], {}
    for index, wallet in enumerate(request["wallets"]):
        rows, meta = provider.fetch_wallet(wallet, request["start_ts"], request["end_ts"], request["max_pages"])
        details.append(meta)
        for event in rows:
            events[event["id"]] = event
            decimals[event["token"]] = event["decimals"]
        if progress:
            progress(int((index+1) / len(request["wallets"]) * 40))
    tokens = sorted(decimals)
    if len(tokens) > 20:
        raise ProviderError("Ingestion exceeds the MVP limit of 20 tokens; narrow the requested time window")
    market_meta, missing = [], []
    if request["include_prices"]:
        if not settings.birdeye_api_key:
            missing.append("BIRDEYE_API_KEY absent: no historical price or liquidity observations retrieved")
        else:
            market = BirdeyeProvider(settings.birdeye_api_key)
            for index, token in enumerate(tokens):
                try:
                    bars, meta = market.fetch(token, request["start_ts"], request["end_ts"])
                    events.update({e["id"]: e for e in bars})
                    market_meta.append({"token": token, **meta})
                except ProviderError as exc:
                    missing.append(f"Historical market retrieval failed for {token}: {exc}")
                if progress:
                    progress(40 + int((index+1) / max(1,len(tokens)) * 50))
    else:
        missing.append("Historical market data was not requested")
    provenance = {"provider": "Helius + Birdeye" if market_meta else "Helius", "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "requested_start": request["start_ts"], "requested_end": request["end_ts"],
        "transaction_coverage_complete": all(m["coverage_complete"] for m in details),
        "wallet_ingestion": [{k:v for k,v in m.items() if k != "raw_transactions"} for m in details], "market_ingestion": market_meta,
        "missing_data": missing, "parser": "explicit SWAP, one wallet-owned input and output; SOL/USDC/USDT quotes only",
        "token_age_source": "unverified; age filter unavailable", "wallet_valuation": "prior historical USD marks; actual USD fills are not inferred"}
    data = {"id": "real_" + uuid.uuid4().hex[:20], "name": "Solana wallet study · " + datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "kind": "REAL", "start_ts": request["start_ts"], "end_ts": request["end_ts"], "resolution_seconds": 300,
        "tokens": [{"mint": t, "symbol": t[:5]+"…"+t[-4:], "decimals": decimals[t], "created_at": None} for t in tokens],
        "wallets": request["wallets"], "events": sorted(events.values(), key=lambda e:(e["ts"],e["id"])), "provenance": provenance,
        "limitations": ["REAL provider observations. No synthetic replacement is used for missing data.",
            "Only explicitly decoded one-input/one-output swaps against SOL, USDC or USDT are supported. Other actions and ambiguous routes are excluded.",
            "The supplied wallet universe can introduce selection and survivorship bias; public historical wallet scores do not eliminate universe-selection bias.",
            "Historical price-series points are made available one five-minute bucket later. Execution is a model at lagged historical marks, not a reconstruction of actual fills.",
            "Historical exit_liquidity_usd is an aggregate depth proxy, not a venue-specific executable quote. Liquidity snapshots are matched exactly, without filling gaps.",
            "Token creation times are not verified. Positive token-age filters are blocked."]}
    return data, details


def execute_ingestion(job_id):
    try:
        with SessionLocal() as db:
            job = db.get(Ingestion, job_id)
            request = job.request
            job.status, job.progress = "running", 1
            db.commit()
        def progress(percent):
            with SessionLocal() as db:
                db.get(Ingestion, job_id).progress = percent
                db.commit()
        data, raw = ingest(request, progress)
        with SessionLocal() as db:
            saved = persist_dataset(db, data)
            job = db.get(Ingestion, job_id)
            job.result = {"dataset": dataset_summary(saved), "raw_wallet_history": raw}
            job.status, job.progress = "completed", 100
            db.commit()
    except Exception as exc:
        # Provider helpers sanitize API URLs/headers; no key appears in this response.
        with SessionLocal() as db:
            job = db.get(Ingestion, job_id)
            job.status, job.error = "failed", str(exc)
            db.commit()

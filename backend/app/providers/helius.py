"""Conservative Enhanced Transactions adapter, verified against official docs 2026-09-29.

Enhanced Transactions is a maintained legacy endpoint. Only explicit SWAP events
with unambiguous wallet-owned economic input/output legs are supported.
"""
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import math
import httpx
from .base import ProviderError, get_json

WSOL = "So11111111111111111111111111111111111111112"
USDC = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
USDT = "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB"
QUOTES = {WSOL, USDC, USDT}


def parse_amount(leg):
    raw = leg.get("rawTokenAmount")
    if not isinstance(raw, dict) or not isinstance(raw.get("decimals"), int) or not 0 <= raw["decimals"] <= 18:
        raise ValueError("missing_decimals")
    try:
        amount = Decimal(str(raw["tokenAmount"])) / (Decimal(10) ** raw["decimals"])
    except (InvalidOperation, KeyError):
        raise ValueError("invalid_amount") from None
    if not amount.is_finite() or amount <= 0:
        raise ValueError("invalid_amount")
    return float(amount), raw["decimals"], str(raw["tokenAmount"])


def normalize_swap(tx, wallet):
    if tx.get("transactionError") is not None:
        return [], "failed_transaction"
    if tx.get("type") != "SWAP":
        return [], "not_supported_swap"
    swap = (tx.get("events") or {}).get("swap")
    if not isinstance(swap, dict):
        return [], "missing_swap_event"
    if not tx.get("signature") or not isinstance(tx.get("timestamp"), int) or not isinstance(tx.get("slot"), int):
        return [], "missing_identity_or_time"
    try:
        def legs(key, native_key):
            result = []
            for leg in swap.get(key) or []:
                if leg.get("userAccount") != wallet:
                    continue
                amount, decimals, raw = parse_amount(leg)
                if not leg.get("mint"):
                    raise ValueError("missing_mint")
                result.append({"mint": leg["mint"], "amount": amount, "decimals": decimals, "raw": raw})
            native = swap.get(native_key)
            if native and native.get("account") == wallet:
                amount = float(Decimal(str(native["amount"])) / Decimal(1_000_000_000))
                if not math.isfinite(amount) or amount <= 0:
                    raise ValueError("invalid_native_amount")
                result.append({"mint": WSOL, "amount": amount, "decimals": 9, "raw": str(native["amount"])})
            return result
        inputs, outputs = legs("tokenInputs", "nativeInput"), legs("tokenOutputs", "nativeOutput")
    except (ValueError, KeyError, TypeError, InvalidOperation):
        return [], "invalid_or_missing_amounts"
    # Economic endpoints only. Never count inner route hops as wallet accumulation.
    if len(inputs) != 1 or len(outputs) != 1:
        return [], "ambiguous_wallet_legs"
    i, o = inputs[0], outputs[0]
    if i["mint"] in QUOTES and o["mint"] not in QUOTES:
        token, quote, side = o, i, "buy"
    elif o["mint"] in QUOTES and i["mint"] not in QUOTES:
        token, quote, side = i, o, "sell"
    else:
        return [], "unsupported_quote_pair"
    return [{"id": f"{tx['signature']}:{wallet}:{token['mint']}:{side}", "signature": tx["signature"],
        "type": "swap", "ts": tx["timestamp"], "slot": tx["slot"], "wallet": wallet,
        "token": token["mint"], "side": side, "quantity": token["amount"], "decimals": token["decimals"],
        "raw_quantity": token["raw"], "quote_mint": quote["mint"], "quote_quantity": quote["amount"],
        "quote_price": quote["amount"] / token["amount"], "execution_price_usd": None,
        "price_source": "unavailable; quote units are not assumed to be USD", "network_fee_lamports": tx.get("fee"),
        "provider": "helius-enhanced-transactions", "dex_source": tx.get("source")}], None


class HeliusProvider:
    name = "helius-enhanced-transactions"
    def __init__(self, api_key, client=None):
        if not api_key:
            raise ProviderError("HELIUS_API_KEY is not configured; no synthetic substitution was made")
        self.key = api_key
        self.client = client or httpx.Client(timeout=30)

    def fetch_wallet(self, wallet, start, end, max_pages=20):
        before, seen, events, rejected = None, set(), [], Counter()
        complete = False
        duplicates = 0
        pages = 0
        raw_records = []
        for page in range(max_pages):
            params = {"api-key": self.key, "gte-time": start, "lte-time": end, "limit": 100,
                "sort-order": "desc", "token-accounts": "balanceChanged", "commitment": "finalized"}
            # Fetch all types and classify locally, avoiding type-filter continuation errors.
            if before:
                params["before-signature"] = before
            data = get_json(self.client, f"https://mainnet.helius-rpc.com/v0/addresses/{wallet}/transactions", params=params)
            pages += 1
            if not isinstance(data, list):
                raise ProviderError("Unexpected Helius history response; dataset was not fabricated")
            if not data:
                complete = True
                break
            for tx in data:
                signature = tx.get("signature")
                if signature in seen:
                    duplicates += 1
                    continue
                if not signature:
                    rejected["missing_signature"] += 1
                    continue
                seen.add(signature)
                raw_records.append(tx)
                if not isinstance(tx.get("timestamp"), int) or not start <= tx["timestamp"] <= end:
                    rejected["outside_requested_coverage"] += 1
                    continue
                normalized, reason = normalize_swap(tx, wallet)
                events.extend(normalized)
                if reason:
                    rejected[reason] += 1
            cursor = data[-1].get("signature")
            if not cursor or cursor == before:
                rejected["pagination_stalled"] += 1
                break
            before = cursor
        return events, {"wallet": wallet, "retrieved_at": datetime.now(timezone.utc).isoformat(), "pages": pages,
            "unique_transactions": len(seen), "duplicates_removed": duplicates, "rejected": dict(rejected),
            "coverage_complete": complete, "continuation_signature": before, "requested_start": start, "requested_end": end,
            "raw_transactions": raw_records}

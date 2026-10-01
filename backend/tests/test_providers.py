from copy import deepcopy
import httpx
import pytest
from app.providers.helius import normalize_swap, HeliusProvider, WSOL, USDC
from app.providers.birdeye import BirdeyeProvider
from app.providers.base import get_json, ProviderError
from app.quality import assess


def swap():
    return {"type": "SWAP", "signature": "signature1", "timestamp": 1767225900, "slot": 123,
        "transactionError": None, "fee": 5000, "events": {"swap": {
            "nativeInput": {"account": "wallet", "amount": "1000000000"},
            "tokenInputs": [], "tokenOutputs": [{"userAccount": "wallet", "mint": "TOKEN",
                "rawTokenAmount": {"tokenAmount": "250000000", "decimals": 6}}]}}}


def test_normalizes_raw_decimals_and_preserves_unknown_usd():
    events, reason = normalize_swap(swap(), "wallet")
    assert reason is None
    e = events[0]
    assert e["quantity"] == 250 and e["decimals"] == 6 and e["quote_quantity"] == 1
    assert e["quote_mint"] == WSOL and e["side"] == "buy"
    assert e["execution_price_usd"] is None
    assert e["slot"] == 123 and e["signature"] == "signature1"


def test_transfer_is_not_a_swap():
    tx = swap()
    tx["type"] = "TRANSFER"
    tx["tokenTransfers"] = [{"mint": "TOKEN", "toUserAccount": "wallet", "tokenAmount": 100}]
    assert normalize_swap(tx, "wallet")[0] == []


@pytest.mark.parametrize("mutation", ["failed", "ambiguous", "no_event", "no_decimals", "other_wallet"])
def test_unsupported_or_ambiguous_transactions_rejected(mutation):
    tx = swap()
    if mutation == "failed": tx["transactionError"] = {"InstructionError": [1, "failed"]}
    if mutation == "ambiguous": tx["events"]["swap"]["tokenOutputs"].append(deepcopy(tx["events"]["swap"]["tokenOutputs"][0]))
    if mutation == "no_event": tx["events"] = {}
    if mutation == "no_decimals": del tx["events"]["swap"]["tokenOutputs"][0]["rawTokenAmount"]["decimals"]
    if mutation == "other_wallet": tx["events"]["swap"]["tokenOutputs"][0]["userAccount"] = "someone-else"
    assert normalize_swap(tx, "wallet")[0] == []


def test_stablecoin_quote_not_silently_treated_as_usd():
    tx = swap()
    tx["events"]["swap"]["nativeInput"] = None
    tx["events"]["swap"]["tokenInputs"] = [{"userAccount": "wallet", "mint": USDC, "rawTokenAmount": {"tokenAmount": "100000000", "decimals": 6}}]
    e = normalize_swap(tx, "wallet")[0][0]
    assert e["quote_price"] == .4 and e["execution_price_usd"] is None


def test_helius_cursor_pagination_and_deduplication():
    requests = []
    newer = swap()
    older = deepcopy(newer)
    older["signature"] = "signature2"
    older["timestamp"] -= 60
    def handler(request):
        requests.append(request)
        return httpx.Response(200, json=([newer] if len(requests)==1 else [newer,older] if len(requests)==2 else []))
    provider = HeliusProvider("secret", httpx.Client(transport=httpx.MockTransport(handler)))
    events, meta = provider.fetch_wallet("wallet", 1767225600, 1767226200, 4)
    assert len(events) == 2 and meta["duplicates_removed"] == 1 and meta["coverage_complete"]
    assert requests[1].url.params["before-signature"] == "signature1"
    assert requests[2].url.params["before-signature"] == "signature2"
    assert all(r.url.params["gte-time"] == "1767225600" for r in requests)


def test_page_budget_marks_coverage_incomplete():
    provider = HeliusProvider("secret", httpx.Client(transport=httpx.MockTransport(lambda _:httpx.Response(200,json=[swap()]))))
    _, meta = provider.fetch_wallet("wallet", 1767225600, 1767226200, 1)
    assert not meta["coverage_complete"]


def test_rate_limit_backoff_and_retry():
    count, delays = [0], []
    def handler(request):
        count[0] += 1
        return httpx.Response(429,headers={"Retry-After":"2"}) if count[0]==1 else httpx.Response(200,json={"ok":True})
    result = get_json(httpx.Client(transport=httpx.MockTransport(handler)),"https://example.invalid",sleep=delays.append)
    assert result == {"ok":True} and count[0] == 2 and delays == [2]


def test_provider_error_does_not_leak_key():
    client = httpx.Client(transport=httpx.MockTransport(lambda _:httpx.Response(403)))
    with pytest.raises(ProviderError) as error:
        get_json(client,"https://example.invalid?api-key=secret-value")
    assert "secret-value" not in str(error.value)


def market_client(missing=False):
    start = 1767225600
    def handler(request):
        assert request.headers["x-chain"] == "solana"
        if request.url.path == "/defi/history_price":
            assert request.url.params["type"] == "5m"
            return httpx.Response(200,json={"success":True,"data":{"items":[{"unixTime":t-300,"value":2+i} for i,t in enumerate(range(start,start+601,300))]}})
        assert request.url.path == "/defi/v3/liquidity/history/token"
        assert request.url.params["resolution"] == "1m" and request.url.params["direction"] == "back"
        return httpx.Response(200,json={"success":True,"data":{"items":[{"unix_time":t,"liquidity_usd":500000,"exit_liquidity_usd":None if missing else 200000} for t in range(start,start+601,300)]}})
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_birdeye_exact_join_and_conservative_price_availability():
    bars, meta = BirdeyeProvider("key",market_client()).fetch("TOKEN",1767225600,1767226200)
    assert len(bars) == 3 and bars[0]["ts"] == 1767225600
    assert bars[0]["source_price_ts"] == 1767225300
    assert bars[0]["liquidity_usd"] == 200000 and meta["missing_liquidity"] == 0


def test_missing_liquidity_is_not_replaced_by_total_or_current():
    bars, meta = BirdeyeProvider("key",market_client(True)).fetch("TOKEN",1767225600,1767226200)
    assert all(b["liquidity_usd"] is None for b in bars)
    assert meta["missing_liquidity"] == 3


def test_missing_credentials_fail_explicitly():
    with pytest.raises(ProviderError,match="HELIUS_API_KEY"):
        HeliusProvider("")
    with pytest.raises(ProviderError,match="BIRDEYE_API_KEY"):
        BirdeyeProvider("")

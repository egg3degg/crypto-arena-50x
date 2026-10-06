"""StalkChain client unit tests (no live API key required)."""
import pytest

from research.stalkchain_client import StalkChainClient, coordinated_buy_symbols


def test_client_disabled_without_key():
    client = StalkChainClient(api_key="")
    assert not client.enabled


@pytest.mark.asyncio
async def test_call_tool_requires_key():
    client = StalkChainClient(api_key="")
    with pytest.raises(Exception) as exc:
        await client.health()
    assert "STALKCHAIN_API_KEY" in str(exc.value)


def test_coordinated_buy_symbols_parses_list():
    payload = {
        "data": [
            {"symbol": "sol", "traderCount": 4},
            {"ticker": "WIF", "traders": 3},
        ]
    }
    assert coordinated_buy_symbols(payload) == {"SOL": 4.0, "WIF": 3.0}

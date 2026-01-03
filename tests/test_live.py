"""Tests for /v1/live endpoint."""

from unittest.mock import patch, Mock
from fastapi.testclient import TestClient
import httpx

from app.main import app
from app.engine.live_data import clear_cache


client = TestClient(app)


def setup_function():
    """Clear cache before each test."""
    clear_cache()


def test_live_endpoint_full_success():
    """Test /v1/live with all mempool endpoints responding successfully."""
    # Mock all three mempool API calls
    with patch("httpx.get") as mock_get:

        def mock_response(url, **kwargs):
            response = Mock()
            response.raise_for_status = Mock()

            if "/api/v1/prices" in url:
                response.json = Mock(return_value={"USD": 95000.50, "EUR": 88000.25})
            elif "/api/v1/fees/recommended" in url:
                response.json = Mock(
                    return_value={
                        "fastestFee": 20,
                        "halfHourFee": 15,
                        "hourFee": 10,
                        "economyFee": 5,
                        "minimumFee": 1,
                    }
                )
            elif "/api/blocks/tip/height" in url:
                response.text = "825000"

            return response

        mock_get.side_effect = mock_response

        response = client.get("/v1/live")

        assert response.status_code == 200
        data = response.json()

        assert data["source"] == "mempool.space"
        assert "updated_at" in data
        assert data["btc_price_usd"] == 95000.50
        assert data["btc_price_eur"] == 88000.25
        assert data["block_height"] == 825000
        assert data["block_subsidy_btc"] == 6.25  # 825000 / 210000 = 3 halvings, 50 / 2^3 = 6.25
        assert data["fees_recommended"]["fastest_fee"] == 20
        assert data["fees_recommended"]["half_hour_fee"] == 15
        assert data["fees_recommended"]["hour_fee"] == 10
        assert data["fees_recommended"]["economy_fee"] == 5
        assert data["fees_recommended"]["minimum_fee"] == 1
        assert any("Block subsidy computed" in note for note in data["notes"])


def test_live_endpoint_partial_failure_fees():
    """Test /v1/live when fees endpoint fails but others succeed."""
    with patch("httpx.get") as mock_get:

        def mock_response(url, **kwargs):
            response = Mock()

            if "/api/v1/prices" in url:
                response.raise_for_status = Mock()
                response.json = Mock(return_value={"USD": 95000.50, "EUR": 88000.25})
            elif "/api/v1/fees/recommended" in url:
                # Simulate fees endpoint failure
                response.raise_for_status = Mock(
                    side_effect=httpx.HTTPStatusError(
                        "503 Server Error", request=Mock(), response=Mock()
                    )
                )
            elif "/api/blocks/tip/height" in url:
                response.raise_for_status = Mock()
                response.text = "825000"

            return response

        mock_get.side_effect = mock_response

        response = client.get("/v1/live")

        assert response.status_code == 200
        data = response.json()

        # Prices and height should still work
        assert data["btc_price_usd"] == 95000.50
        assert data["block_height"] == 825000
        assert data["block_subsidy_btc"] == 6.25

        # Fees should be null/empty
        assert data["fees_recommended"]["fastest_fee"] is None
        assert data["fees_recommended"]["half_hour_fee"] is None

        # Should have notes about fees failure and subsidy computation
        assert any("Failed to fetch fees" in note for note in data["notes"])
        assert any("Block subsidy computed" in note for note in data["notes"])


def test_live_endpoint_partial_failure_prices():
    """Test /v1/live when prices endpoint fails but others succeed."""
    with patch("httpx.get") as mock_get:

        def mock_response(url, **kwargs):
            response = Mock()

            if "/api/v1/prices" in url:
                # Simulate prices endpoint failure
                response.raise_for_status = Mock(
                    side_effect=httpx.HTTPStatusError(
                        "503 Server Error", request=Mock(), response=Mock()
                    )
                )
            elif "/api/v1/fees/recommended" in url:
                response.raise_for_status = Mock()
                response.json = Mock(
                    return_value={
                        "fastestFee": 20,
                        "halfHourFee": 15,
                        "hourFee": 10,
                        "economyFee": 5,
                        "minimumFee": 1,
                    }
                )
            elif "/api/blocks/tip/height" in url:
                response.raise_for_status = Mock()
                response.text = "825000"

            return response

        mock_get.side_effect = mock_response

        response = client.get("/v1/live")

        assert response.status_code == 200
        data = response.json()

        # Fees and height should still work
        assert data["fees_recommended"]["fastest_fee"] == 20
        assert data["block_height"] == 825000
        assert data["block_subsidy_btc"] == 6.25

        # Prices should be null
        assert data["btc_price_usd"] is None
        assert data["btc_price_eur"] is None

        # Should have notes about prices failure and subsidy computation
        assert any("Failed to fetch prices" in note for note in data["notes"])
        assert any("Block subsidy computed" in note for note in data["notes"])


def test_live_endpoint_cache_fallback():
    """Test /v1/live falls back to cache when mempool is unavailable."""
    from datetime import datetime, timedelta
    import app.engine.live_data as live_data_module

    # First, populate the cache with successful data
    with patch("httpx.get") as mock_get:

        def mock_success(url, **kwargs):
            response = Mock()
            response.raise_for_status = Mock()

            if "/api/v1/prices" in url:
                response.json = Mock(return_value={"USD": 95000.50, "EUR": 88000.25})
            elif "/api/v1/fees/recommended" in url:
                response.json = Mock(
                    return_value={
                        "fastestFee": 20,
                        "halfHourFee": 15,
                        "hourFee": 10,
                        "economyFee": 5,
                        "minimumFee": 1,
                    }
                )
            elif "/api/blocks/tip/height" in url:
                response.text = "825000"

            return response

        mock_get.side_effect = mock_success

        response1 = client.get("/v1/live")
        assert response1.status_code == 200
        data1 = response1.json()
        cached_timestamp = data1["updated_at"]

    # Manually expire the cache by setting timestamp to past
    live_data_module._cache_timestamp = datetime.utcnow() - timedelta(seconds=61)

    # Now simulate complete mempool failure
    with patch("httpx.get") as mock_get:
        mock_get.side_effect = httpx.ConnectError("Connection failed")

        response2 = client.get("/v1/live")
        assert response2.status_code == 200
        data2 = response2.json()

        # Should return cached data
        assert data2["btc_price_usd"] == 95000.50
        assert data2["block_height"] == 825000
        assert data2["block_subsidy_btc"] == 6.25

        # Should have note about using cached data
        assert any("Using cached data" in note for note in data2["notes"])
        assert any(cached_timestamp in note for note in data2["notes"])


def test_live_endpoint_no_cache_all_fail():
    """Test /v1/live when all endpoints fail and no cache exists."""
    with patch("httpx.get") as mock_get:
        mock_get.side_effect = httpx.ConnectError("Connection failed")

        response = client.get("/v1/live")

        assert response.status_code == 200
        data = response.json()

        # All data should be null
        assert data["btc_price_usd"] is None
        assert data["btc_price_eur"] is None
        assert data["block_height"] is None
        assert data["block_subsidy_btc"] is None
        assert data["fees_recommended"]["fastest_fee"] is None

        # Should have notes about failures and no cache
        assert any("No cached data available" in note for note in data["notes"])


def test_live_endpoint_missing_eur_price():
    """Test /v1/live when mempool doesn't provide EUR price."""
    with patch("httpx.get") as mock_get:

        def mock_response(url, **kwargs):
            response = Mock()
            response.raise_for_status = Mock()

            if "/api/v1/prices" in url:
                # Only USD, no EUR
                response.json = Mock(return_value={"USD": 95000.50})
            elif "/api/v1/fees/recommended" in url:
                response.json = Mock(
                    return_value={
                        "fastestFee": 20,
                        "halfHourFee": 15,
                        "hourFee": 10,
                        "economyFee": 5,
                        "minimumFee": 1,
                    }
                )
            elif "/api/blocks/tip/height" in url:
                response.text = "825000"

            return response

        mock_get.side_effect = mock_response

        response = client.get("/v1/live")

        assert response.status_code == 200
        data = response.json()

        assert data["btc_price_usd"] == 95000.50
        assert data["btc_price_eur"] is None
        assert data["block_height"] == 825000
        assert data["block_subsidy_btc"] == 6.25

        # Should have notes about missing EUR and subsidy computation
        assert any("EUR price not available" in note for note in data["notes"])
        assert any("Block subsidy computed" in note for note in data["notes"])

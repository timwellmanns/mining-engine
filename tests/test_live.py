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
    # Mock all mempool API calls
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
            elif "/api/v1/blocks" in url:
                # Mock recent blocks with difficulty and fees
                response.json = Mock(
                    return_value=[
                        {
                            "difficulty": 75502165623893.72,
                            "extras": {"totalFees": 25000000}  # 0.25 BTC in sats
                        },
                        {
                            "difficulty": 75502165623893.72,
                            "extras": {"totalFees": 30000000}  # 0.30 BTC in sats
                        },
                        {
                            "difficulty": 75502165623893.72,
                            "extras": {"totalFees": 28000000}  # 0.28 BTC in sats
                        },
                    ]
                )

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

        # New fields: difficulty, hashrate, hashprice
        assert data["difficulty"] == 75502165623893.72
        assert data["network_hashrate_eh_s"] is not None
        assert data["network_hashrate_eh_s"] > 0

        # Fee fields
        assert data["avg_fees_btc_per_block"] is not None
        assert data["avg_fees_btc_per_block"] > 0
        assert data["fee_window_blocks"] == 3

        # Hashprice (should include fees)
        assert data["hashprice_usd_per_th_day"] is not None
        assert data["hashprice_usd_per_th_day"] > 0
        assert data["hashprice_eur_per_th_day"] is not None
        assert data["hashprice_eur_per_th_day"] > 0

        # Verify notes
        assert any("Block subsidy computed" in note for note in data["notes"])
        assert any("Hashprice includes avg tx fees" in note for note in data["notes"])


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


def test_live_endpoint_difficulty_missing():
    """Test /v1/live when difficulty/blocks endpoint fails."""
    with patch("httpx.get") as mock_get:

        def mock_response(url, **kwargs):
            response = Mock()

            if "/api/v1/prices" in url:
                response.raise_for_status = Mock()
                response.json = Mock(return_value={"USD": 95000.50, "EUR": 88000.25})
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
            elif "/api/v1/blocks" in url:
                # Simulate blocks endpoint failure (used for both difficulty and fees)
                response.raise_for_status = Mock(
                    side_effect=httpx.HTTPStatusError(
                        "503 Server Error", request=Mock(), response=Mock()
                    )
                )

            return response

        mock_get.side_effect = mock_response

        response = client.get("/v1/live")

        assert response.status_code == 200
        data = response.json()

        # Other data should still work
        assert data["btc_price_usd"] == 95000.50
        assert data["block_height"] == 825000
        assert data["block_subsidy_btc"] == 6.25

        # Difficulty-derived fields should be None (blocks endpoint failed)
        assert data["difficulty"] is None
        assert data["network_hashrate_eh_s"] is None
        assert data["hashprice_usd_per_th_day"] is None
        assert data["hashprice_eur_per_th_day"] is None

        # Fees should also be None (same endpoint)
        assert data["avg_fees_btc_per_block"] is None
        assert data["fee_window_blocks"] is None

        # Should have notes about both failures
        assert any("Failed to fetch difficulty" in note for note in data["notes"])
        assert any("Failed to fetch block fees" in note for note in data["notes"])


def test_live_endpoint_hashrate_calculation():
    """Test that hashrate is calculated correctly from difficulty."""
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
            elif "/api/v1/blocks" in url:
                # Use a known difficulty value for calculation verification
                response.json = Mock(
                    return_value=[
                        {
                            "difficulty": 60000000000000.0,
                            "extras": {"totalFees": 25000000}
                        }
                    ]
                )

            return response

        mock_get.side_effect = mock_response

        response = client.get("/v1/live")

        assert response.status_code == 200
        data = response.json()

        # Verify difficulty is set
        assert data["difficulty"] == 60000000000000.0

        # Verify hashrate calculation
        # Formula: hashrate_h_s = difficulty * 2^32 / 600
        # hashrate_eh_s = hashrate_h_s / 1e18
        expected_hashrate_h_s = 60000000000000.0 * (2**32) / 600
        expected_hashrate_eh_s = round(expected_hashrate_h_s / 1e18, 2)

        assert data["network_hashrate_eh_s"] == expected_hashrate_eh_s

        # Verify hashprice is computed
        assert data["hashprice_usd_per_th_day"] is not None
        assert data["hashprice_eur_per_th_day"] is not None


def test_live_endpoint_far_future_block_height():
    """Test /v1/live with far-future block height (>= 34 halvings)."""
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
                # Far future: 40 halvings = 210_000 * 40 = 8,400,000
                response.text = "8400000"
            elif "/api/v1/blocks" in url:
                # Mock blocks with difficulty but no fees (testing subsidy=0 scenario)
                response.json = Mock(
                    return_value=[
                        {
                            "difficulty": 75502165623893.72,
                        }
                    ]
                )

            return response

        mock_get.side_effect = mock_response

        response = client.get("/v1/live")

        assert response.status_code == 200
        data = response.json()

        assert data["block_height"] == 8400000
        # After >= 34 halvings, subsidy should be exactly 0.0
        assert data["block_subsidy_btc"] == 0.0

        # Hashprice should be 0 when subsidy is 0
        assert data["hashprice_usd_per_th_day"] == 0.0
        assert data["hashprice_eur_per_th_day"] == 0.0

        # Should have notes about subsidy and hashprice
        assert any("Block subsidy computed" in note for note in data["notes"])
        assert any("Hashprice" in note for note in data["notes"])


def test_live_endpoint_block_fees_missing():
    """Test /v1/live when block fees endpoint fails."""
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
            elif "/api/v1/blocks" in url:
                # Simulate blocks endpoint failure
                response.raise_for_status = Mock(
                    side_effect=httpx.HTTPStatusError(
                        "503 Server Error", request=Mock(), response=Mock()
                    )
                )

            return response

        mock_get.side_effect = mock_response

        response = client.get("/v1/live")

        assert response.status_code == 200
        data = response.json()

        # Price data should still work
        assert data["btc_price_usd"] == 95000.50

        # When blocks endpoint fails, both difficulty and fees should be None
        assert data["difficulty"] is None
        assert data["avg_fees_btc_per_block"] is None
        assert data["fee_window_blocks"] is None

        # Hashprice cannot be computed without difficulty
        assert data["hashprice_usd_per_th_day"] is None
        assert data["hashprice_eur_per_th_day"] is None

        # Should have notes about failures
        assert any("Failed to fetch difficulty" in note or "Failed to fetch block fees" in note for note in data["notes"])


def test_live_endpoint_fee_unit_conversion():
    """Test /v1/live correctly converts fees from satoshis to BTC."""
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
            elif "/api/v1/blocks" in url:
                # Mock blocks with fees in satoshis (large numbers) and difficulty
                response.json = Mock(
                    return_value=[
                        {"difficulty": 75502165623893.72, "fee": 25000000},  # 0.25 BTC in sats
                        {"difficulty": 75502165623893.72, "fee": 30000000},  # 0.30 BTC in sats
                        {"difficulty": 75502165623893.72, "fee": 28000000},  # 0.28 BTC in sats
                    ]
                )

            return response

        mock_get.side_effect = mock_response

        response = client.get("/v1/live")

        assert response.status_code == 200
        data = response.json()

        # Verify fees were converted from sats to BTC
        # Average of (0.25, 0.30, 0.28) = 0.27666667 rounded to 8 decimals
        expected_avg = round((0.25 + 0.30 + 0.28) / 3, 8)
        assert data["avg_fees_btc_per_block"] == expected_avg
        assert data["fee_window_blocks"] == 3

        # Should have note about conversion
        assert any("Converted fees from satoshis to BTC" in note for note in data["notes"])
        assert any("Hashprice includes avg tx fees" in note for note in data["notes"])

"""Calculation endpoint tests."""

from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


def test_calculate_endpoint():
    """Test calculate endpoint returns required fields."""
    payload = {
        "miners_count": 10,
        "miner_id": "antminer_s21_200th_air",
        "miner_power_w": 3500,
        "miner_hashrate_th": 200.0,
        "electricity_eur_per_kwh": 0.05,
        "uptime": 0.95,
        "btc_price_eur": 40000.0,
        "network_hashrate_eh": 500.0,
        "pool_fee": 0.02,
        "capex_eur": 50000.0,
        "opex_eur_month": 500.0,
        "horizon_days": 365,
    }

    response = client.post("/v1/calculate", json=payload)
    assert response.status_code == 200

    data = response.json()

    # Check required fields exist
    assert "assumptions_version" in data
    assert "daily_energy_kwh" in data
    assert "daily_energy_cost_eur" in data
    assert "daily_btc_mined" in data
    assert "daily_revenue_eur" in data
    assert "daily_profit_eur" in data
    assert "breakeven_days" in data
    assert "notes" in data
    assert "inputs_echo" in data

    # Check types
    assert isinstance(data["assumptions_version"], str)
    assert isinstance(data["daily_energy_kwh"], (int, float))
    assert isinstance(data["daily_energy_cost_eur"], (int, float))
    assert isinstance(data["daily_btc_mined"], (int, float))
    assert isinstance(data["daily_revenue_eur"], (int, float))
    assert isinstance(data["daily_profit_eur"], (int, float))
    assert isinstance(data["notes"], list)
    assert isinstance(data["inputs_echo"], dict)

    # Breakeven can be int or null
    assert data["breakeven_days"] is None or isinstance(data["breakeven_days"], int)

    # Verify calculation logic (basic sanity check)
    assert data["daily_energy_kwh"] > 0
    assert data["daily_btc_mined"] > 0


def test_calculate_with_miner_id():
    """Test that miner_id auto-fills miner specs."""
    payload = {
        "miners_count": 5,
        "miner_id": "antminer_s21_200th_air",
        "miner_power_w": 9999,  # Should be overridden by miner_id
        "miner_hashrate_th": 9999.0,  # Should be overridden by miner_id
        "electricity_eur_per_kwh": 0.10,
        "uptime": 0.90,
        "btc_price_eur": 40000.0,
        "network_hashrate_eh": 500.0,
        "pool_fee": 0.02,
        "capex_eur": 25000.0,
        "opex_eur_month": 300.0,
    }

    response = client.post("/v1/calculate", json=payload)
    assert response.status_code == 200

    data = response.json()

    # Check that inputs_echo shows miner library values, not the 9999s
    assert data["inputs_echo"]["miner_power_w"] == 3500
    assert data["inputs_echo"]["miner_hashrate_th"] == 200.0


def test_get_miners():
    """Test miners endpoint returns library."""
    response = client.get("/v1/miners")
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 3

    # Check first miner has expected fields
    miner = data[0]
    assert "id" in miner
    assert "name" in miner
    assert "hashrate_th" in miner
    assert "power_w" in miner
    assert "cooling" in miner
    assert "efficiency_j_th" in miner


def test_get_presets():
    """Test presets endpoint returns configurations."""
    response = client.get("/v1/presets")
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 2

    # Check for expected preset IDs
    preset_ids = [p["id"] for p in data]
    assert "home_miner" in preset_ids
    assert "hydro_1mw" in preset_ids


def test_get_assumptions():
    """Test assumptions endpoint returns version and defaults."""
    response = client.get("/v1/assumptions")
    assert response.status_code == 200

    data = response.json()
    assert "assumptions_version" in data
    assert "block_reward_btc" in data
    assert "blocks_per_day" in data
    assert "simplifications" in data

    assert isinstance(data["simplifications"], list)
    assert len(data["simplifications"]) > 0

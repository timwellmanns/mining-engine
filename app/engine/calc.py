"""Main calculation orchestration."""

from app.models.requests import CalculationRequest
from app.models.responses import CalculationResponse
from app.models.miners import get_miner_by_id
from app.engine.mining import calculate_daily_btc_mined
from app.engine.economics import (
    calculate_daily_energy_kwh,
    calculate_daily_energy_cost,
    calculate_daily_revenue,
    calculate_daily_profit,
    calculate_breakeven_days,
)


def calculate_mining_economics(request: CalculationRequest) -> CalculationResponse:
    """
    Perform complete mining economics calculation.

    Args:
        request: Calculation request with all input parameters

    Returns:
        Calculation response with results and notes
    """
    # If miner_id is provided, fill in miner specs
    effective_power_w = request.miner_power_w
    effective_hashrate_th = request.miner_hashrate_th

    if request.miner_id:
        miner = get_miner_by_id(request.miner_id)
        if miner:
            effective_power_w = miner.power_w
            effective_hashrate_th = miner.hashrate_th

    # Energy calculations
    daily_energy_kwh = calculate_daily_energy_kwh(
        miners_count=request.miners_count,
        miner_power_w=effective_power_w,
        uptime=request.uptime,
    )

    daily_energy_cost_eur = calculate_daily_energy_cost(
        daily_energy_kwh=daily_energy_kwh,
        electricity_eur_per_kwh=request.electricity_eur_per_kwh,
    )

    # Mining calculations
    daily_btc_mined = calculate_daily_btc_mined(
        miners_count=request.miners_count,
        miner_hashrate_th=effective_hashrate_th,
        network_hashrate_eh=request.network_hashrate_eh,
        pool_fee=request.pool_fee,
        uptime=request.uptime,
    )

    # Revenue and profit
    daily_revenue_eur = calculate_daily_revenue(
        daily_btc_mined=daily_btc_mined,
        btc_price_eur=request.btc_price_eur,
    )

    daily_profit_eur = calculate_daily_profit(
        daily_revenue_eur=daily_revenue_eur,
        daily_energy_cost_eur=daily_energy_cost_eur,
        opex_eur_month=request.opex_eur_month,
    )

    # Breakeven
    breakeven_days = calculate_breakeven_days(
        capex_eur=request.capex_eur,
        daily_profit_eur=daily_profit_eur,
    )

    # Build notes
    notes = [
        "Transaction fees not included in mining revenue",
        "Constant block subsidy (3.125 BTC) - halving events not modeled",
        "Network hashrate assumed constant at input value",
        "Difficulty adjustments approximated through hashrate",
        "First-order approximation suitable for initial analysis",
    ]

    # Echo effective inputs
    inputs_echo = {
        "miners_count": request.miners_count,
        "miner_power_w": effective_power_w,
        "miner_hashrate_th": effective_hashrate_th,
        "electricity_eur_per_kwh": request.electricity_eur_per_kwh,
        "uptime": request.uptime,
        "btc_price_eur": request.btc_price_eur,
        "network_hashrate_eh": request.network_hashrate_eh,
        "pool_fee": request.pool_fee,
        "capex_eur": request.capex_eur,
        "opex_eur_month": request.opex_eur_month,
        "horizon_days": request.horizon_days,
    }

    return CalculationResponse(
        assumptions_version=request.assumptions_version or "2026.01.0",
        daily_energy_kwh=daily_energy_kwh,
        daily_energy_cost_eur=daily_energy_cost_eur,
        daily_btc_mined=daily_btc_mined,
        daily_revenue_eur=daily_revenue_eur,
        daily_profit_eur=daily_profit_eur,
        breakeven_days=breakeven_days,
        notes=notes,
        inputs_echo=inputs_echo,
    )

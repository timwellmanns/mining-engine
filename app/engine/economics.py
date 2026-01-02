"""Economic calculations for mining operations."""

from math import ceil
from typing import Optional


def calculate_daily_energy_kwh(
    miners_count: int,
    miner_power_w: int,
    uptime: float,
) -> float:
    """
    Calculate daily energy consumption.

    Args:
        miners_count: Number of mining units
        miner_power_w: Power per miner in watts
        uptime: Uptime ratio (0-1)

    Returns:
        Daily energy consumption in kWh
    """
    return miners_count * miner_power_w * 24 / 1000 * uptime


def calculate_daily_energy_cost(
    daily_energy_kwh: float,
    electricity_eur_per_kwh: float,
) -> float:
    """Calculate daily electricity cost."""
    return daily_energy_kwh * electricity_eur_per_kwh


def calculate_daily_revenue(
    daily_btc_mined: float,
    btc_price_eur: float,
) -> float:
    """Calculate daily revenue in EUR."""
    return daily_btc_mined * btc_price_eur


def calculate_daily_profit(
    daily_revenue_eur: float,
    daily_energy_cost_eur: float,
    opex_eur_month: float,
) -> float:
    """
    Calculate daily profit.

    Args:
        daily_revenue_eur: Daily revenue
        daily_energy_cost_eur: Daily electricity cost
        opex_eur_month: Monthly operational costs

    Returns:
        Daily profit (revenue - energy - opex)
    """
    opex_daily = opex_eur_month / 30
    return daily_revenue_eur - daily_energy_cost_eur - opex_daily


def calculate_breakeven_days(
    capex_eur: float,
    daily_profit_eur: float,
) -> Optional[int]:
    """
    Calculate days to break even on CAPEX.

    Returns:
        Days to breakeven, or None if unprofitable
    """
    if daily_profit_eur <= 0:
        return None
    return int(ceil(capex_eur / daily_profit_eur))

from pydantic import BaseModel, Field
from typing import Optional, List


class Preset(BaseModel):
    """Predefined calculation scenario."""

    id: str = Field(..., description="Unique identifier")
    name: str = Field(..., description="Display name")
    description: str = Field(..., description="Scenario description")
    miners_count: int = Field(..., gt=0)
    miner_id: str = Field(..., description="Reference to miner library")
    electricity_eur_per_kwh: float = Field(..., gt=0)
    uptime: float = Field(..., ge=0, le=1)
    btc_price_eur: float = Field(..., gt=0)
    network_hashrate_eh: float = Field(..., gt=0)
    pool_fee: float = Field(..., ge=0, le=1)
    capex_eur: float = Field(..., ge=0)
    opex_eur_month: float = Field(..., ge=0)
    horizon_days: int = Field(default=365, gt=0)


# Preset library
PRESET_LIBRARY: List[Preset] = [
    Preset(
        id="home_miner",
        name="Home Miner",
        description="Small-scale home mining setup with a few units",
        miners_count=5,
        miner_id="antminer_s21_200th_air",
        electricity_eur_per_kwh=0.10,
        uptime=0.90,
        btc_price_eur=40000.0,
        network_hashrate_eh=500.0,
        pool_fee=0.02,
        capex_eur=25000.0,
        opex_eur_month=300.0,
        horizon_days=365,
    ),
    Preset(
        id="hydro_1mw",
        name="1 MW Hydro Facility",
        description="Medium-scale facility with renewable hydro power",
        miners_count=280,
        miner_id="antminer_s21_pro_234th_air",
        electricity_eur_per_kwh=0.04,
        uptime=0.97,
        btc_price_eur=40000.0,
        network_hashrate_eh=500.0,
        pool_fee=0.015,
        capex_eur=1500000.0,
        opex_eur_month=15000.0,
        horizon_days=730,
    ),
]


def get_preset_by_id(preset_id: str) -> Optional[Preset]:
    """Retrieve a preset from the library by ID."""
    for preset in PRESET_LIBRARY:
        if preset.id == preset_id:
            return preset
    return None

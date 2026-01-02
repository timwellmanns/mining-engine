from pydantic import BaseModel, Field, field_validator
from app.core.config import ASSUMPTIONS_VERSION


class CalculationRequest(BaseModel):
    """Request model for mining economics calculation."""

    assumptions_version: str | None = Field(
        default=None,
        description="Assumptions version to use (defaults to current)",
    )
    miners_count: int = Field(..., gt=0, description="Number of mining units")
    miner_id: str | None = Field(
        default=None,
        description="Miner ID from library (auto-fills power and hashrate)",
    )
    miner_power_w: int = Field(..., gt=0, description="Power consumption per miner in watts")
    miner_hashrate_th: float = Field(..., gt=0, description="Hashrate per miner in TH/s")
    electricity_eur_per_kwh: float = Field(..., gt=0, description="Electricity cost in EUR/kWh")
    uptime: float = Field(..., ge=0, le=1, description="Uptime ratio (0-1)")
    btc_price_eur: float = Field(..., gt=0, description="Bitcoin price in EUR")
    network_hashrate_eh: float = Field(..., gt=0, description="Network hashrate in EH/s")
    pool_fee: float = Field(..., ge=0, le=1, description="Pool fee ratio (0-1)")
    capex_eur: float = Field(..., ge=0, description="Capital expenditure in EUR")
    opex_eur_month: float = Field(..., ge=0, description="Monthly operational costs in EUR")
    horizon_days: int = Field(default=365, gt=0, description="Analysis horizon in days")

    @field_validator("assumptions_version", mode="before")
    @classmethod
    def set_default_version(cls, v):
        """Set default assumptions version if not provided."""
        if v is None:
            return ASSUMPTIONS_VERSION
        return v

from pydantic import BaseModel, Field
from typing import Any, Optional, List, Dict


class CalculationResponse(BaseModel):
    """Response model for mining economics calculation."""

    assumptions_version: str = Field(..., description="Assumptions version used")
    daily_energy_kwh: float = Field(..., description="Daily energy consumption in kWh")
    daily_energy_cost_eur: float = Field(..., description="Daily electricity cost in EUR")
    daily_btc_mined: float = Field(..., description="Daily BTC mined (after pool fees)")
    daily_revenue_eur: float = Field(..., description="Daily revenue in EUR")
    daily_profit_eur: float = Field(..., description="Daily profit (revenue - costs)")
    breakeven_days: Optional[int] = Field(
        ...,
        description="Days to break even on CAPEX (None if unprofitable)",
    )
    notes: List[str] = Field(default_factory=list, description="Calculation notes and warnings")
    inputs_echo: Dict[str, Any] = Field(
        default_factory=dict,
        description="Echo of effective inputs used in calculation",
    )


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(default="ok")
    service: str = Field(default="mining-engine")

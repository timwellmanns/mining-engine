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


class RecommendedFees(BaseModel):
    """Recommended fee rates in sat/vB."""

    fastest_fee: Optional[int] = Field(None, description="Fastest confirmation (~10 min)")
    half_hour_fee: Optional[int] = Field(None, description="Half hour confirmation (~30 min)")
    hour_fee: Optional[int] = Field(None, description="Hour confirmation (~60 min)")
    economy_fee: Optional[int] = Field(None, description="Economy confirmation (~few hours)")
    minimum_fee: Optional[int] = Field(None, description="Minimum relay fee")


class LiveDataResponse(BaseModel):
    """Live Bitcoin network and market data from mempool.space."""

    source: str = Field(default="mempool.space", description="Data source identifier")
    updated_at: str = Field(..., description="UTC ISO timestamp of data fetch")
    btc_price_usd: Optional[float] = Field(None, description="Current BTC price in USD")
    btc_price_eur: Optional[float] = Field(None, description="Current BTC price in EUR")
    block_height: Optional[int] = Field(None, description="Current blockchain tip height")
    block_subsidy_btc: Optional[float] = Field(
        None, description="Current block subsidy in BTC (computed from block height)"
    )
    fees_recommended: RecommendedFees = Field(
        ..., description="Recommended fee rates in sat/vB"
    )
    difficulty: Optional[float] = Field(None, description="Current network difficulty")
    network_hashrate_eh_s: Optional[float] = Field(
        None, description="Estimated network hashrate in EH/s (derived from difficulty)"
    )
    avg_fees_btc_per_block: Optional[float] = Field(
        None, description="Average transaction fees per block in BTC (over recent blocks)"
    )
    fee_window_blocks: Optional[int] = Field(
        None, description="Number of recent blocks used for fee average"
    )
    hashprice_usd_per_th_day: Optional[float] = Field(
        None, description="Estimated USD revenue per TH/s per day (includes fees if available)"
    )
    hashprice_eur_per_th_day: Optional[float] = Field(
        None, description="Estimated EUR revenue per TH/s per day (includes fees if available)"
    )
    notes: List[str] = Field(default_factory=list, description="Warnings and fallback notes")

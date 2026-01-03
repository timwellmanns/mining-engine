"""API v1 route handlers."""

from typing import List
from fastapi import APIRouter

from app.models.requests import CalculationRequest
from app.models.responses import CalculationResponse, LiveDataResponse
from app.models.assumptions import Assumptions, get_default_assumptions
from app.models.miners import Miner, MINER_LIBRARY
from app.models.presets import Preset, PRESET_LIBRARY
from app.engine.calc import calculate_mining_economics
from app.engine.live_data import fetch_live_data


router = APIRouter()


@router.get("/presets", response_model=List[Preset])
def get_presets() -> List[Preset]:
    """Get available calculation presets."""
    return PRESET_LIBRARY


@router.get("/assumptions", response_model=Assumptions)
def get_assumptions() -> Assumptions:
    """Get current calculation assumptions and version."""
    return get_default_assumptions()


@router.get("/miners", response_model=List[Miner])
def get_miners() -> List[Miner]:
    """Get mining hardware library."""
    return MINER_LIBRARY


@router.post("/calculate", response_model=CalculationResponse)
def calculate(request: CalculationRequest) -> CalculationResponse:
    """Calculate mining economics based on provided parameters."""
    return calculate_mining_economics(request)


@router.get("/live", response_model=LiveDataResponse)
def get_live_data() -> LiveDataResponse:
    """
    Get live Bitcoin network and market data.

    Fetches real-time data from mempool.space including:
    - BTC prices (USD, EUR)
    - Current blockchain tip height
    - Recommended transaction fee rates

    Data is cached for 60 seconds (configurable via LIVE_CACHE_TTL_SECONDS).
    Falls back to cached data if mempool.space is temporarily unavailable.
    """
    return fetch_live_data()

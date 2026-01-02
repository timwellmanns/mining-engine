"""API v1 route handlers."""

from typing import List
from fastapi import APIRouter

from app.models.requests import CalculationRequest
from app.models.responses import CalculationResponse
from app.models.assumptions import Assumptions, get_default_assumptions
from app.models.miners import Miner, MINER_LIBRARY
from app.models.presets import Preset, PRESET_LIBRARY
from app.engine.calc import calculate_mining_economics


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

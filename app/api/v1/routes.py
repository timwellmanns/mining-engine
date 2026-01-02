"""API v1 route handlers."""

from fastapi import APIRouter

from app.models.requests import CalculationRequest
from app.models.responses import CalculationResponse
from app.models.assumptions import Assumptions, get_default_assumptions
from app.models.miners import Miner, MINER_LIBRARY
from app.models.presets import Preset, PRESET_LIBRARY
from app.engine.calc import calculate_mining_economics


router = APIRouter()


@router.get("/presets", response_model=list[Preset])
def get_presets() -> list[Preset]:
    """Get available calculation presets."""
    return PRESET_LIBRARY


@router.get("/assumptions", response_model=Assumptions)
def get_assumptions() -> Assumptions:
    """Get current calculation assumptions and version."""
    return get_default_assumptions()


@router.get("/miners", response_model=list[Miner])
def get_miners() -> list[Miner]:
    """Get mining hardware library."""
    return MINER_LIBRARY


@router.post("/calculate", response_model=CalculationResponse)
def calculate(request: CalculationRequest) -> CalculationResponse:
    """Calculate mining economics based on provided parameters."""
    return calculate_mining_economics(request)

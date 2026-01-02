from pydantic import BaseModel, Field
from app.core.config import ASSUMPTIONS_VERSION


class Assumptions(BaseModel):
    """Default calculation assumptions and their version."""

    assumptions_version: str = Field(
        default=ASSUMPTIONS_VERSION,
        description="Version identifier for the calculation methodology",
    )
    block_reward_btc: float = Field(
        default=3.125,
        description="Current block subsidy in BTC (post-2024 halving)",
    )
    blocks_per_day: int = Field(
        default=144,
        description="Expected number of blocks mined per day",
    )
    simplifications: list[str] = Field(
        default=[
            "Transaction fees not included in revenue",
            "Constant block subsidy (halving events not modeled)",
            "Network hashrate provided as fixed input",
            "Difficulty adjustments approximated through hashrate",
            "First-order approximation for initial analysis",
        ],
        description="Known simplifications in the current model",
    )


def get_default_assumptions() -> Assumptions:
    """Get the default assumptions for calculations."""
    return Assumptions()

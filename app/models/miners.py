from pydantic import BaseModel, Field, computed_field
from typing import Literal


class Miner(BaseModel):
    """Bitcoin mining hardware specification."""

    id: str = Field(..., description="Unique identifier for the miner")
    name: str = Field(..., description="Display name")
    hashrate_th: float = Field(..., gt=0, description="Hashrate in TH/s")
    power_w: int = Field(..., gt=0, description="Power consumption in watts")
    cooling: Literal["air", "hydro"] = Field(..., description="Cooling method")
    notes: str | None = Field(None, description="Additional notes")

    @computed_field
    @property
    def efficiency_j_th(self) -> float:
        """Energy efficiency in J/TH (joules per terahash)."""
        return self.power_w / self.hashrate_th


# Miner library with example hardware
MINER_LIBRARY: list[Miner] = [
    Miner(
        id="antminer_s21_200th_air",
        name="Antminer S21 (200 TH/s)",
        hashrate_th=200.0,
        power_w=3500,
        cooling="air",
        notes="Standard air-cooled configuration",
    ),
    Miner(
        id="antminer_s21_pro_234th_air",
        name="Antminer S21 Pro (234 TH/s)",
        hashrate_th=234.0,
        power_w=3510,
        cooling="air",
        notes="Pro model with enhanced performance",
    ),
    Miner(
        id="whatsminer_m60_186th_air",
        name="Whatsminer M60 (186 TH/s)",
        hashrate_th=186.0,
        power_w=3400,
        cooling="air",
        notes="Efficient air-cooled option",
    ),
]


def get_miner_by_id(miner_id: str) -> Miner | None:
    """Retrieve a miner from the library by ID."""
    for miner in MINER_LIBRARY:
        if miner.id == miner_id:
            return miner
    return None

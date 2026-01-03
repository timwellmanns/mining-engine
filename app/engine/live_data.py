"""Live Bitcoin network data fetcher with caching (mempool.space)."""

import os
from datetime import datetime, timedelta
from typing import Optional
import httpx

from app.models.responses import LiveDataResponse, RecommendedFees


# Configuration from environment
MEMPOOL_BASE_URL = os.getenv("MEMPOOL_BASE_URL", "https://mempool.space")
CACHE_TTL_SECONDS = int(os.getenv("LIVE_CACHE_TTL_SECONDS", "60"))

# In-process cache
_cache: Optional[LiveDataResponse] = None
_cache_timestamp: Optional[datetime] = None


def _is_cache_valid() -> bool:
    """Check if the cached data is still valid."""
    if _cache is None or _cache_timestamp is None:
        return False
    age = datetime.utcnow() - _cache_timestamp
    return age < timedelta(seconds=CACHE_TTL_SECONDS)


def _fetch_mempool_prices() -> tuple[Optional[float], Optional[float], list[str]]:
    """
    Fetch BTC prices from mempool.space.

    Returns:
        (usd_price, eur_price, notes)
    """
    notes = []
    try:
        url = f"{MEMPOOL_BASE_URL}/api/v1/prices"
        response = httpx.get(url, timeout=5.0)
        response.raise_for_status()
        data = response.json()

        usd = data.get("USD")
        eur = data.get("EUR")

        if usd is None:
            notes.append("USD price not available from mempool")
        if eur is None:
            notes.append("EUR price not available from mempool")

        return usd, eur, notes
    except Exception as e:
        notes.append(f"Failed to fetch prices: {str(e)}")
        return None, None, notes


def _fetch_mempool_fees() -> tuple[RecommendedFees, list[str]]:
    """
    Fetch recommended fees from mempool.space.

    Returns:
        (RecommendedFees, notes)
    """
    notes = []
    try:
        url = f"{MEMPOOL_BASE_URL}/api/v1/fees/recommended"
        response = httpx.get(url, timeout=5.0)
        response.raise_for_status()
        data = response.json()

        fees = RecommendedFees(
            fastest=data.get("fastestFee"),
            half_hour=data.get("halfHourFee"),
            hour=data.get("hourFee"),
            economy=data.get("economyFee"),
            minimum=data.get("minimumFee"),
        )

        return fees, notes
    except Exception as e:
        notes.append(f"Failed to fetch fees: {str(e)}")
        return RecommendedFees(), notes


def _fetch_mempool_tip_height() -> tuple[Optional[int], list[str]]:
    """
    Fetch current blockchain tip height from mempool.space.

    Returns:
        (tip_height, notes)
    """
    notes = []
    try:
        url = f"{MEMPOOL_BASE_URL}/api/blocks/tip/height"
        response = httpx.get(url, timeout=5.0)
        response.raise_for_status()

        # This endpoint returns plain text integer
        tip_height = int(response.text.strip())
        return tip_height, notes
    except Exception as e:
        notes.append(f"Failed to fetch tip height: {str(e)}")
        return None, notes


def fetch_live_data() -> LiveDataResponse:
    """
    Fetch live Bitcoin network data from mempool.space.

    Uses in-process caching with configurable TTL.
    Falls back to cached data if mempool is temporarily unavailable.

    Returns:
        LiveDataResponse with current or cached data
    """
    global _cache, _cache_timestamp

    # Return cached data if still valid
    if _is_cache_valid():
        return _cache

    # Attempt to fetch fresh data
    notes = []

    usd_price, eur_price, price_notes = _fetch_mempool_prices()
    notes.extend(price_notes)

    fees, fee_notes = _fetch_mempool_fees()
    notes.extend(fee_notes)

    tip_height, height_notes = _fetch_mempool_tip_height()
    notes.extend(height_notes)

    # Check if we got any data at all
    has_any_data = (
        usd_price is not None
        or eur_price is not None
        or tip_height is not None
        or any(
            [
                fees.fastest,
                fees.half_hour,
                fees.hour,
                fees.economy,
                fees.minimum,
            ]
        )
    )

    # If all fetches failed and we have cached data, return it with a note
    if not has_any_data and _cache is not None:
        notes.append(
            f"Using cached data from {_cache.fetched_at_iso} (mempool temporarily unavailable)"
        )
        # Return a copy of cache with updated notes
        cached_response = _cache.model_copy(deep=True)
        cached_response.notes = notes
        return cached_response

    # If no data and no cache, return empty response
    if not has_any_data:
        notes.append("No cached data available; mempool.space is unreachable")

    # Create new response
    now = datetime.utcnow()
    response = LiveDataResponse(
        source="mempool",
        fetched_at_iso=now.isoformat() + "Z",
        btc_price_usd=usd_price,
        btc_price_eur=eur_price,
        tip_height=tip_height,
        recommended_fees_sat_vb=fees,
        notes=notes,
    )

    # Update cache
    _cache = response
    _cache_timestamp = now

    return response


def clear_cache() -> None:
    """Clear the in-process cache. Useful for testing."""
    global _cache, _cache_timestamp
    _cache = None
    _cache_timestamp = None

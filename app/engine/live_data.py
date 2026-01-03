"""Live Bitcoin network data fetcher with caching (mempool.space)."""

import os
from datetime import datetime, timedelta
from typing import Optional
import httpx

from app.models.responses import LiveDataResponse, RecommendedFees


# Configuration from environment
MEMPOOL_BASE_URL = os.getenv("MEMPOOL_BASE_URL", "https://mempool.space")
CACHE_TTL_SECONDS = int(os.getenv("LIVE_CACHE_TTL_SECONDS", "60"))
FEE_WINDOW_BLOCKS = int(os.getenv("LIVE_FEE_WINDOW_BLOCKS", "24"))

# In-process cache
_cache: Optional[LiveDataResponse] = None
_cache_timestamp: Optional[datetime] = None


def _is_cache_valid() -> bool:
    """Check if the cached data is still valid."""
    if _cache is None or _cache_timestamp is None:
        return False
    age = datetime.utcnow() - _cache_timestamp
    return age < timedelta(seconds=CACHE_TTL_SECONDS)


def _calculate_block_subsidy(block_height: Optional[int]) -> Optional[float]:
    """
    Calculate the current block subsidy based on block height.

    Bitcoin started with 50 BTC per block and halves every 210,000 blocks.

    Args:
        block_height: Current blockchain tip height

    Returns:
        Current block subsidy in BTC, or None if height is unavailable
    """
    if block_height is None:
        return None

    # Initial subsidy was 50 BTC
    initial_subsidy = 50.0
    # Halving occurs every 210,000 blocks
    halving_interval = 210_000

    # Calculate number of halvings that have occurred
    halvings = block_height // halving_interval

    # Cap: after ~34 halvings, subsidy is effectively 0 (satoshi precision limit)
    if halvings >= 34:
        return 0.0

    # Subsidy after n halvings: 50 / (2^n)
    subsidy = initial_subsidy / (2**halvings)

    # Round to 8 decimals to avoid float artifacts (BTC precision)
    return round(subsidy, 8)


def _fetch_mempool_prices() -> tuple[Optional[float], Optional[float], list[str]]:
    """
    Fetch BTC prices from mempool.space.

    Returns:
        (usd_price, eur_price, notes)
    """
    notes = []
    try:
        url = f"{MEMPOOL_BASE_URL}/api/v1/prices"
        response = httpx.get(url, timeout=3.0)
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
        response = httpx.get(url, timeout=3.0)
        response.raise_for_status()
        data = response.json()

        fees = RecommendedFees(
            fastest_fee=data.get("fastestFee"),
            half_hour_fee=data.get("halfHourFee"),
            hour_fee=data.get("hourFee"),
            economy_fee=data.get("economyFee"),
            minimum_fee=data.get("minimumFee"),
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
        response = httpx.get(url, timeout=3.0)
        response.raise_for_status()

        # This endpoint returns plain text integer
        tip_height = int(response.text.strip())
        return tip_height, notes
    except Exception as e:
        notes.append(f"Failed to fetch tip height: {str(e)}")
        return None, notes


def _fetch_mempool_difficulty() -> tuple[Optional[float], list[str]]:
    """
    Fetch current network difficulty from mempool.space.

    Uses /api/v1/blocks endpoint and extracts difficulty from the most recent block.

    Returns:
        (difficulty, notes)
    """
    notes = []
    try:
        url = f"{MEMPOOL_BASE_URL}/api/v1/blocks"
        response = httpx.get(url, timeout=3.0)
        response.raise_for_status()
        blocks = response.json()

        if not isinstance(blocks, list) or len(blocks) == 0:
            notes.append("No blocks available from mempool")
            return None, notes

        # Get difficulty from most recent block
        difficulty = blocks[0].get("difficulty")

        if difficulty is None:
            notes.append("Difficulty field not found in recent block")
            return None, notes

        return float(difficulty), notes
    except Exception as e:
        notes.append(f"Failed to fetch difficulty: {str(e)}")
        return None, notes


def _fetch_recent_block_fees_btc() -> tuple[Optional[float], Optional[int], list[str]]:
    """
    Fetch average transaction fees per block from recent blocks.

    Returns:
        (avg_fees_btc_per_block, fee_window_blocks, notes)
    """
    notes = []
    try:
        url = f"{MEMPOOL_BASE_URL}/api/v1/blocks"
        response = httpx.get(url, timeout=3.0)
        response.raise_for_status()
        blocks = response.json()

        if not isinstance(blocks, list) or len(blocks) == 0:
            notes.append("No block data available from mempool")
            return None, None, notes

        # Limit to configured window or available blocks
        window = min(FEE_WINDOW_BLOCKS, len(blocks))
        fee_values = []

        for block in blocks[:window]:
            # Tolerant parsing: check extras.totalFees first (most reliable), then fallbacks
            fee = None
            if "extras" in block and "totalFees" in block["extras"]:
                fee = block["extras"]["totalFees"]
            else:
                # Fallback to other possible field names
                fee = block.get("fee") or block.get("fees") or block.get("totalFees")

            if fee is not None:
                fee_float = float(fee)

                # Unit detection heuristic
                # If value > 1000, likely in satoshis; if < 10, likely in BTC
                if fee_float > 1000:
                    # Convert from satoshis to BTC
                    fee_btc = fee_float / 1e8
                    if len(fee_values) == 0:  # Note only once
                        notes.append("Converted fees from satoshis to BTC")
                else:
                    fee_btc = fee_float

                fee_values.append(fee_btc)

        if len(fee_values) == 0:
            notes.append("No fee data found in recent blocks")
            return None, None, notes

        # Compute average
        avg_fees = sum(fee_values) / len(fee_values)

        # Round to 8 decimals (BTC precision)
        avg_fees_btc = round(avg_fees, 8)

        return avg_fees_btc, len(fee_values), notes

    except Exception as e:
        notes.append(f"Failed to fetch block fees: {str(e)}")
        return None, None, notes


def _estimate_hashrate_eh_s(difficulty: Optional[float]) -> Optional[float]:
    """
    Estimate network hashrate in EH/s from difficulty.

    Uses standard approximation:
    hashrate_h_s = difficulty * 2^32 / 600 (target block interval)

    Args:
        difficulty: Current network difficulty

    Returns:
        Estimated network hashrate in EH/s, or None if difficulty unavailable
    """
    if difficulty is None:
        return None

    # Standard formula: hashrate = difficulty * 2^32 / target_interval
    hashrate_h_s = difficulty * (2**32) / 600  # 600s = 10 min

    # Convert to EH/s (exahashes per second)
    hashrate_eh_s = hashrate_h_s / 1e18

    # Round to 2 decimals for API stability
    return round(hashrate_eh_s, 2)


def _compute_hashprice_per_th_day(
    block_subsidy_btc: Optional[float],
    btc_price_usd: Optional[float],
    btc_price_eur: Optional[float],
    difficulty: Optional[float],
    avg_fees_btc_per_block: Optional[float] = None,
    fee_window_blocks: Optional[int] = None,
) -> tuple[Optional[float], Optional[float], list[str]]:
    """
    Compute hashprice (revenue per TH/s per day) in USD and EUR.

    Estimates daily miner revenue per TH from network economics.
    Includes transaction fees if available.

    Args:
        block_subsidy_btc: Current block subsidy in BTC
        btc_price_usd: BTC price in USD
        btc_price_eur: BTC price in EUR
        difficulty: Current network difficulty
        avg_fees_btc_per_block: Average tx fees per block in BTC (optional)
        fee_window_blocks: Number of blocks used for fee average (optional)

    Returns:
        (hashprice_usd, hashprice_eur, notes)
    """
    notes = []

    # Check if we have all required inputs
    if difficulty is None or block_subsidy_btc is None:
        return None, None, notes

    # Calculate network hashrate
    hashrate_h_s = difficulty * (2**32) / 600
    network_hashrate_th_s = hashrate_h_s / 1e12  # Convert to TH/s

    # Blocks per day (144 = 24 * 60 / 10)
    blocks_per_day = 144

    # Network BTC per day (subsidy + fees)
    if avg_fees_btc_per_block is not None and avg_fees_btc_per_block > 0:
        network_btc_per_day = (block_subsidy_btc + avg_fees_btc_per_block) * blocks_per_day
        notes.append(f"Hashprice includes avg tx fees ({fee_window_blocks} blocks)")
    else:
        network_btc_per_day = block_subsidy_btc * blocks_per_day
        notes.append("Hashprice excludes tx fees (fees unavailable)")

    # BTC per TH per day
    btc_per_th_day = network_btc_per_day / network_hashrate_th_s

    # Convert to USD and EUR
    hashprice_usd = None
    hashprice_eur = None

    if btc_price_usd is not None:
        hashprice_usd = round(btc_per_th_day * btc_price_usd, 4)

    if btc_price_eur is not None:
        hashprice_eur = round(btc_per_th_day * btc_price_eur, 4)

    return hashprice_usd, hashprice_eur, notes


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

    difficulty, difficulty_notes = _fetch_mempool_difficulty()
    notes.extend(difficulty_notes)

    avg_fees_btc, fee_window, fee_fetch_notes = _fetch_recent_block_fees_btc()
    notes.extend(fee_fetch_notes)

    # Check if we got any data at all
    has_any_data = (
        usd_price is not None
        or eur_price is not None
        or tip_height is not None
        or difficulty is not None
        or avg_fees_btc is not None
        or any(
            [
                fees.fastest_fee,
                fees.half_hour_fee,
                fees.hour_fee,
                fees.economy_fee,
                fees.minimum_fee,
            ]
        )
    )

    # If all fetches failed and we have cached data, return it with a note
    if not has_any_data and _cache is not None:
        notes.append(
            f"Using cached data from {_cache.updated_at} (mempool temporarily unavailable)"
        )
        # Return a copy of cache with updated notes
        cached_response = _cache.model_copy(deep=True)
        cached_response.notes = notes
        return cached_response

    # If no data and no cache, return empty response
    if not has_any_data:
        notes.append("No cached data available; mempool.space is unreachable")

    # Calculate block subsidy from height
    block_subsidy = _calculate_block_subsidy(tip_height)
    if block_subsidy is not None:
        notes.append("Block subsidy computed from current block height")

    # Estimate network hashrate from difficulty
    network_hashrate_eh_s = _estimate_hashrate_eh_s(difficulty)

    # Compute hashprice (revenue per TH/s per day) including fees if available
    hashprice_usd, hashprice_eur, hashprice_notes = _compute_hashprice_per_th_day(
        block_subsidy, usd_price, eur_price, difficulty, avg_fees_btc, fee_window
    )
    notes.extend(hashprice_notes)

    # Create new response
    now = datetime.utcnow()
    response = LiveDataResponse(
        source="mempool.space",
        updated_at=now.isoformat() + "Z",
        btc_price_usd=usd_price,
        btc_price_eur=eur_price,
        block_height=tip_height,
        block_subsidy_btc=block_subsidy,
        fees_recommended=fees,
        difficulty=difficulty,
        network_hashrate_eh_s=network_hashrate_eh_s,
        avg_fees_btc_per_block=avg_fees_btc,
        fee_window_blocks=fee_window,
        hashprice_usd_per_th_day=hashprice_usd,
        hashprice_eur_per_th_day=hashprice_eur,
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

"""Bitcoin mining calculations."""


def calculate_daily_btc_mined(
    miners_count: int,
    miner_hashrate_th: float,
    network_hashrate_eh: float,
    pool_fee: float,
    uptime: float,
    block_reward_btc: float = 3.125,
    blocks_per_day: int = 144,
) -> float:
    """
    Calculate daily BTC mined.

    Args:
        miners_count: Number of mining units
        miner_hashrate_th: Hashrate per miner in TH/s
        network_hashrate_eh: Network hashrate in EH/s
        pool_fee: Pool fee ratio (0-1)
        uptime: Uptime ratio (0-1)
        block_reward_btc: Block subsidy in BTC (default 3.125)
        blocks_per_day: Expected blocks per day (default 144)

    Returns:
        Daily BTC mined after pool fees and uptime adjustment
    """
    # Total BTC mined per day across network
    btc_per_day = blocks_per_day * block_reward_btc

    # Calculate our share of network hashrate
    our_hashrate_hs = miners_count * miner_hashrate_th * 1e12  # Convert TH to H
    network_hashrate_hs = network_hashrate_eh * 1e18  # Convert EH to H
    our_share = our_hashrate_hs / network_hashrate_hs

    # Apply share, pool fee, and uptime
    daily_btc = btc_per_day * our_share * (1 - pool_fee) * uptime

    return daily_btc

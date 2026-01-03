# Mining Engine

A generic Bitcoin mining economics calculator API built with FastAPI.

## Features

- **RESTful API** for mining profitability calculations
- **Versioned assumptions** to track calculation methodology changes
- **Miner library** with popular hardware specifications
- **Preset configurations** for quick scenario modeling
- **Docker support** for easy deployment

## API Endpoints

- `GET /health` - Health check
- `GET /v1/presets` - Available calculation presets
- `GET /v1/assumptions` - Current calculation assumptions and version
- `GET /v1/miners` - Library of mining hardware specifications
- `POST /v1/calculate` - Calculate mining economics
- `GET /v1/live` - Live Bitcoin network and market data from mempool.space

## Quick Start

### Local Development

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in editable mode
pip install -e .

# Run the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Visit http://localhost:8000/docs for interactive API documentation.

### Docker

```bash
# Build and run with docker-compose
docker-compose up --build

# Or with docker
docker build -t mining-engine .
docker run -p 8000:8000 mining-engine
```

## Configuration

Environment variables:

- `CORS_ORIGINS` - Comma-separated list of additional CORS origins (optional)
- `MEMPOOL_BASE_URL` - Base URL for mempool.space API (default: `https://mempool.space`)
- `LIVE_CACHE_TTL_SECONDS` - Cache duration for live data in seconds (default: `60`)
- `LIVE_FEE_WINDOW_BLOCKS` - Number of recent blocks for fee averaging (default: `24`)

## Example Usage

```bash
# Health check
curl http://localhost:8000/health

# Get miner library
curl http://localhost:8000/v1/miners

# Get live Bitcoin network data
curl http://localhost:8000/v1/live

# Calculate mining economics
curl -X POST http://localhost:8000/v1/calculate \
  -H "Content-Type: application/json" \
  -d '{
    "miners_count": 10,
    "miner_id": "antminer_s21_200th_air",
    "electricity_eur_per_kwh": 0.05,
    "uptime": 0.95,
    "btc_price_eur": 40000,
    "network_hashrate_eh": 500,
    "pool_fee": 0.02,
    "capex_eur": 50000,
    "opex_eur_month": 500,
    "horizon_days": 365
  }'
```

### Live Data Response Example

The `/v1/live` endpoint returns real-time Bitcoin network and market data:

```json
{
  "source": "mempool.space",
  "updated_at": "2026-01-03T12:00:00.000000Z",
  "btc_price_usd": 95000.50,
  "btc_price_eur": 88000.25,
  "block_height": 825000,
  "block_subsidy_btc": 6.25,
  "fees_recommended": {
    "fastest_fee": 20,
    "half_hour_fee": 15,
    "hour_fee": 10,
    "economy_fee": 5,
    "minimum_fee": 1
  },
  "difficulty": 75502165623893.72,
  "network_hashrate_eh_s": 540.5,
  "avg_fees_btc_per_block": 0.27,
  "fee_window_blocks": 24,
  "hashprice_usd_per_th_day": 0.0951,
  "hashprice_eur_per_th_day": 0.0882,
  "notes": [
    "Block subsidy computed from current block height",
    "Hashprice includes avg tx fees (24 blocks)"
  ]
}
```

**Features:**
- 60-second in-memory cache to prevent rate bursts
- Graceful degradation: returns partial data if some endpoints fail
- Fallback to cached data if mempool.space is temporarily unavailable
- Block subsidy automatically computed from current height
- Network hashrate estimated from difficulty (EH/s)
- Average transaction fees computed from recent blocks (configurable window)
- Hashprice computed as revenue per TH/s per day (includes tx fees when available)

**Performance Notes:**
- Fee window defaults to 24 blocks for optimal performance on free-tier hosting
- Larger windows (up to 144) provide more stable averages but may increase latency
- All mempool.space API calls have 3-second timeouts

## Testing

```bash
pytest
```

## Model Simplifications

The current calculation model includes the following simplifications (documented in response notes):

- Transaction fees are not included in mining revenue
- Bitcoin halving events are not modeled (constant subsidy)
- Network hashrate is provided as a fixed input (not projected)
- Difficulty adjustments are approximated through hashrate
- This provides first-order approximations suitable for initial analysis

## License

MIT

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

## Example Usage

```bash
# Health check
curl http://localhost:8000/health

# Get miner library
curl http://localhost:8000/v1/miners

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

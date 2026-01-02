"""Mining Engine FastAPI application."""

from fastapi import FastAPI

from app.core.cors import setup_cors
from app.models.responses import HealthResponse
from app.api.v1.routes import router as v1_router


app = FastAPI(
    title="Mining Engine",
    description="Generic Bitcoin mining economics calculator API",
    version="0.1.0",
)

# Setup CORS
setup_cors(app)

# Include v1 routes
app.include_router(v1_router, prefix="/v1", tags=["v1"])


@app.get("/health", response_model=HealthResponse, tags=["health"])
def health_check() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(status="ok", service="mining-engine")

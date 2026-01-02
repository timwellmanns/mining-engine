import os
from typing import List


def get_cors_origins() -> List[str]:
    """Get CORS origins from environment and defaults."""
    default_origins = [
        "http://localhost:5173",
        "https://mining.timwellmanns.com",
    ]

    # Add additional origins from environment variable
    env_origins = os.getenv("CORS_ORIGINS", "")
    if env_origins:
        additional_origins = [origin.strip() for origin in env_origins.split(",") if origin.strip()]
        default_origins.extend(additional_origins)

    return default_origins


ASSUMPTIONS_VERSION = "2026.01.0"

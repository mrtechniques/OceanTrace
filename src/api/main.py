"""
Main application factory and router registration for OceanTrace API.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from src.api.dependencies import ModelService
from src.api.routers import ais, correlation, health, predict, satellite

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("oceantrace.api")

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan context manager to pre-warm model weights on server startup."""
    logger.info("Initializing OceanTrace backend...")
    service = ModelService.get_instance()
    try:
        service.load()
        logger.info(
            "Neural network ready on device: %s (Epoch: %s, Best Val Dice: %s)",
            service.device_str,
            service.metadata.get("epoch"),
            service.metadata.get("best_val_dice"),
        )
    except Exception as exc:
        logger.error("Failed to pre-warm model during startup: %s", exc)
    yield
    logger.info("OceanTrace backend shutting down.")


def create_app() -> FastAPI:
    """Instantiate and configure the OceanTrace FastAPI application."""
    app = FastAPI(
        title="OceanTrace — Marine Oil Spill Detection API",
        description=(
            "Automated satellite SAR & optical oil spill detection system.\n\n"
            "**Key Capabilities:**\n"
            "- Upload Sentinel-1 SAR GeoTIFF, PNG, and JPG imagery for deep-learning inference.\n"
            "- Pre-trained ResNet-34 U-Net segmentation pipeline.\n"
            "- Full geospatial metadata preservation and boundary-blended tiled inference.\n"
            "- Binary segmentation mask and publication-quality 3-panel visualization generation.\n\n"
            "*Notice: Model performance on synthetic data verifies mathematical and pipeline mechanics; "
            "operational deployment requires validation against real-world ground-truth marine SAR slicks.*"
        ),
        version="0.1.0",
        lifespan=lifespan,
    )

    # Enable CORS for frontend integration across any local port or domain
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register API routers
    app.include_router(health.router, prefix="/api")
    app.include_router(predict.router, prefix="/api")
    app.include_router(ais.router, prefix="/api")
    app.include_router(satellite.router, prefix="/api")
    app.include_router(correlation.router, prefix="/api")

    # Mount static frontend assets if available
    ui_dir = REPO_ROOT / "ui"
    if ui_dir.exists():
        app.mount("/ui", StaticFiles(directory=str(ui_dir), html=True), name="ui")

    @app.get("/", include_in_schema=False)
    def root():
        """Redirect root index to the integrated UI, fallback to API documentation."""
        if (REPO_ROOT / "ui" / "index.html").exists():
            return RedirectResponse(url="/ui/index.html")
        return RedirectResponse(url="/docs")

    return app


app = create_app()

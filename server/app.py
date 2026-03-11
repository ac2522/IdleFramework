"""FastAPI application -- serves API + static frontend."""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from server.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure games directories exist
    Path(settings.games_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.user_games_dir).mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(
    title="IdleFramework API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and include route modules
from server.routes import analysis, engine, games  # noqa: E402

app.include_router(games.router, prefix="/api/v1/games", tags=["games"])
app.include_router(analysis.router, prefix="/api/v1/analysis", tags=["analysis"])
app.include_router(engine.router, prefix="/api/v1/engine", tags=["engine"])

# Mount static frontend (production build) if it exists
_static_dir = Path(__file__).parent.parent / "frontend" / "dist"
if _static_dir.is_dir():
    from fastapi.staticfiles import StaticFiles
    app.mount("/", StaticFiles(directory=str(_static_dir), html=True), name="frontend")

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .routes.health import router as health_router
from .routes.analytics import router as analytics_router
from .routes.agent import router as agent_router
from .routes.guardrails import router as guardrails_router
from .routes.demo import router as demo_router
from .routes.commerce import router as commerce_router
from .routes.measurement import router as measurement_router
from .routes.razorpay import router as razorpay_router
from .routes.experiments import router as experiments_router
from .services.database import ensure_database_directory


@asynccontextmanager
async def lifespan(_: FastAPI):
    ensure_database_directory()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )
    app.include_router(health_router)
    app.include_router(razorpay_router)
    app.include_router(analytics_router)
    app.include_router(agent_router)
    app.include_router(guardrails_router)
    app.include_router(demo_router)
    app.include_router(commerce_router)
    app.include_router(measurement_router)
    app.include_router(experiments_router)
    return app

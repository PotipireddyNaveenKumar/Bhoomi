import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.logging import logger
from app.db.session import engine
from app.db.base import Base

# Routers
from app.api.v1.auth import router as auth_router
from app.api.v1.assistant import router as assistant_router
from app.api.v1.farmer import router as farmer_router
from app.api.v1.farms import router as farms_router
from app.api.v1.chat import router as chat_router
from app.api.v1.voice import router as voice_router
from app.api.v1.image import router as image_router
from app.api.v1.weather import router as weather_router
from app.api.v1.market import router as market_router
from app.api.v1.crop import router as crop_router
from app.api.v1.yield_routes import router as yield_router
from app.api.v1.profit import router as profit_router
from app.api.v1.simulation import router as simulation_router
from app.api.v1.risk import router as risk_router
from app.api.v1.tasks import router as tasks_router
from app.api.v1.ml import router as ml_router
from app.api.v1.vision_routes import router as vision_router
from app.api.v1.rag_routes import router as rag_router
from app.api.v1.farm_routes import router as farm_mgmt_router
from app.api.v1.farm_manager_routes import router as farm_manager_router
from app.api.v1.decision_routes import router as decision_router
from app.api.v1.pilot import router as pilot_router
from app.api.v1.demo import router as demo_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB tables for development/testing
    logger.info("Initializing BHOOMI V2 database schema...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database schema initialized.")
    from app.services.demo.demo_service import DemoModeService
    from app.db.session import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        await DemoModeService.ensure_canonical_demo_data(session)
    DemoModeService.reset_demo_state()
    logger.info("Initialized pristine demo tasks and canonical demo farmer in database.")
    yield
    logger.info("Shutting down BHOOMI V2 backend...")
    await engine.dispose()
    logger.info("Database engine connections closed.")

app = FastAPI(
    title=settings.APP_NAME,
    description="Voice-First Multilingual Personal AI Farm Manager & Agricultural Decision Intelligence Platform",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS
allowed_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:8080",
    "http://127.0.0.1:8080",
    "http://localhost:5000",
    "http://127.0.0.1:5000",
]
if isinstance(settings.BACKEND_CORS_ORIGINS, list):
    for o in settings.BACKEND_CORS_ORIGINS:
        if o != "*" and o not in allowed_origins:
            allowed_origins.append(o)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled Exception on {request.url.path}: {str(exc)}", exc_info=True)
    err_str = str(exc)
    for secret in [settings.SECRET_KEY, settings.GEMINI_API_KEY, settings.SARVAM_API_KEY, settings.OPENAI_API_KEY]:
        if secret and len(secret) > 6 and secret in err_str:
            err_str = err_str.replace(secret, "[REDACTED]")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": err_str or "An unexpected error occurred. Please try again.",
            }
        }
    )

# Web Frontend Static Directory
WEB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "web"))
STATIC_DIR = os.path.join(WEB_DIR, "static")

# Root Health Check & Web Entrypoint
@app.get("/", tags=["Health"])
async def root(request: Request):
    accept = request.headers.get("accept", "")
    if "application/json" in accept and "text/html" not in accept:
        return {
            "app": settings.APP_NAME,
            "status": "healthy",
            "version": "2.0.0",
            "demo_mode": settings.DEMO_MODE,
            "voice_provider": settings.VOICE_PROVIDER,
            "llm_provider": settings.LLM_PROVIDER,
            "weather_provider": settings.WEATHER_PROVIDER,
            "market_provider": settings.MARKET_PROVIDER,
            "real_field_pilot_data": "NOT_PRESENT",
            "production_status": "NOT_PRODUCTION_READY",
            "rice_status": "RESEARCH_ONLY",
            "product_loop": "ASK -> REMEMBER -> PLAN -> MONITOR -> PREDICT -> COMPARE -> DECIDE -> REMIND -> ADAPT"
        }
    index_path = os.path.join(WEB_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {
        "app": settings.APP_NAME,
        "status": "healthy",
        "version": "2.0.0",
        "demo_mode": settings.DEMO_MODE
    }

@app.get("/health", tags=["Health"])
async def health():
    return {
        "app": settings.APP_NAME,
        "status": "healthy",
        "version": "2.0.0",
        "demo_mode": settings.DEMO_MODE,
        "voice_provider": settings.VOICE_PROVIDER,
        "llm_provider": settings.LLM_PROVIDER,
        "weather_provider": settings.WEATHER_PROVIDER,
        "market_provider": settings.MARKET_PROVIDER
    }

# Register V1 Routers
api_v1 = settings.API_V1_STR
app.include_router(auth_router, prefix=api_v1)
app.include_router(assistant_router, prefix=api_v1)
app.include_router(farmer_router, prefix=api_v1)
app.include_router(farms_router, prefix=api_v1)
app.include_router(chat_router, prefix=api_v1)
app.include_router(voice_router, prefix=api_v1)
app.include_router(image_router, prefix=api_v1)
app.include_router(weather_router, prefix=api_v1)
app.include_router(market_router, prefix=api_v1)
app.include_router(crop_router, prefix=api_v1)
app.include_router(yield_router, prefix=api_v1)
app.include_router(profit_router, prefix=api_v1)
app.include_router(simulation_router, prefix=api_v1)
app.include_router(risk_router, prefix=api_v1)
app.include_router(tasks_router, prefix=api_v1)
app.include_router(ml_router, prefix=api_v1)
app.include_router(vision_router, prefix=api_v1)
app.include_router(rag_router, prefix=api_v1)
app.include_router(farm_mgmt_router, prefix=api_v1)
app.include_router(farm_manager_router, prefix=api_v1)
app.include_router(decision_router, prefix=api_v1)
app.include_router(pilot_router, prefix=api_v1)
app.include_router(demo_router, prefix=api_v1)

# Web Frontend Mounting
WEB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "web"))
STATIC_DIR = os.path.join(WEB_DIR, "static")

if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/app", tags=["System"])
async def app_portal():
    index_path = os.path.join(WEB_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return JSONResponse(status_code=404, content={"detail": "Web app index.html not found"})

@app.get("/manifest.json", tags=["System"])
async def manifest():
    manifest_path = os.path.join(WEB_DIR, "manifest.json")
    if os.path.exists(manifest_path):
        return FileResponse(manifest_path, media_type="application/json")
    return JSONResponse(status_code=404, content={"detail": "Manifest not found"})

@app.get("/sw.js", tags=["System"])
async def service_worker():
    sw_path = os.path.join(WEB_DIR, "sw.js")
    if os.path.exists(sw_path):
        return FileResponse(sw_path, media_type="application/javascript")
    return JSONResponse(status_code=404, content={"detail": "Service worker not found"})


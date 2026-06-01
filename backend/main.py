"""
--- FILE: backend/main.py ---

FastAPI app entrypoint: registers routers, middleware and startup lifespan.
"""
import asyncio
import logging
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from backend.database.db import init_db
from backend.routers.live_interview_router import router as interview_router
from intake.job_requisition_api import router as job_requisition_router
from screening.screening_api import router as screening_router
from outreach.outreach_api import router as outreach_router
from prescreening.prescreening_api import router as prescreening_router
from analytics.routers.analytics_router import router as analytics_router
from offer.routers.offer_router import router as offer_router
from onboarding.routers.onboarding_router import router as onboarding_router
from backend.middleware.cors import add_cors
from backend.middleware.request_logging import log_request
from backend.middleware.rate_limit import rate_limit_middleware
from backend.config import settings
from fastapi.responses import FileResponse

logger = logging.getLogger("interview.app")


def create_app() -> FastAPI:
    app = FastAPI(title="IntelliHire Interview API")

    # Middleware
    add_cors(app)
    app.middleware("http")(log_request)

    # rate limit as dependency-style middleware: added as event handler wrapper
    @app.middleware("http")
    async def _rate_limit(request, call_next):
        await rate_limit_middleware(request)
        return await call_next(request)

    # include routers
    app.include_router(interview_router, prefix="/api/v1/interview")
    app.include_router(job_requisition_router, prefix="/api")
    app.include_router(screening_router, prefix="/api")
    app.include_router(outreach_router, prefix="/api")
    app.include_router(prescreening_router, prefix="/api")
    app.include_router(analytics_router, prefix="/api")
    app.include_router(offer_router, prefix="/api")
    app.include_router(onboarding_router, prefix="/api")

    # Serve frontend static files via explicit SPA routes below (avoid mounting at '/'
    # which can conflict with programmatic fallback routing in some dev setups).

    # Explicit root route: return index.html so visiting / loads the dashboard
    try:
        index_file = Path(__file__).resolve().parents[1] / "frontend" / "index.html"
        if index_file.exists():
            @app.get("/", include_in_schema=False)
            async def _root():
                return FileResponse(str(index_file))
            @app.get("/_which_index", include_in_schema=False)
            async def _which_index():
                return {"index": str(index_file), "exists": index_file.exists()}
            @app.get("/{full_path:path}", include_in_schema=False)
            async def _spa(full_path: str):
                # Serve files directly from frontend when present, else return index.html (SPA fallback)
                try:
                    candidate = (index_file.parent / full_path).resolve()
                    # Prevent escaping outside frontend dir
                    if not str(candidate).startswith(str(index_file.parent)):
                        return FileResponse(str(index_file))
                    if candidate.exists() and candidate.is_file():
                        return FileResponse(str(candidate))
                    # Support requests from nested SPA paths like /candidate/services/... by
                    # attempting to strip the first path segment and resolving again.
                    if "/" in full_path:
                        _, rest = full_path.split("/", 1)
                        candidate2 = (index_file.parent / rest).resolve()
                        if str(candidate2).startswith(str(index_file.parent)) and candidate2.exists() and candidate2.is_file():
                            return FileResponse(str(candidate2))
                    # If a candidate interview route is requested, serve the dedicated
                    # candidate-prescreening page when available instead of the main SPA.
                    if full_path.startswith("candidate/interview"):
                        cp = index_file.parent / "candidate-prescreening.html"
                        if cp.exists():
                            return FileResponse(str(cp))
                except Exception:
                    pass
                return FileResponse(str(index_file))
    except Exception:
        logger.exception("Failed to add explicit root index route")

    @app.get("/health")
    async def health():
        return JSONResponse({"status": "ok"})

    @app.on_event("startup")
    async def startup():
        logger.info("Initializing DB...")
        await init_db()
        # Attempt to test redis availability if configured
        try:
            import aioredis
            redis_url = getattr(settings, "REDIS_URL", None)
            if redis_url:
                r = await aioredis.from_url(redis_url)
                await r.ping()
                logger.info("Redis reachable")
        except Exception:
            logger.info("Redis not configured or unreachable; continuing")

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=settings.API_PORT)

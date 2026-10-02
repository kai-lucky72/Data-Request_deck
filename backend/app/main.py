"""FastAPI application entry point, request logging, and API registration."""

import logging
import json
import time
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.api import auth
from app.api import requests, episodes, analytics, users, events

logger = logging.getLogger("dataset_desk.requests")
logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title=settings.APP_NAME,
    description="A FastAPI application for dataset request management",
    version="0.1.0",
    docs_url="/docs",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(requests.router)
app.include_router(episodes.router)
app.include_router(analytics.router)
app.include_router(users.router)
app.include_router(events.router)

# Serve Vite's production build. Keep the lookup usable from both the Docker
# working directory (/app) and a local repository checkout.
_repo_root = Path(__file__).resolve().parents[2]
_dist_candidates = (Path.cwd() / "frontend" / "dist", _repo_root / "frontend" / "dist")
FRONTEND_DIST = next((path for path in _dist_candidates if path.is_dir()), _dist_candidates[0])
if (FRONTEND_DIST / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")


@app.get("/", include_in_schema=False)
@app.get("/login", include_in_schema=False)
@app.get("/client", include_in_schema=False)
@app.get("/operator/requests", include_in_schema=False)
@app.get("/operator/episodes", include_in_schema=False)
@app.get("/operator/analytics", include_in_schema=False)
@app.get("/admin/users", include_in_schema=False)
@app.get("/admin/requests", include_in_schema=False)
@app.get("/admin/episodes", include_in_schema=False)
@app.get("/admin/analytics", include_in_schema=False)
def frontend_app():
    """Return the React entry point for known client and staff routes."""
    index = FRONTEND_DIST / "index.html"
    if not index.is_file():
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="Frontend build is missing")
    return FileResponse(index)

@app.middleware("http")
async def log_request(request: Request, call_next):
    """Emit one structured JSON log record for every completed HTTP request."""
    started = time.perf_counter()
    status_code = 500  # If endpoint code raises unexpectedly, report that as a server error.
    try:
        response = await call_next(request)
        status_code = response.status_code
    except Exception:
        # Still emit the access record before Starlette's outer error handler responds.
        raise
    finally:
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        # Auth dependency stores user only in the dependency scope, so decode the
        # subject for logging; route dependencies separately verify authorization.
        user_id = None
        authorization = request.headers.get("authorization", "")
        if authorization.lower().startswith("bearer "):
            from app.core.security import decode_access_token
            claims = decode_access_token(authorization.split(" ", 1)[1])
            user_id = claims.get("sub") if claims else None
        logger.info("%s", json.dumps({
            "event": "http_request",
            "method": request.method,
            "path": request.url.path,
            "status": status_code,
            "duration_ms": duration_ms,
            "user_id": user_id,
        }))
    return response


# setting up the endpoint to check the health of the app
@app.get("/health")
def health_check():
    return{
        "status":"ok",
        "app":settings.APP_NAME
    }

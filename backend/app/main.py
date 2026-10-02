"""FastAPI application entry point, request logging, and API registration."""

import logging
import json
import time

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.api import auth
from app.api import requests, episodes, analytics, users

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

app.mount("/static", StaticFiles(directory="frontend"), name="frontend")

@app.get("/", include_in_schema=False)
def home():
    return FileResponse("frontend/index.html")

@app.get("/client.html", include_in_schema=False)
def client_page():
    return FileResponse("frontend/client.html")

@app.get("/operator.html", include_in_schema=False)
def operator_page():
    return FileResponse("frontend/operator.html")

@app.get("/operator-episodes.html", include_in_schema=False)
def operator_episodes_page():
    return FileResponse("frontend/operator-episodes.html")

@app.get("/operator-analytics.html", include_in_schema=False)
def operator_analytics_page():
    return FileResponse("frontend/operator-analytics.html")

@app.get("/admin.html", include_in_schema=False)
def admin_page():
    return FileResponse("frontend/admin.html")

@app.get("/styles.css", include_in_schema=False)
def styles():
    return FileResponse("frontend/styles.css")

@app.get("/app.js", include_in_schema=False)
def app_js():
    return FileResponse("frontend/app.js")

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

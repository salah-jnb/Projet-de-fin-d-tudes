import logging
import sys
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.requests import Request
from src.controllers.api_controllers import router
from src.application.app_service_impl import ApiServiceImpl
from src.application.nightly_scheduler import (
    get_scheduler_status,
    start_nightly_scheduler,
    stop_nightly_scheduler,
)

app = FastAPI(title="Système Distributeur PFE")
_nightly_service = ApiServiceImpl()

# Music cache served read-only on the LAN: the Pi receives a URL like
# http://<host>:<port>/cache/music/<sha1>.wav from /api/audio/speech-to-action
# and streams it directly (cheaper than embedding ~5 MB in JSON).
_MUSIC_CACHE_DIR = Path("cache/music").resolve()
_MUSIC_CACHE_DIR.mkdir(parents=True, exist_ok=True)
app.mount(
    "/cache/music",
    StaticFiles(directory=str(_MUSIC_CACHE_DIR)),
    name="music_cache",
)


@app.middleware("http")
async def log_each_request(request: Request, call_next):
    """Trace chaque requête entrante (utile pour vérifier que le mobile atteint bien le PC)."""
    client_host = request.client.host if request.client else "?"
    print(f"[HTTP] {request.method} {request.url.path} client={client_host}", flush=True)
    return await call_next(request)


# Inclure toutes les routes définies dans le contrôleur
app.include_router(router, prefix="/api")


@app.on_event("startup")
def _configure_console_and_http_loggers():
    """Évite UnicodeEncodeError / 'charmap' sous Windows (logs HTTP, arabe, etc.)."""
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    if hasattr(sys.stderr, "reconfigure"):
        try:
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    for name in (
        "urllib3",
        "urllib3.connectionpool",
        "urllib3.util.retry",
        "requests",
        "requests.packages.urllib3",
        "http.client",
    ):
        logging.getLogger(name).setLevel(logging.WARNING)


@app.on_event("startup")
def list_routes():
    print("\n--- ROUTES ENREGISTRÉES ---")
    for route in app.routes:
        methods = getattr(route, "methods", None)
        if methods:
            print(f"[{methods}] {route.path}")
        elif hasattr(route, "path"):
            print(f"[MOUNT] {route.path}")
    print("---------------------------\n")


@app.on_event("startup")
def _start_nightly_user_scheduler():
    start_nightly_scheduler(_nightly_service.run_nightly_user_webhook_trigger)


@app.on_event("shutdown")
def _stop_nightly_user_scheduler():
    stop_nightly_scheduler()


@app.get("/")
def home():
    return {"message": "Serveur opérationnel", "routes_prefix": "/api"}

@app.get("/test")
def test():
    return {"message": "Test OK"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
import logging
import os

from fastapi import FastAPI, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.auth import user_from_token
from app.config import settings
from app.database import SessionLocal, engine, init_db
from app.routers import admin, auth, donors, hospitals, matching, notifications, requests, stats
from app.services.websocket import manager

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("bloodbridge")

# Creates missing tables only; never drops or alters existing data.
init_db()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Blood Bridge Real-Time Blood Request & Donor Matching System API",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,  # auth uses a bearer token header, not cookies
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    """Return readable validation messages, e.g. 'Value error, Blood group is required for donors.'"""
    messages = []
    for err in exc.errors():
        msg = str(err.get("msg", "Invalid value")).removeprefix("Value error, ")
        loc = [str(p) for p in err.get("loc", []) if p not in ("body", "query", "path")]
        if err.get("type") != "value_error" and loc:
            msg = f"{loc[-1].replace('_', ' ').capitalize()}: {msg}"
        messages.append(msg)
    return JSONResponse(status_code=422, content={"detail": "; ".join(messages) or "Invalid input.",
                                                  "errors": [{"loc": e.get("loc"), "msg": e.get("msg")} for e in exc.errors()]})


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Something went wrong on our side. Please try again."})


for r in (auth, donors, requests, matching, hospitals, notifications, admin, stats):
    app.include_router(r.router, prefix=settings.API_V1_STR)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(default="")):
    """Authenticated real-time channel: connect to /ws?token=<JWT>."""
    db = SessionLocal()
    try:
        user = user_from_token(db, token) if token else None
    finally:
        db.close()
    if user is None:
        await websocket.close(code=4401)
        return
    await manager.connect(user.id, websocket)
    try:
        while True:
            await websocket.receive_text()
            await websocket.send_json({"event": "PONG"})
    except WebSocketDisconnect:
        manager.disconnect(user.id, websocket)


@app.get("/api/health")
def health():
    db_ok = True
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        db_ok = False
    return {"status": "ok" if db_ok else "degraded", "database": "ok" if db_ok else "unreachable",
            "database_engine": engine.dialect.name, "version": settings.VERSION}


# Serve the built React app from the same server (single-service deployment, e.g. Render).
# FRONTEND_DIST may be absolute or relative to the backend folder, e.g. "../frontend/dist".
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_dist = settings.FRONTEND_DIST
if _dist and not os.path.isabs(_dist):
    _dist = os.path.normpath(os.path.join(_BACKEND_DIR, _dist))
if _dist and not os.path.isfile(os.path.join(_dist, "index.html")):
    logger.warning("FRONTEND_DIST=%s has no index.html; the website will not be served. "
                   "Build the frontend first (npm run build).", _dist)
    _dist = ""
if _dist:
    _dist_real = os.path.realpath(_dist)
    if os.path.isdir(os.path.join(_dist, "assets")):
        app.mount("/assets", StaticFiles(directory=os.path.join(_dist, "assets")), name="assets")
    logger.info("Serving the website from %s", _dist_real)

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_react_app(full_path: str):
        if full_path.startswith("api/") or full_path == "ws":
            return JSONResponse(status_code=404, content={"detail": "Not found."})
        file_path = os.path.realpath(os.path.join(_dist_real, full_path))
        if file_path.startswith(_dist_real + os.sep) and os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(_dist_real, "index.html"))

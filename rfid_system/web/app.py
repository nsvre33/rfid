"""FastAPI web application for RFID dashboard."""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.event_broker import broker
from backend.data_manager import data_manager
from backend.config import config


# Create FastAPI app
app = FastAPI(title="RFID Dashboard", version="1.0.0")

# Get the directory where this file is located
BASE_DIR = Path(__file__).parent

# Mount static files
static_dir = BASE_DIR / "static"
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/", response_class=HTMLResponse)
async def root() -> str:
    """Serve the main dashboard HTML page."""
    index_path = static_dir / "index.html"
    if index_path.exists():
        return index_path.read_text(encoding='utf-8')
    return HTMLResponse(
        content="<h1>Dashboard not found</h1><p>Please ensure index.html exists in web/static/</p>",
        status_code=404
    )


@app.get("/api/scans")
async def get_scans(limit: int = 50) -> JSONResponse:
    """Get recent scan events."""
    events = broker.get_recent(limit)
    return JSONResponse(content={"scans": events})


@app.get("/api/registry")
async def get_registry() -> JSONResponse:
    """Get all registry entries."""
    entries = data_manager.get_registry_entries()
    return JSONResponse(content={"entries": entries})


@app.get("/api/stats")
async def get_stats() -> JSONResponse:
    """Get scan statistics."""
    stats = broker.get_stats()
    return JSONResponse(content=stats)


def run_server(host: str = "0.0.0.0", port: int = 8000) -> None:
    """Run the FastAPI server with uvicorn."""
    import uvicorn
    uvicorn.run(
        "web.app:app",
        host=host,
        port=port,
        log_level="error",
        reload=False
    )

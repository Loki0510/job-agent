from pathlib import Path
from fastapi.responses import HTMLResponse
from app.worker_api import app

DASHBOARD_PATH=Path(__file__).with_name("dashboard.html")

@app.get("/dashboard",response_class=HTMLResponse)
async def dashboard():
    if not DASHBOARD_PATH.exists():
        return HTMLResponse("<h1>Dashboard unavailable</h1>",status_code=404)
    return HTMLResponse(DASHBOARD_PATH.read_text(encoding="utf-8"))

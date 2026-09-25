import os
import pathlib
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

WORKER_API=os.getenv("WORKER_API","https://job-agent-worker-production.up.railway.app").rstrip("/")
SETUP_TOKEN=os.getenv("SETUP_TOKEN","")
DASHBOARD=pathlib.Path(__file__).with_name("dashboard.html")

app=FastAPI(title="Job Agent Dashboard")

def _check(token):
    if not SETUP_TOKEN or token!=SETUP_TOKEN:
        raise HTTPException(status_code=401,detail="invalid access token")

@app.get("/",response_class=HTMLResponse)
async def home(token: str):
    _check(token)
    page=DASHBOARD.read_text(encoding="utf-8")
    return HTMLResponse(page)

@app.get("/applications")
async def applications(token: str):
    _check(token)
    async with httpx.AsyncClient(timeout=20,follow_redirects=True) as client:
        response=await client.get(f"{WORKER_API}/applications",params={"token":SETUP_TOKEN})
        response.raise_for_status()
        return response.json()

@app.get("/health")
async def health():
    async with httpx.AsyncClient(timeout=10,follow_redirects=True) as client:
        try:
            response=await client.get(f"{WORKER_API}/health")
            data=response.json()
            return {"status":"ok","auto_submit":bool(data.get("auto_submit"))}
        except Exception:
            return {"status":"degraded","auto_submit":False}

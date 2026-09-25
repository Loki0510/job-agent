import asyncio
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Header, HTTPException
from app.core.config import settings
from app.core.profile import PROFILE
from app.services.discovery import discover_configured, records, eligible_records, stats
from app.services.application_log import add as add_application, entries as application_entries

async def _poller():
    while True:
        try:
            await discover_configured()
        except Exception as exc:
            print(f"discovery error: {exc}")
        await asyncio.sleep(max(int(settings.poll_seconds),60))

@asynccontextmanager
async def lifespan(app: FastAPI):
    task=asyncio.create_task(_poller())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

app=FastAPI(title="Autonomous Job Agent",version="0.5",lifespan=lifespan)

@app.get("/health")
async def health():
    return {"status":"ok","auto_submit":settings.auto_submit}

@app.get("/profile")
async def profile():
    return {
        "country":PROFILE.country,
        "locations":PROFILE.locations,
        "remote_ok":PROFILE.remote_ok,
        "hybrid_ok":PROFILE.hybrid_ok,
        "onsite_ok":PROFILE.onsite_ok,
        "willing_to_relocate":PROFILE.willing_to_relocate,
        "min_salary_usd":PROFILE.min_salary_usd,
        "authorized_us":PROFILE.authorized_us,
        "requires_sponsorship":PROFILE.requires_sponsorship_now_or_future,
        "years_experience":PROFILE.years_experience,
        "primary_titles":PROFILE.primary_titles,
        "secondary_titles":PROFILE.secondary_titles,
        "skills":PROFILE.skills,
    }

@app.post("/discover")
async def discover_now():
    new=await discover_configured()
    return {"new_jobs":len(new),"jobs":new}

@app.get("/jobs")
async def jobs():
    data=records()
    return {"count":len(data),"jobs":data}

@app.get("/queue")
async def application_queue():
    data=eligible_records()
    return {"count":len(data),"jobs":data}

@app.get("/stats")
async def discovery_stats():
    return stats()

@app.post("/applications/report")
async def application_report(payload: dict, x_report_token: str|None=Header(default=None)):
    expected=os.getenv("REPORT_TOKEN","")
    if expected and x_report_token!=expected:
        raise HTTPException(status_code=401,detail="invalid report token")
    return add_application(payload)

@app.get("/applications")
async def applications():
    data=application_entries()
    return {"count":len(data),"applications":data}

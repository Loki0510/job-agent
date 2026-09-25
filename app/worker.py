import asyncio
import json
import os
import httpx
from app.submission.browser import inspect_and_fill
from app.worker_state import (
    append_history, baseline_ids, has_baseline, save_baseline, terminal_ids
)

DISCOVERY_API=os.getenv("DISCOVERY_API","https://job-agent-live-production-473f.up.railway.app").rstrip("/")
REPORT_TOKEN=os.getenv("REPORT_TOKEN","")
AUTO_SUBMIT=os.getenv("AUTO_SUBMIT","false").strip().lower() in {"1","true","yes","on"}
POLL_SECONDS=max(int(os.getenv("APPLICATION_POLL_SECONDS","120")),60)
BATCH_SIZE=max(int(os.getenv("APPLICATION_BATCH_SIZE","8")),1)
FORM_TIMEOUT=max(int(os.getenv("FORM_TIMEOUT_SECONDS","75")),30)
_seen=set()

def log(payload):
    print(json.dumps(payload,ensure_ascii=False),flush=True)

async def report(client,payload):
    headers={"X-Report-Token":REPORT_TOKEN} if REPORT_TOKEN else {}
    try:
        await client.post(f"{DISCOVERY_API}/applications/report",json=payload,headers=headers,timeout=20)
    except Exception as exc:
        log({"report_error":str(exc),"job":payload.get("external_id")})

async def fetch_queue(client):
    response=await client.get(f"{DISCOVERY_API}/queue",timeout=30)
    response.raise_for_status()
    return response.json().get("jobs",[])

async def cycle():
    log({"cycle":"start","seen":len(_seen),"auto_submit":AUTO_SUBMIT})
    async with httpx.AsyncClient(follow_redirects=True) as client:
        jobs=await fetch_queue(client)

        if AUTO_SUBMIT and not has_baseline():
            payload=save_baseline([j.get("external_id") for j in jobs if j.get("external_id")])
            log({"baseline":"created","count":len(payload.get("external_ids",[]))})
            return

        completed=terminal_ids()
        baseline=baseline_ids() if AUTO_SUBMIT else set()

        candidates=[]
        for job in jobs:
            external_id=job.get("external_id")
            if not external_id or external_id in _seen or external_id in completed:
                continue
            if AUTO_SUBMIT and external_id in baseline:
                continue
            candidates.append(job)

        candidates.sort(
            key=lambda j: (float(j.get("posted_ts") or 0), float(j.get("fit_score") or 0)),
            reverse=True,
        )
        candidates=candidates[:BATCH_SIZE]
        log({
            "cycle":"fetched",
            "eligible":len(jobs),
            "selected":len(candidates),
            "baseline":len(baseline),
            "completed":len(completed),
        })

        for job in candidates:
            external_id=job.get("external_id")
            _seen.add(external_id)
            log({"job":"start","external_id":external_id,"company":job.get("company"),"title":job.get("title")})
            try:
                result=await asyncio.wait_for(
                    inspect_and_fill(job,dry_run=not AUTO_SUBMIT),
                    timeout=FORM_TIMEOUT,
                )
            except asyncio.TimeoutError:
                result={"status":"blocked","reason":"application form timed out","unknown_required":[]}
            except Exception as exc:
                result={"status":"blocked","reason":f"application error: {exc}","unknown_required":[]}

            payload={
                "external_id":external_id,
                "company":job.get("company"),
                "title":job.get("title"),
                "location":job.get("location"),
                "posted_at":job.get("posted_at"),
                "posted_ts":job.get("posted_ts"),
                "apply_url":job.get("apply_url"),
                "resume_profile":job.get("resume_profile"),
                "fit_score":job.get("fit_score"),
                "mode":"live" if AUTO_SUBMIT else "dry_run",
                **result,
            }
            append_history(payload)
            log(payload)
            await report(client,payload)
    log({"cycle":"done"})

async def main():
    log({
        "worker":"started",
        "auto_submit":AUTO_SUBMIT,
        "poll_seconds":POLL_SECONDS,
        "form_timeout":FORM_TIMEOUT,
    })
    while True:
        try:
            await cycle()
        except Exception as exc:
            log({"worker_error":str(exc)})
        await asyncio.sleep(POLL_SECONDS)

if __name__=="__main__":
    asyncio.run(main())

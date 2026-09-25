import asyncio
import json
import os
import httpx
from app.submission.browser import inspect_and_fill

DISCOVERY_API=os.getenv("DISCOVERY_API","https://job-agent-live-production-473f.up.railway.app").rstrip("/")
REPORT_TOKEN=os.getenv("REPORT_TOKEN","")
AUTO_SUBMIT=os.getenv("AUTO_SUBMIT","false").strip().lower() in {"1","true","yes","on"}
POLL_SECONDS=max(int(os.getenv("APPLICATION_POLL_SECONDS","120")),60)
BATCH_SIZE=max(int(os.getenv("APPLICATION_BATCH_SIZE","8")),1)
_seen=set()

async def report(client,payload):
    headers={"X-Report-Token":REPORT_TOKEN} if REPORT_TOKEN else {}
    try:
        await client.post(f"{DISCOVERY_API}/applications/report",json=payload,headers=headers,timeout=20)
    except Exception as exc:
        print(json.dumps({"report_error":str(exc),"job":payload.get("external_id")}))

async def cycle():
    async with httpx.AsyncClient(follow_redirects=True) as client:
        response=await client.get(f"{DISCOVERY_API}/jobs",timeout=30)
        response.raise_for_status()
        jobs=response.json().get("jobs",[])
        candidates=[j for j in jobs if j.get("action")=="apply" and j.get("external_id") not in _seen][:BATCH_SIZE]
        for job in candidates:
            _seen.add(job.get("external_id"))
            result=await inspect_and_fill(job,dry_run=not AUTO_SUBMIT)
            payload={
                "external_id":job.get("external_id"),
                "company":job.get("company"),
                "title":job.get("title"),
                "apply_url":job.get("apply_url"),
                "resume_profile":job.get("resume_profile"),
                "fit_score":job.get("fit_score"),
                "mode":"live" if AUTO_SUBMIT else "dry_run",
                **result,
            }
            print(json.dumps(payload,ensure_ascii=False))
            await report(client,payload)

async def main():
    print(json.dumps({"worker":"started","auto_submit":AUTO_SUBMIT,"poll_seconds":POLL_SECONDS}))
    while True:
        try:
            await cycle()
        except Exception as exc:
            print(json.dumps({"worker_error":str(exc)}))
        await asyncio.sleep(POLL_SECONDS)

if __name__=="__main__":
    asyncio.run(main())

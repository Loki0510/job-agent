import asyncio
import json
from app.connectors.greenhouse import GreenhouseConnector
from app.connectors.lever import LeverConnector
from app.core.profile import PROFILE
from app.core.config import settings
from app.services.matcher import match_job
from app.services.policy import decide

_seen=set()
_records=[]

def _mapping(raw):
    try:
        value=json.loads(raw or "{}")
        return value if isinstance(value,dict) else {}
    except Exception:
        return {}

async def _fetch_source(kind, site, company, semaphore):
    async with semaphore:
        try:
            if kind=="greenhouse":
                jobs=await GreenhouseConnector(site,company).discover()
            else:
                jobs=await LeverConnector(site,company).discover()
            return {"jobs":jobs,"error":None}
        except Exception as exc:
            return {
                "jobs":[],
                "error":{"source":kind,"site":site,"company":company,"error":str(exc)}
            }

async def discover_configured():
    greenhouse=_mapping(settings.greenhouse_boards_json)
    lever=_mapping(settings.lever_sites_json)
    semaphore=asyncio.Semaphore(8)
    tasks=[]
    for token,company in greenhouse.items():
        tasks.append(_fetch_source("greenhouse",token,company,semaphore))
    for site,company in lever.items():
        tasks.append(_fetch_source("lever",site,company,semaphore))

    results=await asyncio.gather(*tasks)
    discovered=[]
    source_errors=[]
    for result in results:
        discovered.extend(result["jobs"])
        if result["error"]:
            source_errors.append(result["error"])

    if source_errors:
        print(json.dumps({"source_errors":source_errors},ensure_ascii=False),flush=True)

    new=[]
    for job in discovered:
        if job.external_id in _seen:
            continue
        _seen.add(job.external_id)
        match=match_job(PROFILE,job.title,job.description)
        decision=decide(
            PROFILE,match,job.title,job.location,job.description,
            job.salary_min,job.salary_max,settings.min_fit_score
        )
        record={
            "external_id":job.external_id,
            "source":job.source,
            "company":job.company,
            "title":job.title,
            "location":job.location,
            "apply_url":job.apply_url,
            "salary_min":job.salary_min,
            "salary_max":job.salary_max,
            "remote":job.remote,
            "fit_score":match.score,
            "matched_skills":match.matched_skills,
            "action":decision.action,
            "reason":decision.reason,
            "resume_profile":decision.resume_profile,
        }
        _records.append(record)
        new.append(record)

    apply_count=sum(1 for r in _records if r.get("action")=="apply")
    skip_count=sum(1 for r in _records if r.get("action")=="skip")
    print(json.dumps({
        "discovery_summary":{
            "new":len(new),
            "stored":len(_records),
            "apply":apply_count,
            "skip":skip_count,
            "sources":len(greenhouse)+len(lever),
            "source_errors":len(source_errors)
        }
    },ensure_ascii=False),flush=True)
    return new

def records():
    return list(reversed(_records[-1000:]))

def eligible_records(limit=500):
    eligible=[x for x in _records if x.get("action")=="apply"]
    return list(reversed(eligible[-limit:]))

def stats():
    reasons={}
    sources={}
    for item in _records:
        sources[item["source"]]=sources.get(item["source"],0)+1
        if item.get("action")=="skip":
            reason=item.get("reason") or "unknown"
            reasons[reason]=reasons.get(reason,0)+1
    return {
        "stored":len(_records),
        "apply":sum(1 for x in _records if x.get("action")=="apply"),
        "skip":sum(1 for x in _records if x.get("action")=="skip"),
        "skip_reasons":reasons,
        "sources":sources,
    }

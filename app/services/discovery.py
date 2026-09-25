import asyncio
import json
import os
import time
from app.connectors.greenhouse import GreenhouseConnector
from app.connectors.lever import LeverConnector
from app.core.profile import PROFILE
from app.core.config import settings
from app.services.matcher import match_job
from app.services.policy import decide

_seen=set()
_records=[]
MAX_JOB_AGE_DAYS=max(int(os.getenv("MAX_JOB_AGE_DAYS","14")),1)
MAX_JOB_AGE_SECONDS=MAX_JOB_AGE_DAYS*86400

def _mapping(raw):
    try:
        value=json.loads(raw or "{}")
        return value if isinstance(value,dict) else {}
    except Exception:
        return {}

def _fresh_ts(value,now=None):
    try:
        ts=float(value or 0)
    except Exception:
        return False
    if ts<=0:
        return False
    current=float(now or time.time())
    return current-MAX_JOB_AGE_SECONDS <= ts <= current+86400

def _fresh_record(item,now=None):
    return _fresh_ts(item.get("posted_ts"),now)

def _prune_old(now=None):
    current=float(now or time.time())
    _records[:]=[item for item in _records if _fresh_record(item,current)]
    _seen.intersection_update({item.get("external_id") for item in _records if item.get("external_id")})

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
    now=time.time()
    _prune_old(now)

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
    freshness_excluded=0
    for job in discovered:
        if not _fresh_ts(job.posted_ts,now):
            freshness_excluded+=1
            continue
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
            "posted_at":job.posted_at,
            "posted_ts":job.posted_ts,
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
            "max_job_age_days":MAX_JOB_AGE_DAYS,
            "freshness_excluded":freshness_excluded,
            "sources":len(greenhouse)+len(lever),
            "source_errors":len(source_errors)
        }
    },ensure_ascii=False),flush=True)
    return new

def records():
    _prune_old()
    return list(reversed(_records[-1000:]))

def eligible_records(limit=500):
    _prune_old()
    eligible=[x for x in _records if x.get("action")=="apply"]
    eligible.sort(key=lambda x:(float(x.get("posted_ts") or 0),float(x.get("fit_score") or 0)),reverse=True)
    return eligible[:limit]

def stats():
    _prune_old()
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
        "max_job_age_days":MAX_JOB_AGE_DAYS,
        "skip_reasons":reasons,
        "sources":sources,
    }

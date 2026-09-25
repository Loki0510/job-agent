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

async def discover_configured():
    discovered=[]
    source_errors=[]
    for token, company in _mapping(settings.greenhouse_boards_json).items():
        try:
            discovered.extend(await GreenhouseConnector(token,company).discover())
        except Exception as exc:
            source_errors.append({"source":"greenhouse","site":token,"company":company,"error":str(exc)})
    for site, company in _mapping(settings.lever_sites_json).items():
        try:
            discovered.extend(await LeverConnector(site,company).discover())
        except Exception as exc:
            source_errors.append({"source":"lever","site":site,"company":company,"error":str(exc)})

    if source_errors:
        print(json.dumps({"source_errors":source_errors},ensure_ascii=False))

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
            "sources":len(_mapping(settings.greenhouse_boards_json))+len(_mapping(settings.lever_sites_json))
        }
    },ensure_ascii=False))
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

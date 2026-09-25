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
    for token, company in _mapping(settings.greenhouse_boards_json).items():
        discovered.extend(await GreenhouseConnector(token,company).discover())
    for site, company in _mapping(settings.lever_sites_json).items():
        discovered.extend(await LeverConnector(site,company).discover())

    new=[]
    for job in discovered:
        if job.external_id in _seen:
            continue
        _seen.add(job.external_id)
        match=match_job(PROFILE,job.title,job.description)
        decision=decide(PROFILE,match,job.salary_min,job.salary_max,settings.min_fit_score)
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
    return new

def records():
    return list(reversed(_records[-1000:]))

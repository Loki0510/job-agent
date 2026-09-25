import json, os
from pydantic import BaseModel, Field

def _list(name, default):
    raw=os.getenv(name)
    if not raw:
        return list(default)
    try:
        value=json.loads(raw)
        return [str(x) for x in value] if isinstance(value,list) else list(default)
    except Exception:
        return list(default)

def _bool(name, default):
    raw=os.getenv(name)
    return default if raw is None else raw.strip().lower() in {"1","true","yes","y","on"}

class CandidateProfile(BaseModel):
    name: str=""
    country: str="US"
    locations: list[str]=Field(default_factory=lambda:["United States"])
    remote_ok: bool=True
    hybrid_ok: bool=True
    onsite_ok: bool=True
    willing_to_relocate: bool=False
    min_salary_usd: int=0
    authorized_us: bool=False
    requires_sponsorship_now_or_future: bool=False
    years_experience: float=0
    primary_titles: list[str]=Field(default_factory=lambda:["Software Engineer"])
    secondary_titles: list[str]=Field(default_factory=list)
    skills: list[str]=Field(default_factory=lambda:["java","python","sql","javascript"])
    past_employers: list[str]=Field(default_factory=list)
    education: list[str]=Field(default_factory=list)

PROFILE=CandidateProfile(
    name=os.getenv("CANDIDATE_NAME",""),
    country=os.getenv("CANDIDATE_COUNTRY","US"),
    locations=_list("CANDIDATE_LOCATIONS_JSON",["United States"]),
    remote_ok=_bool("REMOTE_OK",True),
    hybrid_ok=_bool("HYBRID_OK",True),
    onsite_ok=_bool("ONSITE_OK",True),
    willing_to_relocate=_bool("WILLING_TO_RELOCATE",False),
    min_salary_usd=int(os.getenv("MIN_SALARY_USD","0")),
    authorized_us=_bool("AUTHORIZED_US",False),
    requires_sponsorship_now_or_future=_bool("REQUIRES_SPONSORSHIP",False),
    years_experience=float(os.getenv("YEARS_EXPERIENCE","0")),
    primary_titles=_list("PRIMARY_TITLES_JSON",["Software Engineer"]),
    secondary_titles=_list("SECONDARY_TITLES_JSON",[]),
    skills=_list("SKILLS_JSON",["java","python","sql","javascript"]),
    past_employers=_list("PAST_EMPLOYERS_JSON",[]),
    education=_list("EDUCATION_JSON",[])
)

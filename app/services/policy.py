import re
from dataclasses import dataclass

@dataclass
class PolicyDecision:
    action: str
    reason: str
    resume_profile: str

_US_MARKERS = (
    "united states","usa","u.s.","u.s.a.","remote - us","remote us","us remote",
)
_US_STATES = (
    "alabama","alaska","arizona","arkansas","california","colorado","connecticut","delaware",
    "florida","georgia","hawaii","idaho","illinois","indiana","iowa","kansas","kentucky",
    "louisiana","maine","maryland","massachusetts","michigan","minnesota","mississippi",
    "missouri","montana","nebraska","nevada","new hampshire","new jersey","new mexico",
    "new york","north carolina","north dakota","ohio","oklahoma","oregon","pennsylvania",
    "rhode island","south carolina","south dakota","tennessee","texas","utah","vermont",
    "virginia","washington","west virginia","wisconsin","wyoming","district of columbia",
)
_NON_US = (
    "canada","ontario","quebec","mississauga","toronto","vancouver","montreal","calgary",
    "mexico","united kingdom","uk","london","ireland","dublin","india","hyderabad","bengaluru",
    "bangalore","europe","emea","apac","australia","singapore","philippines","germany",
    "france","spain","poland","romania","serbia","ukraine","israel","brazil","argentina",
)
_AI_OVERLEVEL = ("principal","staff","director","vice president","vp ","head of","architect","manager")

def _norm(value):
    return re.sub(r"\s+"," ",(value or "").lower()).strip()

def _us_eligible(location, description):
    loc=_norm(location)
    body=_norm(description)
    if any(marker in loc for marker in _NON_US):
        return False
    if any(marker in loc for marker in _US_MARKERS):
        return True
    if any(state in loc for state in _US_STATES):
        return True
    if loc in {"remote","remote, usa","remote - usa","remote (us)"}:
        return any(marker in body for marker in _US_MARKERS) or "united states" in body
    if not loc:
        return "united states" in body or "usa" in body or "u.s." in body
    return False

def decide(profile, match, title, location, description, salary_min, salary_max, min_fit_score):
    resume="ai" if match.ai_track else "java"
    title_norm=_norm(title)
    if not _us_eligible(location,description):
        return PolicyDecision("skip","job is not clearly U.S.-based",resume)
    if match.ai_track and any(term in title_norm for term in _AI_OVERLEVEL):
        return PolicyDecision("skip","AI role seniority is outside configured target level",resume)
    if salary_max is not None and salary_max < profile.min_salary_usd:
        return PolicyDecision("skip","salary below configured minimum",resume)
    if match.score < min_fit_score:
        return PolicyDecision("skip",f"fit score {match.score:.2f} below threshold",resume)
    return PolicyDecision("apply","eligible under configured rules",resume)

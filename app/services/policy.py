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
    "mexico","united kingdom","london","ireland","dublin","india","hyderabad","bengaluru",
    "bangalore","europe","emea","apac","australia","singapore","philippines","germany",
    "france","spain","poland","romania","serbia","ukraine","israel","brazil","argentina",
)
_AI_OVERLEVEL = ("principal","staff","director","vice president","vp ","head of","architect","manager")
_NON_US_WORK_RIGHTS = ("australian working rights","right to work in australia","australia working rights","uk working rights","right to work in the uk")

_HARD_UNKNOWN = (
    "u.s. citizenship required","us citizenship required","u.s. citizen required",
    "active secret clearance required","active top secret clearance required",
    "active ts/sci","ts/sci required","security clearance required",
)

def _norm(value):
    return re.sub(r"\s+"," ",(value or "").lower()).strip()

def _us_eligible(location, description):
    loc=_norm(location)
    body=_norm(description)
    if any(marker in loc for marker in _NON_US):
        return False
    if loc in {"us","u.s.","usa","united states"}:
        return True
    if any(marker in loc for marker in _US_MARKERS):
        return True
    if any(state in loc for state in _US_STATES):
        return True
    if any(marker in body for marker in _US_MARKERS):
        return True
    if loc=="remote":
        return False
    return False

def _required_years(description):
    body=_norm(description)
    patterns=(
        r"(\d{1,2})\+?\s+years?\s+of\s+(?:professional\s+|relevant\s+)?experience",
        r"(\d{1,2})\+?\s+years?\s+(?:professional\s+|relevant\s+)?experience",
        r"minimum\s+of\s+(\d{1,2})\s+years?\s+of\s+experience",
        r"at\s+least\s+(\d{1,2})\s+years?\s+of\s+experience",
    )
    values=[]
    for pattern in patterns:
        values.extend(int(x) for x in re.findall(pattern,body))
    return max(values) if values else None

def decide(profile, match, title, location, description, salary_min, salary_max, min_fit_score):
    resume="ai" if match.ai_track else "java"
    title_norm=_norm(title)
    body=_norm(description)
    if not _us_eligible(location,description):
        return PolicyDecision("skip","job is not clearly U.S.-based",resume)
    if any(term in body for term in _NON_US_WORK_RIGHTS):
        return PolicyDecision("skip","job requires non-U.S. work rights",resume)
    if any(term in body for term in _HARD_UNKNOWN):
        return PolicyDecision("skip","citizenship or security-clearance requirement is not configured",resume)
    required_years=_required_years(description)
    if required_years is not None and required_years > profile.years_experience + 1:
        return PolicyDecision("skip",f"requires about {required_years}+ years of experience",resume)
    if match.ai_track and any(term in title_norm for term in _AI_OVERLEVEL):
        return PolicyDecision("skip","AI role seniority is outside configured target level",resume)
    if salary_max is not None and salary_max < profile.min_salary_usd:
        return PolicyDecision("skip","salary below configured minimum",resume)
    if match.score < min_fit_score:
        return PolicyDecision("skip",f"fit score {match.score:.2f} below threshold",resume)
    return PolicyDecision("apply","eligible under configured rules",resume)

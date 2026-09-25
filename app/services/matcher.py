import re
from dataclasses import dataclass

@dataclass
class MatchResult:
    score: float
    matched_skills: list[str]
    title_match: bool
    ai_track: bool

def _norm(value):
    return re.sub(r"\s+"," ",(value or "").lower()).strip()

def match_job(profile,title,description):
    title_norm=_norm(title)
    body=_norm((title or "")+" "+(description or ""))
    primary=any(_norm(x) in title_norm or title_norm in _norm(x) for x in profile.primary_titles)
    secondary=any(_norm(x) in title_norm or title_norm in _norm(x) for x in profile.secondary_titles)
    matched=[skill for skill in profile.skills if _norm(skill) in body]
    score=round(0.55*(1 if primary or secondary else 0)+0.45*min(len(matched)/10,1),3)
    return MatchResult(score,matched,primary or secondary,secondary)

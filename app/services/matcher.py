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

def _tokens(value):
    return {x for x in re.findall(r"[a-z0-9+#.]+",_norm(value)) if len(x)>1}

def _title_match(title,target):
    t=_norm(title)
    x=_norm(target)
    if x in t:
        return True
    tt=_tokens(title)
    xt=_tokens(target)
    if not xt:
        return False
    overlap=len(tt & xt)/len(xt)
    return overlap>=0.75

def match_job(profile,title,description):
    title_norm=_norm(title)
    body=_norm((title or "")+" "+(description or ""))
    primary=any(_title_match(title,x) for x in profile.primary_titles)
    secondary_title=any(_title_match(title,x) for x in profile.secondary_titles)
    ai_marker=bool(re.search(r"\b(ai|llm|genai|generative ai|rag|machine learning|ml engineer|agentic)\b",title_norm))
    ai_track=secondary_title and ai_marker
    title_match=primary or ai_track
    matched=[skill for skill in profile.skills if _norm(skill) in body]
    score=round(0.55*(1 if title_match else 0)+0.45*min(len(matched)/10,1),3)
    return MatchResult(score,matched,title_match,ai_track)

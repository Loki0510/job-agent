from dataclasses import dataclass

@dataclass
class PolicyDecision:
    action: str
    reason: str
    resume_profile: str

def decide(profile, match, salary_min, salary_max, min_fit_score):
    resume="ai" if match.ai_track else "java"
    if salary_max is not None and salary_max < profile.min_salary_usd:
        return PolicyDecision("skip","salary below configured minimum",resume)
    if match.score < min_fit_score:
        return PolicyDecision("skip",f"fit score {match.score:.2f} below threshold",resume)
    return PolicyDecision("apply","eligible under configured rules",resume)

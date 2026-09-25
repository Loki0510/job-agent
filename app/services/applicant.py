import os, re
from dataclasses import dataclass
from app.core.profile import PROFILE

@dataclass
class Applicant:
    name: str
    email: str
    phone: str
    linkedin: str
    current_company: str
    city: str
    state: str
    postal_code: str
    timezone: str

    @property
    def first_name(self):
        return (self.name.strip().split() or [""])[0]

    @property
    def last_name(self):
        parts=self.name.strip().split()
        return parts[-1] if len(parts)>1 else ""

    @property
    def location_text(self):
        return ", ".join(x for x in (self.city,self.state) if x)

APPLICANT=Applicant(
    name=os.getenv("CANDIDATE_NAME",""),
    email=os.getenv("CANDIDATE_EMAIL",""),
    phone=os.getenv("CANDIDATE_PHONE",""),
    linkedin=os.getenv("CANDIDATE_LINKEDIN",""),
    current_company=os.getenv("CANDIDATE_CURRENT_COMPANY",""),
    city=os.getenv("CANDIDATE_CITY",""),
    state=os.getenv("CANDIDATE_STATE",""),
    postal_code=os.getenv("CANDIDATE_ZIP",""),
    timezone=os.getenv("CANDIDATE_TIMEZONE",""),
)

def norm(value):
    return re.sub(r"[^a-z0-9]+"," ",(value or "").lower()).strip()

def worked_for_company(company):
    c=norm(company)
    if not c:
        return False
    for employer in PROFILE.past_employers:
        e=norm(employer)
        if e and (e in c or c in e):
            return True
    return False

def answer_for_label(label, company=""):
    q=norm(label)
    if not q:
        return None
    if "authorized" in q and ("united states" in q or "u s" in q or "work" in q):
        return "Yes" if PROFILE.authorized_us else "No"
    if "legally permitted" in q and "united states" in q:
        return "Yes" if PROFILE.authorized_us else "No"
    if "sponsor" in q or "sponsorship" in q:
        return "Yes" if PROFILE.requires_sponsorship_now_or_future else "No"
    if "relocat" in q:
        return "Yes" if PROFILE.willing_to_relocate else "No"
    if ("5 day" in q or "five day" in q) and ("office" in q or "onsite" in q or "on site" in q):
        return "Yes" if PROFILE.onsite_ok and PROFILE.willing_to_relocate else "No"
    if ("est time zone" in q or "eastern time" in q) and APPLICANT.timezone in {"America/New_York","US/Eastern"}:
        return "Yes"
    if "previously worked" in q or "worked for" in q or "former employee" in q or "currently or previously" in q:
        return "Yes" if worked_for_company(company) else "No"
    if "certify" in q and ("accurate" in q or "true" in q):
        return "Yes"
    if "years" in q and "experience" in q:
        return str(int(PROFILE.years_experience))
    return None

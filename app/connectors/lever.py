import httpx
from app.connectors.base import DiscoveredJob
from app.services.salary import annualize_salary

class LeverConnector:
    def __init__(self, site, company, timeout=20.0):
        self.site=site
        self.company=company
        self.timeout=timeout

    async def discover(self):
        base="https://api.lever.co"
        endpoint=f"{base}/v0/postings/{self.site}"
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            response=await client.get(endpoint, params={"mode":"json","limit":500})
            response.raise_for_status()
            payload=response.json()
        jobs=[]
        for raw in payload:
            categories=raw.get("categories") or {}
            location=(categories.get("location") or "").strip()
            salary=raw.get("salaryRange") or {}
            jobs.append(DiscoveredJob(
                external_id=f"lever:{self.site}:{raw.get('id')}",
                source="lever",
                company=self.company,
                title=(raw.get("text") or "").strip(),
                location=location,
                description=(raw.get("descriptionPlain") or raw.get("openingPlain") or "").strip(),
                apply_url=(raw.get("applyUrl") or raw.get("hostedUrl") or "").strip(),
                salary_min=annualize_salary(salary.get("min"),salary.get("interval")),
                salary_max=annualize_salary(salary.get("max"),salary.get("interval")),
                remote=((raw.get("workplaceType") or "").lower()=="remote" or "remote" in location.lower()),
            ))
        return jobs

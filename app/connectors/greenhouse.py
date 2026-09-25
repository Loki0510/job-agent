import html
import re
import httpx
from app.connectors.base import DiscoveredJob

_TAG=re.compile(r"<[^>]+>")

def _plain(value):
    return re.sub(r"\s+"," ",_TAG.sub(" ",html.unescape(value or ""))).strip()

class GreenhouseConnector:
    def __init__(self, board_token, company, timeout=20.0):
        self.board_token=board_token
        self.company=company
        self.timeout=timeout

    async def discover(self):
        base="https://boards-api.greenhouse.io"
        endpoint=f"{base}/v1/boards/{self.board_token}/jobs"
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            response=await client.get(endpoint, params={"content":"true"})
            response.raise_for_status()
            payload=response.json()
        jobs=[]
        for raw in payload.get("jobs",[]):
            location=((raw.get("location") or {}).get("name") or "")
            jobs.append(DiscoveredJob(
                external_id=f"greenhouse:{self.board_token}:{raw.get('id')}",
                source="greenhouse",
                company=self.company,
                title=raw.get("title") or "",
                location=location,
                description=_plain(raw.get("content")),
                apply_url=raw.get("absolute_url") or "",
                remote="remote" in location.lower(),
            ))
        return jobs

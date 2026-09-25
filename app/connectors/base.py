from dataclasses import dataclass

@dataclass
class DiscoveredJob:
    external_id: str
    source: str
    company: str
    title: str
    location: str
    description: str
    apply_url: str
    salary_min: int|None=None
    salary_max: int|None=None
    remote: bool=False

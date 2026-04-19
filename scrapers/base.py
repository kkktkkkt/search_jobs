from dataclasses import dataclass, field


@dataclass
class JobRecord:
    site: str
    title: str
    company: str = ""
    skills: str = ""
    description: str = ""
    url: str = ""


class BaseScraper:
    site_name: str = ""

    def fetch(self, query: str, max_pages: int = 3) -> list[JobRecord]:
        raise NotImplementedError

import feedparser
from .base import BaseScraper, JobRecord


class KyujinBoxScraper(BaseScraper):
    site_name = "求人ボックス"
    RSS_URL = "https://xn--pckua2a7gp15o89zb.com/jobs/k-{query}/rss"

    def fetch(self, query: str, max_pages: int = 3) -> list[JobRecord]:
        url = self.RSS_URL.format(query=query)
        feed = feedparser.parse(url)
        records = []
        for entry in feed.entries:
            summary = entry.get("summary", "")
            records.append(JobRecord(
                site=self.site_name,
                title=entry.get("title", ""),
                company=entry.get("author", ""),
                description=summary,
                url=entry.get("link", ""),
            ))
        return records

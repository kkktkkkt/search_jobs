import time
from playwright.sync_api import sync_playwright
from .base import BaseScraper, JobRecord


class IndeedScraper(BaseScraper):
    site_name = "Indeed"
    BASE_URL = "https://jp.indeed.com/jobs?q={query}&l=&start={start}"

    def fetch(self, query: str, max_pages: int = 3) -> list[JobRecord]:
        records = []
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            ctx = browser.new_context(user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ))
            page = ctx.new_page()
            for page_num in range(max_pages):
                start = page_num * 10
                url = self.BASE_URL.format(query=query, start=start)
                page.goto(url, timeout=30000)
                page.wait_for_timeout(2000)
                cards = page.query_selector_all("div.job_seen_beacon")
                if not cards:
                    break
                for card in cards:
                    title_el = card.query_selector("h2.jobTitle span")
                    company_el = card.query_selector("[data-testid='company-name']")
                    desc_el = card.query_selector("div.job-snippet")
                    link_el = card.query_selector("a[data-jk]")
                    title = title_el.inner_text() if title_el else ""
                    company = company_el.inner_text() if company_el else ""
                    desc = desc_el.inner_text() if desc_el else ""
                    href = "https://jp.indeed.com" + link_el.get_attribute("href") if link_el else ""
                    if title:
                        records.append(JobRecord(
                            site=self.site_name,
                            title=title,
                            company=company,
                            description=desc,
                            url=href,
                        ))
                time.sleep(1)
            browser.close()
        return records

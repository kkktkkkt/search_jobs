import time
from playwright.sync_api import sync_playwright
from .base import BaseScraper, JobRecord


class IndeedScraper(BaseScraper):
    site_name = "Indeed"
    BASE_URL = "https://jp.indeed.com/jobs?q={query}&l=&start={start}"

    def fetch(self, query: str, max_pages: int = 3) -> list[JobRecord]:
        records = []
        with sync_playwright() as p:
            browser = p.chromium.launch(channel="chrome", headless=True)
            ctx = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1280, "height": 800},
                locale="ja-JP",
            )
            ctx.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
            page = ctx.new_page()
            for page_num in range(max_pages):
                start = page_num * 10
                url = self.BASE_URL.format(query=query, start=start)
                page.goto(url, timeout=30000, wait_until="domcontentloaded")

                if "Blocked" in page.title() or "blocked" in page.url:
                    break

                try:
                    # 求人カードが出るまで待つ
                    page.wait_for_selector(
                        "div.job_seen_beacon, div.jobsearch-SerpJobCard, td.resultContent",
                        timeout=10000,
                    )
                except Exception:
                    break

                cards = page.query_selector_all("div.job_seen_beacon, div.jobsearch-SerpJobCard")
                if not cards:
                    cards = page.query_selector_all("td.resultContent")
                if not cards:
                    break

                for card in cards:
                    title_el = card.query_selector("h2.jobTitle span, h2 span[title]")
                    company_el = card.query_selector("[data-testid='company-name'], span.companyName")
                    desc_el = card.query_selector("div.job-snippet, div[class*='snippet']")
                    link_el = card.query_selector("a[data-jk], a[id*='job_']")
                    title = title_el.inner_text().strip() if title_el else ""
                    company = company_el.inner_text().strip() if company_el else ""
                    desc = desc_el.inner_text().strip() if desc_el else ""
                    href = link_el.get_attribute("href") if link_el else ""
                    if href and not href.startswith("http"):
                        href = "https://jp.indeed.com" + href
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

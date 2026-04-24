import time
from playwright.sync_api import sync_playwright
from .base import BaseScraper, JobRecord


class MeitecNextScraper(BaseScraper):
    site_name = "メイテックネクスト"
    SEARCH_URL_P1 = "https://www.m-next.jp/job/s/w{query}/"
    SEARCH_URL_PN = "https://www.m-next.jp/job/s/w{query}/p{page}/#paging"

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
                locale="ja-JP",
            )
            page = ctx.new_page()
            for page_num in range(1, max_pages + 1):
                url = (self.SEARCH_URL_P1 if page_num == 1 else self.SEARCH_URL_PN).format(
                    query=query, page=page_num
                )
                page.goto(url, timeout=30000, wait_until="domcontentloaded")
                try:
                    # 求人カードが出るまで待つ
                    page.wait_for_selector("a[href*='/job/'] .position", timeout=10000)
                except Exception:
                    break

                cards = page.query_selector_all("a[href*='/job/']")
                job_cards = [c for c in cards if c.query_selector(".position")]
                if not job_cards:
                    break

                for card in job_cards:
                    href = card.get_attribute("href") or ""
                    if not href.startswith("http"):
                        href = "https://www.m-next.jp" + href
                    title_el = card.query_selector(".position")
                    company_el = card.query_selector(".img span, .img")
                    data_el = card.query_selector(".data")
                    tag_el = card.query_selector(".tag")
                    title = title_el.inner_text().strip() if title_el else ""
                    company = company_el.inner_text().strip() if company_el else ""
                    desc = " ".join(filter(None, [
                        data_el.inner_text().strip() if data_el else "",
                        tag_el.inner_text().strip() if tag_el else "",
                    ]))
                    if title:
                        records.append(JobRecord(
                            site=self.site_name,
                            title=title,
                            company=company,
                            description=desc,
                            url=href,
                        ))
                time.sleep(0.5)
            browser.close()
        return records

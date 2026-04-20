import time
from playwright.sync_api import sync_playwright
from .base import BaseScraper, JobRecord


class DodaScraper(BaseScraper):
    site_name = "Doda"

    def fetch(self, query: str, max_pages: int = 3) -> list[JobRecord]:
        records = []
        with sync_playwright() as p:
            browser = p.chromium.launch(channel="chrome", headless=True)
            ctx = browser.new_context(user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ))
            page = ctx.new_page()
            for page_num in range(1, max_pages + 1):
                url = (
                    f"https://doda.jp/DodaFront/View/JobSearchList/"
                    f"j_oc__1/-preBtn__1/kwl__{query}/org__1/pn__{page_num}/"
                )
                try:
                    page.goto(url, timeout=30000, wait_until="domcontentloaded")
                except Exception:
                    # HTTP/2エラー等の通信エラーは無視して取得済みで終了
                    break
                page.wait_for_timeout(3000)
                cards = page.query_selector_all("article")
                if not cards:
                    break
                for card in cards:
                    title_el = card.query_selector("h2")
                    link_el = card.query_selector("a[href*='JobSearchDetail']")
                    company_el = card.query_selector("[class*='company'], [class*='Company']")
                    desc_el = card.query_selector("p[class*='text'], p[class*='Text']")
                    title = title_el.inner_text().strip() if title_el else ""
                    company = company_el.inner_text().strip() if company_el else ""
                    desc = desc_el.inner_text().strip() if desc_el else ""
                    href = link_el.get_attribute("href") if link_el else ""
                    if href and not href.startswith("http"):
                        href = "https://doda.jp" + href
                    if title:
                        records.append(JobRecord(
                            site=self.site_name,
                            title=title,
                            company=company,
                            description=desc,
                            url=href,
                        ))
                time.sleep(3)  # ページ間の待機を長めに
            browser.close()
        return records

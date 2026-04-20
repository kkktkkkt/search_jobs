import time
from playwright.sync_api import sync_playwright
from .base import BaseScraper, JobRecord


class KyujinBoxScraper(BaseScraper):
    site_name = "求人ボックス"

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
            # トップページからフォーム送信で検索
            page.goto("https://xn--pckua2a7gp15o89zb.com/", timeout=20000)
            page.wait_for_timeout(1500)
            page.fill("input[name='form[keyword]']", query)
            page.press("input[name='form[keyword]']", "Enter")
            page.wait_for_timeout(3000)

            for page_num in range(max_pages):
                if page_num > 0:
                    # 次ページへ
                    next_btn = page.query_selector("a[rel='next'], a.c-pagination_next, a[class*='next']")
                    if not next_btn:
                        break
                    next_btn.click()
                    page.wait_for_timeout(2000)

                cards = page.query_selector_all(".p-result_card")
                if not cards:
                    break

                for card in cards:
                    title_el = card.query_selector(".p-result_title_link, [class*='title_link']")
                    company_el = card.query_selector(".p-result_name, .p-result_company, [class*='name']")
                    desc_el = card.query_selector(".p-result_area, [class*='area'], [class*='info']")
                    link_el = card.query_selector("a.p-result_title_link, a[href]")
                    title = title_el.inner_text().strip() if title_el else ""
                    company = company_el.inner_text().strip() if company_el else ""
                    desc = desc_el.inner_text().strip() if desc_el else ""
                    href = link_el.get_attribute("href") if link_el else ""
                    if href and not href.startswith("http"):
                        href = "https://xn--pckua2a7gp15o89zb.com" + href
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

import time
import httpx
from bs4 import BeautifulSoup
from .base import BaseScraper, JobRecord


class MeitecNextScraper(BaseScraper):
    site_name = "メイテックネクスト"
    SEARCH_URL = "https://www.meitec-next.jp/search/?keyword={query}&page={page}"
    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        )
    }

    def fetch(self, query: str, max_pages: int = 3) -> list[JobRecord]:
        records = []
        with httpx.Client(headers=self.HEADERS, follow_redirects=True, timeout=20) as client:
            for page_num in range(1, max_pages + 1):
                url = self.SEARCH_URL.format(query=query, page=page_num)
                resp = client.get(url)
                if resp.status_code != 200:
                    break
                soup = BeautifulSoup(resp.text, "lxml")
                cards = soup.select("div.job-list__item, li.job-item, article.job-card")
                if not cards:
                    # フォールバック: 汎用的なリンクタイトル抽出
                    cards = soup.select("div.search-result-item, div.jobItem")
                if not cards:
                    break
                for card in cards:
                    title_el = card.select_one("h2, h3, .job-title, .jobTitle")
                    company_el = card.select_one(".company, .companyName")
                    skills_el = card.select_one(".skill, .required-skill, .skills, .jobDetail")
                    link_el = card.select_one("a[href]")
                    title = title_el.get_text(strip=True) if title_el else ""
                    company = company_el.get_text(strip=True) if company_el else ""
                    skills = skills_el.get_text(strip=True) if skills_el else ""
                    href = link_el["href"] if link_el else ""
                    if href and not href.startswith("http"):
                        href = "https://www.meitec-next.jp" + href
                    if title:
                        records.append(JobRecord(
                            site=self.site_name,
                            title=title,
                            company=company,
                            skills=skills,
                            url=href,
                        ))
                time.sleep(1)
        return records

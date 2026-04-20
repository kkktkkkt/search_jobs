import threading
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

    def fetch_in_thread(self, query: str, max_pages: int = 3) -> list[JobRecord]:
        """Streamlit の asyncio ループと競合しないよう別スレッドで実行する"""
        result: list[JobRecord] = []
        error: list[Exception] = []

        def target():
            try:
                result.extend(self.fetch(query, max_pages))
            except Exception as e:
                error.append(e)

        t = threading.Thread(target=target)
        t.start()
        t.join()

        if error:
            raise error[0]
        return result

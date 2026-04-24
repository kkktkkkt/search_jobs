import re
from collections import Counter
from config import TECH_KEYWORDS


def _make_pattern(kw: str) -> str:
    """
    キーワードの前後にアルファベットが来ないことを確認するパターンを生成。
    例: "R" が "React" や "REST" にマッチしないようにする。
    """
    return r'(?<![a-zA-Z])' + re.escape(kw) + r'(?![a-zA-Z])'


# 起動時にパターンをコンパイルしてキャッシュ
_PATTERNS = {kw: re.compile(_make_pattern(kw), re.IGNORECASE) for kw in TECH_KEYWORDS}


def extract_keywords(text: str) -> list[str]:
    found = []
    for kw, pattern in _PATTERNS.items():
        if pattern.search(text):
            found.append(kw)
    return found


def aggregate(records: list[dict]) -> Counter:
    counter = Counter()
    for r in records:
        text = " ".join([r.get("title", ""), r.get("skills", ""), r.get("description", "")])
        for kw in extract_keywords(text):
            counter[kw] += 1
    return counter

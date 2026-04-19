import re
from collections import Counter
from config import TECH_KEYWORDS


def extract_keywords(text: str) -> list[str]:
    found = []
    text_lower = text.lower()
    for kw in TECH_KEYWORDS:
        pattern = re.escape(kw)
        if re.search(pattern, text, re.IGNORECASE):
            found.append(kw)
    return found


def aggregate(records: list[dict]) -> Counter:
    counter = Counter()
    for r in records:
        text = " ".join([r.get("title", ""), r.get("skills", ""), r.get("description", "")])
        for kw in extract_keywords(text):
            counter[kw] += 1
    return counter

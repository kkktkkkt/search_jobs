import re
from dataclasses import dataclass


# ---- スコア定義 ------------------------------------------------

EASE_PLUS: list[tuple[list[str], int, str]] = [
    # (キーワードリスト, 点数, タグ表示名)
    (["テスター", "テスト実行", "動作確認", "検証", "QA補助", "テスト補助", "結合テスト", "単体テスト実行"], 4, "🔍 検証・テスト"),
    (["アシスタントSE", "アシスタントエンジニア", "サポートエンジニア", "補助", "補佐", "アシスタント"], 4, "🤝 アシスタント"),
    (["マニュアルあり", "手順書", "指示に基づく", "指示された", "マニュアル通り", "ルーティン"], 3, "📋 マニュアル作業"),
    (["フルリモート", "完全在宅", "フルリモートワーク"], 3, "🏠 フルリモート"),
    (["リモート", "テレワーク", "在宅勤務"], 2, "💻 リモート可"),
    (["週3", "週4", "週3日", "週4日", "時短勤務", "パートタイム"], 3, "⏰ 短時間勤務"),
    (["残業なし", "残業ほぼなし", "ノー残業", "定時退社", "残業少", "残業ゼロ"], 3, "🕐 残業なし"),
    (["年間休日120", "年間休日125", "年間休日130", "完全週休2日"], 2, "📅 休日多め"),
    (["未経験可", "未経験歓迎", "未経験OK", "経験不問"], 2, "🌱 未経験可"),
    (["転勤なし", "転居不要", "勤務地固定"], 1, "📍 転勤なし"),
    (["服装自由", "私服OK", "カジュアル"], 1, "👕 服装自由"),
    (["フレックス", "フレキシブル", "自由な時間"], 2, "🔓 フレックス"),
]

EASE_MINUS: list[tuple[list[str], int]] = [
    # (キーワードリスト, 減点)
    (["リーダー", "チームリード", "テックリード", "リード"], 4),
    (["プロジェクトマネージャー", "PM ", "プロマネ", "マネージャー", "管理職", "統括", "責任者", "部長", "課長"], 5),
    (["アーキテクト", "アーキテクチャ設計", "技術選定", "技術戦略"], 4),
    (["要件定義", "基本設計", "詳細設計", "仕様策定", "0→1", "ゼロイチ", "新規事業立ち上げ"], 4),
    (["ノルマ", "目標必達", "成果主義", "インセンティブ重視", "歩合"], 3),
    (["スピード感", "スピード重視", "高速", "アジャイル推進"], 2),
    (["体育会", "ガツガツ", "向上心必須", "成長志向必須", "ハングリー精神"], 3),
    (["激務", "ハードワーク", "24時間", "夜間対応", "オンコール"], 3),
    (["土日出勤", "シフト制", "夜勤", "交代勤務"], 2),
    (["海外出張", "海外赴任", "グローバル展開"], 1),
]


# ---- スコアリング -----------------------------------------------

@dataclass
class EaseResult:
    score: int
    plus_tags: list[str]      # マッチした楽さタグ
    minus_tags: list[str]     # マッチしたきつさタグ
    salary_min: int | None    # 万円
    salary_max: int | None    # 万円


def score(record: dict) -> EaseResult:
    text = " ".join([
        record.get("title", ""),
        record.get("skills", ""),
        record.get("description", ""),
    ])

    total = 0
    plus_tags: list[str] = []
    minus_tags: list[str] = []

    for keywords, pts, tag in EASE_PLUS:
        for kw in keywords:
            if kw in text:
                total += pts
                plus_tags.append(tag)
                break  # 同カテゴリは1回だけ加点

    for keywords, pts in EASE_MINUS:
        for kw in keywords:
            if kw in text:
                total -= pts
                minus_tags.append(kw)
                break

    salary_min, salary_max = _extract_salary(text)

    return EaseResult(
        score=total,
        plus_tags=list(dict.fromkeys(plus_tags)),   # 重複除去・順序保持
        minus_tags=list(dict.fromkeys(minus_tags)),
        salary_min=salary_min,
        salary_max=salary_max,
    )


def _extract_salary(text: str) -> tuple[int | None, int | None]:
    """テキストから年収(万円)を抽出する"""
    # 例: 年収500〜800万円 / 500万円〜800万円 / 530～900万円
    m = re.search(r'(\d{3,4})\s*[〜～~\-－]\s*(\d{3,4})\s*万円', text)
    if m:
        return int(m.group(1)), int(m.group(2))
    # 単独: 年収600万円
    m = re.search(r'年収\s*(\d{3,4})\s*万円', text)
    if m:
        v = int(m.group(1))
        return v, v
    # 〇〇万円〜
    m = re.search(r'(\d{3,4})\s*万円', text)
    if m:
        v = int(m.group(1))
        return v, v
    return None, None


def rank(records: list[dict]) -> list[tuple[dict, EaseResult]]:
    """全求人をスコアリングして降順ソート"""
    scored = [(r, score(r)) for r in records]
    return sorted(scored, key=lambda x: x[1].score, reverse=True)

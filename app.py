import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st
import pandas as pd
import plotly.express as px
from collections import Counter
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

from config import SEARCH_QUERY, MAX_PAGES
from scrapers.kyujin_box import KyujinBoxScraper
from scrapers.indeed import IndeedScraper
from scrapers.doda import DodaScraper
from scrapers.meitec_next import MeitecNextScraper
from analysis.keyword_extractor import aggregate

def _find_japanese_font() -> str | None:
    candidates = [
        "C:/Windows/Fonts/meiryo.ttc",
        "C:/Windows/Fonts/msgothic.ttc",
        "C:/Windows/Fonts/YuGothM.ttc",
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


SCRAPERS = {
    "求人ボックス": KyujinBoxScraper(),
    "Indeed": IndeedScraper(),
    "Doda": DodaScraper(),
    "メイテックネクスト": MeitecNextScraper(),
}

@st.cache_data(ttl=3600, show_spinner=False)
def cached_fetch(site_name: str, query: str, max_pages: int) -> list[dict]:
    """結果を1時間キャッシュ。同じ条件なら再スクレイピング不要。"""
    records = SCRAPERS[site_name].fetch_in_thread(query, max_pages)
    return [r.__dict__ for r in records]

st.set_page_config(page_title="求人トレンド分析", page_icon="📊", layout="wide")
st.title("📊 求人トレンドキーワード分析")

with st.sidebar:
    st.header("検索設定")
    query = st.text_input("検索キーワード", value=SEARCH_QUERY)
    max_pages = st.slider("取得ページ数 (サイトごと)", 1, 5, MAX_PAGES)
    selected_sites = st.multiselect(
        "対象サイト",
        options=list(SCRAPERS.keys()),
        default=list(SCRAPERS.keys()),
    )
    top_n = st.slider("表示するキーワード数 TOP N", 5, 50, 20)
    run = st.button("🔍 取得・分析開始", type="primary")
    if st.button("🗑️ キャッシュをクリア"):
        cached_fetch.clear()
        st.success("キャッシュをクリアしました")

if run:
    from concurrent.futures import ThreadPoolExecutor, as_completed
    import traceback

    all_records = []
    site_records: dict[str, list] = {}
    progress = st.progress(0, text="全サイトを並列取得中...")
    completed_count = 0

    def scrape(site_name: str):
        dicts = cached_fetch(site_name, query, max_pages)
        from scrapers.base import JobRecord
        records = [JobRecord(**d) for d in dicts]
        return site_name, records

    with ThreadPoolExecutor(max_workers=len(selected_sites)) as executor:
        futures = {executor.submit(scrape, s): s for s in selected_sites}
        for future in as_completed(futures):
            completed_count += 1
            progress.progress(completed_count / len(selected_sites),
                              text=f"{completed_count}/{len(selected_sites)} サイト完了...")
            try:
                site_name, records = future.result()
                all_records.extend(records)
                site_records[site_name] = records
            except Exception as e:
                site_name = futures[future]
                st.warning(f"{site_name}: 取得エラー ({e})")
                st.code(traceback.format_exc())
                site_records[site_name] = []

    progress.progress(1.0, text="完了!")

    if not all_records:
        st.error("求人データを取得できませんでした。")
        st.stop()

    st.success(f"合計 {len(all_records)} 件取得")

    # --- 全体集計 ---
    total_counter = aggregate([r.__dict__ for r in all_records])
    top_items = total_counter.most_common(top_n)
    df_all = pd.DataFrame(top_items, columns=["キーワード", "件数"])

    st.subheader(f"🏆 技術キーワード TOP {top_n}（全サイト合計）")
    fig = px.bar(
        df_all, x="件数", y="キーワード",
        orientation="h",
        color="件数",
        color_continuous_scale="Blues",
        height=max(400, top_n * 22),
    )
    fig.update_layout(yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(df_all, use_container_width=True, hide_index=True)

    # --- サイト別比較 ---
    st.subheader("📊 サイト別キーワード比較")
    site_dfs = []
    for site_name, records in site_records.items():
        if not records:
            continue
        counter = aggregate([r.__dict__ for r in records])
        for kw, cnt in counter.most_common(top_n):
            site_dfs.append({"サイト": site_name, "キーワード": kw, "件数": cnt})

    if site_dfs:
        df_site = pd.DataFrame(site_dfs)
        top_kws = df_all["キーワード"].tolist()[:15]
        df_site_filtered = df_site[df_site["キーワード"].isin(top_kws)]
        fig2 = px.bar(
            df_site_filtered,
            x="キーワード", y="件数",
            color="サイト",
            barmode="group",
            height=500,
        )
        fig2.update_xaxes(tickangle=-45)
        st.plotly_chart(fig2, use_container_width=True)

    # --- ワードクラウド ---
    st.subheader("☁️ ワードクラウド")
    if total_counter:
        font_path = _find_japanese_font()
        wc = WordCloud(
            width=900, height=400,
            background_color="white",
            font_path=font_path,
            max_words=80,
        ).generate_from_frequencies(dict(total_counter))
        fig3, ax = plt.subplots(figsize=(12, 5))
        ax.imshow(wc, interpolation="bilinear")
        ax.axis("off")
        st.pyplot(fig3)

    # --- 求人一覧テーブル ---
    with st.expander("📋 取得した求人一覧"):
        df_jobs = pd.DataFrame([r.__dict__ for r in all_records])
        st.dataframe(df_jobs, use_container_width=True, hide_index=True)

    # --- CSV ダウンロード ---
    csv = df_all.to_csv(index=False, encoding="utf-8-sig")
    st.download_button("⬇️ TOP キーワードをCSVでダウンロード", csv, "keywords.csv", "text/csv")

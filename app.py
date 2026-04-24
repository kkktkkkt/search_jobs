import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st
import pandas as pd
import plotly.express as px
from collections import Counter
from wordcloud import WordCloud
import matplotlib.pyplot as plt

from config import SEARCH_QUERY, MAX_PAGES
from scrapers.kyujin_box import KyujinBoxScraper
from scrapers.indeed import IndeedScraper
from scrapers.doda import DodaScraper
from scrapers.meitec_next import MeitecNextScraper
from analysis.keyword_extractor import aggregate
from analysis.ease_scorer import rank as ease_rank


def _find_japanese_font() -> str | None:
    for path in [
        "C:/Windows/Fonts/meiryo.ttc",
        "C:/Windows/Fonts/msgothic.ttc",
        "C:/Windows/Fonts/YuGothM.ttc",
    ]:
        if os.path.exists(path):
            return path
    return None


SCRAPERS = {
    "求人ボックス": KyujinBoxScraper(),
    "Indeed":       IndeedScraper(),
    "Doda":         DodaScraper(),
    "メイテックネクスト": MeitecNextScraper(),
}


@st.cache_data(ttl=3600, show_spinner=False)
def cached_fetch(site_name: str, query: str, max_pages: int) -> list[dict]:
    records = SCRAPERS[site_name].fetch_in_thread(query, max_pages)
    return [r.__dict__ for r in records]


# ---- UI --------------------------------------------------------

st.set_page_config(page_title="求人トレンド分析", page_icon="📊", layout="wide")
st.title("📊 求人トレンドキーワード分析")

with st.sidebar:
    st.header("検索設定")
    query      = st.text_input("検索キーワード", value=SEARCH_QUERY)
    max_pages  = st.slider("取得ページ数 (サイトごと)", 1, 5, MAX_PAGES)
    selected_sites = st.multiselect(
        "対象サイト",
        options=list(SCRAPERS.keys()),
        default=list(SCRAPERS.keys()),
    )
    top_n = st.slider("表示するキーワード数 TOP N", 5, 50, 20)
    ease_top_n = st.slider("楽さランキング 表示件数", 5, 50, 20)
    run = st.button("🔍 取得・分析開始", type="primary")
    if st.button("🗑️ キャッシュをクリア"):
        cached_fetch.clear()
        st.success("キャッシュをクリアしました")

if run:
    from concurrent.futures import ThreadPoolExecutor, as_completed
    import traceback

    all_records  = []
    site_records: dict[str, list] = {}
    progress     = st.progress(0, text="全サイトを並列取得中...")
    done         = 0

    def scrape(site_name: str):
        dicts = cached_fetch(site_name, query, max_pages)
        from scrapers.base import JobRecord
        return site_name, [JobRecord(**d) for d in dicts]

    with ThreadPoolExecutor(max_workers=len(selected_sites)) as ex:
        futures = {ex.submit(scrape, s): s for s in selected_sites}
        for future in as_completed(futures):
            done += 1
            progress.progress(done / len(selected_sites),
                              text=f"{done}/{len(selected_sites)} サイト完了...")
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

    tab_kw, tab_ease = st.tabs(["🏆 キーワード分析", "🛋️ 楽さランキング"])

    # ============================================================
    # TAB 1: キーワード分析
    # ============================================================
    with tab_kw:
        total_counter = aggregate([r.__dict__ for r in all_records])
        top_items     = total_counter.most_common(top_n)
        df_all        = pd.DataFrame(top_items, columns=["キーワード", "件数"])

        st.subheader(f"TOP {top_n} 技術キーワード（全サイト合計）")
        fig = px.bar(
            df_all, x="件数", y="キーワード",
            orientation="h", color="件数",
            color_continuous_scale="Blues",
            height=max(400, top_n * 22),
        )
        fig.update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(df_all, use_container_width=True, hide_index=True)

        # サイト別比較
        st.subheader("📊 サイト別キーワード比較")
        site_rows = []
        for sn, recs in site_records.items():
            if not recs:
                continue
            for kw, cnt in aggregate([r.__dict__ for r in recs]).most_common(top_n):
                site_rows.append({"サイト": sn, "キーワード": kw, "件数": cnt})
        if site_rows:
            df_site = pd.DataFrame(site_rows)
            top_kws = df_all["キーワード"].tolist()[:15]
            fig2 = px.bar(
                df_site[df_site["キーワード"].isin(top_kws)],
                x="キーワード", y="件数", color="サイト",
                barmode="group", height=500,
            )
            fig2.update_xaxes(tickangle=-45)
            st.plotly_chart(fig2, use_container_width=True)

        # ワードクラウド
        st.subheader("☁️ ワードクラウド")
        if total_counter:
            wc = WordCloud(
                width=900, height=400,
                background_color="white",
                font_path=_find_japanese_font(),
                max_words=80,
            ).generate_from_frequencies(dict(total_counter))
            fig3, ax = plt.subplots(figsize=(12, 5))
            ax.imshow(wc, interpolation="bilinear")
            ax.axis("off")
            st.pyplot(fig3)

        with st.expander("📋 取得した求人一覧"):
            st.dataframe(
                pd.DataFrame([r.__dict__ for r in all_records]),
                use_container_width=True, hide_index=True,
            )

        csv = df_all.to_csv(index=False, encoding="utf-8-sig")
        st.download_button("⬇️ TOP キーワードをCSVでダウンロード",
                           csv, "keywords.csv", "text/csv")

    # ============================================================
    # TAB 2: 楽さランキング
    # ============================================================
    with tab_ease:
        st.subheader("🛋️ 楽さランキング（サイドFIRE向け）")
        st.caption("責任が低い・検証・アシスタント・リモート・残業なし などを加点、リーダー・設計・激務 などを減点してスコアリングします。")

        all_dicts = [r.__dict__ for r in all_records]
        ranked    = ease_rank(all_dicts)

        # ---- 散布図: 楽さスコア × 年収 -------------------------
        scatter_rows = []
        for rec, result in ranked:
            salary = result.salary_min
            scatter_rows.append({
                "タイトル":   rec.get("title", "")[:30],
                "サイト":     rec.get("site", ""),
                "楽さスコア": result.score,
                "年収(万円)": salary,
                "タグ":       " ".join(result.plus_tags[:3]),
                "URL":        rec.get("url", ""),
            })
        df_scatter = pd.DataFrame(scatter_rows).dropna(subset=["年収(万円)"])

        if not df_scatter.empty:
            st.subheader("💰 楽さスコア × 年収（コスパマップ）")
            fig_s = px.scatter(
                df_scatter, x="楽さスコア", y="年収(万円)",
                color="サイト", hover_name="タイトル",
                hover_data=["タグ"],
                height=500,
            )
            # コスパゾーン（高スコア・低年収）を強調
            fig_s.add_vrect(
                x0=df_scatter["楽さスコア"].quantile(0.6), x1=df_scatter["楽さスコア"].max() + 1,
                annotation_text="🛋️ 楽ゾーン",
                annotation_position="top left",
                fillcolor="lightgreen", opacity=0.15, line_width=0,
            )
            st.plotly_chart(fig_s, use_container_width=True)
        else:
            st.info("年収情報が取得できた求人が少ないため散布図を表示できません。")

        # ---- TOP N カード表示 ----------------------------------
        st.subheader(f"🏅 楽さランキング TOP {ease_top_n}")

        STAR_MAX = 5

        for i, (rec, result) in enumerate(ranked[:ease_top_n]):
            score     = result.score
            stars     = min(STAR_MAX, max(0, score))
            star_str  = "⭐" * stars + "☆" * (STAR_MAX - stars)
            title     = rec.get("title", "(タイトルなし)")
            site      = rec.get("site", "")
            url       = rec.get("url", "")
            salary_str = (
                f"{result.salary_min}〜{result.salary_max}万円"
                if result.salary_min and result.salary_max and result.salary_min != result.salary_max
                else f"{result.salary_min}万円" if result.salary_min
                else "年収非公開"
            )

            with st.container(border=True):
                col_rank, col_body = st.columns([1, 9])
                with col_rank:
                    st.markdown(f"### #{i+1}")
                    st.markdown(f"**{score:+d}点**")
                with col_body:
                    title_md = f"[{title}]({url})" if url else title
                    st.markdown(f"**{title_md}**　`{site}`　💴 {salary_str}")
                    st.markdown(f"{star_str}")
                    if result.plus_tags:
                        st.markdown(" ".join(
                            f"`{t}`" for t in result.plus_tags
                        ))
                    if result.minus_tags:
                        st.markdown(
                            "⚠️ " + " ".join(f"`{t}`" for t in result.minus_tags[:3])
                        )

        # ---- CSVダウンロード -----------------------------------
        df_ease = pd.DataFrame([
            {
                "順位":       i + 1,
                "タイトル":   rec.get("title", ""),
                "サイト":     rec.get("site", ""),
                "楽さスコア": r.score,
                "年収(万円)": r.salary_min,
                "楽さタグ":   " / ".join(r.plus_tags),
                "注意タグ":   " / ".join(r.minus_tags),
                "URL":        rec.get("url", ""),
            }
            for i, (rec, r) in enumerate(ranked)
        ])
        st.download_button(
            "⬇️ 楽さランキングをCSVでダウンロード",
            df_ease.to_csv(index=False, encoding="utf-8-sig"),
            "ease_ranking.csv", "text/csv",
        )

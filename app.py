import os
import pandas as pd
import streamlit as st
import altair as alt

st.set_page_config(page_title="Steam Next Fest Dashboard", layout="wide")
st.title("2025년 10월 에디션 가장 많이 플레이된 체험판 50개-지원언어")

# -----------------------
# CSV 파일 로드
# -----------------------
WIDE_DEFAULT = "nextfest_50_games_languages_wide.csv"
LONG_DEFAULT = "nextfest_50_games_languages_long.csv"

@st.cache_data
def load_data():
    df_w = pd.read_csv(WIDE_DEFAULT)
    df_l = pd.read_csv(LONG_DEFAULT)
    return df_w, df_l

df, df_long = load_data()

# -----------------------
# 데이터 정리
# -----------------------
df["language_count"] = pd.to_numeric(df.get("language_count"), errors="coerce").fillna(0).astype(int)
df["name"] = df.get("name").fillna("(no name)")
df_long["language"] = df_long["language"].astype(str)

all_langs = sorted(df_long["language"].dropna().unique().tolist())
if len(all_langs) == 0:
    st.warning("언어 데이터가 비어있어요. CSV 내용을 확인해 주세요.")
    st.stop()

# -----------------------
# 사이드바 필터 (통합 컨트롤)
# -----------------------
st.sidebar.subheader("필터")

selected_langs = st.sidebar.multiselect(
    "언어 선택 (선택한 언어를 지원하는 게임만)",
    options=all_langs,
    default=[],
    key="sidebar_langs"
)

min_langs = st.sidebar.slider("최소 지원 언어 수", 0, int(df["language_count"].max() or 0), 0)

top_n = st.sidebar.slider("언어 TOP N", 5, 30, 15)

sort_key = st.sidebar.selectbox(
    "게임 리스트 정렬",
    ["지원 언어 수(내림차순)", "지원 언어 수(오름차순)", "이름(A→Z)"],
    index=0
)

show_tables = st.sidebar.checkbox("표도 같이 보기", value=True)

# -----------------------
# 필터 적용
# -----------------------
if selected_langs:
    appids = set(df_long[df_long["language"].isin(selected_langs)]["appid"].unique().tolist())
    df_f = df[df["appid"].isin(appids)].copy()
    df_long_f = df_long[df_long["appid"].isin(appids)].copy()
else:
    df_f = df.copy()
    df_long_f = df_long.copy()

df_f = df_f[df_f["language_count"] >= min_langs].copy()
df_long_f = df_long_f[df_long_f["appid"].isin(df_f["appid"])].copy()

# -----------------------
# KPI 영역
# -----------------------
avg_langs = df_f["language_count"].mean() if len(df_f) else 0

# 평균 언어 수의 상위 3개 언어
top_3_langs = (
    df_long_f.groupby("language")["appid"]
    .nunique()
    .sort_values(ascending=False)
    .head(3)
    .index.tolist()
)

# 최대 지원 언어 게임 정보
max_lang_count = int(df_f["language_count"].max() if len(df_f) else 0)
max_lang_games = df_f[df_f["language_count"] == max_lang_count]

if len(max_lang_games) > 0:
    max_game = max_lang_games.iloc[0]
    max_game_name = max_game.get("name", "N/A")
    max_game_genre = max_game.get("genre", "N/A")  # 장르 컬럼이 있다고 가정
    max_game_langs = max_game.get("languages", "")
    if isinstance(max_game_langs, str):
        max_game_langs_list = [lang.strip() for lang in max_game_langs.split(",")]
    else:
        max_game_langs_list = []
else:
    max_game_name = "N/A"
    max_game_genre = "N/A"
    max_game_langs_list = []

k1, k2, k3 = st.columns(3)

with k1:
    st.metric("필터 적용 게임 수", f"{len(df_f)} 개")

with k2:
    st.metric("평균 지원 언어 수", f"{avg_langs:.2f} 개")
    if top_3_langs:
        st.caption(f"**상위 3개 언어:** {', '.join(top_3_langs)}")

with k3:
    st.metric("최대 지원 언어 수", f"{max_lang_count} 개")
    st.caption(f"**게임명:** {max_game_name}")
    if max_game_genre != "N/A":
        st.caption(f"**장르:** {max_game_genre}")
    if max_game_langs_list:
        st.caption(f"**지원 언어:** {', '.join(max_game_langs_list[:15])}")

st.divider()

# -----------------------
# 탭 구성
# -----------------------
tab1, tab2, tab3 = st.tabs(["요약", "언어 TOP", "게임 리스트"])

# -----------------------
# 1) 요약 탭
# -----------------------
with tab1:
    st.subheader("요약")

    top_f = (
        df_long_f.groupby("language")["appid"]
        .nunique()
        .sort_values(ascending=False)
        .reset_index(name="game_count")
    )

    # 빠른 필터 추가
    col_chart, col_filter = st.columns([3, 1])
    
    with col_filter:
        st.markdown("#### 빠른 필터")
        lang_pick_summary = st.selectbox(
            "언어 선택",
            options=all_langs,
            index=(all_langs.index("English") if "English" in all_langs else 0),
            key="summary_lang_filter"
        )
        
        # 선택한 언어로 필터 업데이트
        if lang_pick_summary:
            appids_for_lang = df_long_f[df_long_f["language"] == lang_pick_summary]["appid"].unique().tolist()
            df_lang_games_summary = df_f[df_f["appid"].isin(appids_for_lang)].copy()
            
            st.metric(f"{lang_pick_summary} 지원 게임 수", f"{len(df_lang_games_summary)} 개")
            
            df_lang_games_summary = df_lang_games_summary.sort_values(["language_count", "name"], ascending=[False, True])
            cols = [c for c in ["name", "language_count", "languages", "appid"] if c in df_lang_games_summary.columns]
            st.dataframe(df_lang_games_summary[cols].head(10), use_container_width=True, height=300)

    with col_chart:
        # 정수형 축으로 차트 생성
        chart = (
            alt.Chart(top_f.head(top_n))
            .mark_bar()
            .encode(
                y=alt.Y("language:N", sort="-x", title=None),
                x=alt.X("game_count:Q", title="지원 게임 수", axis=alt.Axis(format='d')),
                tooltip=[
                    alt.Tooltip("language:N", title="언어"), 
                    alt.Tooltip("game_count:Q", title="게임 수", format='d')
                ]
            )
            .properties(height=520)
        )
        st.altair_chart(chart, use_container_width=True)

    if show_tables:
        st.caption("언어별 지원 게임 수(필터 적용)")
        st.dataframe(top_f.head(top_n), use_container_width=True)

# -----------------------
# 2) 언어 TOP 탭
# -----------------------
with tab2:
    st.subheader(f"가장 많이 지원되는 언어 TOP {top_n}")

    top_f = (
        df_long_f.groupby("language")["appid"]
        .nunique()
        .sort_values(ascending=False)
        .reset_index(name="game_count")
    )

    c1, c2 = st.columns([2, 1])

    with c1:
        # 정수형 축으로 차트 생성
        chart = (
            alt.Chart(top_f.head(top_n))
            .mark_bar()
            .encode(
                y=alt.Y("language:N", sort="-x", title=None),
                x=alt.X("game_count:Q", title="지원 게임 수", axis=alt.Axis(format='d')),
                tooltip=[
                    alt.Tooltip("language:N", title="언어"), 
                    alt.Tooltip("game_count:Q", title="게임 수", format='d')
                ]
            )
            .properties(height=520)
        )
        st.altair_chart(chart, use_container_width=True)

    with c2:
        st.markdown("#### 빠른 필터")
        lang_pick = st.selectbox(
            "언어 선택(해당 언어 지원 게임 보기)",
            options=all_langs,
            index=(all_langs.index("English") if "English" in all_langs else 0),
            key="top_lang_filter"
        )
        appids_for_lang = df_long_f[df_long_f["language"] == lang_pick]["appid"].unique().tolist()
        df_lang_games = df_f[df_f["appid"].isin(appids_for_lang)].copy()

        st.metric(f"{lang_pick} 지원 게임 수", f"{len(df_lang_games)} 개")
        df_lang_games = df_lang_games.sort_values(["language_count", "name"], ascending=[False, True])
        cols = [c for c in ["name", "language_count", "languages", "appid"] if c in df_lang_games.columns]
        st.dataframe(df_lang_games[cols].head(20), use_container_width=True, height=420)

    if show_tables:
        st.caption("언어 TOP 표")
        st.dataframe(top_f.head(top_n), use_container_width=True)

# -----------------------
# 3) 게임 리스트 탭
# -----------------------
with tab3:
    st.subheader("게임별 지원 언어 수")

    if sort_key == "지원 언어 수(내림차순)":
        df_show = df_f.sort_values(["language_count", "name"], ascending=[False, True])
    elif sort_key == "지원 언어 수(오름차순)":
        df_show = df_f.sort_values(["language_count", "name"], ascending=[True, True])
    else:
        df_show = df_f.sort_values(["name"], ascending=[True])

    # 검색(게임명)
    query = st.text_input("게임명 검색", value="")
    if query.strip():
        df_show = df_show[df_show["name"].str.contains(query, case=False, na=False)].copy()

    cols = [c for c in ["name", "language_count", "languages", "appid"] if c in df_show.columns]

    st.dataframe(df_show[cols], use_container_width=True, height=560)

    # 분포 히스토그램 (정수형)
    hist = (
        alt.Chart(df_f)
        .mark_bar()
        .encode(
            x=alt.X("language_count:Q", bin=alt.Bin(maxbins=20), title="지원 언어 수", axis=alt.Axis(format='d')),
            y=alt.Y("count():Q", title="게임 수", axis=alt.Axis(format='d')),
            tooltip=[alt.Tooltip("count():Q", title="게임 수", format='d')]
        )
        .properties(height=240)
    )
    st.caption("지원 언어 수 분포")
    st.altair_chart(hist, use_container_width=True)

# -----------------------
# 출처 링크 (하단)
# -----------------------
st.divider()
st.markdown(
    '<p style="text-align: center; font-size: 12px;">'
    '<a href="https://store.steampowered.com/sale/nextfestmostplayed?l=koreana" '
    'style="color: blue;" target="_blank">데이터 출처: Steam Next Fest Most Played</a>'
    '</p>',
    unsafe_allow_html=True
)

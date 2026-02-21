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
    
    # * 기호 제거 (인터페이스만 지원 표시)
    df_l["language"] = df_l["language"].str.replace("*", "", regex=False)
    df_w["languages"] = df_w["languages"].str.replace("*", "", regex=False) if "languages" in df_w.columns else df_w.get("languages", "")
    
    return df_w, df_l

df, df_long = load_data()

# -----------------------
# 데이터 정리
# -----------------------
df["language_count"] = pd.to_numeric(df.get("language_count"), errors="coerce").fillna(0).astype(int)
df["name"] = df.get("name").fillna("(no name)")
df_long["language"] = df_long["language"].astype(str).str.strip()

all_langs = sorted(df_long["language"].dropna().unique().tolist())
if len(all_langs) == 0:
    st.warning("언어 데이터가 비어있어요. CSV 내용을 확인해 주세요.")
    st.stop()

# -----------------------
# KPI 영역
# -----------------------
avg_langs = df["language_count"].mean() if len(df) else 0

# 평균 언어 수의 상위 3개 언어
top_3_langs = (
    df_long.groupby("language")["appid"]
    .nunique()
    .sort_values(ascending=False)
    .head(3)
    .index.tolist()
)

# 최대 지원 언어 게임 정보
max_lang_count = int(df["language_count"].max() if len(df) else 0)
max_lang_games = df[df["language_count"] == max_lang_count]

if len(max_lang_games) > 0:
    max_game = max_lang_games.iloc[0]
    max_game_name = max_game.get("name", "N/A")
    max_game_genre = max_game.get("genre", "N/A")
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
    st.metric("전체 게임 수", f"{len(df)} 개")

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
tab1, tab2, tab3 = st.tabs(["요약", "가장 많이 지원되는 언어 TOP 5", "게임 리스트"])

# -----------------------
# 1) 요약 탭
# -----------------------
with tab1:
    st.subheader("전체 50개 게임의 지원 언어 분석")
    
    # 언어 선택 필터
    st.markdown("#### 언어 선택")
    lang_options = ["-"] + all_langs
    selected_lang = st.selectbox(
        "특정 언어로 필터링",
        options=lang_options,
        index=0,
        key="summary_lang_select",
        label_visibility="collapsed"
    )
    
    # 필터링된 데이터
    if selected_lang and selected_lang != "-":
        appids_filtered = df_long[df_long["language"] == selected_lang]["appid"].unique()
        df_filtered = df[df["appid"].isin(appids_filtered)]
        df_long_filtered = df_long[df_long["appid"].isin(appids_filtered)]
        st.info(f"'{selected_lang}' 언어를 지원하는 게임: {len(df_filtered)}개")
    else:
        df_filtered = df.copy()
        df_long_filtered = df_long.copy()
    
    # 언어별 게임 수 집계
    top_langs = (
        df_long_filtered.groupby("language")["appid"]
        .nunique()
        .sort_values(ascending=False)
        .reset_index(name="game_count")
    )
    
    # 차트
    chart = (
        alt.Chart(top_langs)
        .mark_bar()
        .encode(
            y=alt.Y("language:N", sort="-x", title="언어"),
            x=alt.X("game_count:Q", title="지원 게임 수", axis=alt.Axis(format='d')),
            tooltip=[
                alt.Tooltip("language:N", title="언어"), 
                alt.Tooltip("game_count:Q", title="게임 수", format='d')
            ]
        )
        .properties(height=500)
    )
    st.altair_chart(chart, use_container_width=True)
    
    st.divider()
    
    # 상세 표 (게임명 포함)
    st.caption("언어별 지원 게임 상세")
    
    top_langs_with_games = top_langs.copy()
    game_names_list = []
    
    for _, row in top_langs_with_games.iterrows():
        lang = row['language']
        game_appids = df_long_filtered[df_long_filtered["language"] == lang]["appid"].unique()
        games = df_filtered[df_filtered["appid"].isin(game_appids)]["name"].tolist()
        game_names_list.append(", ".join(games))
    
    top_langs_with_games["게임 명칭"] = game_names_list
    
    st.dataframe(
        top_langs_with_games[["language", "game_count", "게임 명칭"]], 
        use_container_width=True,
        height=600
    )

# -----------------------
# 2) 가장 많이 지원되는 언어 TOP 5 탭
# -----------------------
with tab2:
    st.subheader("가장 많이 지원되는 언어 TOP 5")
    
    # TOP 5 언어
    top_5_langs = (
        df_long.groupby("language")["appid"]
        .nunique()
        .sort_values(ascending=False)
        .head(5)
        .reset_index(name="game_count")
    )
    
    # 차트
    chart_top5 = (
        alt.Chart(top_5_langs)
        .mark_bar()
        .encode(
            y=alt.Y("language:N", sort="-x", title="언어"),
            x=alt.X("game_count:Q", title="지원 게임 수", axis=alt.Axis(format='d')),
            tooltip=[
                alt.Tooltip("language:N", title="언어"), 
                alt.Tooltip("game_count:Q", title="게임 수", format='d')
            ]
        )
        .properties(height=300)
    )
    st.altair_chart(chart_top5, use_container_width=True)
    
    st.divider()
    
    # 상세 표 (게임명 포함)
    st.caption("TOP 5 언어별 지원 게임 상세")
    
    top_5_with_games = top_5_langs.copy()
    game_names_list_top5 = []
    
    for _, row in top_5_with_games.iterrows():
        lang = row['language']
        game_appids = df_long[df_long["language"] == lang]["appid"].unique()
        games = df[df["appid"].isin(game_appids)]["name"].tolist()
        game_names_list_top5.append(", ".join(games))
    
    top_5_with_games["게임 명칭"] = game_names_list_top5
    
    st.dataframe(
        top_5_with_games[["language", "game_count", "게임 명칭"]], 
        use_container_width=True,
        height=400
    )

# -----------------------
# 3) 게임 리스트 탭
# -----------------------
with tab3:
    st.subheader("게임별 지원 언어 분석")
    
    # 필터
    col1, col2, col3 = st.columns(3)
    
    with col1:
        sort_option = st.selectbox(
            "정렬",
            ["지원 언어 수 (많은 순)", "지원 언어 수 (적은 순)", "게임명 (A-Z)"],
            index=0
        )
    
    with col2:
        search_query = st.text_input("게임명 검색", value="")
    
    with col3:
        show_histogram = st.checkbox("분포 그래프 보기", value=True)
    
    # 정렬
    if sort_option == "지원 언어 수 (많은 순)":
        df_show = df.sort_values(["language_count", "name"], ascending=[False, True])
    elif sort_option == "지원 언어 수 (적은 순)":
        df_show = df.sort_values(["language_count", "name"], ascending=[True, True])
    else:
        df_show = df.sort_values(["name"], ascending=[True])
    
    # 검색
    if search_query.strip():
        df_show = df_show[df_show["name"].str.contains(search_query, case=False, na=False)].copy()
    
    # 히스토그램 (상단)
    if show_histogram:
        st.caption("지원 언어 수 분포")
        
        # 데이터 집계 (내림차순)
        hist_data = (
            df["language_count"]
            .value_counts()
            .reset_index()
            .rename(columns={"language_count": "언어_수", "count": "게임_수"})
            .sort_values("언어_수", ascending=False)
        )
        
        hist_chart = (
            alt.Chart(hist_data)
            .mark_bar()
            .encode(
                x=alt.X("언어_수:Q", title="지원 언어 수", axis=alt.Axis(format='d')),
                y=alt.Y("게임_수:Q", title="게임 수", axis=alt.Axis(format='d')),
                tooltip=[
                    alt.Tooltip("언어_수:Q", title="지원 언어 수", format='d'),
                    alt.Tooltip("게임_수:Q", title="게임 수", format='d')
                ]
            )
            .properties(height=240)
        )
        st.altair_chart(hist_chart, use_container_width=True)
        
        st.divider()
    
    # 게임 리스트 테이블
    st.caption(f"전체 게임 목록 ({len(df_show)}개)")
    cols = [c for c in ["name", "language_count", "languages", "appid"] if c in df_show.columns]
    st.dataframe(df_show[cols], use_container_width=True, height=500)

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

# -----------------------
# * 표시 설명
# -----------------------
st.markdown(
    '<p style="text-align: center; font-size: 11px; color: gray;">'
    '참고: 원본 데이터의 "*" 표시(인터페이스만 지원)는 자동으로 제거되었습니다.'
    '</p>',
    unsafe_allow_html=True
)

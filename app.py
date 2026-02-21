import os
import pandas as pd
import streamlit as st
import altair as alt

st.set_page_config(page_title="Steam Next Fest Dashboard", layout="wide")
st.title("Steam Next Fest - Supported Languages Dashboard")

# -----------------------
# 설정: CSV 자동 로드(폴더에 파일이 있으면 업로드 UI 숨김)
# -----------------------
WIDE_DEFAULT = "nextfest_50_games_languages_wide.csv"
LONG_DEFAULT = "nextfest_50_games_languages_long.csv"

st.sidebar.header("설정")

auto_mode = st.sidebar.checkbox(
    "폴더의 CSV 자동 로드(업로드 숨김)",
    value=os.path.exists(WIDE_DEFAULT) and os.path.exists(LONG_DEFAULT),
)

def load_data():
    if auto_mode:
        df_w = pd.read_csv(WIDE_DEFAULT)
        df_l = pd.read_csv(LONG_DEFAULT)
        return df_w, df_l

    wide_file = st.file_uploader("wide CSV 업로드", type=["csv"], key="wide")
    long_file = st.file_uploader("long CSV 업로드", type=["csv"], key="long")

    if not (wide_file and long_file):
        st.info("CSV 두 개(wide/long)를 업로드하면 대시보드가 표시됩니다.")
        st.stop()

    df_w = pd.read_csv(wide_file)
    df_l = pd.read_csv(long_file)
    return df_w, df_l

df, df_long = load_data()

# -----------------------
# 데이터 정리
# -----------------------
df["language_count"] = pd.to_numeric(df.get("language_count"), errors="coerce").fillna(0).astype(int)
df["name"] = df.get("name").fillna("(no name)")
df_long["language"] = df_long["language"].astype(str)

all_langs = sorted(df_long["language"].dropna().unique().tolist())
if "English" not in all_langs and len(all_langs) == 0:
    st.warning("언어 데이터가 비어있어요. CSV 내용을 확인해 주세요.")
    st.stop()

# -----------------------
# 사이드바 필터
# -----------------------
st.sidebar.subheader("필터")

english_only = st.sidebar.checkbox("영어(English)만 보기", value=False)

selected_langs = st.sidebar.multiselect(
    "언어 선택(선택한 언어를 지원하는 게임만)",
    options=all_langs,
    default=(["English"] if english_only and "English" in all_langs else []),
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

k1, k2, k3 = st.columns(3)
k1.metric("필터 적용 게임 수", f"{len(df_f)} 개")
k2.metric("평균 지원 언어 수", f"{avg_langs:.2f} 개")
k3.metric("최대 지원 언어 수", f"{int(df_f['language_count'].max() if len(df_f) else 0)} 개")

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

    # 예쁜 가로 막대 (Altair)
    chart = (
        alt.Chart(top_f.head(top_n))
        .mark_bar()
        .encode(
            y=alt.Y("language:N", sort="-x", title=None),
            x=alt.X("game_count:Q", title="지원 게임 수"),
            tooltip=[alt.Tooltip("language:N", title="언어"), alt.Tooltip("game_count:Q", title="게임 수")]
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
        chart = (
            alt.Chart(top_f.head(top_n))
            .mark_bar()
            .encode(
                y=alt.Y("language:N", sort="-x", title=None),
                x=alt.X("game_count:Q", title="지원 게임 수"),
                tooltip=[alt.Tooltip("language:N", title="언어"), alt.Tooltip("game_count:Q", title="게임 수")]
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

    # 분포 히스토그램(예쁘게)
    hist = (
        alt.Chart(df_f)
        .mark_bar()
        .encode(
            x=alt.X("language_count:Q", bin=alt.Bin(maxbins=20), title="지원 언어 수"),
            y=alt.Y("count():Q", title="게임 수"),
            tooltip=[alt.Tooltip("count():Q", title="게임 수")]
        )
        .properties(height=240)
    )
    st.caption("지원 언어 수 분포")
    st.altair_chart(hist, use_container_width=True)

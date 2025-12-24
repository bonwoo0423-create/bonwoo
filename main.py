import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
import unicodedata
import io

# ===============================
# Streamlit 기본 설정
# ===============================
st.set_page_config(
    page_title="극지식물 최적 EC 농도 연구",
    layout="wide"
)

# 한글 폰트 (Streamlit)
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR&display=swap');
html, body, [class*="css"] {
    font-family: 'Noto Sans KR', 'Malgun Gothic', sans-serif;
}
</style>
""", unsafe_allow_html=True)

PLOTLY_FONT = dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")

# ===============================
# 경로 설정
# ===============================
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

# ===============================
# 유틸: 키워드 기반 한글 파일 탐색 (NFC/NFD 안전)
# ===============================
def find_file_by_keywords(directory: Path, keywords: list):
    for f in directory.iterdir():
        fname = unicodedata.normalize("NFC", f.name)
        if all(k in fname for k in keywords):
            return f
    return None

# ===============================
# 환경 데이터 로딩
# ===============================
@st.cache_data
def load_environment_data():
    schools = ["송도고", "하늘고", "아라고", "동산고"]
    env_data = {}

    for school in schools:
        file_path = find_file_by_keywords(
            DATA_DIR,
            [school, "환경데이터"]
        )

        if file_path is None:
            st.error(f"환경 데이터 파일을 찾을 수 없습니다: {school}")
            continue

        df = pd.read_csv(file_path)
        df["school"] = school
        env_data[school] = df

    return env_data

# ===============================
# 생육 데이터 로딩
# ===============================
@st.cache_data
def load_growth_data():
    file_path = find_file_by_keywords(
        DATA_DIR,
        ["생육결과데이터"]
    )

    if file_path is None:
        st.error("생육 결과 XLSX 파일을 찾을 수 없습니다.")
        return {}

    xls = pd.ExcelFile(file_path, engine="openpyxl")
    growth_data = {}

    for sheet in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet)
        df["school"] = sheet
        growth_data[sheet] = df

    return growth_data

# ===============================
# 데이터 로딩
# ===============================
with st.spinner("데이터 로딩 중..."):
    env_data = load_environment_data()
    growth_data = load_growth_data()

if not env_data or not growth_data:
    st.error("필수 데이터가 없어 앱을 실행할 수 없습니다.")
    st.stop()

# ===============================
# EC 정보
# ===============================
EC_INFO = {
    "송도고": 1.0,
    "하늘고": 2.0,
    "아라고": 4.0,
    "동산고": 8.0,
}

# ===============================
# 사이드바
# ===============================
st.sidebar.title("학교 선택")
school_option = st.sidebar.selectbox(
    "학교",
    ["전체"] + list(EC_INFO.keys())
)

selected_schools = (
    list(env_data.keys())
    if school_option == "전체"
    else [school_option]
)

# ===============================
# 제목
# ===============================
st.title("🌱 극지식물 최적 EC 농도 연구")

# ===============================
# 탭
# ===============================
tab1, tab2, tab3 = st.tabs(["📖 실험 개요", "🌡️ 환경 데이터", "📊 생육 결과"])

# ======================================================
# Tab 1 실험 개요
# ======================================================
with tab1:
    st.subheader("연구 목적")
    st.markdown("""
    4개 학교에서 서로 다른 EC 조건으로 재배된 극지식물의  
    **생육 결과를 비교하여 최적 EC 농도를 도출**한다.
    """)

    rows = []
    for school, ec in EC_INFO.items():
        rows.append({
            "학교": school,
            "EC 목표": ec,
            "개체 수": len(growth_data.get(school, []))
        })

    df_info = pd.DataFrame(rows)
    st.dataframe(df_info, use_container_width=True)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("총 개체 수", df_info["개체 수"].sum())
    c2.metric("평균 온도", f"{pd.concat(env_data.values())['temperature'].mean():.1f}℃")
    c3.metric("평균 습도", f"{pd.concat(env_data.values())['humidity'].mean():.1f}%")
    c4.metric("최적 EC", "2.0 (하늘고) ⭐")

# ======================================================
# Tab 2 환경 데이터
# ======================================================
with tab2:
    env_all = pd.concat(
        [env_data[s] for s in selected_schools],
        ignore_index=True
    )

    avg = env_all.groupby("school").mean(numeric_only=True).reset_index()

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=["평균 온도", "평균 습도", "평균 pH", "EC 비교"]
    )

    fig.add_bar(x=avg["school"], y=avg["temperature"], row=1, col=1)
    fig.add_bar(x=avg["school"], y=avg["humidity"], row=1, col=2)
    fig.add_bar(x=avg["school"], y=avg["ph"], row=2, col=1)
    fig.add_bar(x=avg["school"], y=avg["ec"], name="실측 EC", row=2, col=2)
    fig.add_bar(x=list(EC_INFO.keys()), y=list(EC_INFO.values()), name="목표 EC", row=2, col=2)

    fig.update_layout(height=700, font=PLOTLY_FONT)
    st.plotly_chart(fig, use_container_width=True)

# ======================================================
# Tab 3 생육 결과
# ======================================================
with tab3:
    growth_all = pd.concat(
        [growth_data[s] for s in selected_schools],
        ignore_index=True
    )

    growth_all["EC"] = growth_all["school"].map(EC_INFO)

    ec_avg = growth_all.groupby("EC").mean(numeric_only=True).reset_index()
    best_ec = ec_avg.loc[ec_avg["생중량(g)"].idxmax(), "EC"]

    st.metric("🥇 최고 평균 생중량 EC", f"{best_ec}")

    fig = px.box(
        growth_all,
        x="school",
        y="생중량(g)",
        color="school",
        title="학교별 생중량 분포"
    )
    fig.update_layout(font=PLOTLY_FONT)
    st.plotly_chart(fig, use_container_width=True)

    buffer = io.BytesIO()
    growth_all.to_excel(buffer, index=False, engine="openpyxl")
    buffer.seek(0)

    st.download_button(
        "생육 데이터 XLSX 다운로드",
        data=buffer,
        file_name="생육결과_통합.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

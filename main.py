import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
import unicodedata
import io

# ===============================
# 기본 설정
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
# 유틸: 한글 파일 찾기 (NFC/NFD 안전)
# ===============================
def find_file_by_name(directory: Path, target_name: str):
    target_nfc = unicodedata.normalize("NFC", target_name)
    target_nfd = unicodedata.normalize("NFD", target_name)

    for f in directory.iterdir():
        fname_nfc = unicodedata.normalize("NFC", f.name)
        fname_nfd = unicodedata.normalize("NFD", f.name)
        if fname_nfc == target_nfc or fname_nfd == target_nfd:
            return f
    return None

# ===============================
# 데이터 로딩
# ===============================
@st.cache_data
def load_environment_data():
    school_files = {
        "송도고": "송도고_환경데이터.csv",
        "하늘고": "하늘고_환경데이터.csv",
        "아라고": "아라고_환경데이터.csv",
        "동산고": "동산고_환경데이터.csv",
    }

    env_data = {}
    for school, fname in school_files.items():
        file_path = find_file_by_name(DATA_DIR, fname)
        if file_path is None:
            st.error(f"환경 데이터 파일을 찾을 수 없습니다: {fname}")
            continue
        df = pd.read_csv(file_path)
        df["school"] = school
        env_data[school] = df

    return env_data


@st.cache_data
def load_growth_data():
    xlsx_name = "4개교_생육결과데이터.xlsx"
    file_path = find_file_by_name(DATA_DIR, xlsx_name)
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


with st.spinner("데이터 로딩 중..."):
    env_data = load_environment_data()
    growth_data = load_growth_data()

if not env_data or not growth_data:
    st.error("필수 데이터가 없어 앱을 실행할 수 없습니다.")
    st.stop()

# ===============================
# 기본 정보
# ===============================
EC_INFO = {
    "송도고": 1.0,
    "하늘고": 2.0,
    "아라고": 4.0,
    "동산고": 8.0,
}

COLOR_MAP = {
    "송도고": "#1f77b4",
    "하늘고": "#2ca02c",
    "아라고": "#ff7f0e",
    "동산고": "#d62728",
}

# =============================

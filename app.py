# 메인 앱에 통합하는 코드
import streamlit as st
import pandas as pd
import numpy as np
import os
from datetime import date
from pyecharts import options as opts
from pyecharts.charts import Tree
from pyecharts.commons.utils import JsCode
from streamlit_echarts import st_pyecharts
import plotly.express as px
import gspread

# ------------------ CONFIG ------------------
st.set_page_config(
    page_title='Cell Line Manager', 
    layout='wide',
    initial_sidebar_state="expanded",
    menu_items={
        'About': "Cell Line Tube Manager - Version 3.0"
    }
)

# ------------------ 스타일링 코드 주입 ------------------
st.markdown("""
<style>
/* 모던한 색상 팔레트 */
:root {
  --primary: #6366F1;       /* 인디고 */
  --primary-light: #818CF8; /* 밝은 인디고 */
  --secondary: #10B981;     /* 에메랄드 */
  --accent: #F59E0B;        /* 앰버 */
  --danger: #EF4444;        /* 빨강 */
  --success: #22C55E;       /* 녹색 */
  --gray-50: #F9FAFB;
  --gray-100: #F3F4F6;
  --gray-200: #E5E7EB;
  --gray-300: #D1D5DB;
  --gray-400: #9CA3AF;
  --gray-500: #6B7280;
  --gray-600: #4B5563;
  --gray-700: #374151;
  --gray-800: #1F2937;
  --gray-900: #111827;
  --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
  --shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06);
  --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
  --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
}

/* 기본 스타일링 */
.stApp {
  background-color: var(--gray-50);
  font-family: "Inter", -apple-system, BlinkMacSystemFont, sans-serif;
  color: var(--gray-800);
}

/* 헤더 스타일링 */
h1 {
  font-size: 2rem;
  font-weight: 700;
  color: var(--gray-900);
  margin-bottom: 1.5rem;
  letter-spacing: -0.025em;
  line-height: 1.2;
}

h2 {
  font-size: 1.5rem;
  font-weight: 600;
  color: var(--gray-800);
  margin: 1.75rem 0 1rem;
  letter-spacing: -0.025em;
}

h3 {
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--gray-700);
  margin: 1.25rem 0 0.75rem;
  letter-spacing: -0.025em;
}

/* 카드 & 컨테이너 */
.container, .info-card, .metric-card {
  background-color: white;
  border-radius: 0.75rem;
  padding: 1.5rem;
  box-shadow: var(--shadow-md);
  border: 1px solid var(--gray-200);
  transition: transform 0.2s, box-shadow 0.2s;
}

.container:hover, .info-card:hover, .metric-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-lg);
}

/* 버튼 */
.stButton > button {
  border-radius: 0.5rem;
  font-weight: 600;
  letter-spacing: -0.01em;
  padding: 0.5rem 1.25rem;
  color: white !important;
  background-color: var(--primary) !important;
  transition: all 0.2s;
  border: none;
  box-shadow: var(--shadow-sm);
}

.stButton > button:hover {
  background-color: var(--primary-light) !important;
  transform: translateY(-1px);
  box-shadow: var(--shadow);
}

.stButton > button:active {
  transform: scale(0.98);
}

/* 버튼 변형 */
.secondary-button {
  background-color: var(--secondary) !important;
  color: white !important;
}

.danger-button {
  background-color: var(--danger) !important;
  color: white !important;
}

.success-button {
  background-color: var(--success) !important;

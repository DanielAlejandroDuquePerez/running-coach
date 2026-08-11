import os
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

# 1. Cargar variables de entorno desde el archivo .env (Desarrollo local)
load_dotenv()

# 2. Sincronizar API Key con st.secrets (Streamlit Cloud / secrets.toml)
if "GEMINI_API_KEY" not in os.environ and "GEMINI_API_KEY" in st.secrets:
    os.environ["GEMINI_API_KEY"] = st.secrets["GEMINI_API_KEY"]

from src.config import DATA_PATH
from src.data_loader import load_data
from src.dashboard_helpers import ensure_upload_state, render_status_badge
from src.metrics import add_pace, clean_data
from src.tabs_analitica import render_analitica_tab
from src.tabs_ai import render_ai_tab
from src.tabs_ritmos import render_ritmos_tab
from src.tabs_seguimiento import render_seguimiento_tab
from src.tabs_today import render_today_tab
from src.ui import render_stress_alert


st.set_page_config(
    page_title="Performance Dashboard",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    :root {
        --bg-main: #0B0E14;
        --bg-panel: #121824;
        --bg-panel-strong: #0F1520;
        --border-panel: #1E2A38;
        --text-primary: #FFFFFF;
        --text-secondary: #8A99AD;
        --accent-cyan: #00D2FF;
        --accent-lime: #00E676;
        --accent-amber: #FFB300;
        --accent-red: #FF3366;
        --grid-soft: rgba(255, 255, 255, 0.05);
    }

    html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"], [data-testid="stToolbar"] {
        background: var(--bg-main) !important;
        color: var(--text-primary) !important;
    }

    .block-container {
        padding-top: 1.1rem !important;
        padding-bottom: 2rem !important;
        padding-left: 0.9rem !important;
        padding-right: 0.9rem !important;
        max-width: 100% !important;
    }

    h1, h2, h3, h4, h5, h6, p, span, div, label {
        color: var(--text-primary);
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 0.5rem;
        background: rgba(18, 24, 36, 0.92);
        border: 1px solid var(--border-panel);
        border-radius: 16px;
        padding: 0.35rem;
        box-shadow: 0 10px 24px rgba(0, 0, 0, 0.18);
    }

    .stTabs [data-baseweb="tab"] {
        height: 44px;
        padding: 0.55rem 1rem;
        border-radius: 12px;
        background: transparent;
        color: var(--text-secondary) !important;
        font-weight: 700;
        border: 1px solid transparent;
    }

    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        color: var(--text-primary) !important;
        border-color: rgba(0, 210, 255, 0.55);
        background: linear-gradient(180deg, rgba(0, 210, 255, 0.16) 0%, rgba(0, 210, 255, 0.08) 100%);
        box-shadow: inset 0 -2px 0 0 var(--accent-cyan);
    }

    .stExpander {
        border: 1px solid var(--border-panel) !important;
        border-radius: 12px !important;
        background: rgba(18, 24, 36, 0.88) !important;
        margin-bottom: 0.8rem;
        box-shadow: 0 10px 20px rgba(0, 0, 0, 0.20);
    }

    [data-testid="stDataFrame"] {
        border-radius: 12px;
        overflow: hidden;
        border: 1px solid var(--border-panel);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

ensure_upload_state()

if "km_agudos" not in st.session_state:
    st.session_state["km_agudos"] = 40.0
if "km_cronicos" not in st.session_state:
    st.session_state["km_cronicos"] = 35.0
if "prompt_sugerido_ia" not in st.session_state:
    st.session_state["prompt_sugerido_ia"] = ""
if "readiness_log" not in st.session_state:
    st.session_state["readiness_log"] = []
if "feedback_data" not in st.session_state:
    st.session_state["feedback_data"] = {}
if "current_ai_plan" not in st.session_state:
    st.session_state["current_ai_plan"] = ""

try:
    raw_data = load_data(DATA_PATH)
except Exception as exc:
    st.error(f"No se pudo cargar el archivo de datos: {exc}")
    st.stop()

cleaned_data = add_pace(clean_data(raw_data))

if cleaned_data.empty or "Activity Date" not in cleaned_data.columns:
    st.warning("No hay datos válidos para mostrar.")
    st.stop()

cleaned_data["Activity Date"] = pd.to_datetime(cleaned_data["Activity Date"], errors="coerce")
cleaned_data = cleaned_data.dropna(subset=["Activity Date"])

if cleaned_data.empty:
    st.warning("No hay actividades válidas con fecha para mostrar.")
    st.stop()

from datetime import date

data_min = cleaned_data["Activity Date"].min().date()
data_max = cleaned_data["Activity Date"].max().date()
min_date = data_min
max_date = max(data_max, date.today())

if "date_range" not in st.session_state:
    st.session_state["date_range"] = (min_date, max_date)

with st.sidebar:
    st.markdown("### Configuración de Análisis")
    selected_dates = st.date_input(
        "Rango de Fechas",
        value=st.session_state["date_range"],
        min_value=min_date,
        max_value=max_date,
    )

if isinstance(selected_dates, tuple) and len(selected_dates) == 2:
    inicio, fin = selected_dates
else:
    inicio, fin = st.session_state["date_range"]

st.session_state["date_range"] = (inicio, fin)

filtered = cleaned_data[(cleaned_data["Activity Date"].dt.date >= inicio) & (cleaned_data["Activity Date"].dt.date <= fin)].copy()
filtered_data = filtered.copy()

if filtered.empty:
    render_status_badge("No hay datos registrados en el rango de fechas seleccionado.", tone="warning", icon="!")
    st.stop()

st.title("Panel de Rendimiento Atlético")
st.caption("Fase Específica | Objetivo Principal: Reto Rosa (15K)")
st.markdown("---")

render_stress_alert(cleaned_data)

if "df_actividades" not in st.session_state:
    st.session_state["df_actividades"] = None

# Pestañas por dominio
_tabs = st.tabs([
    "🏠 Tablero Hoy",
    "🎯 Ritmos & Marcas",
    "🩺 Readiness y Sensaciones",
    "🤖 Coach IA",
    "📓 Seguimiento",
])

with _tabs[0]:
    render_today_tab(st.session_state, filtered, cleaned_data)

with _tabs[1]:
    render_ritmos_tab(st.session_state, filtered)

with _tabs[2]:
    render_analitica_tab(st.session_state, filtered)

with _tabs[3]:
    render_ai_tab(st.session_state, filtered_data)

with _tabs[4]:
    render_seguimiento_tab(st.session_state)
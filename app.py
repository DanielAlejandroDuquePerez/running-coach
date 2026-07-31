import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from plotly.subplots import make_subplots

def make_responsive_chart(fig, height=320, title=""):
    """Aplica formato optimizado para touch y pantallas móviles."""
    fig.update_layout(
        title=dict(text=title, font=dict(size=14)),
        height=height,
        margin=dict(l=10, r=10, t=35, b=20),
        legend=dict(orientation="h", y=-0.2, x=0.5, xanchor="center"),
        hovermode="x unified",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)"
    )
    return fig

import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- FUNCIÓN PARA EL GRÁFICO COMBINADO VOLUMEN vs ACWR ---
def render_interactive_ecosystem_chart(df):
    if df is None or df.empty:
        return

    # Asegurar orden por fecha
    df_copy = df.copy()
    col_fecha = next((col for col in df_copy.columns if 'fecha' in col or 'date' in col), None)
    col_dist = next((col for col in df_copy.columns if 'distancia' in col or 'km' in col or 'distance' in col), None)

    if not col_fecha or not col_dist:
        return

    df_copy[col_fecha] = pd.to_datetime(df_copy[col_fecha])
    df_copy['semana'] = df_copy[col_fecha].dt.to_period('W').dt.start_time
    df_weekly = df_copy.groupby('semana')[col_dist].sum().reset_index()

    # Cálculo dinámico de carga
    df_weekly['cronica'] = df_weekly[col_dist].rolling(window=4, min_periods=1).mean()
    df_weekly['acwr'] = df_weekly[col_dist] / df_weekly['cronica'].replace(0, 1)

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Barras de Volumen
    fig.add_trace(
        go.Bar(
            x=df_weekly['semana'], 
            y=df_weekly[col_dist], 
            name="Volumen Semanal (Km)",
            marker_color="#1E88E5",
            opacity=0.7
        ),
        secondary_y=False
    )

    # Línea de ACWR
    fig.add_trace(
        go.Scatter(
            x=df_weekly['semana'], 
            y=df_weekly['acwr'], 
            name="Ratio ACWR",
            mode="lines+markers",
            line=dict(color="#FFC107", width=3)
        ),
        secondary_y=True
    )

    # Líneas horizontales de riesgo
    fig.add_hline(y=1.5, line_dash="dot", line_color="red", secondary_y=True)
    fig.add_hline(y=0.8, line_dash="dot", line_color="green", secondary_y=True)

    fig.update_layout(
        title="<b>Evolución de Carga: Volumen Semanal vs ACWR</b>",
        height=320,
        margin=dict(l=10, r=10, t=35, b=20),
        legend=dict(orientation="h", y=-0.2),
        hovermode="x unified",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)"
    )

    st.plotly_chart(fig, use_container_width=True)

# --- FUNCIÓN PARA CALCULAR PREDISPOSICIÓN AL ENTRENAMIENTO (GARMIN STYLE) ---
def calculate_training_readiness(acwr, rpe_promedio, dias_descanso_recientes=1):
    """
    Calcula un score de 0 a 100% de Predisposición al Entrenamiento
    inspirado en Garmin Training Readiness.
    """
    # 1. Puntuación por ACWR (Zona dulce 0.8 - 1.3)
    if 0.8 <= acwr <= 1.3:
        score_acwr = 100
    elif 1.3 < acwr <= 1.5:
        score_acwr = 70
    elif acwr > 1.5:
        score_acwr = 30
    else:  # < 0.8 (Subentrenamiento)
        score_acwr = 85

    # 2. Puntuación por RPE / Fatiga percibida (Escala 1 - 10)
    if rpe_promedio <= 4:
        score_rpe = 100
    elif rpe_promedio <= 6:
        score_rpe = 80
    elif rpe_promedio <= 8:
        score_rpe = 50
    else:
        score_rpe = 20

    # 3. Puntuación por Días de Recuperación
    score_rest = min(100, 50 + (dias_descanso_recientes * 25))

    # Ponderación total
    readiness = (score_acwr * 0.40) + (score_rpe * 0.40) + (score_rest * 0.20)
    readiness_val = round(max(0, min(100, readiness)), 0)

    # Categorización visual estilo Garmin
    if readiness_val >= 80:
        estado = "Alto (¡Listo para entrenar fuerte!)"
        color_badge = "success"
    elif readiness_val >= 50:
        estado = "Moderado (Entrenamiento controlado)"
        color_badge = "warning"
    else:
        estado = "Bajo (Priorizar recuperación / Regenerativo)"
        color_badge = "error"

    return readiness_val, estado, color_badge

# --- FUNCIÓN PARA CARGAR DATOS DE ACTIVIDADES ---
def calculate_race_predictions(base_distance_km, base_time_min):
    """
    Calcula predicciones de tiempo para 5K, 10K, 15K y 21K usando la Fórmula de Riegel.
    """
    if base_distance_km <= 0 or base_time_min <= 0:
        return {}

    target_distances = {
        "5K": 5.0,
        "10K": 10.0,
        "15K": 15.0,
        "Media Maratón (21K)": 21.0975
    }

    predictions = {}
    for name, d2 in target_distances.items():
        # Formula Riegel: T2 = T1 * (D2 / D1)^1.06
        t2_min = base_time_min * ((d2 / base_distance_km) ** 1.06)
        
        # Calcular ritmo medio (min/km)
        pace_min_km = t2_min / d2
        pace_minutes = int(pace_min_km)
        pace_seconds = int((pace_min_km - pace_minutes) * 60)
        
        # Formatear tiempo total HH:MM:SS o MM:SS
        hours = int(t2_min // 60)
        mins = int(t2_min % 60)
        secs = int((t2_min - int(t2_min)) * 60)
        
        time_str = f"{hours:02d}:{mins:02d}:{secs:02d}" if hours > 0 else f"{mins:02d}:{secs:02d}"
        pace_str = f"{pace_minutes}:{pace_seconds:02d} min/km"
        
        predictions[name] = {
            "tiempo": time_str,
            "ritmo": pace_str
        }

    return predictions

# 1. Configuración de la página (Debe ser la primera instrucción)
st.set_page_config(
    page_title="Performance Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inicialización del Cerebro Central de Datos
if "df_actividades" not in st.session_state:
    st.session_state["df_actividades"] = None
if "km_agudos" not in st.session_state:
    st.session_state["km_agudos"] = 40.0
if "km_cronicos" not in st.session_state:
    st.session_state["km_cronicos"] = 35.0
if "prompt_sugerido_ia" not in st.session_state:
    st.session_state["prompt_sugerido_ia"] = ""

# --- INYECCIÓN CSS PARA DISEÑO RESPONSIVO Y TARJETAS PRO ---
st.markdown("""
    <style>
    /* Reducir espacio superior en dispositivos móviles y escritorio */
    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 2rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }
    
    /* Estilizar las tarjetas de métricas (st.metric) */
    [data-testid="stMetric"] {
        background-color: #1e222a;
        border: 1px solid #2d3139;
        border-radius: 10px;
        padding: 12px 16px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    
    /* Optimizar títulos en pantallas pequeñas */
    h1 { font-size: 1.8rem !important; }
    h2 { font-size: 1.4rem !important; }
    h3 { font-size: 1.1rem !important; }

    /* Ajuste para que las tablas no rompan el layout horizontal */
    [data-testid="stDataFrame"] {
        border-radius: 8px;
        overflow: hidden;
    }

    .stExpander {
        border: 1px solid #2d3139 !important;
        border-radius: 12px !important;
        background: rgba(30, 34, 42, 0.75) !important;
        margin-bottom: 0.8rem;
    }

    [data-testid="stExpanderToggle"] {
        padding: 0.7rem 0.8rem !important;
    }

    [data-testid="stExpanderDetails"] {
        padding: 0.3rem 0.8rem 0.8rem !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- INYECCIÓN DE CSS PARA DISEÑO MOBILE-FIRST Y TARJETAS PRO ---
st.markdown("""
    <style>
    /* 1. Reducir padding sobrante en bordes para móviles */
    .block-container {
        padding-top: 1.2rem !important;
        padding-bottom: 2rem !important;
        padding-left: 0.8rem !important;
        padding-right: 0.8rem !important;
    }

    /* 2. Tarjetas de métricas modernas con bordes y sombra */
    [data-testid="stMetric"] {
        background: #1e222a;
        border: 1px solid #2d3139;
        border-radius: 12px;
        padding: 12px 14px;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
    }
    
    [data-testid="stMetricLabel"] {
        font-size: 0.85rem !important;
        color: #a0aab8 !important;
    }

    [data-testid="stMetricValue"] {
        font-size: 1.4rem !important;
        font-weight: 700 !important;
    }

    /* 3. Ajuste de jerarquía tipográfica para pantallas pequeñas */
    h1 { font-size: 1.6rem !important; font-weight: 700 !important; }
    h2 { font-size: 1.25rem !important; font-weight: 600 !important; }
    h3 { font-size: 1.05rem !important; font-weight: 600 !important; }

    /* 4. Tablas con bordes redondeados y scroll horizontal limpio */
    [data-testid="stDataFrame"] {
        border-radius: 10px;
        overflow: hidden;
    }
    </style>
""", unsafe_allow_html=True)

# 2. Consolidación de importaciones
from src.metrics import calculate_vdot, calculate_pacing_splits, compute_acwr_ratio, calculate_acwr
from src.metrics import calculate_pacing_splits
from src.storage import save_new_plan, load_all_plans, update_full_plan
from src.data_loader import load_data
from src.config import DATA_PATH
from src.ai_coach import ask_ai_coach
from src.metrics import (
    add_pace,
    aerobic_efficiency_status,
    basic_stats,
    best_pace,
    clean_data,
    performance_status,
    weekly_distance_summary,
    weekly_pace,
    aerobic_efficiency_status,
    predict_race_times,
    calculate_tsb_metrics,
    get_vdot_from_df,   
    get_jack_daniels_zones,
)
from src.ui import (
    render_kpi_dashboard, 
    render_acwr_card, 
    render_polarization_card, 
    render_stress_alert, 
    render_daniels_chart, 
    render_ai_coach_section, 
    render_vdot_calculator_section,
    render_weekly_metrics,
    render_weekly_checkin,
)

# 3. Estilos CSS personalizados (Minimalista y profesional)
st.markdown(
    """
    <style>
    .metric-card {
        background-color: #1E1E1E;
        padding: 24px;
        border-radius: 8px;
        border: 1px solid #333;
        text-align: center;
        box-shadow: 0px 2px 4px rgba(0,0,0,0.2);
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: transparent;
        border-radius: 4px 4px 0px 0px;
        padding-top: 10px;
        padding-bottom: 10px;
        font-weight: 600;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# 4. Carga y procesamiento de datos
data = load_data(DATA_PATH)
cleaned_data = add_pace(clean_data(data))

# Asegurar formato datetime en la columna
from datetime import date

# 1. Asegurar formato datetime en la columna de fechas
cleaned_data["Activity Date"] = pd.to_datetime(cleaned_data["Activity Date"], errors="coerce")

# 2. Determinar límites reales de los datos
data_min = cleaned_data["Activity Date"].min().date() if not cleaned_data["Activity Date"].dropna().empty else date.today()
data_max = cleaned_data["Activity Date"].max().date() if not cleaned_data["Activity Date"].dropna().empty else date.today()

# 3. Permitir seleccionar desde el inicio de los datos HASTA el día de hoy (2026)
min_date = data_min
max_date = max(data_max, date.today())  # 👈 Esto desbloquea el año 2026

# 4. Configurar rango por defecto si no existe en la sesión
if "date_range" not in st.session_state:
    st.session_state["date_range"] = (min_date, max_date)

# 5. Barra lateral sin conflicto de 'key' en el widget
with st.sidebar:
    st.markdown("### Configuración de Análisis")
    
    selected_dates = st.date_input(
        "Rango de Fechas",
        value=st.session_state["date_range"],
        min_value=min_date,
        max_value=max_date
    )

# 6. Capturar la selección de forma fluida (sin bloquearse mientras haces clic)
if isinstance(selected_dates, (tuple, list)):
    if len(selected_dates) == 2:
        inicio, fin = selected_dates
        st.session_state["date_range"] = (inicio, fin)
    elif len(selected_dates) == 1:
        inicio = selected_dates[0]
        fin = max_date
    else:
        inicio, fin = min_date, max_date
else:
    inicio, fin = selected_dates, selected_dates

# --- BARRA LATERAL: CHECK-IN CUALITATIVO DEL ATLETA ---
with st.sidebar:
    st.header("📋 Check-in Semanal del Atleta")
    st.caption("Ajusta tu estado físico y mental para que la IA adapte el plan.")

    # 1. Nivel de fatiga percibida
    fatigue_rpe = st.slider(
        "⚡ Nivel de Fatiga Percibida (RPE)",
        min_value=1,
        max_value=10,
        value=3,
        help="1 = Fresco/Descansado, 10 = Exhausto/Sobrecargado"
    )

    # 2. Calidad del descanso
    sleep_quality = st.select_slider(
        "😴 Calidad del Sueño",
        options=["Mala", "Regular", "Buena", "Excelente"],
        value="Buena"
    )

    # 3. Estrés extradeportivo
    stress_level = st.selectbox(
        "🧠 Nivel de Estrés (Trabajo/Estudio)",
        options=["Bajo", "Moderado", "Alto"]
    )

    # 4. Selector de molestias físicas
    discomforts = st.multiselect(
        "🩹 Molestias Físicas o Molestias Musculares",
        options=[
            "Ninguna",
            "Gemelos / Sóleo",
            "Rodilla",
            "Isquiotibiales",
            "Planta del pie / Fascia",
            "Cadera / Glúteo",
            "Espalda baja"
        ],
        default=["Ninguna"]
    )

    # 5. Notas abiertas del atleta
    user_notes = st.text_area(
        "📝 Notas adicionales para el Coach",
        placeholder="Ej: El jueves tengo poco tiempo para entrenar...",
        height=80
    )

    # Guardar en la sesión de Streamlit
    st.session_state["feedback_data"] = {
        "fatigue_rpe": fatigue_rpe,
        "sleep_quality": sleep_quality,
        "stress_level": stress_level,
        "discomforts": discomforts,
        "notes": user_notes
    }

    st.divider()

    # 7. Filtrar comparando únicamente el DÍA (.dt.date) para no perder entrenamientos
    mask = (cleaned_data["Activity Date"].dt.date >= inicio) & (cleaned_data["Activity Date"].dt.date <= fin)
    filtered_data = cleaned_data[mask]
    st.markdown("---")
    st.markdown("### Visualización")
    mostrar_tabla = st.checkbox("Mostrar registro tabular", True)
    mostrar_grafica = st.checkbox("Mostrar gráficas de tendencia", True)
    st.markdown("---")
    
# Lógica de filtrado
if isinstance(inicio, tuple) or isinstance(inicio, list):
    inicio, fin = inicio

filtered = cleaned_data[
    (cleaned_data["Activity Date"] >= pd.to_datetime(inicio))
    & (cleaned_data["Activity Date"] <= pd.to_datetime(fin))
]

if filtered.empty:
    st.warning("No hay datos registrados en el rango de fechas seleccionado.")
    st.stop()

# Cálculos globales
total, runs, avg = basic_stats(cleaned_data)
best = best_pace(cleaned_data)
weekly_km = weekly_distance_summary(filtered)

metrics_summary = {
    "weekly_km": float(weekly_km["Distance"].iloc[-1]) if not weekly_km.empty else 0.0,
    "avg_pace": round(float(filtered["pace_min_km"].mean()), 2) if not filtered.empty else "N/A",
    "zone_distribution": {},
}

# 6. Cabecera Principal de la Aplicación
st.title("Panel de Rendimiento Atlético")
st.caption("Fase Específica | Objetivo Principal: Reto Rosa (15K)")
st.markdown("---")

# Alerta crítica siempre visible en la parte superior
render_stress_alert(data)

# 7. Arquitectura de Pestañas
tabs = st.tabs([
    "🏠 Tablero Hoy",
    "🎯 Ritmos & Marcas",
    "📊 Historial de Carga y Gestión de Archivos",
    "🤖 Coach IA",
    "📓 Seguimiento",
])
tab_hoy = tabs[0]
tab_ritmos = tabs[1]
tab_analitica = tabs[2]
tab_ai = tabs[3]
tab_seguimiento = tabs[4]
with tab_hoy:
    st.title("🏃 Running Coach — Performance Hub")
    st.caption("Resumen diario de predisposición, carga de entrenamiento y balance de rendimiento.")
    today_acwr = calculate_acwr(filtered)

    feedback_data = st.session_state.get("feedback_data", {})
    rpe_promedio = float(feedback_data.get("fatigue_rpe", 5))
    dias_descanso_recientes = max((date.today() - filtered["Activity Date"].max().date()).days, 0)
    readiness_score, readiness_state, readiness_badge = calculate_training_readiness(
        acwr=today_acwr.get("acwr", 0.0),
        rpe_promedio=rpe_promedio,
        dias_descanso_recientes=dias_descanso_recientes,
    )

    # 1. Tarjeta de Readiness
    readiness_col, readiness_note = st.columns([1.1, 1.4])
    with readiness_col:
        st.metric("Readiness de Hoy", f"{int(readiness_score)} / 100")
        st.progress(readiness_score / 100)
    with readiness_note:
        if readiness_badge == "success":
            st.success(f"🟢 {readiness_state}")
        elif readiness_badge == "warning":
            st.warning(f"🟡 {readiness_state}")
        else:
            st.error(f"🔴 {readiness_state}")
        st.caption(
            f"Calculado con ACWR {today_acwr.get('acwr', 0.0):.2f}, RPE {rpe_promedio:.0f} y {dias_descanso_recientes} día(s) de recuperación reciente."
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # 2. Métricas clave
    metric_cols = st.columns(3)
    metric_cols[0].metric("ACWR", f"{today_acwr.get('acwr', 0.0):.2f}")
    metric_cols[1].metric("Carga Aguda", f"{today_acwr.get('carga_aguda', 0.0):.1f} km")
    metric_cols[2].metric("Carga Crónica", f"{today_acwr.get('carga_cronica', 0.0):.1f} km")

    # 3. Gráfico Interactivo Combinado
    st.markdown("### 📈 Volumen vs ACWR")
    render_interactive_ecosystem_chart(filtered)

    # 4. Alerta inteligente con CTA al Coach IA
    if today_acwr.get("status") in {"caution", "danger"}:
        if today_acwr["status"] == "danger":
            st.error(today_acwr["message"])
        else:
            st.warning(today_acwr["message"])

        prompt_auto = (
            f"Hola Coach, hoy tengo un ACWR de {today_acwr.get('acwr', 0.0):.2f}, "
            f"con carga aguda de {today_acwr.get('carga_aguda', 0.0):.1f} km y carga crónica de {today_acwr.get('carga_cronica', 0.0):.1f} km. "
            f"Mi readiness actual es {int(readiness_score)} / 100. ¿Qué ajuste me recomiendas para esta semana?"
        )

        if st.button("🤖 Enviar alerta al Coach IA", type="primary", use_container_width=True):
            st.session_state["prompt_sugerido_ia"] = prompt_auto
            st.info("La consulta quedó lista en la pestaña Coach IA.")
    else:
        st.success(today_acwr["message"])

# --- PESTAÑA 2: RITMOS Y MARCAS ---
with tab_ritmos:
    st.subheader("🎯 Control de Ritmos y Predictor de Competencia")
    st.caption("Ajusta tu marca de referencia para proyectar tiempos objetivo y zonas fisiológicas.")

    col_ref_1, col_ref_2 = st.columns(2)
    with col_ref_1:
        dist_base = st.selectbox(
            "Distancia de referencia (km)",
            [3.0, 5.0, 10.0, 15.0, 21.1],
            index=1,
        )
    with col_ref_2:
        tiempo_base = st.number_input(
            "Tiempo de referencia (minutos)",
            min_value=5.0,
            max_value=300.0,
            value=25.0,
            step=0.5,
        )

    # 2. Tarjetas de Race Predictor (5K, 10K, 15K, 21K)
    predictions = calculate_race_predictions(dist_base, tiempo_base)
    if not predictions:
        st.info("Ingresa una marca de referencia válida para activar el predictor de competencia.")
    else:
        st.markdown("### 🏁 Race Predictor")
        pred_cols = st.columns(4)
        for idx, (label, info) in enumerate(predictions.items()):
            with pred_cols[idx]:
                st.metric(
                    label=label,
                    value=info["tiempo"],
                    delta=f"Ritmo: {info['ritmo']}",
                    delta_color="normal",
                )

    st.markdown("---")

    # 3. Acordeones con zonas fisiológicas Z2 a Z5
    st.subheader("🧬 Zonas Fisiológicas de Entrenamiento")
    vdot_calc, vdot_ref = get_vdot_from_df(filtered)

    if not vdot_calc:
        st.info("No fue posible calcular un VDOT de referencia con los datos filtrados.")
    else:
        if vdot_ref:
            st.caption(
                f"Base usada: {vdot_ref.get('name')} ({vdot_ref.get('distance')} km a {vdot_ref.get('pace'):.2f} min/km el {vdot_ref.get('date')})."
            )

        df_zones = get_jack_daniels_zones(vdot_calc)
        zone_map = {
            "Z2": "Easy / Rodaje Suave (E)",
            "Z3": "Marathon Pace (M)",
            "Z4": "Threshold / Umbral (T)",
            "Z5": "Interval / VO2Max (I)",
        }

        for zone_code, zone_name in zone_map.items():
            zone_row = df_zones[df_zones["Código"].str.contains(zone_code, na=False)]
            if zone_row.empty:
                zone_row = df_zones[df_zones["Zona de Entrenamiento"].str.contains(zone_name.split(" /")[0], case=False, na=False)]

            with st.expander(f"{zone_code} - {zone_name}", expanded=False):
                if zone_row.empty:
                    st.info("No se encontró información para esta zona.")
                else:
                    row = zone_row.iloc[0]
                    st.metric("Rango de Ritmo", row["Rango de Ritmo (min/km)"])
                    st.markdown(f"**Propósito fisiológico:** {row['Propósito Fisiológico']}")

# FUNCIÓN AUXILIAR DE PROCESAMIENTO DE ARCHIVOS CSV / EXCEL
    # ------------------------------------------------------------------
    def process_uploaded_activities(file):
        try:
            if file.name.endswith('.csv'):
                df = pd.read_csv(file)
            else:
                df = pd.read_excel(file, sheet_name=0)
                
            df.columns = [str(col).strip().lower() for col in df.columns]
            col_fecha = next((col for col in df.columns if 'fecha' in col or 'date' in col), None)
            col_dist = next((col for col in df.columns if 'distancia' in col or 'km' in col or 'distance' in col), None)
            
            if not col_fecha or not col_dist:
                return None, "El archivo debe contener al menos una columna de 'Fecha' y una de 'Distancia_Km'."

            df[col_fecha] = pd.to_datetime(df[col_fecha], errors='coerce')
            df[col_dist] = pd.to_numeric(df[col_dist], errors='coerce').fillna(0)
            df = df.dropna(subset=[col_fecha]).sort_values(by=col_fecha, ascending=False)

            if df.empty:
                return None, "No se encontraron fechas válidas en el archivo."

            fecha_max = df[col_fecha].max()
            fecha_7d = fecha_max - pd.Timedelta(days=7)
            fecha_28d = fecha_max - pd.Timedelta(days=28)

            km_agudos = float(df[df[col_fecha] > fecha_7d][col_dist].sum())
            km_totales_28d = float(df[df[col_fecha] > fecha_28d][col_dist].sum())
            km_cronicos = km_totales_28d / 4.0 if km_totales_28d > 0 else 1.0

            return {
                "total_sesiones": len(df),
                "fecha_reciente": fecha_max.strftime("%Y-%m-%d"),
                "km_agudos": round(km_agudos, 1),
                "km_cronicos": round(km_cronicos, 1),
                "df": df 
            }, None
        except Exception as e:
            return None, f"Error al procesar archivo: {str(e)}"

    # ------------------------------------------------------------------
    # MÓDULO DE PREVENCIÓN DE LESIONES: RATIO ACWR + FILE UPLOADER
    # ------------------------------------------------------------------
    st.markdown("---")
    st.subheader("🛡️ Prevención de Lesiones: Ratio ACWR")
    st.caption("Sincroniza tu historial de entrenamiento desde un archivo o ajusta los valores manualmente.")

    # Valores por defecto para fallback manual
    km_agudos_val = 40.0
    km_cronicos_val = 35.0

    # Expander 1: Carga de Archivos Automática
    with st.expander("📁 Cargar Historial desde Archivo (CSV / Excel)", expanded=False):
        uploaded_file = st.file_uploader(
            "Selecciona tu archivo de entrenamiento (.csv o .xlsx)", 
            type=["csv", "xlsx"],
            help="El archivo debe tener columnas de Fecha y Distancia (Km)."
        )

        if uploaded_file is not None:
            resumen_file, err_file = process_uploaded_activities(uploaded_file)
            if err_file:
                st.error(f"❌ {err_file}")
            else:
                st.success(f"✅ Historial cargado. Última actividad: **{resumen_file['fecha_reciente']}** ({resumen_file['total_sesiones']} registros).")
                km_agudos_val = resumen_file["km_agudos"]
                km_cronicos_val = resumen_file["km_cronicos"]
                
                # 👈 GUARDAMOS LA TABLA EN EL ESTADO GLOBAL
                st.session_state["df_actividades"] = resumen_file["df"]

                col_c1, col_c2 = st.columns(2)
                col_c1.metric("Carga Aguda Detectada (7 días)", f"{km_agudos_val} km")
                col_c2.metric("Carga Crónica Detectada (28d prom.)", f"{km_cronicos_val} km/sem")

    # 👈 MOSTRAR EL GRÁFICO COMBINADO SI HAY DATOS CARGADOS
    if st.session_state.get("df_actividades") is not None:
        with st.expander("📊 Ver gráfico histórico de Carga vs ACWR", expanded=True):
            render_interactive_ecosystem_chart(st.session_state["df_actividades"])


    # Expander 2: Entradas / Ajuste Manual
    with st.expander("⚙️ Ingreso o Ajuste Manual de Carga", expanded=True):
        col_a1, col_a2 = st.columns(2)
        with col_a1:
            km_agudos = float(st.number_input("Carga Aguda (Km última semana):", min_value=0.0, max_value=200.0, value=km_agudos_val, step=1.0))
        with col_a2:
            km_cronicos = float(st.number_input("Carga Crónica (Promedio semanal 28 días):", min_value=1.0, max_value=200.0, value=km_cronicos_val, step=1.0))

    # Cálculo y Visualización del ACWR
    val_acwr, estado_acwr, tipo_alerta, desc_acwr = compute_acwr_ratio(km_agudos, km_cronicos)

    col_m1, col_m2 = st.columns([1, 2])
    with col_m1:
        st.metric("Ratio ACWR Actual", f"{val_acwr:.2f}")
    with col_m2:
        if tipo_alerta == "success":
            st.success(f"**{estado_acwr}**\n\n{desc_acwr}")
        elif tipo_alerta == "warning":
            st.warning(f"**{estado_acwr}**\n\n{desc_acwr}")
        elif tipo_alerta == "error":
            st.error(f"**{estado_acwr}**\n\n{desc_acwr}")
        else:
            st.info(f"**{estado_acwr}**\n\n{desc_acwr}")
# ------------------------------------------------------------------
    # TARJETA TIPO GARMIN: PREDISPOSICIÓN AL ENTRENAMIENTO (READINESS)
    # ------------------------------------------------------------------
    st.markdown("---")
    st.subheader("⌚ Nivel de Predisposición al Entrenamiento (Training Readiness)")
    st.caption("Indicador holístico de preparación diaria basado en tu balance de carga y fatiga.")

    # Calcular score con los valores actuales del estado
    readiness_score, estado_readiness, tipo_badge = calculate_training_readiness(
        acwr=val_acwr, 
        rpe_promedio=6.0,  # O el promedio extraído del archivo
        dias_descanso_recientes=1
    )

    col_r1, col_r2 = st.columns([1, 2])
    with col_r1:
        st.metric("Predisposición Hoy", f"{int(readiness_score)} / 100")
    with col_r2:
        if tipo_badge == "success":
            st.success(f"🟢 **{estado_readiness}**")
        elif tipo_badge == "warning":
            st.warning(f"🟡 **{estado_readiness}**")
        else:
            st.error(f"🔴 **{estado_readiness}**")

    # Progreso visual
    st.progress(readiness_score / 100.0)

# ------------------------------------------------------------------
    # PREDICTOR DE MARCAS DE COMPETENCIA (GARMIN RACE PREDICTOR)
    # ------------------------------------------------------------------
    st.markdown("---")
    st.subheader("🏁 Predictor de Tiempos de Competencia")
    st.caption("Proyección de marcas potenciales según tu rendimiento reciente (Fórmula de Riegel).")

    # Tomar de base una marca de referencia (ej. un 10K reciente o un test de 5K)
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        dist_base = st.number_input("Distancia de referencia reciente (km):", min_value=1.0, max_value=50.0, value=10.0, step=0.5)
    with col_p2:
        tiempo_base = st.number_input("Tiempo registrado (minutos):", min_value=5.0, max_value=300.0, value=48.0, step=0.5)

    predicciones = calculate_race_predictions(dist_base, tiempo_base)

    if predicciones:
        cols = st.columns(4)
        for idx, (dist_name, info) in enumerate(predicciones.items()):
            with cols[idx]:
                st.metric(
                    label=f"🎯 {dist_name}",
                    value=info["tiempo"],
                    delta=f"Ritmo: {info['ritmo']}",
                    delta_color="off"
                )

# 2. Si el ACWR está fuera de la zona dulce, sugerir consulta automática a la IA
    if val_acwr > 1.3 or val_acwr < 0.8:
        prompt_auto = (
            f"Hola Coach, mi ratio ACWR actual es de {val_acwr:.2f} con una carga aguda de {km_agudos} km "
            f"y crónica de {km_cronicos} km/sem. Mi estado actual es: {estado_acwr}. "
            f"¿Qué ajustes específicos de descarga o intensidades me recomiendas para esta semana?"
        )
        if st.button("🤖 Generar consulta automática para el Coach IA sobre esta alerta", type="secondary"):
            st.session_state["prompt_sugerido_ia"] = prompt_auto
            st.info("👉 Se ha guardado la consulta. Ve a la pestaña **'Coach IA'** para enviarla.")
            
with tab_ai:
    st.subheader("🤖 Planificación Semanal con Inteligencia Artificial")
    st.caption("Generación de un plan adaptado a tu VDOT real, TSB, frescura y sensaciones de la semana.")

#  MOSTRAR CONSULTA SUGERIDA DESDE ACWR SI EXISTE
    if st.session_state.get("prompt_sugerido_ia"):
        st.info(f"💡 **Consulta pendiente desde el módulo de ACWR:**\n\n_{st.session_state['prompt_sugerido_ia']}_")
        if st.button("🧹 Limpiar sugerencia"):
            st.session_state["prompt_sugerido_ia"] = ""
            st.rerun()

    # 1. Botón para desencadenar la generación
    if st.button("⚡ Generar Plan Semanal con IA", type="primary"):
        with st.spinner("Sintetizando balance TSB, VDOT real y generando plan personalizado..."):
            # Extraer estadísticas base
            stats = basic_stats(filtered_data)
            
            if isinstance(stats, tuple):
                weekly_km_val = stats[0] if len(stats) > 0 else 0
                avg_pace_val = stats[1] if len(stats) > 1 else "N/A"
            elif isinstance(stats, dict):
                weekly_km_val = stats.get("total_distance", 0)
                avg_pace_val = stats.get("avg_pace", "N/A")
            else:
                weekly_km_val, avg_pace_val = 0, "N/A"

            metrics_summary = {
                "weekly_km": weekly_km_val,
                "avg_pace": avg_pace_val,
                "zone_distribution": {}
            }
            
            # Obtener VDOT actual
            vdot_real, _ = get_vdot_from_df(filtered_data)
            
            # Consultar al módulo de IA
            generated_text = ask_ai_coach(
                metrics_summary=metrics_summary,
                df=filtered_data,
                feedback_data=st.session_state.get("feedback_data", None),
                vdot_actual=vdot_real
            )
            
            # GUARDAR EN SESSION STATE PARA EVITAR QUE SE BORRE
            st.session_state["current_ai_plan"] = generated_text

    # 2. Renderizar el plan si ya existe en la memoria de la sesión
    if "current_ai_plan" in st.session_state and st.session_state["current_ai_plan"]:
        st.markdown("---")
        
        col_actions1, col_actions2 = st.columns([1, 1])
        
        with col_actions1:
            # Botón de descarga
            st.download_button(
                label="📥 Descargar Plan (.md)",
                data=st.session_state["current_ai_plan"],
                file_name="Plan_Semanal_Running_Coach.md",
                mime="text/markdown",
                use_container_width=True
            )
            
        with col_actions2:
            # Botón para persistir en la Base de Datos Local
            if st.button("💾 Guardar Plan en Base de Datos", use_container_width=True, type="secondary"):
                vdot_real, _ = get_vdot_from_df(filtered_data)
                
                saved_record = save_new_plan(
                    vdot=vdot_real,
                    km_objetivo=40.0, # O la meta semanal configurada
                    plan_markdown=st.session_state["current_ai_plan"],
                    feedback_atleta=st.session_state.get("feedback_data", {})
                )
                
                st.success(f"✅ Plan guardado exitosamente (ID: `{saved_record['id']}`). ¡Ya puedes darle seguimiento!")

        # Mostrar el plan generado en pantalla
        st.markdown(st.session_state["current_ai_plan"])

# --- PESTAÑA 3: HISTORIAL DE CARGA Y GESTIÓN DE ARCHIVOS ---
with tab_analitica:
    st.subheader("📊 Historial de Carga y Gestión de Archivos")
    st.caption("Sincroniza tus registros (.csv / .xlsx) y examina el desglose detallado de actividades.")

    def process_uploaded_activities(file):
        try:
            if file.name.lower().endswith(".csv"):
                df = pd.read_csv(file)
            else:
                df = pd.read_excel(file, sheet_name=0)

            df.columns = [str(col).strip() for col in df.columns]
            lower_map = {col.lower(): col for col in df.columns}

            fecha_col = next((lower_map[key] for key in lower_map if "fecha" in key or "date" in key), None)
            dist_col = next((lower_map[key] for key in lower_map if "distancia" in key or "distance" in key or "km" == key), None)

            if not fecha_col or not dist_col:
                return None, "El archivo debe incluir al menos una columna de fecha y una de distancia."

            df[fecha_col] = pd.to_datetime(df[fecha_col], errors="coerce")
            df[dist_col] = pd.to_numeric(df[dist_col], errors="coerce")
            df = df.dropna(subset=[fecha_col]).copy()
            df = df.sort_values(by=fecha_col, ascending=False)

            display_df = df[[fecha_col, dist_col]].copy()
            display_df.columns = ["Fecha", "Distancia"]
            if "Activity Name" in df.columns:
                display_df.insert(1, "Actividad", df["Activity Name"].astype(str).values)

            return display_df, None
        except Exception as exc:
            return None, f"Error al procesar archivo: {exc}"

    uploaded_file = st.file_uploader(
        "Cargar historial de entrenamiento",
        type=["csv", "xlsx"],
        help="Sube un archivo con tus actividades para revisar el historial de carga.",
    )

    if uploaded_file is not None:
        uploaded_df, upload_error = process_uploaded_activities(uploaded_file)
        if upload_error:
            st.error(upload_error)
        else:
            st.session_state["df_actividades"] = uploaded_df
            st.success(f"Historial cargado: {len(uploaded_df)} registros procesados.")

    df_actividades = st.session_state.get("df_actividades")
    if df_actividades is not None and not df_actividades.empty:
        st.markdown("### Actividades procesadas")
        st.dataframe(df_actividades, use_container_width=True, hide_index=True)
    else:
        st.info("Carga un archivo para ver aquí tu historial procesado.")

    st.markdown("---")
    st.subheader("⚙️ Ajuste manual de kilometraje")
    st.caption("Ajusta la carga aguda y crónica para recalcular tu ACWR de forma rápida.")

    km_agudos_manual = st.number_input(
        "Carga aguda (km última semana)",
        min_value=0.0,
        max_value=250.0,
        value=float(st.session_state.get("km_agudos", 40.0)),
        step=1.0,
    )
    km_cronicos_manual = st.number_input(
        "Carga crónica (km promedio semanal)",
        min_value=1.0,
        max_value=250.0,
        value=float(st.session_state.get("km_cronicos", 35.0)),
        step=1.0,
    )

    st.session_state["km_agudos"] = float(km_agudos_manual)
    st.session_state["km_cronicos"] = float(km_cronicos_manual)

    acwr_manual, estado_acwr_manual, tipo_alerta_manual, desc_acwr_manual = compute_acwr_ratio(
        km_agudos_manual,
        km_cronicos_manual,
    )

    metric_manual_1, metric_manual_2 = st.columns(2)
    with metric_manual_1:
        st.metric("ACWR Manual", f"{acwr_manual:.2f}")
    with metric_manual_2:
        if tipo_alerta_manual == "success":
            st.success(f"**{estado_acwr_manual}**\n\n{desc_acwr_manual}")
        elif tipo_alerta_manual == "warning":
            st.warning(f"**{estado_acwr_manual}**\n\n{desc_acwr_manual}")
        elif tipo_alerta_manual == "error":
            st.error(f"**{estado_acwr_manual}**\n\n{desc_acwr_manual}")
        else:
            st.info(f"**{estado_acwr_manual}**\n\n{desc_acwr_manual}")

with tab_ai:
    st.subheader("🤖 Coach IA — Planificación Personalizada")
    st.caption("Ajusta tu microciclo semanal considerando tus sensaciones, VDOT y nivel de fatiga.")

    # 1. Lectura del prompt_sugerido_ia (Si proviene de una alerta de ACWR/Readiness)
    if st.session_state.get("prompt_sugerido_ia"):
        st.info(
            f"💡 **Consulta pendiente desde otro módulo:**\n\n_{st.session_state['prompt_sugerido_ia']}_"
        )
        if st.button("🧹 Limpiar sugerencia", key="btn_limpiar_sugerencia_ia"):
            st.session_state["prompt_sugerido_ia"] = ""
            st.rerun()

    # 2. Formulario de sensaciones del usuario
    st.markdown("### 📝 Formulario de sensaciones")
    with st.form("form_coach_ia"):
        col_form_1, col_form_2 = st.columns(2)

        with col_form_1:
            fatigue_rpe = st.slider(
                "Fatiga percibida (1-10)",
                min_value=1,
                max_value=10,
                value=int(st.session_state.get("feedback_data", {}).get("fatigue_rpe", 3)),
            )
            sleep_quality = st.select_slider(
                "Calidad del sueño",
                options=["Mala", "Regular", "Buena", "Excelente"],
                value=st.session_state.get("feedback_data", {}).get("sleep_quality", "Buena"),
            )

        with col_form_2:
            stress_level = st.selectbox(
                "Estrés externo",
                options=["Bajo", "Moderado", "Alto"],
                index=["Bajo", "Moderado", "Alto"].index(st.session_state.get("feedback_data", {}).get("stress_level", "Moderado")),
            )
            discomforts = st.multiselect(
                "Molestias físicas",
                options=[
                    "Ninguna",
                    "Gemelos / Sóleo",
                    "Rodilla",
                    "Isquiotibiales",
                    "Planta del pie / Fascia",
                    "Cadera / Glúteo",
                    "Espalda baja",
                ],
                default=st.session_state.get("feedback_data", {}).get("discomforts", ["Ninguna"]),
            )

        user_notes = st.text_area(
            "Notas adicionales",
            value=st.session_state.get("feedback_data", {}).get("notes", ""),
            placeholder="Ej: El rodaje del martes se sintió pesado o tengo poco tiempo para entrenar...",
            height=100,
        )

        generate_plan = st.form_submit_button("⚡ Generar Plan Semanal con IA", type="primary")

    # 3. Botón de generación del plan semanal
    if generate_plan:
        st.session_state["feedback_data"] = {
            "fatigue_rpe": fatigue_rpe,
            "sleep_quality": sleep_quality,
            "stress_level": stress_level,
            "discomforts": discomforts,
            "notes": user_notes,
        }

        with st.spinner("Sintetizando sensaciones, VDOT y cargas para crear el plan..."):
            stats = basic_stats(filtered_data)

            if isinstance(stats, tuple):
                weekly_km_val = stats[0] if len(stats) > 0 else 0
                avg_pace_val = stats[1] if len(stats) > 1 else "N/A"
            elif isinstance(stats, dict):
                weekly_km_val = stats.get("total_distance", 0)
                avg_pace_val = stats.get("avg_pace", "N/A")
            else:
                weekly_km_val, avg_pace_val = 0, "N/A"

            metrics_summary = {
                "weekly_km": weekly_km_val,
                "avg_pace": avg_pace_val,
                "zone_distribution": {},
            }

            vdot_real, _ = get_vdot_from_df(filtered_data)
            generated_text = ask_ai_coach(
                metrics_summary=metrics_summary,
                df=filtered_data,
                feedback_data=st.session_state.get("feedback_data", None),
                vdot_actual=vdot_real,
            )

            st.session_state["current_ai_plan"] = generated_text

    if st.session_state.get("current_ai_plan"):
        st.markdown("---")
        st.markdown("### 📄 Plan Semanal Generado")

        col_actions1, col_actions2 = st.columns(2)

        with col_actions1:
            st.download_button(
                label="📥 Descargar Plan (.md)",
                data=st.session_state["current_ai_plan"],
                file_name="Plan_Semanal_Running_Coach.md",
                mime="text/markdown",
                use_container_width=True,
            )

        with col_actions2:
            if st.button("💾 Guardar Plan en Base de Datos", use_container_width=True, type="secondary"):
                vdot_real, _ = get_vdot_from_df(filtered_data)
                saved_record = save_new_plan(
                    vdot=vdot_real,
                    km_objetivo=40.0,
                    plan_markdown=st.session_state["current_ai_plan"],
                    feedback_atleta=st.session_state.get("feedback_data", {}),
                )
                st.success(f"✅ Plan guardado exitosamente (ID: `{saved_record['id']}`).")

        st.markdown(st.session_state["current_ai_plan"])

# --- PESTAÑA 4: SEGUIMIENTO Y ADHERENCIA ---
with tab_seguimiento:
    st.subheader("📍 Diario del Atleta y Registro de Adherencia")
    st.caption("Evalúa cada sesión de la semana, registra tus sensaciones y calcula automáticamente tu adherencia real.")

    saved_plans = load_all_plans()

    if not saved_plans:
        st.info("ℹ️ Aún no has guardado ningún plan. Genera uno en la pestaña 'Coach Virtual IA' y presiona '💾 Guardar Plan'.")
    else:
        # 📊 1. GRÁFICA DE HISTORIAL DE ADHERENCIA
        hist_data = []
        for p in reversed(saved_plans):  # Orden cronológico (antiguo a reciente)
            fecha_corta = p.get("fecha_creacion", "").split(" ")[0]
            hist_data.append({
                "Fecha": fecha_corta,
                "Adherencia (%)": p.get("adherencia_pct", 0),
                "VDOT": p.get("vdot_base", 0)
            })
            
        df_hist = pd.DataFrame(hist_data)

        if not df_hist.empty:
            fig_adh = px.bar(
                df_hist,
                x="Fecha",
                y="Adherencia (%)",
                text="Adherencia (%)",
                title="📈 Evolución Histórica de Adherencia Semanal",
                color="Adherencia (%)",
                color_continuous_scale="RdYlGn",
                range_y=[0, 105]
            )
            fig_adh.update_traces(texttemplate='%{text}%', textposition='outside')
            fig_adh.update_layout(height=280, margin=dict(l=20, r=20, t=40, b=20))
            st.markdown("---")

        with st.expander("📊 Ver historial de adherencia", expanded=False):
            fig_adh.update_xaxes(type='category')
            fig_adh.update_traces(texttemplate='%{text}%', textposition='outside')
            fig_adh.update_layout(height=280, margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig_adh, use_container_width=True)

        # 📋 2. SELECTOR DE PLAN GUARDADO
        plan_options = {f"{p['fecha_creacion']} | VDOT: {p['vdot_base']} | Estado: {p['estado']}": p['id'] for p in saved_plans}
        selected_label = st.selectbox("📋 Seleccionar Plan Guardado:", options=list(plan_options.keys()))
        selected_id = plan_options[selected_label]

        # Obtener el plan actual
        selected_plan = next(p for p in saved_plans if p["id"] == selected_id)

        # 📓 3. CARGAR DIARIO DE SESIONES EN UN DATAFRAME EDITABLE
        df_diario = pd.DataFrame(selected_plan.get("diario_sesiones", []))

        st.markdown("### 📓 Registro Sesión por Sesión (Lunes a Domingo)")
        st.caption("Edita directamente en las celdas: marca qué días cumpliste, tus kilómetros reales y tu RPE.")

        # Editor de datos interactivo
        edited_df = st.data_editor(
            df_diario,
            column_config={
                "Día": st.column_config.TextColumn("Día", disabled=True),
                "Tipo / Prescripción": st.column_config.TextColumn("Prescripción / Foco", width="medium"),
                "Completado": st.column_config.CheckboxColumn("¿Completado?", default=False),
                "Km Real": st.column_config.NumberColumn("Km Reales", min_value=0.0, max_value=50.0, step=0.5, format="%.1f km"),
                "RPE (1-10)": st.column_config.NumberColumn("RPE (1-10)", min_value=1, max_value=10, step=1),
                "Sensaciones / Notas": st.column_config.TextColumn("Notas de la Sesión", width="large"),
            },
            hide_index=True,
            use_container_width=True,
            num_rows="fixed"
        )

        # 🎯 4. CÁLCULO AUTOMÁTICO DE MÉTRICAS
        dias_completados = edited_df["Completado"].sum() if "Completado" in edited_df.columns else 0
        km_totales_reales = edited_df["Km Real"].sum() if "Km Real" in edited_df.columns else 0.0
        adherencia_calculada = int((dias_completados / 7) * 100)

        st.markdown("---")
        st.markdown("### 🎯 Métricas Semanales de Cumplimiento")

        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        col_m1.metric("Sesiones Cumplidas", f"{dias_completados} / 7 días")
        col_m2.metric("Volumen Real Acumulado", f"{km_totales_reales:.1f} km")
        col_m3.metric("Adherencia Automática", f"{adherencia_calculada}%")
        
        # Estado manual y notas globales
        with col_m4:
            nuevo_estado = st.selectbox(
                "Estado General",
                options=["En Curso", "Completado", "Archivado"],
                index=["En Curso", "Completado", "Archivado"].index(selected_plan.get("estado", "En Curso"))
            )

        notas_globales = st.text_input(
            "📝 Resumen/Conclusión general de la semana:",
            value=selected_plan.get("notas_seguimiento", ""),
            placeholder="Ej: Buena semana de carga, el domingo completé la tirada sin molestias."
        )

        # 💾 5. GUARDAR CAMBIOS EN LA BASE DE DATOS
        if st.button("💾 Guardar Cambios en el Diario", type="primary", use_container_width=True):
            diario_actualizado = edited_df.to_dict(orient="records")
            
            if update_full_plan(selected_id, nuevo_estado, adherencia_calculada, notas_globales, diario_actualizado):
                st.success("✅ Diario y métricas de adherencia guardados con éxito en la base de datos local.")
                st.rerun()

        st.markdown("---")
        st.markdown("### 📄 Plan Semanal Original Generado por IA")
        st.markdown(selected_plan["plan_markdown"])
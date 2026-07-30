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
from src.metrics import calculate_vdot, calculate_pacing_splits, compute_acwr_ratio
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
tab_dashboard, tab_planning, tab_ai, tab_history, tab_seguimiento = st.tabs([
    "Resumen Semanal", 
    "Planificación Fisiológica", 
    "Análisis de Inteligencia Artificial", 
    "Historial y Tendencias",
    "Seguimiento & Adherencia"
])

# --- PESTAÑA 1: DASHBOARD SEMANAL ---
with tab_dashboard:
    # Métricas de alto nivel
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Sesiones", runs)
    col2.metric("Volumen (Km)", round(total, 1))
    col3.metric("Ritmo Promedio", f"{round(avg, 2)} /km")
    col4.metric("Mejor Ritmo", f"{round(best, 2)} /km")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    with st.expander("📊 Ver gráficos y tendencias", expanded=False):
        render_kpi_dashboard(data)
        
        col_a, col_b = st.columns(2)
        with col_a:
            render_acwr_card(data)
        with col_b:
            render_polarization_card(data)
            
        render_weekly_metrics({"weekly_km": weekly_km})

# --- PESTAÑA 2: PLANIFICACIÓN Y ZONAS ---
with tab_planning:
    st.subheader("Modelo de Jack Daniels")
    render_vdot_calculator_section(data)
    
    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader("Distribución de Carga")
    render_daniels_chart(data)

# --- PREDICCIÓN DE TIEMPOS DE CARRERA ---
    st.subheader("⏱️ Predicción de Tiempos de Carrera (Modelo Riegel)")
    st.caption("Proyección de ritmos y tiempos objetivo calculados a partir de tu mejor sesión reciente.")
    
    race_data = predict_race_times(filtered)
    
    if race_data is None:
        st.info("Registra al menos un entrenamiento mayor a 3 km para activar el calculador de tiempos.")
    else:
        ref = race_data["ref_run"]
        predictions_df = race_data["predictions"]
        
        # Tarjeta informativa sobre la sesión tomada como referencia
        ref_date = str(ref.get('Activity Date', 'Reciente'))[:10]
        st.markdown(
            f"> 💡 **Sesión de Referencia Detectada:** {ref.get('Activity Name', 'Entrenamiento')} "
            f"({ref['Distance']:.2f} km a {ref['pace_min_km']:.2f} min/km el {ref_date})"
        )
        
        # Renderizamos los resultados en 4 tarjetas métricas interactivas
        cols = st.columns(4)
        for idx, row in predictions_df.iterrows():
            with cols[idx]:
                st.metric(
                    label=row["Distancia"],
                    value=row["Tiempo Estimado"],
                    delta=f"Ritmo: {row['Ritmo Objetivo']}",
                    delta_color="normal"
                )
                
        st.markdown("---")

# --- MONITOR DE FRESCURA Y FATIGA (TSB) ---
    st.subheader("🛡️ Monitor de Frescura y Fatiga (Modelo TSB)")
    st.caption("Control de Carga Crónica (Forma) vs. Carga Aguda (Fatiga) en los últimos 30 días.")
    
    tsb_data = calculate_tsb_metrics(filtered)
    
    if tsb_data is None:
        st.info("No hay suficientes datos de fechas para calcular las métricas TSB.")
    else:
        # 1. Indicadores Métricos
        c1, c2, c3 = st.columns(3)
        c1.metric("Forma Física (CTL)", f"{tsb_data['current_ctl']} km/día", help="Base acumulada a 42 días")
        c2.metric("Fatiga Reciente (ATL)", f"{tsb_data['current_atl']} km/día", help="Estrés de los últimos 7 días")
        c3.metric("Frescura (TSB)", f"{tsb_data['current_tsb']}", help="Diferencia: CTL - ATL")
        
        # 2. Mensaje de Estado
        if tsb_data['state'] == "success":
            st.success(f"🟢 **{tsb_data['verdict']}**")
        elif tsb_data['state'] == "warning":
            st.warning(f"🟡 **{tsb_data['verdict']}**")
        elif tsb_data['state'] == "error":
            st.error(f"🔴 **{tsb_data['verdict']}**")
        else:
            st.info(f"🔵 **{tsb_data['verdict']}**")
            
        # 3. Gráfico Interactivo de Tendencia
        st.markdown("**Evolución de Forma, Fatiga y Frescura (Últimos 30 días)**")
        st.line_chart(tsb_data["daily_df"])
        
    st.markdown("---")

# --- CALCULADORA DINÁMICA DE VDOT Y ZONAS DE JACK DANIELS ---
    st.subheader("🎯 Zonas Personalizadas de Entrenamiento (Metodología Jack Daniels)")
    
    # 1. Calculamos el VDOT dinámico
    vdot_calc, vdot_ref = get_vdot_from_df(filtered)
    
    if vdot_calc:
        c_vdot1, c_vdot2 = st.columns([1, 2])
        with c_vdot1:
            st.metric(
                label="Índice VDOT Calculado",
                value=f"{vdot_calc}",
                help="Índice de capacidad aeróbica equivalente calculado a partir de tu mejor sesión reciente."
            )
        with c_vdot2:
            if vdot_ref:
                st.info(
                    f"💡 **Base de Cálculo:** Basado en tu sesión *'{vdot_ref.get('name')}'* "
                    f"({vdot_ref.get('distance')} km a {vdot_ref.get('pace'):.2f} min/km el {vdot_ref.get('date')})."
                )
        
        # 2. Obtenemos y mostramos la tabla de zonas
        df_zones = get_jack_daniels_zones(vdot_calc)
        st.dataframe(
            df_zones,
            column_config={
                "Zona de Entrenamiento": st.column_config.TextColumn("Zona", width="medium"),
                "Código": st.column_config.TextColumn("Código", width="small"),
                "Rango de Ritmo (min/km)": st.column_config.TextColumn("Ritmo Objetivo", width="medium"),
                "Propósito Fisiológico": st.column_config.TextColumn("Propósito Fisiológico", width="large"),
            },
            hide_index=True,
            use_container_width=True
        )
    st.markdown("---")

    st.markdown("---")
    st.subheader("🏁 Estrategia de Carrera & Calculadora de Parciales (Pace Band)")
    st.caption("Estructura la táctica de ritmo kilómetro a kilómetro para tu próxima competencia objetivo.")

    col_p1, col_p2, col_p3 = st.columns(3)
    with col_p1:
        dist_carrera = st.selectbox("Distancia Objetivo:", [5.0, 10.0, 15.0, 21.1], index=1)
    with col_p2:
        tiempo_target = st.number_input("Tiempo Objetivo (minutos):", min_value=15.0, max_value=300.0, value=45.0, step=0.5)
    with col_p3:
        estrategia_sel = st.selectbox("Estrategia de Ritmo:", ["Negative Split", "Ritmo Uniforme", "Positive Split"])

    if st.button("📊 Calcular Parciales de Carrera", type="primary"):
        df_splits = calculate_pacing_splits(dist_carrera, tiempo_target, estrategia_sel)
        
        # Gráfica de Ritmo km a km
        fig_splits = px.line(
            df_splits,
            x="Km",
            y="Ritmo_Segundos",
            text="Ritmo Prescrito (min/km)",
            title=f"Perfil de Ritmo Proyectado ({estrategia_sel})",
            markers=True
        )
        fig_splits.update_traces(textposition="top center")
        fig_splits.update_yaxes(title="Ritmo (Segundos/km)", autorange="reversed") # Invertido: arriba es más rápido
        st.plotly_chart(fig_splits, use_container_width=True)

        # Tabla limpia de parciales
        st.dataframe(
            df_splits[["Km", "Ritmo Prescrito (min/km)", "Tiempo Acumulado"]],
            use_container_width=True,
            hide_index=True
        )

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

# --- PESTAÑA 4: HISTORIAL DE DATOS ---
with tab_history:
    # 1. DIAGNÓSTICO PRINCIPAL INTEGRAL
    st.subheader("Estado de Rendimiento Integral")
    
    col_ritmo, col_corazon = st.columns(2)
    
    with col_ritmo:
        st.markdown("##### Análisis Biomecánico (Ritmo)")
        performance = performance_status(filtered)
        if performance["change"] > 0.3:
            st.success("Progreso detectado: El ritmo promedio está en mejora continua, indicando un estado óptimo.")
        elif performance["change"] < -0.3:
            st.warning("Alerta de rendimiento: Caída reciente en las métricas de ritmo. Se sugiere priorizar la recuperación.")
        else:
            st.info("Mantenimiento: Rendimiento biomecánico estable y consolidado.")
            
    with col_corazon:
        st.markdown("##### Análisis Fisiológico (Eficiencia Aeróbica)")
        ef_status = aerobic_efficiency_status(filtered)
        
        if ef_status["status"] == "no_data":
            st.info("Sin registros de frecuencia cardíaca en el archivo o rango seleccionado.")
        elif ef_status["status"] == "insufficient_data":
            st.info("Datos de pulso insuficientes para calcular la tendencia de eficiencia.")
        else:
            if ef_status["state"] == "positive":
                st.success(f"{ef_status['verdict']} (EF: {ef_status['recent_ef']})")
            elif ef_status["state"] == "negative":
                st.warning(f"{ef_status['verdict']} (EF: {ef_status['recent_ef']})")
            else:
                st.info(f"{ef_status['verdict']} (EF: {ef_status['recent_ef']})")
                
    st.markdown("---")
    
    # 2. ANÁLISIS INDIVIDUAL POR SESIÓN (Líneas con colores de acento)
    if mostrar_grafica:
        with st.expander("📈 Ver gráficas de tendencia", expanded=False):
            col_graf1, col_graf2 = st.columns(2)
            
            with col_graf1:
                st.subheader("Volumen por Actividad")
                # Aplicamos el naranja principal
                st.line_chart(filtered.set_index("Activity Date")["Distance"], color="#FC4C02")
                
            with col_graf2:
                st.subheader("Evolución de Ritmo")
                # Aplicamos un cian brillante para contrastar la velocidad
                st.line_chart(filtered.set_index("Activity Date")["pace_min_km"], color="#00E5FF")
        
            st.markdown("---")
            
            # 3. TENDENCIA AGREGADA (Ocupando todo el ancho para facilitar la lectura a largo plazo)
            st.subheader("Tendencia Semanal de Ritmo")
            weekly_pace_data = weekly_pace(filtered)
            st.line_chart(weekly_pace_data.set_index("label")["pace_min_km"], color="#FC4C02")
    
    # 4. DATOS CRUDOS (Al final de la página)
    # 4. DATOS CRUDOS (Al final de la página)
    if mostrar_tabla:
        st.markdown("---")
        st.subheader("Registro Tabular")
        
        # 1. Filtramos y hacemos una copia de las columnas de interés
        df_display = filtered[["Activity Date", "Activity Name", "Distance", "pace_min_km"]].copy()
        
        # 2. Aplicamos el estilo de Pandas (Mapa de calor)
        # Usamos el mapa de color 'viridis_r' (invertido) para que los ritmos más bajos 
        # (más rápidos) brillen en tonos amarillos/verdes, ideal para el Dark Mode.
        styled_df = df_display.style.background_gradient(
            subset=['pace_min_km'], 
            cmap='viridis_r' 
        ).format({
            "Distance": "{:.2f} km",
            "pace_min_km": "{:.2f} /km"
        })
        
        # 3. Renderizamos la tabla estilizada en Streamlit
        st.dataframe(
            styled_df,
            use_container_width=True,
            hide_index=True 
        )

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
import plotly.graph_objects as go
import streamlit as st
import plotly.express as px
import pandas as pd
import json

from src.ai_coach import ask_ai_coach
from src.metrics import calculate_acwr, calculate_polarization_ratio, get_vdot_training_paces
from datetime import datetime
from datetime import datetime
from src.metrics import fatigue_ratio
from src.ai_coach import ask_ai_coach
from src.metrics import evaluate_stress_balance
from src.metrics import calculate_dynamic_vdot, get_vdot_training_paces_dynamic

def render_weekly_metrics(stats):
    weekly_km = stats["weekly_km"]

    promedio = weekly_km["Distance"].mean()
    ultima_semana = weekly_km["Distance"].iloc[-1]
    semana_anterior = weekly_km["Distance"].iloc[-2]
    cambio_pct = ((ultima_semana - semana_anterior) / semana_anterior) * 100
    mejor_semana = weekly_km["Distance"].max()
    promedio_semanal = weekly_km["Distance"].mean()

    st.subheader("📊 Kilómetros por semana")
    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=weekly_km["label"],
            y=weekly_km["Distance"],
            name="Km semanales"
        )
    )

    fig.add_trace(
        go.Scatter(
            x=weekly_km["label"],
            y=[promedio] * len(weekly_km),
            mode="lines",
            name="Promedio semanal"
        )
    )

    fig.add_trace(
        go.Scatter(
            x=weekly_km["label"],
            y=weekly_km["rolling_avg"],
            mode="lines",
            name="Tendencia",
        )
    )

    fig.update_layout(
        title="Carga semanal",
        xaxis_title="Semanas",
        yaxis_title="Kilómetros",
        template="plotly_dark",
        height=500
    )

    st.plotly_chart(fig, use_container_width=True)

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("📈 Semana actual", f"{ultima_semana:.1f} km")
    col2.metric("📊 Cambio", f"{cambio_pct:.1f}%")
    col3.metric("🏆 Mejor semana", f"{mejor_semana:.1f} km")
    col4.metric("📉 Promedio", f"{promedio_semanal:.1f} km")

    if cambio_pct > 10:
        st.warning(
            "⚠️ Tu carga semanal aumentó mucho. "
            "Considera recuperación."
        )
    elif cambio_pct < -20:
        st.info("📉 Semana más ligera de lo normal.")
    else:
        st.success("✅ Carga semanal estable.")

    st.subheader("⚡ Análisis de fatiga")
    weekly_km = fatigue_ratio(weekly_km)

    fatigue = weekly_km["fatigue_ratio"].iloc[-1]

    if fatigue > 1.5:
        st.error("⚠️ Riesgo alto de fatiga")
    elif fatigue > 1.3:
        st.warning("⚠️ Carga elevada, monitorea recuperación")
    else:
        st.success("✅ Carga estable")

# boton para generar el análisis del entrenador virtual
def render_ai_coach_section(df: pd.DataFrame):
    """
    Renderiza la sección interactiva del Entrenador Virtual con un botón
    que consulta la API de Gemini utilizando las métricas y la regla de estrés.
    """
    st.markdown("---")
    st.subheader("🤖 Entrenador Virtual (AI Coach)")
    st.caption("Obtén un diagnóstico técnico personalizado basado en tus métricas reales y la regla de estrés.")

    # Usamos un key único para evitar conflictos en Streamlit
    if st.button("Generar Diagnóstico y Plan Semanal", key="btn_generar_diagnostico_ia"):
        with st.spinner("Analizando microciclos y conectando con el Entrenador IA..."):
            
            # Calculamos de forma dinámica el kilometraje de la semana más reciente
            if not df.empty and 'Week' in df.columns and 'Distance' in df.columns:
                ultima_semana = df[df['Week'] == df['Week'].max()]
                weekly_km = round(ultima_semana['Distance'].sum(), 1)
            else:
                weekly_km = 0.0

            metrics_summary = {
                "weekly_km": weekly_km,
                "avg_pace": "5:20", # Ajustable según tus métricas de ritmo promedio
                "zone_distribution": "Basado en Puntos de Daniels"
            }
            
            # Invocamos la función unificada enviando el resumen y el DataFrame completo
            consejo = ask_ai_coach(metrics_summary, df)
            
            if consejo:
                st.markdown("### 📋 Análisis y Recomendaciones")
                st.markdown(consejo)
            else:
                st.warning("La IA no pudo generar una respuesta en este momento.")

        # Mostramos la respuesta dentro de la misma tarjeta
        if "ai_feedback" in st.session_state:
            st.divider()
            st.markdown(st.session_state["ai_feedback"])


# Función para renderizar el gráfico de Puntos Daniels
def render_daniels_chart(df: pd.DataFrame):
    st.subheader("📈 Estrés de Entrenamiento (Puntos de Daniels)")
    st.caption("Visualiza tu carga fisiológica real, desglosada por intensidad.")

    weekly_points = df.groupby('Week')[['points_E', 'points_T', 'points_I']].sum().reset_index()

    fig = px.bar(
        weekly_points,
        x='Week',
        y=['points_E', 'points_T', 'points_I'],
        labels={'value': 'Puntos de Estrés', 'variable': 'Zonas'},
        color_discrete_map={
            'points_E': '#2ecc71',
            'points_T': '#f1c40f',
            'points_I': '#e74c3c'
        }
    )
    
    # 🚀 Asignamos un key exclusivo que no se repita en ninguna otra parte del proyecto
    st.plotly_chart(fig, use_container_width=True, key="chart_daniels_unique_matrix_id")


# Función para renderizar la alerta de estrés
def render_stress_alert(df: pd.DataFrame):
    """
    Muestra una alerta visual basada en la evaluación automática de estrés.
    """
    
    evaluacion = evaluate_stress_balance(df)
    
    # Renderizamos la alerta según el estado devuelto
    if evaluacion["status"] == "danger":
        st.error(evaluacion["message"])
    elif evaluacion["status"] == "warning":
        st.warning(evaluacion["message"])
    else:
        st.success(evaluacion["message"])


def render_kpi_dashboard(df: pd.DataFrame):
    """
    Renderiza un panel superior con tarjetas de KPIs y la cuenta regresiva
    para el objetivo principal (Reto Rosa 15K en Roldanillo).
    """
    st.subheader("📊 Panel de Control y Objetivos")
    
    col1, col2, col3 = st.columns(3)
    
    # 1. Calcular kilometraje de la semana más reciente
    if not df.empty and 'Week' in df.columns and 'Distance' in df.columns:
        ultima_semana = df[df['Week'] == df['Week'].max()]
        weekly_km = round(ultima_semana['Distance'].sum(), 1)
        estres_semana = round(ultima_semana['daniels_total'].sum(), 1) if 'daniels_total' in ultima_semana.columns else 0.0
    else:
        weekly_km = 0.0
        estres_semana = 0.0
        
    with col1:
        st.metric(
            label="Kilometraje Semana Actual", 
            value=f"{weekly_km} km", 
            delta="Volumen base"
        )
        
    # 2. Cuenta regresiva para el Reto Rosa 15K (Roldanillo - Octubre)
    # Definimos la fecha estimada del evento (ej. Tercer domingo de octubre)
    fecha_objetivo = datetime(2026, 10, 18)
    dias_restantes = (fecha_objetivo - datetime.now()).days
    
    with col2:
        st.metric(
            label="⏳ Reto Rosa 15K (Roldanillo)", 
            value=f"{max(0, dias_restantes)} días", 
            delta="Octubre 2026"
        )
        
    # 3. Puntos de estrés de la semana
    with col3:
        st.metric(
            label="⚡ Estrés Fisiológico (Daniels)", 
            value=f"{estres_semana} pts",
            delta="Carga interna"
        )
    
    st.markdown("---")

# Función para renderizar la tarjeta de ACWR
def render_acwr_card(df: pd.DataFrame):
    """
    Renderiza la tarjeta de métrica ACWR con su respectivo estado de seguridad.
    """
    from src.metrics import calculate_acwr
    
    resultado = calculate_acwr(df)
    
    st.subheader("🛡️ Control de Carga y Prevención (ACWR)")
    
    if resultado["status"] == "nodata" or resultado["status"] == "learning":
        st.info(resultado["message"])
        return

    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            label="Ratio ACWR", 
            value=resultado["acwr"], 
            delta="Óptimo: 0.8 - 1.3"
        )
    with col2:
        st.metric(
            label="Carga Aguda (Semana)", 
            value=f"{resultado['carga_aguda']} pts"
        )
    with col3:
        st.metric(
            label="Carga Crónica (Prom. 4 Sem)", 
            value=f"{resultado['carga_cronica']} pts"
        )
        
    # Mensaje de alerta dinámico según el estado
    if resultado["status"] == "optimal":
        st.success(resultado["message"])
    elif resultado["status"] == "caution":
        st.warning(resultado["message"])
    elif resultado["status"] == "danger":
        st.error(resultado["message"])
    else:
        st.info(resultado["message"])

# Función para renderizar la tarjeta de Polarización
def render_polarization_card(df: pd.DataFrame):
    """
    Renderiza la tarjeta del Índice de Polarización del entrenamiento.
    """
    from src.metrics import calculate_polarization_ratio
    
    resultado = calculate_polarization_ratio(df)
    
    st.subheader("⚖️ Índice de Polarización (Modelo Aeróbico)")
    
    if resultado["status"] == "nodata":
        st.info(resultado["message"])
        return

    col1, col2 = st.columns(2)
    
    with col1:
        st.metric(
            label="Base Aeróbica (Zona E)", 
            value=f"{resultado['pct_e']}%", 
            delta="Ideal: ~80%"
        )
    with col2:
        st.metric(
            label="Intensidad Alta (Zonas T/I)", 
            value=f"{resultado['pct_hard']}%",
            delta="Ideal: ~20%"
        )
        
    # Mensaje de estado dinámico
    if resultado["status"] == "optimal":
        st.success(resultado["message"])
    elif resultado["status"] == "moderate":
        st.warning(resultado["message"])
    else:
        st.error(resultado["message"])

# Función para renderizar la sección de la calculadora de ritmos VDOT
def render_vdot_calculator_section(df):
    """
    Renderiza la calculadora VDOT conectada directamente a la evolución del DataFrame de Strava.
    """
    st.subheader("🎯 Calculadora Dinámica de Ritmos VDOT & Predicciones")
    st.caption("Zonas fisiológicas actualizadas automáticamente según las marcas de tus entrenamientos recientes.")

    # Calculamos el VDOT real basado en el CSV subido
    vdot_actual = calculate_dynamic_vdot(df)
    ritmos = get_vdot_training_paces_dynamic(vdot_actual)

    col1, col2 = st.columns([1, 2])

    with col1:
        st.metric(
            label="Índice VDOT Actualizado", 
            value=ritmos["vdot"], 
            delta="¡Evolución de ritmo detectada! 🚀"
        )
        st.markdown("#### 🔮 Nuevos Objetivos (Predicción)")
        st.markdown(f"* **Meta 10K:** `{ritmos['pred_10k']}`")
        st.markdown(f"* **Reto Rosa (15K):** `{ritmos['pred_15k']}`")

    with col2:
        st.markdown("#### ⚡ Zonas de Ritmo Evolucionadas")
        st.markdown(f"* **🟢 Zona Fácil (E):** `{ritmos['Easy (E)']}`")
        st.markdown(f"* **🔵 Zona Maratón (M):** `{ritmos['Marathon (M)']}`")
        st.markdown(f"* **🟡 Zona Umbral (T):** `{ritmos['Threshold (T)']}`")
        st.markdown(f"* **🔴 Zona Intervalos (I):** `{ritmos['Interval (I)']}`")
        st.markdown(f"* **🟣 Zona Repeticiones (R):** `{ritmos['Repetition (R)']}`")
    
    st.markdown("---")

# Función para renderizar el check-in de bienestar y recuperación
def render_weekly_checkin(df, metrics_summary, vdot_actual):
    st.subheader("🧠 Check-in de Bienestar y Análisis IA")
    st.caption("Añade tu contexto cualitativo para que el Coach IA personalice el análisis de esta semana.")

    with st.form("wellness_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            rpe = st.slider("Sensación de Fatiga General (1 = Fresco, 10 = Exhausto)", 1, 10, 5)
            sleep_quality = st.select_slider(
                "Calidad del sueño esta semana",
                options=["Muy mala", "Regular", "Buena", "Excelente"], value="Buena"
            )

        with col2:
            stress_level = st.radio("Estrés externo (no deportivo)", ["Bajo", "Moderado", "Alto"], horizontal=True)
            pains = st.multiselect(
                "¿Alguna molestia física a considerar?",
                ["Ninguna", "Rodillas", "Fascia plantar", "Gemelos/Aquiles", "Isquiotibiales", "Espalda baja", "Otro"]
            )

        user_notes = st.text_area("Comentarios adicionales (Opcional)", placeholder="Ej: Las repeticiones en 3:35 las sentí controladas, pero amanecí con los gemelos cargados...")

        # Botón de envío
        submitted = st.form_submit_button("Generar Análisis IA", type="primary")

    if submitted:
        # 1. Empaquetar los datos cualitativos
        feedback_data = {
            "rpe_fatiga": rpe,
            "sueño": sleep_quality,
            "estres": stress_level,
            "molestias": pains,
            "notas": user_notes
        }
        
        # 2. Llamar a la IA mostrando un spinner de carga
        with st.spinner("Analizando tus métricas de Strava y tu recuperación..."):
            ai_response = ask_ai_coach(
                metrics_summary=metrics_summary, 
                df=df, 
                feedback_data=feedback_data, 
                vdot_actual=vdot_actual
            )
        
        # 3. Mostrar el resultado
        st.success("¡Análisis completado!")
        st.markdown("### 🤖 Feedback de tu Coach IA")
        st.info(ai_response)
        
    st.markdown("---")
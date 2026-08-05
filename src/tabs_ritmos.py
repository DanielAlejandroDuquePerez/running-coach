import pandas as pd
import streamlit as st

from src.dashboard_helpers import build_daniels_weekly_summary, render_hud_metric, render_status_badge, render_upload_notice, set_upload_notice, process_uploaded_activities
from src.charts import create_internal_load_chart, render_interactive_ecosystem_chart, calculate_daniels_points_row
from src.metrics import compute_acwr_ratio, get_jack_daniels_zones, get_vdot_from_df


def render_ritmos_tab(state, filtered):
    st.subheader("🎯 Control de Ritmos y Predictor de Competencia")
    st.caption("Ajusta tu marca de referencia para proyectar tiempos objetivo y zonas fisiológicas.")

    col_ref_1, col_ref_2 = st.columns(2)
    with col_ref_1:
        dist_base = st.selectbox("Distancia de referencia (km)", [3.0, 5.0, 10.0, 15.0, 21.1], index=1)
    with col_ref_2:
        tiempo_base = st.number_input("Tiempo de referencia (minutos)", min_value=5.0, max_value=300.0, value=25.0, step=0.5)

    from src.performance_context import calculate_race_predictions
    predictions = calculate_race_predictions(dist_base, tiempo_base)
    if not predictions:
        render_status_badge("Ingresa una marca de referencia válida para activar el predictor de competencia.", tone="info", icon="i")
    else:
        st.markdown("### 🏁 Race Predictor")
        pred_cols = st.columns(4)
        for idx, (label, info) in enumerate(predictions.items()):
            with pred_cols[idx]:
                render_hud_metric(label, info["tiempo"], delta=f"Ritmo: {info['ritmo']}", tone="cyan")

    st.markdown("---")
    st.subheader("🧬 Zonas Fisiológicas de Entrenamiento")
    vdot_calc, vdot_ref = get_vdot_from_df(filtered)

    if not vdot_calc:
        render_status_badge("No fue posible calcular un VDOT de referencia con los datos filtrados.", tone="warning", icon="!")
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
                    render_status_badge("No se encontró información para esta zona.", tone="info", icon="i")
                else:
                    row = zone_row.iloc[0]
                    zone_cols = st.columns([1, 1.35])
                    with zone_cols[0]:
                        render_hud_metric("Rango de Ritmo", row["Rango de Ritmo (min/km)"], tone="lime")
                    with zone_cols[1]:
                        render_status_badge(row["Propósito Fisiológico"], tone="info", icon="○")

    st.markdown("---")
    st.subheader("🛡️ Prevención de Lesiones: Ratio ACWR")
    st.caption("Sincroniza tu historial de entrenamiento desde un archivo o ajusta los valores manualmente.")

    km_agudos_val = float(state.get("km_agudos", 40.0))
    km_cronicos_val = float(state.get("km_cronicos", 35.0))

    with st.expander("📁 Cargar Historial desde Archivo (CSV / Excel)", expanded=False):
        uploaded_file = st.file_uploader("Cargar historial de entrenamiento", type=["csv", "xlsx"])

    if uploaded_file is not None:
        resumen_file, err_file = process_uploaded_activities(uploaded_file)
        if err_file:
            set_upload_notice(err_file, tone="danger", icon="⚠")
        else:
            state["df_actividades"] = resumen_file["df_actividades"]
            state["df_actividades_tabla"] = resumen_file["display_df"]
            state["df_semanal"] = resumen_file["df_semanal"]
            set_upload_notice(
                f"Historial cargado: {len(resumen_file['df_actividades'])} registros procesados.",
                tone="success",
                icon="✓",
            )

    render_upload_notice()

    df_act = state.get("df_actividades")
    df_tabla = state.get("df_actividades_tabla")
    df_sem = state.get("df_semanal")

    if isinstance(df_act, pd.DataFrame) and not df_act.empty:
        if not isinstance(df_sem, pd.DataFrame) or df_sem.empty:
            df_sem = build_daniels_weekly_summary(df_act)
            state["df_semanal"] = df_sem

    if isinstance(df_tabla, pd.DataFrame) and not df_tabla.empty:
        st.subheader("📋 Registro Detallado de Actividades")
        st.dataframe(df_tabla, use_container_width=True)

    if isinstance(df_sem, pd.DataFrame) and not df_sem.empty:
        with st.expander("🔥 Ver Carga Interna: Puntos de Estrés Daniels (Por Intensidad)", expanded=True):
            st.subheader("Distribución de Estrés Fisiológico Semanal")
            st.caption("Evolución del esfuerzo real en Puntos Daniels según la intensidad de las zonas recorridas.")
            fig_internal = create_internal_load_chart(df_sem)
            st.plotly_chart(fig_internal, use_container_width=True, config={"displayModeBar": False}, key="analitica_daniels_chart_preview")
    else:
        st.info("💡 Sube tu archivo de entrenamientos para visualizar la Carga Interna Daniels.")

    col_c1, col_c2 = st.columns(2)
    with col_c1:
        html_aguda = (
            f'<div class="hud-card" style="--hud-accent: #FFB300;">'
            f'<div class="hud-accent-bar"></div>'
            f'<div class="hud-label">CARGA AGUDA DETECTADA</div>'
            f'<div class="hud-value">{km_agudos_val:.1f} <span style="font-size:1rem;color:#8A99AD">km</span></div>'
            f'<div class="hud-subtitle">Últimos 7 días</div>'
            f'</div>'
        )
        st.markdown(html_aguda, unsafe_allow_html=True)

    with col_c2:
        html_cronica = (
            f'<div class="hud-card" style="--hud-accent: #00D2FF;">'
            f'<div class="hud-accent-bar"></div>'
            f'<div class="hud-label">CARGA CRÓNICA DETECTADA</div>'
            f'<div class="hud-value">{km_cronicos_val:.1f} <span style="font-size:1rem;color:#8A99AD">km/sem</span></div>'
            f'<div class="hud-subtitle">Promedio 28 días</div>'
            f'</div>'
        )
        st.markdown(html_cronica, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    if state.get("df_semanal") is not None:
        with st.expander("📊 Ver gráfico histórico de Carga vs ACWR", expanded=False):
            render_interactive_ecosystem_chart(state.get("df_actividades"))

    with st.expander("⚙️ Ingreso o Ajuste Manual de Carga", expanded=True):
        col_a1, col_a2 = st.columns(2)
        with col_a1:
            km_agudos = float(st.number_input("Carga Aguda (Km última semana):", min_value=0.0, max_value=200.0, value=km_agudos_val, step=1.0, key="analitica_km_agudos"))
        with col_a2:
            km_cronicos = float(st.number_input("Carga Crónica (Promedio semanal 28 días):", min_value=1.0, max_value=200.0, value=km_cronicos_val, step=1.0, key="analitica_km_cronicos"))

    val_acwr, estado_acwr, tipo_alerta, desc_acwr = compute_acwr_ratio(km_agudos, km_cronicos)

    col_m1, col_m2 = st.columns([1, 2])
    with col_m1:
        render_hud_metric("Ratio ACWR Actual", f"{val_acwr:.2f}", tone="cyan")
    with col_m2:
        if tipo_alerta == "success":
            render_status_badge(f"{estado_acwr} · {desc_acwr}", tone="success", icon="✓")
        elif tipo_alerta == "warning":
            render_status_badge(f"{estado_acwr} · {desc_acwr}", tone="warning", icon="⚠")
        elif tipo_alerta == "error":
            render_status_badge(f"{estado_acwr} · {desc_acwr}", tone="danger", icon="⚠")
        else:
            render_status_badge(f"{estado_acwr} · {desc_acwr}", tone="info", icon="i")

    if val_acwr > 1.3 or val_acwr < 0.8:
        prompt_auto = (
            f"Hola Coach, mi ratio ACWR actual es de {val_acwr:.2f} con una carga aguda de {km_agudos} km "
            f"y crónica de {km_cronicos} km/sem. Mi estado actual es: {estado_acwr}. "
            f"¿Qué ajustes específicos de descarga o intensidades me recomiendas para esta semana?"
        )
        if st.button("🤖 Generar consulta automática para el Coach IA sobre esta alerta", type="secondary"):
            state["prompt_sugerido_ia"] = prompt_auto
            render_status_badge("Consulta guardada. Ve a la pestaña Coach IA para enviarla.", tone="info", icon="↗")

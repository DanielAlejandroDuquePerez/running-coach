import pandas as pd
import streamlit as st

from src.charts import create_internal_load_chart, render_interactive_ecosystem_chart, calculate_daniels_points_row
from src.dashboard_helpers import build_daniels_weekly_summary, render_status_badge
from src.metrics import calculate_acwr
from src.performance_context import calculate_training_readiness


def render_custom_card(label: str, value: str, subtitle: str, tone: str = "cyan", delta: str = None):
    """Renderiza tarjetas compactas unificando el HTML en una sola línea para evitar fallos de renderizado en Streamlit."""
    tone_colors = {
        "lime": "#00E676",
        "cyan": "#00D2FF",
        "amber": "#FFB300",
        "red": "#FF3366",
        "slate": "#8A99AD"
    }
    accent = tone_colors.get(tone, "#00D2FF")
    
    delta_html = f'<div style="font-size:0.85rem;font-weight:600;color:{accent};margin-top:2px;">{delta}</div>' if delta else ''
    
    # HTML en cadena única para evitar que el parser de Markdown de Streamlit cree cajas de código
    html_str = (
        f'<div style="background-color:#111827;border:1px solid #1F2937;border-left:4px solid {accent};'
        f'border-radius:8px;padding:12px 16px;margin-bottom:10px;">'
        f'<div style="font-size:0.75rem;font-weight:700;color:#8A99AD;text-transform:uppercase;letter-spacing:0.5px;">{label}</div>'
        f'<div style="font-size:1.6rem;font-weight:800;color:#FFFFFF;line-height:1.2;margin-top:4px;">{value}</div>'
        f'{delta_html}'
        f'<div style="font-size:0.75rem;color:#9CA3AF;margin-top:4px;">{subtitle}</div>'
        f'</div>'
    )
    st.markdown(html_str, unsafe_allow_html=True)


def render_today_tab(state, filtered, data):
    st.title("🏃 Running Coach — Performance Hub")
    st.caption("Panel de control fisiológico en tiempo real basado en Daniels, Pfitzinger y Fitzgerald.")

    # 1. CÁLCULO DE MÉTRICAS BASE
    today_acwr = calculate_acwr(filtered)
    feedback_data = state.get("feedback_data", {})
    rpe_promedio = float(feedback_data.get("fatigue_rpe", 5))
    
    dias_descanso = 0
    if not filtered.empty and "Activity Date" in filtered.columns:
        dias_descanso = max((pd.Timestamp.today().date() - filtered["Activity Date"].max().date()).days, 0)

    acwr_val = today_acwr.get("acwr", 1.0)
    carga_aguda = today_acwr.get("carga_aguda", 0.0)
    carga_cronica = today_acwr.get("carga_cronica", 0.0)

    readiness_score, readiness_state, readiness_badge = calculate_training_readiness(
        acwr=acwr_val,
        rpe_promedio=rpe_promedio,
        dias_descanso_recientes=dias_descanso,
    )

    # 2. SECCIÓN PRINCIPAL: BARRA DE ESTADO DE READINESS (RECUPERADA)
    st.subheader("⚡ Estado de Predisposición Diaria")
    
    readiness_col, readiness_note = st.columns([1.1, 1.4])
    with readiness_col:
        accent_color = "#00E676" if readiness_badge == "success" else "#FFB300" if readiness_badge == "warning" else "#FF3366"
        html_readiness = (
            f'<div style="background-color:#111827;border:1px solid #1F2937;border-left:4px solid {accent_color};'
            f'border-radius:8px;padding:12px 16px;margin-bottom:6px;">'
            f'<div style="font-size:0.75rem;font-weight:700;color:#8A99AD;text-transform:uppercase;">READINESS DE HOY</div>'
            f'<div style="font-size:1.8rem;font-weight:800;color:#FFFFFF;">{int(readiness_score)} <span style="font-size:1rem;color:#8A99AD">/ 100</span></div>'
            f'<div style="font-size:0.75rem;color:#9CA3AF;">Predisposición diaria al entrenamiento</div>'
            f'</div>'
        )
        st.markdown(html_readiness, unsafe_allow_html=True)
        # Barra de progreso para salir a entrenar
        st.progress(readiness_score / 100)

    with readiness_note:
        if readiness_badge == "success":
            render_status_badge(readiness_state, tone="success", icon="●")
        elif readiness_badge == "warning":
            render_status_badge(readiness_state, tone="warning", icon="●")
        else:
            render_status_badge(readiness_state, tone="danger", icon="●")
            
        st.caption(
            f"Calculado con ACWR **{acwr_val:.2f}**, RPE promedio **{rpe_promedio:.0f}** y **{dias_descanso}** día(s) de descanso reciente."
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # 3. PERFORMANCE HUB (Métricas complementarias de Carga)
    st.subheader("📊 Métricas de Carga y Balance")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if 0.8 <= acwr_val <= 1.3:
            status_acwr, tone_a = "Sweet Spot", "cyan"
        elif 1.3 < acwr_val <= 1.5:
            status_acwr, tone_a = "Precaución", "amber"
        elif acwr_val > 1.5:
            status_acwr, tone_a = "Riesgo Spike", "red"
        else:
            status_acwr, tone_a = "Subentrenamiento", "slate"
            
        render_custom_card("📉 Ratio ACWR", f"{acwr_val:.2f}", "Equilibrio Carga A/C", tone=tone_a, delta=status_acwr)
        
    with col2:
        render_custom_card("🔥 Carga Aguda", f"{carga_aguda:.1f} km", "Últimos 7 días", tone="amber")
        
    with col3:
        render_custom_card("🛡️ Carga Crónica", f"{carga_cronica:.1f} km", "Promedio 28 días", tone="cyan")

    # 4. ALERTA SEMÁNTICA DE ESTADO
    if acwr_val < 0.8:
        st.info("🛋️ **Subentrenamiento:** Tu carga aguda es menor a la crónica. Considera aumentar progresivamente el estímulo.")
    elif 0.8 <= acwr_val <= 1.3:
        st.success("✅ **Entrenamiento Productivo (Sweet Spot):** Estás en la zona óptima de adaptación sin sobrecargar la estructura.")
    elif 1.3 < acwr_val <= 1.5:
        st.warning("⚠️ **Precaución por Fatiga:** Incremento rápido de la carga. Prioriza el descanso y la hidratación.")
    else:
        st.error("🚨 **Alerta de Spike (Alto Riesgo):** Fatiga acumulada excesiva. Se recomienda una sesión de descarga o descanso activo.")

    st.markdown("<br>", unsafe_allow_html=True)

    # 5. PRESUPUESTO DE ESTRÉS DANIELS & GRÁFICOS HISTÓRICOS
    if state.get('df_semanal') is not None:
        df_sem = state['df_semanal'].copy()
        required_pts = ['pts_e', 'pts_m', 'pts_t', 'pts_i', 'pts_r']
        if not all(col in df_sem.columns for col in required_pts):
            pts_df = df_sem.apply(calculate_daniels_points_row, axis=1)
            df_sem = pd.concat([df_sem, pts_df], axis=1)

        with st.expander("🔥 Presupuesto y Distribución de Estrés (Puntos Daniels)", expanded=True):
            pts_totales = df_sem['pts_acumulados'].sum() if 'pts_acumulados' in df_sem.columns else 85.0
            objetivo_pts = 120.0
            progreso = min(max(pts_totales / objetivo_pts, 0.0), 1.0)
            
            st.markdown("##### 📊 Consumo de Carga Semanal")
            st.progress(progreso)
            st.caption(f"Has consumido **{pts_totales:.1f}** de **{objetivo_pts:.1f}** Puntos Daniels previstos ({int(progreso * 100)}%).")
            
            fig_internal = create_internal_load_chart(df_sem)
            st.plotly_chart(fig_internal, use_container_width=True, config={'displayModeBar': False}, key="hoy_daniels_chart")

        st.markdown("### 📈 Evolución: Volumen vs ACWR")
        render_interactive_ecosystem_chart(filtered)

        # Botón para consulta automática
        if today_acwr.get("status") in {"caution", "danger"}:
            prompt_auto = (
                f"Hola Coach, hoy tengo un ACWR de {acwr_val:.2f}, "
                f"con carga aguda de {carga_aguda:.1f} km y carga crónica de {carga_cronica:.1f} km. "
                f"Mi readiness actual es {int(readiness_score)}/100. ¿Qué ajuste me recomiendas para esta semana?"
            )
            if st.button("🤖 Solicitar diagnóstico al Coach IA", type="primary", use_container_width=True):
                state["prompt_sugerido_ia"] = prompt_auto
                render_status_badge("Consulta guardada. Ve a la pestaña Coach IA para enviarla.", tone="info", icon="↗")


def render_ritmos_tab(state, filtered):
    """Pestaña secundaria para ritmos y calculadoras"""
    from src.dashboard_helpers import render_status_badge
    from src.metrics import get_jack_daniels_zones, get_vdot_from_df
    from src.performance_context import calculate_race_predictions

    st.subheader("🎯 Control de Ritmos y Predictor de Competencia")
    st.caption("Ajusta tu marca de referencia para proyectar tiempos objetivo y zonas fisiológicas.")

    col_ref_1, col_ref_2 = st.columns(2)
    with col_ref_1:
        dist_base = st.selectbox("Distancia de referencia (km)", [3.0, 5.0, 10.0, 15.0, 21.1], index=1)
    with col_ref_2:
        tiempo_base = st.number_input("Tiempo de referencia (minutos)", min_value=5.0, max_value=300.0, value=25.0, step=0.5)

    predictions = calculate_race_predictions(dist_base, tiempo_base)
    if not predictions:
        render_status_badge("Ingresa una marca de referencia válida para activar el predictor de competencia.", tone="info", icon="i")
    else:
        st.markdown("### 🏁 Race Predictor")
        pred_cols = st.columns(4)
        for idx, (label, info) in enumerate(predictions.items()):
            with pred_cols[idx]:
                render_custom_card(label, info["tiempo"], f"Ritmo: {info['ritmo']}", tone="cyan")

    st.markdown("---")
    st.subheader("🧬 Zonas Fisiológicas de Entrenamiento")
    vdot_calc, vdot_ref = get_vdot_from_df(filtered)

    if not vdot_calc:
        render_status_badge("No fue posible calcular un VDOT de referencia con los datos filtrados.", tone="warning", icon="!")
    else:
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
                if not zone_row.empty:
                    row = zone_row.iloc[0]
                    zone_cols = st.columns([1, 1.35])
                    with zone_cols[0]:
                        render_custom_card("Rango de Ritmo", row["Rango de Ritmo (min/km)"], "Ritmo objetivo", tone="lime")
                    with zone_cols[1]:
                        render_status_badge(row["Propósito Fisiológico"], tone="info", icon="○")

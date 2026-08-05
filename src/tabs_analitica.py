import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.charts import make_responsive_chart
from src.dashboard_helpers import render_hud_metric, render_status_badge
from src.metrics import calculate_acwr
from src.performance_context import build_readiness_log_df, calculate_mind_body_score, calculate_training_readiness


def render_analitica_tab(state, filtered):
    st.subheader("🩺 Readiness y Sensaciones")
    st.caption("Diario diario inspirado en Pfitzinger y Fitzgerald para conectar recuperación, mente y cuerpo.")

    acwr_context = calculate_acwr(filtered)
    days_since_last_run = max((pd.Timestamp.today().date() - filtered["Activity Date"].max().date()).days, 0)
    feedback_data = state.get("feedback_data", {})

    current_sleep_quality = feedback_data.get("sleep_quality", "Buena")
    current_stress = feedback_data.get("stress_level", "Moderado")
    current_mood = feedback_data.get("mood", "Neutral")
    current_notes = feedback_data.get("notes", "")

    current_readiness_score, current_readiness_state, current_readiness_badge = calculate_training_readiness(
        acwr_context.get("acwr", 0.0),
        float(feedback_data.get("fatigue_rpe", 3)),
        days_since_last_run,
    )
    current_mind_body_score = calculate_mind_body_score(
        current_sleep_quality,
        current_mood,
        float(feedback_data.get("motivation", 6)),
        float(feedback_data.get("focus", 6)),
        float(feedback_data.get("soreness", 3)),
        current_stress,
    )

    history_df = build_readiness_log_df(state.get("readiness_log", []))

    metric_cols = st.columns(4)
    with metric_cols[0]:
        render_hud_metric("Recover-ability", f"{current_readiness_score:.0f}%", delta=current_readiness_state, tone="cyan")
    with metric_cols[1]:
        render_hud_metric("Mind-Body", f"{current_mind_body_score:.0f}%", delta=f"Sueño {current_sleep_quality}", tone="lime")
    with metric_cols[2]:
        render_hud_metric("Días sin correr", f"{days_since_last_run}", delta="Contexto de recuperación", tone="amber")
    with metric_cols[3]:
        render_hud_metric("ACWR Contextual", f"{acwr_context.get('acwr', 0.0):.2f}", delta=acwr_context.get("message", ""), tone="slate")

    st.markdown("---")
    st.markdown("### 📋 Diario diario de recuperación y sensaciones")

    with st.form("readiness_daily_form"):
        form_date = st.date_input("Fecha del registro", value=pd.Timestamp.today().date(), key="readiness_date")

        form_cols_1 = st.columns(3)
        with form_cols_1[0]:
            sleep_hours = st.number_input("Horas de sueño", min_value=0.0, max_value=12.0, value=float(feedback_data.get("sleep_hours", 7.5)), step=0.25, key="readiness_sleep_hours")
            sleep_quality = st.select_slider("Calidad del sueño", options=["Mala", "Regular", "Buena", "Excelente"], value=current_sleep_quality, key="readiness_sleep_quality")
        with form_cols_1[1]:
            fatigue_rpe = st.slider("Fatiga percibida", 1, 10, int(feedback_data.get("fatigue_rpe", 3)), key="readiness_fatigue_rpe")
            soreness = st.slider("Rigidez / dolor muscular", 1, 10, int(feedback_data.get("soreness", 3)), key="readiness_soreness")
        with form_cols_1[2]:
            resting_hr = st.number_input("FC reposo (ppm)", min_value=35, max_value=120, value=int(feedback_data.get("resting_hr", 52)), step=1, key="readiness_resting_hr")
            body_state = st.selectbox("Estado corporal", ["Ligero", "Normal", "Pesado", "Cargado"], index=["Ligero", "Normal", "Pesado", "Cargado"].index(feedback_data.get("body_state", "Normal")), key="readiness_body_state")

        form_cols_2 = st.columns(3)
        with form_cols_2[0]:
            mood = st.selectbox("Estado de ánimo", ["Muy bajo", "Bajo", "Neutral", "Alto", "Muy alto"], index=["Muy bajo", "Bajo", "Neutral", "Alto", "Muy alto"].index(current_mood), key="readiness_mood")
            stress_level = st.selectbox("Estrés externo", ["Bajo", "Moderado", "Alto"], index=["Bajo", "Moderado", "Alto"].index(current_stress), key="readiness_stress")
        with form_cols_2[1]:
            motivation = st.slider("Motivación", 1, 10, int(feedback_data.get("motivation", 6)), key="readiness_motivation")
            focus = st.slider("Enfoque mental", 1, 10, int(feedback_data.get("focus", 6)), key="readiness_focus")
        with form_cols_2[2]:
            confidence = st.slider("Confianza competitiva", 1, 10, int(feedback_data.get("confidence", 6)), key="readiness_confidence")
            energy = st.slider("Energía percibida", 1, 10, int(feedback_data.get("energy", 6)), key="readiness_energy")

        notes = st.text_area(
            "Notas del día",
            value=current_notes,
            placeholder="Ej: Dormí mal, piernas pesadas, pero me sentí tranquilo mentalmente.",
            height=100,
            key="readiness_notes",
        )

        save_entry = st.form_submit_button("Registrar sensaciones", type="primary")

    if save_entry:
        recoverability_score = calculate_training_readiness(acwr_context.get("acwr", 0.0), fatigue_rpe, days_since_last_run)[0]
        mind_body_score = calculate_mind_body_score(sleep_quality, mood, motivation, focus, soreness, stress_level)
        record = {
            "fecha": pd.Timestamp(form_date),
            "recoverability_score": recoverability_score,
            "mind_body_score": mind_body_score,
            "sleep_hours": float(sleep_hours),
            "sleep_quality": sleep_quality,
            "fatigue_rpe": int(fatigue_rpe),
            "soreness": int(soreness),
            "resting_hr": int(resting_hr),
            "body_state": body_state,
            "mood": mood,
            "stress_level": stress_level,
            "motivation": int(motivation),
            "focus": int(focus),
            "confidence": int(confidence),
            "energy": int(energy),
            "notes": notes,
        }

        history = [row for row in state.get("readiness_log", []) if pd.Timestamp(row.get("fecha")).date() != pd.Timestamp(form_date).date()]
        history.append(record)
        state["readiness_log"] = history
        state["feedback_data"] = {
            "fatigue_rpe": fatigue_rpe,
            "sleep_quality": sleep_quality,
            "stress_level": stress_level,
            "discomforts": [body_state],
            "notes": notes,
            "sleep_hours": sleep_hours,
            "resting_hr": resting_hr,
            "mood": mood,
            "motivation": motivation,
            "focus": focus,
            "confidence": confidence,
            "energy": energy,
            "soreness": soreness,
            "body_state": body_state,
        }
        st.rerun()

    if history_df.empty:
        st.info("Registra tu primer día para activar las gráficas de readiness y sensaciones.")
    else:
        st.markdown("### 📈 Visualizaciones")
        chart_cols = st.columns([1.3, 1.0])

        with chart_cols[0]:
            fig_trend = go.Figure()
            fig_trend.add_trace(go.Scatter(x=history_df["fecha"], y=history_df["recoverability_score"], name="Recover-ability", mode="lines+markers", line=dict(color="#00D2FF", width=3)))
            fig_trend.add_trace(go.Scatter(x=history_df["fecha"], y=history_df["mind_body_score"], name="Mind-Body", mode="lines+markers", line=dict(color="#00E676", width=3)))
            fig_trend = make_responsive_chart(fig_trend, height=320, title="Evolución diaria de recuperación y estado mental")
            fig_trend.update_yaxes(range=[0, 100])
            st.plotly_chart(fig_trend, use_container_width=True, key="readiness_trend_chart")

        with chart_cols[1]:
            latest = history_df.iloc[-1]
            radar_labels = ["Sueño", "Motivación", "Enfoque", "Confianza", "Energía", "Recuperación"]
            sleep_quality_map = {"Mala": 35, "Regular": 60, "Buena": 80, "Excelente": 95}
            radar_values = [
                sleep_quality_map.get(latest.get("sleep_quality", "Buena"), 60),
                float(latest.get("motivation", 6)) * 10,
                float(latest.get("focus", 6)) * 10,
                float(latest.get("confidence", 6)) * 10,
                float(latest.get("energy", 6)) * 10,
                float(latest.get("recoverability_score", 0)),
            ]
            radar_values.append(radar_values[0])
            radar_labels.append(radar_labels[0])

            fig_radar = go.Figure()
            fig_radar.add_trace(
                go.Scatterpolar(
                    r=radar_values,
                    theta=radar_labels,
                    fill="toself",
                    name="Último registro",
                    line=dict(color="#FFB300", width=3),
                    fillcolor="rgba(255, 179, 0, 0.18)",
                )
            )
            fig_radar.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                polar=dict(
                    bgcolor="rgba(0,0,0,0)",
                    radialaxis=dict(visible=True, range=[0, 100], tickfont=dict(color="#8A99AD")),
                    angularaxis=dict(tickfont=dict(color="#FFFFFF")),
                ),
                margin=dict(l=20, r=20, t=35, b=20),
                showlegend=False,
                height=320,
            )
            st.plotly_chart(fig_radar, use_container_width=True, key="readiness_radar_chart")

        st.markdown("### 🗒️ Últimos registros")
        st.dataframe(history_df.tail(10).sort_values("fecha", ascending=False), use_container_width=True)

    st.markdown("---")
    st.markdown("### 💡 Interpretación rápida")
    tip_cols = st.columns(3)
    with tip_cols[0]:
        render_status_badge("Pfitzinger: la recuperación contextualiza la carga real.", tone="info", icon="i")
    with tip_cols[1]:
        render_status_badge("Fitzgerald: las sensaciones son datos, no ruido.", tone="success", icon="●")
    with tip_cols[2]:
        render_status_badge("Si el estrés mental sube, baja la ambición mecánica.", tone="warning", icon="⚠")

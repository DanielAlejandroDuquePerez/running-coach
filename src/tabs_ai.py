import hashlib
import json

import pandas as pd
import streamlit as st

from src.ai_coach import ask_ai_coach, build_llm_prompt
from src.ai_engine import build_coach_context, generate_training_recommendations
from src.dashboard_helpers import render_hud_metric, render_status_badge
from src.metrics import basic_stats, calculate_acwr, get_vdot_from_df
from src.storage import load_all_plans, save_new_plan


def _context_signature(normalized_context: dict, recommendations: dict, acwr_snapshot: dict) -> str:
    payload = {
        "weekly_km_raw": normalized_context.get("weekly_km_raw"),
        "avg_pace": normalized_context.get("avg_pace"),
        "alert_message": normalized_context.get("alert_message"),
        "vdot_actual": normalized_context.get("vdot_actual"),
        "feedback": normalized_context.get("feedback", {}),
        "adherence": normalized_context.get("adherence", {}),
        "tsb": {
            "current_tsb": (normalized_context.get("tsb") or {}).get("current_tsb"),
            "current_ctl": (normalized_context.get("tsb") or {}).get("current_ctl"),
            "current_atl": (normalized_context.get("tsb") or {}).get("current_atl"),
            "verdict": (normalized_context.get("tsb") or {}).get("verdict"),
            "state": (normalized_context.get("tsb") or {}).get("state"),
        },
        "ef_status": {
            "status": (normalized_context.get("ef_status") or {}).get("status"),
            "recent_ef": (normalized_context.get("ef_status") or {}).get("recent_ef"),
            "change": (normalized_context.get("ef_status") or {}).get("change"),
            "verdict": (normalized_context.get("ef_status") or {}).get("verdict"),
        },
        "top_prediction": recommendations.get("top_prediction", {}),
        "recommendations": {
            "load_focus": recommendations.get("load_focus"),
            "intensity_bias": recommendations.get("intensity_bias"),
            "recovery_priority": recommendations.get("recovery_priority"),
            "risk_flags": recommendations.get("risk_flags", []),
            "performance_note": recommendations.get("performance_note"),
        },
        "acwr": acwr_snapshot.get("acwr"),
        "acwr_status": acwr_snapshot.get("status"),
        "acwr_message": acwr_snapshot.get("message"),
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _render_diagnostic_cards(recommendations: dict, acwr_snapshot: dict):
    st.markdown("### 🧪 Diagnóstico Técnico")

    card_cols = st.columns(4)
    with card_cols[0]:
        render_hud_metric(
            "Foco de Carga",
            recommendations.get("load_focus", "N/A"),
            subtitle="Estrategia semanal",
            tone="cyan",
        )
    with card_cols[1]:
        render_hud_metric(
            "Intensidad",
            recommendations.get("intensity_bias", "N/A"),
            subtitle="Distribución sugerida",
            tone="lime",
        )
    with card_cols[2]:
        render_hud_metric(
            "Recuperación",
            recommendations.get("recovery_priority", "N/A"),
            subtitle="Prioridad fisiológica",
            tone="amber",
        )
    with card_cols[3]:
        risk_count = len(recommendations.get("risk_flags", []))
        tone = "red" if risk_count else "slate"
        render_hud_metric(
            "Riesgos",
            str(risk_count),
            subtitle="Señales activas",
            tone=tone,
        )

    if acwr_snapshot.get("acwr", 0.0) > 1.5:
        st.error("Diagnóstico Crítico: El Coach IA priorizará el descanso")
    elif acwr_snapshot.get("status") in {"caution", "danger"}:
        render_status_badge(acwr_snapshot.get("message", "Revisar carga"), tone="warning", icon="⚠")
    else:
        render_status_badge(acwr_snapshot.get("message", "Carga bajo control"), tone="success", icon="✓")

    risk_flags = recommendations.get("risk_flags", [])
    if risk_flags:
        st.markdown("#### Señales de riesgo")
        for flag in risk_flags:
            st.markdown(f"- {flag}")

    st.markdown("#### Claves del diagnóstico")
    st.markdown(f"- Nota fisiológica: {recommendations.get('performance_note', 'N/A')}")
    st.markdown(f"- Guardrails: {' | '.join(recommendations.get('guardrails', []))}")

    top_prediction = recommendations.get("top_prediction") or {}
    if top_prediction:
        st.markdown("#### Proyección base")
        st.markdown(
            f"- {top_prediction.get('Distancia', 'N/A')}: {top_prediction.get('Tiempo Estimado', 'N/A')} ({top_prediction.get('Ritmo Objetivo', 'N/A')})"
        )


def render_ai_tab(state, filtered_data):
    st.subheader("🤖 Coach IA — Planificación Personalizada")
    st.caption("Ajusta tu microciclo semanal considerando tus sensaciones, VDOT y nivel de fatiga.")

    if state.get("prompt_sugerido_ia"):
        render_status_badge(f"Consulta pendiente: {state['prompt_sugerido_ia']}", tone="info", icon="i")
        if st.button("🧹 Limpiar sugerencia", key="btn_limpiar_sugerencia_ia"):
            state["prompt_sugerido_ia"] = ""
            st.rerun()

    if state.get("current_ai_plan"):
        plan_words = len(state["current_ai_plan"].split())
        ai_summary_cols = st.columns(2)
        with ai_summary_cols[0]:
            render_hud_metric("Plan Activo", f"{plan_words} palabras", subtitle="Contenido generado por IA", tone="lime")
        with ai_summary_cols[1]:
            render_status_badge("Plan disponible para descarga o guardado", tone="success", icon="✓")

    st.markdown("### 📝 Formulario de sensaciones")
    with st.form("form_coach_ia"):
        col_form_1, col_form_2 = st.columns(2)

        with col_form_1:
            fatigue_rpe = st.slider(
                "Fatiga percibida (1-10)",
                min_value=1,
                max_value=10,
                value=int(state.get("feedback_data", {}).get("fatigue_rpe", 3)),
            )
            sleep_quality = st.select_slider(
                "Calidad del sueño",
                options=["Mala", "Regular", "Buena", "Excelente"],
                value=state.get("feedback_data", {}).get("sleep_quality", "Buena"),
            )

        with col_form_2:
            stress_level = st.selectbox(
                "Estrés externo",
                options=["Bajo", "Moderado", "Alto"],
                index=["Bajo", "Moderado", "Alto"].index(state.get("feedback_data", {}).get("stress_level", "Moderado")),
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
                default=state.get("feedback_data", {}).get("discomforts", ["Ninguna"]),
            )

        user_notes = st.text_area(
            "Notas adicionales",
            value=state.get("feedback_data", {}).get("notes", ""),
            placeholder="Ej: El rodaje del martes se sintió pesado o tengo poco tiempo para entrenar...",
            height=100,
        )

        update_diagnostic = st.form_submit_button("Actualizar diagnóstico", type="primary")

    if update_diagnostic:
        state["feedback_data"] = {
            "fatigue_rpe": fatigue_rpe,
            "sleep_quality": sleep_quality,
            "stress_level": stress_level,
            "discomforts": discomforts,
            "notes": user_notes,
        }
        state["ai_diagnostic_reviewed"] = False
        state["ai_diagnostic_review_ack"] = False
        state["ai_diagnostic_signature"] = ""

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
    today_acwr = calculate_acwr(filtered_data)
    normalized_context = build_coach_context(
        metrics_summary=metrics_summary,
        df=filtered_data,
        feedback_data=state.get("feedback_data", None),
        vdot_actual=vdot_real,
        saved_plans=load_all_plans(),
    )
    recommendations = generate_training_recommendations(normalized_context)
    diagnostic_signature = _context_signature(normalized_context, recommendations, today_acwr)

    if state.get("ai_diagnostic_signature") != diagnostic_signature:
        state["ai_diagnostic_signature"] = diagnostic_signature
        state["ai_diagnostic_reviewed"] = False

    _render_diagnostic_cards(recommendations, today_acwr)

    review_cols = st.columns([1.2, 1.0])
    with review_cols[0]:
        reviewed = st.checkbox(
            "He revisado el diagnóstico y autorizo la generación del plan",
            key="ai_diagnostic_review_ack",
        )
        state["ai_diagnostic_reviewed"] = reviewed
    with review_cols[1]:
        st.caption("El plan sólo se habilita cuando confirmas la revisión del diagnóstico actual.")

    prompt_preview = build_llm_prompt(normalized_context)
    with st.expander("Ver prompt técnico normalizado", expanded=False):
        st.code(prompt_preview, language="markdown")

    generate_plan = st.button(
        "⚡ Generar Plan Semanal con IA",
        type="primary",
        use_container_width=True,
        disabled=not state.get("ai_diagnostic_reviewed", False),
    )

    if not state.get("ai_diagnostic_reviewed", False):
        st.info("Revisa el diagnóstico y marca la casilla para habilitar la generación del plan.")

    if generate_plan:
        with st.spinner("Sintetizando sensaciones, VDOT y cargas para crear el plan..."):
            generated_text = ask_ai_coach(
                metrics_summary=metrics_summary,
                df=filtered_data,
                feedback_data=state.get("feedback_data", None),
                vdot_actual=vdot_real,
                normalized_context=normalized_context,
            )
            state["current_ai_plan"] = generated_text

    if state.get("current_ai_plan"):
        st.markdown("---")
        st.markdown("### 📄 Plan Semanal Generado")

        col_actions1, col_actions2 = st.columns(2)

        with col_actions1:
            st.download_button(
                label="📥 Descargar Plan (.md)",
                data=state["current_ai_plan"],
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
                    plan_markdown=state["current_ai_plan"],
                    feedback_atleta=state.get("feedback_data", {}),
                )
                render_status_badge(f"Plan guardado exitosamente (ID: {saved_record['id']}).", tone="success", icon="✓")

        st.markdown(state["current_ai_plan"])

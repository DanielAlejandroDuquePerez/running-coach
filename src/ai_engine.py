"""
Motor lógico puro para análisis y recomendaciones de entrenamiento.
No depende de Streamlit ni de clientes externos de IA.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any

import pandas as pd

from src.config import TARGET_10K_TIME_MIN, WEEKLY_KM_TARGET
from src.metrics import (
    aerobic_efficiency_status,
    calculate_tsb_metrics,
    evaluate_stress_balance,
    predict_race_times,
)


@dataclass
class CoachContext:
    weekly_km: str
    avg_pace: str
    zone_distribution: Any
    vdot_actual: float
    alert_message: str
    weekly_km_raw: float
    tsb: dict[str, Any] | None
    ef_status: dict[str, Any] | None
    race_data: dict[str, Any] | None
    feedback: dict[str, Any] | None
    adherence: dict[str, Any] | None


def _sanitize_weekly_km(raw_weekly_km: float) -> str:
    if raw_weekly_km > 180:
        return f"Meta base de {WEEKLY_KM_TARGET} km/semana (Acumulado histórico en CSV: {raw_weekly_km:.1f} km)"
    return f"{raw_weekly_km:.1f} km"


def _normalize_feedback(feedback_data: dict | None) -> dict[str, Any]:
    if not feedback_data:
        return {
            "fatigue_rpe": "N/A",
            "sleep_quality": "N/A",
            "stress_level": "N/A",
            "notes": "",
            "discomforts": ["Ninguna"],
        }

    raw_molestias = feedback_data.get("discomforts") or feedback_data.get("molestias") or ["Ninguna"]
    molestias = ", ".join(raw_molestias) if isinstance(raw_molestias, list) else str(raw_molestias)

    return {
        "fatigue_rpe": feedback_data.get("fatigue_rpe") or feedback_data.get("rpe_fatiga") or "N/A",
        "sleep_quality": feedback_data.get("sleep_quality") or feedback_data.get("sueño") or "N/A",
        "stress_level": feedback_data.get("stress_level") or feedback_data.get("estres") or "N/A",
        "notes": feedback_data.get("notes") or feedback_data.get("notas") or "",
        "discomforts": raw_molestias,
        "discomforts_text": molestias,
    }


def _normalize_adherence(saved_plans: list[dict[str, Any]] | None) -> dict[str, Any] | None:
    if not saved_plans:
        return None

    last_plan = saved_plans[0]
    diario = last_plan.get("diario_sesiones", [])
    dias_cumplidos = [s["Día"] for s in diario if isinstance(s, dict) and s.get("Completado", False)]

    return {
        "last_pct": last_plan.get("adherencia_pct", 0),
        "estado": last_plan.get("estado", "N/A"),
        "notas_previas": last_plan.get("notas_seguimiento", "Sin observaciones"),
        "dias_cumplidos": dias_cumplidos,
    }


def build_coach_context(
    metrics_summary: dict,
    df: pd.DataFrame | None = None,
    feedback_data: dict | None = None,
    vdot_actual: float = 55.0,
    tsb_data: dict | None = None,
    ef_status: dict | None = None,
    race_data: dict | None = None,
    saved_plans: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Construye un contexto estructurado, independiente de la UI, para el coach."""
    raw_weekly_km = float(metrics_summary.get("weekly_km", 0) or 0)
    weekly_km_str = _sanitize_weekly_km(raw_weekly_km)
    avg_pace = metrics_summary.get("avg_pace", "N/A")
    zone_dist = metrics_summary.get("zone_distribution", {})

    alerta_actual = {"message": "N/A"}
    if df is not None and not df.empty:
        alerta_actual = evaluate_stress_balance(df)
        if tsb_data is None:
            tsb_data = calculate_tsb_metrics(df)
        if ef_status is None:
            ef_status = aerobic_efficiency_status(df)
        if race_data is None:
            race_data = predict_race_times(df)

    return asdict(
        CoachContext(
            weekly_km=weekly_km_str,
            avg_pace=avg_pace,
            zone_distribution=zone_dist,
            vdot_actual=vdot_actual,
            alert_message=alerta_actual.get("message", "N/A"),
            weekly_km_raw=raw_weekly_km,
            tsb=tsb_data,
            ef_status=ef_status,
            race_data=race_data,
            feedback=_normalize_feedback(feedback_data),
            adherence=_normalize_adherence(saved_plans),
        )
    )


def generate_training_recommendations(context: dict[str, Any]) -> dict[str, Any]:
    """Genera recomendaciones deterministas basadas en el contexto técnico."""
    weekly_km_raw = float(context.get("weekly_km_raw", 0) or 0)
    alert_message = str(context.get("alert_message", "N/A"))
    feedback = context.get("feedback") or {}
    adherence = context.get("adherence") or {}
    tsb = context.get("tsb") or {}
    ef_status = context.get("ef_status") or {}
    race_data = context.get("race_data") or {}

    risk_flags: list[str] = []
    load_focus = "Desarrollo equilibrado"
    intensity_bias = "80% fácil / 20% calidad"
    recovery_priority = "Moderada"

    if weekly_km_raw > WEEKLY_KM_TARGET * 1.25:
        risk_flags.append("Volumen semanal por encima de la referencia base")
        load_focus = "Descarga parcial"
        intensity_bias = "90% fácil / 10% calidad"
        recovery_priority = "Alta"
    elif weekly_km_raw < WEEKLY_KM_TARGET * 0.75:
        risk_flags.append("Volumen semanal por debajo del estímulo de base")
        load_focus = "Construcción progresiva"
        intensity_bias = "75% fácil / 25% calidad"
        recovery_priority = "Moderada"

    if "Sobrecarga" in alert_message or "Riesgo" in alert_message:
        risk_flags.append("Alerta de estrés de carga detectada")
        load_focus = "Control de carga"
        intensity_bias = "85% fácil / 15% calidad"
        recovery_priority = "Alta"

    if tsb and tsb.get("current_tsb") is not None and tsb.get("current_tsb", 0) < -10:
        risk_flags.append("TSB negativo: fatiga acumulada alta")
        load_focus = "Recuperación y asimilación"
        intensity_bias = "90% fácil / 10% calidad"
        recovery_priority = "Muy alta"

    if feedback.get("fatigue_rpe") not in (None, "N/A"):
        try:
            if float(feedback["fatigue_rpe"]) >= 7:
                risk_flags.append("Fatiga percibida elevada")
                recovery_priority = "Muy alta"
        except (TypeError, ValueError):
            pass

    if adherence:
        try:
            last_pct = float(adherence.get("last_pct", 0) or 0)
            if last_pct < 70:
                risk_flags.append("Adherencia previa insuficiente")
                load_focus = "Simplificación del microciclo"
        except (TypeError, ValueError):
            pass

    if ef_status.get("status") == "success" and ef_status.get("change", 0) > 0:
        performance_note = "La eficiencia aeróbica está mejorando."
    elif ef_status.get("status") == "success":
        performance_note = "La eficiencia aeróbica está estable."
    else:
        performance_note = "No hay suficiente información de eficiencia aeróbica."

    if race_data and isinstance(race_data.get("predictions"), pd.DataFrame):
        top_prediction = race_data["predictions"].iloc[0].to_dict() if not race_data["predictions"].empty else {}
    else:
        top_prediction = {}

    plan_guardrails = [
        f"Mantener {int(WEEKLY_KM_TARGET)} km/semana como referencia base.",
        "Evitar acumular más de dos sesiones duras consecutivas.",
        "Proteger los rodajes suaves como base adaptativa.",
    ]

    if feedback.get("sleep_quality") in {"Mala", "Regular"}:
        risk_flags.append("Sueño insuficiente reportado")
        recovery_priority = "Muy alta"

    return {
        "load_focus": load_focus,
        "intensity_bias": intensity_bias,
        "recovery_priority": recovery_priority,
        "risk_flags": risk_flags,
        "performance_note": performance_note,
        "guardrails": plan_guardrails,
        "top_prediction": top_prediction,
        "vdot_actual": context.get("vdot_actual", 55.0),
        "weekly_km": context.get("weekly_km", "N/A"),
        "avg_pace": context.get("avg_pace", "N/A"),
        "zone_distribution": context.get("zone_distribution", {}),
        "alert_message": alert_message,
        "feedback": feedback,
        "adherence": adherence,
        "tsb": tsb,
        "ef_status": ef_status,
        "race_data": race_data,
    }


def build_coach_prompt_from_context(context: dict[str, Any], target_10k_time_min: float = TARGET_10K_TIME_MIN) -> str:
    """Convierte el contexto y recomendaciones en un prompt estructurado."""
    recommendations = generate_training_recommendations(context)
    feedback = context.get("feedback") or {}
    adherence = context.get("adherence") or {}
    tsb = context.get("tsb") or {}
    ef_status = context.get("ef_status") or {}
    race_data = context.get("race_data") or {}

    tsb_section = ""
    if tsb:
        tsb_section = f"""
        BALANCE DE CARGA Y FRESCURA (Modelo TSB):
        - Forma Física (CTL): {tsb.get('current_ctl', 'N/A')} km/día
        - Fatiga Reciente (ATL): {tsb.get('current_atl', 'N/A')} km/día
        - Balance de Frescura (TSB): {tsb.get('current_tsb', 'N/A')} ({tsb.get('verdict', 'N/A')})
        """

    ef_section = ""
    if ef_status and ef_status.get("status") == "success":
        ef_section = f"""
        EFICIENCIA AERÓBICA (EF):
        - Factor de Eficiencia Reciente: {ef_status.get('recent_ef', 'N/A')}
        - Diagnóstico EF: {ef_status.get('verdict', 'N/A')}
        """

    riegel_section = ""
    if race_data and "predictions" in race_data and isinstance(race_data["predictions"], pd.DataFrame):
        preds = [
            f"{row['Distancia']}: {row['Tiempo Estimado']} ({row['Ritmo Objetivo']})"
            for _, row in race_data["predictions"].iterrows()
        ]
        riegel_section = f"""
        PROYECCIONES DE RENDIMIENTO (Modelo Riegel):
        - {"; ".join(preds)}
        """

    qualitative_section = f"""
    ESTADO CUALITATIVO ACTUAL (Check-in de esta semana):
    - Fatiga percibida (RPE 1-10): {feedback.get('fatigue_rpe', 'N/A')}
    - Calidad del sueño: {feedback.get('sleep_quality', 'N/A')}
    - Nivel de estrés externo: {feedback.get('stress_level', 'N/A')}
    - Molestias físicas reportadas: {feedback.get('discomforts_text', 'Ninguna')}
    - Notas adicionales del atleta: "{feedback.get('notes', '')}"
    """

    adherence_section = "\nHISTORIAL Y ADHERENCIA: Sin historial previo cargado."
    if adherence:
        adherence_section = f"""
        HISTORIAL Y ADHERENCIA DE LA SEMANA ANTERIOR:
        - Porcentaje de Cumplimiento: {adherence.get('last_pct', 0)}% (Estado: {adherence.get('estado', 'N/A')})
        - Días Cumplidos Exitosamente: {", ".join(adherence.get('dias_cumplidos', [])) if adherence.get('dias_cumplidos') else "Ninguno registrado"}
        - Observaciones del atleta sobre la semana previa: "{adherence.get('notas_previas', 'Sin observaciones')}"
        """

    recommendations = generate_training_recommendations(context)

    prompt = f"""
    Actúa como un Entrenador de Atletismo de Élite experto en Fisiología del Deporte, Entrenamiento Polarizado (80/20) y Metodología de Jack Daniels (VDOT).

    PERFIL Y MÉTRICAS ACTUALES DEL ATLETA:
    - Volumen semanal de referencia: {context.get('weekly_km', 'N/A')} (Meta base objetivo: {WEEKLY_KM_TARGET} km)
    - Ritmo promedio habitual: {context.get('avg_pace', 'N/A')} min/km
    - Índice VDOT actual: {context.get('vdot_actual', 55.0)}
    - Distribución por zonas de esfuerzo: {context.get('zone_distribution', {})}
    - Evaluación de estrés de carga: {context.get('alert_message', 'N/A')}
    {tsb_section}
    {ef_section}
    {riegel_section}
    {qualitative_section}
    {adherence_section}

    REGLAS DE DECISIÓN BASEADAS EN EL CONTEXTO:
    - Foco de carga: {recommendations['load_focus']}
    - Sesgo de intensidad recomendado: {recommendations['intensity_bias']}
    - Prioridad de recuperación: {recommendations['recovery_priority']}
    - Señales de riesgo: {", ".join(recommendations['risk_flags']) if recommendations['risk_flags'] else "Sin señales de riesgo adicionales"}
    - Nota fisiológica: {recommendations['performance_note']}

    OBJETIVOS DEL ATLETA:
    - Optimizar economía de carrera y prevenir lesiones por sobrecarga.
    - Preparación progresiva para mejorar la marca en 10K (Objetivo: sub-{target_10k_time_min} min) y afinar detalles para los 15K del "Reto Rosa" en Roldanillo durante octubre.

    REGLAS ESTRICTAS DE ANÁLISIS:
    1. NO inventes "errores de GPS" ni anomalías de lectura en los datos a menos que el usuario lo mencione en sus notas.
    2. Considera que el volumen objetivo semanal del atleta es de ~{WEEKLY_KM_TARGET} km y planifica los entrenamientos en torno a este número.

    INSTRUCCIONES DE RESPUESTA:
    Genera un informe analítico completo y un **Plan de Entrenamiento Semanal Detallado**, estructurado rigurosamente en Markdown con las siguientes 4 secciones:

    ### 1. 📊 Diagnóstico Fisiológico y Evaluación de Adherencia Previa
    - Evalúa el estado actual considerando las métricas de carga, TSB, VDOT y la adherencia lograda en la semana anterior.

    ### 2. 🎯 Foco Táctico de la Semana
    - Define el objetivo principal de la semana en función de las molestias físicas, el RPE y el cumplimiento previo.

    ### 3. 🗓️ Plan de Entrenamiento Semanal (Lunes a Domingo)
    Presenta una **tabla en Markdown** ordenada con las columnas: `| Día | Tipo de Sesión | Estructura / Distancia | Ritmo / Zona VDOT | Propósito Fisiológico |`.
    - Ajusta las cargas con ritmos objetivos exactos basados en el VDOT actual ({context.get('vdot_actual', 55.0)}).

    ### 4. ⚠️ Pautas de Prevención y Recomendaciones
    - Indicaciones específicas sobre prevención de molestias y recuperación.
    """
    return prompt

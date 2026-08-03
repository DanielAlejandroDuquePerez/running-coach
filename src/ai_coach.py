"""
Módulo para la integración con la API de Google GenAI (Gemini).
"""

import os
import pandas as pd
from dotenv import load_dotenv
from google import genai
from src.config import WEEKLY_KM_TARGET, TARGET_10K_TIME_MIN
from src.storage import load_all_plans
from src.metrics import (
    evaluate_stress_balance,
    calculate_tsb_metrics,
    aerobic_efficiency_status,
    predict_race_times,
)

# Cargar las variables definidas en el archivo .env
load_dotenv()


def get_genai_client() -> genai.Client:
    """Inicializa y retorna el cliente oficial de Gemini comprobando la API Key."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError(
            "No se encontró la 'GEMINI_API_KEY'. Asegúrate de configurarla en el archivo .env"
        )
    return genai.Client(api_key=api_key)


def build_coach_prompt(
    metrics_summary: dict,
    df: pd.DataFrame = None,
    feedback_data: dict = None,
    vdot_actual: float = 55.0,
    tsb_data: dict = None,
    ef_status: dict = None,
    race_data: dict = None,
) -> str:
    """
    Construye un prompt técnico enviando el contexto cuantitativo,
    fisiológico y cualitativo del atleta para solicitar un plan semanal integral.
    """
    # 1. Sanitización de Kilometraje Semanal
    raw_weekly_km = metrics_summary.get("weekly_km", 0)
    
    # Cortafuegos: Si el valor recibido supera los 180 km, se trata del acumulado histórico total
    if raw_weekly_km > 180:
        weekly_km_str = f"Meta base de {WEEKLY_KM_TARGET} km/semana (Acumulado histórico en CSV: {raw_weekly_km:.1f} km)"
    else:
        weekly_km_str = f"{raw_weekly_km:.1f} km"

    avg_pace = metrics_summary.get("avg_pace", "N/A")
    zone_dist = metrics_summary.get("zone_distribution", {})

    # Extracción de métricas avanzadas si se pasa el DataFrame
    if df is not None:
        alerta_actual = evaluate_stress_balance(df)
        if tsb_data is None:
            tsb_data = calculate_tsb_metrics(df)
        if ef_status is None:
            ef_status = aerobic_efficiency_status(df)
        if race_data is None:
            race_data = predict_race_times(df)
    else:
        alerta_actual = {"message": "N/A"}

    # Bloque TSB (Frescura/Fatiga)
    tsb_section = ""
    if tsb_data:
        tsb_section = f"""
        BALANCE DE CARGA Y FRESCURA (Modelo TSB):
        - Forma Física (CTL): {tsb_data.get('current_ctl', 'N/A')} km/día
        - Fatiga Reciente (ATL): {tsb_data.get('current_atl', 'N/A')} km/día
        - Balance de Frescura (TSB): {tsb_data.get('current_tsb', 'N/A')} ({tsb_data.get('verdict', 'N/A')})
        """

    # Bloque EF (Eficiencia Aeróbica)
    ef_section = ""
    if ef_status and ef_status.get("status") == "success":
        ef_section = f"""
        EFICIENCIA AERÓBICA (EF):
        - Factor de Eficiencia Reciente: {ef_status.get('recent_ef', 'N/A')}
        - Diagnóstico EF: {ef_status.get('verdict', 'N/A')}
        """

    # Bloque Riegel (Predicciones)
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

    # Bloque cualitativo (Check-in del Atleta)
    if feedback_data:
        fatiga = feedback_data.get('fatigue_rpe') or feedback_data.get('rpe_fatiga') or 'N/A'
        sueno = feedback_data.get('sleep_quality') or feedback_data.get('sueño') or 'N/A'
        estres = feedback_data.get('stress_level') or feedback_data.get('estres') or 'N/A'
        notas = feedback_data.get('notes') or feedback_data.get('notas') or ''

        raw_molestias = feedback_data.get('discomforts') or feedback_data.get('molestias') or ["Ninguna"]
        molestias = ", ".join(raw_molestias) if isinstance(raw_molestias, list) else str(raw_molestias)

        qualitative_section = f"""
        ESTADO CUALITATIVO ACTUAL (Check-in de esta semana):
        - Fatiga percibida (RPE 1-10): {fatiga}
        - Calidad del sueño: {sueno}
        - Nivel de estrés externo: {estres}
        - Molestias físicas reportadas: {molestias}
        - Notas adicionales del atleta: "{notas}"
        """
    else:
        qualitative_section = "\nESTADO CUALITATIVO ACTUAL: No se proporcionó check-in esta semana."

    # Bloque de Adherencia e Historial
    saved_plans = load_all_plans()
    adherencia_section = ""
    last_pct = 0
    if saved_plans:
        last_plan = saved_plans[0]
        last_pct = last_plan.get("adherencia_pct", 0)
        estado = last_plan.get("estado", "N/A")
        notas_previas = last_plan.get("notas_seguimiento", "Sin observaciones")
        
        diario = last_plan.get("diario_sesiones", [])
        dias_cumplidos = [s["Día"] for s in diario if isinstance(s, dict) and s.get("Completado", False)]
        
        adherencia_section = f"""
        HISTORIAL Y ADHERENCIA DE LA SEMANA ANTERIOR:
        - Porcentaje de Cumplimiento: {last_pct}% (Estado: {estado})
        - Días Cumplidos Exitosamente: {", ".join(dias_cumplidos) if dias_cumplidos else "Ninguno registrado"}
        - Observaciones del atleta sobre la semana previa: "{notas_previas}"
        """

    prompt = f"""
    Actúa como un Entrenador de Atletismo de Élite experto en Fisiología del Deporte, Entrenamiento Polarizado (80/20) y Metodología de Jack Daniels (VDOT).

    PERFIL Y MÉTRICAS ACTUALES DEL ATLETA:
    - Volumen semanal de referencia: {weekly_km_str} (Meta base objetivo: {WEEKLY_KM_TARGET} km)
    - Ritmo promedio habitual: {avg_pace} min/km
    - Índice VDOT actual: {vdot_actual}
    - Distribución por zonas de esfuerzo: {zone_dist}
    - Evaluación de estrés de carga: {alerta_actual.get('message', 'N/A')}
    {tsb_section}
    {ef_section}
    {riegel_section}
    {qualitative_section}
    {adherencia_section}

    OBJETIVOS DEL ATLETA:
    - Optimizar economía de carrera y prevenir lesiones por sobrecarga.
    - Preparación progresiva para mejorar la marca en 10K (Objetivo: sub-{TARGET_10K_TIME_MIN} min) y afinar detalles para los 15K del "Reto Rosa" en Roldanillo durante octubre.

    REGLAS ESTRICTAS DE ANÁLISIS:
    1. NO inventes "errores de GPS" ni anomalías de lectura en los datos a menos que el usuario lo mencione en sus notas.
    2. Considera que el volumen objetivo semanal del atleta es de ~{WEEKLY_KM_TARGET} km y planifica los entrenamientos en torno a este número.

    INSTRUCCIONES DE RESPUESTA:
    Genera un informe analítico completo y un **Plan de Entrenamiento Semanal Detallado**, estructurado rigurosamente en Markdown con las siguientes 4 secciones:

    ### 1. 📊 Diagnóstico Fisiológico y Evaluación de Adherencia Previa
    - Evalúa el estado actual considerando las métricas de carga, TSB, VDOT y la adherencia lograda en la semana anterior ({last_pct}%).

    ### 2. 🎯 Foco Táctico de la Semana
    - Define el objetivo principal de la semana en función de las molestias físicas, el RPE y el cumplimiento previo.

    ### 3. 🗓️ Plan de Entrenamiento Semanal (Lunes a Domingo)
    Presenta una **tabla en Markdown** ordenada con las columnas: `| Día | Tipo de Sesión | Estructura / Distancia | Ritmo / Zona VDOT | Propósito Fisiológico |`.
    - Ajusta las cargas con ritmos objetivos exactos basados en el VDOT actual ({vdot_actual}).

    ### 4. ⚠️ Pautas de Prevención y Recomendaciones
    - Indicaciones específicas sobre prevención de molestias y recuperación.
    """
    return prompt


def ask_ai_coach(
    metrics_summary: dict,
    df: pd.DataFrame = None,
    feedback_data: dict = None,
    vdot_actual: float = 55.0,
    tsb_data: dict = None,
    ef_status: dict = None,
    race_data: dict = None,
) -> str:
    """
    Orquesta la consulta a la API de Gemini enviando el contexto completo,
    retornando la planificación semanal estructurada en texto Markdown.
    """
    try:
        client = get_genai_client()
        prompt = build_coach_prompt(
            metrics_summary=metrics_summary,
            df=df,
            feedback_data=feedback_data,
            vdot_actual=vdot_actual,
            tsb_data=tsb_data,
            ef_status=ef_status,
            race_data=race_data,
        )

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        return response.text
    except Exception as e:
        return f"Error al conectar con el Entrenador Virtual: {str(e)}"
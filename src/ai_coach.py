"""
Módulo para la integración con la API de Google GenAI (Gemini).
"""

import os
import pandas as pd
from dotenv import load_dotenv
from google import genai
from src.storage import load_all_plans
from src.ai_engine import build_coach_context, build_coach_prompt_from_context

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


def build_llm_prompt(normalized_context: dict) -> str:
    """Construye el prompt LLM usando únicamente un contexto ya normalizado."""
    return build_coach_prompt_from_context(normalized_context)


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
    Construye un prompt técnico usando el motor lógico independiente de la UI.
    """
    normalized_context = build_coach_context(
        metrics_summary=metrics_summary,
        df=df,
        feedback_data=feedback_data,
        vdot_actual=vdot_actual,
        tsb_data=tsb_data,
        ef_status=ef_status,
        race_data=race_data,
        saved_plans=load_all_plans(),
    )
    return build_llm_prompt(normalized_context)


def ask_ai_coach(
    metrics_summary: dict,
    df: pd.DataFrame = None,
    feedback_data: dict = None,
    vdot_actual: float = 55.0,
    tsb_data: dict = None,
    ef_status: dict = None,
    race_data: dict = None,
    normalized_context: dict | None = None,
) -> str:
    """
    Orquesta la consulta a la API de Gemini enviando el contexto completo,
    retornando la planificación semanal estructurada en texto Markdown.
    """
    try:
        client = get_genai_client()
        if normalized_context is None:
            normalized_context = build_coach_context(
                metrics_summary=metrics_summary,
                df=df,
                feedback_data=feedback_data,
                vdot_actual=vdot_actual,
                tsb_data=tsb_data,
                ef_status=ef_status,
                race_data=race_data,
                saved_plans=load_all_plans(),
            )

        prompt = build_llm_prompt(normalized_context)

        response = client.models.generate_content(
            model="gemini-flash-latest",
            contents=prompt,
        )
        return response.text
    except Exception as e:
        return f"Error al conectar con el Entrenador Virtual: {str(e)}"
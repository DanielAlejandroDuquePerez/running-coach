"""
Módulo de Persistencia de Datos para Planes Semanales y Diario del Atleta.
"""

import json
import os
from datetime import datetime

DATA_DIR = "data"
PLANS_FILE = os.path.join(DATA_DIR, "weekly_plans.json")

# Estructura base para el diario semanal de 7 días
DEFAULT_DAILY_LOG = [
    {"Día": "Lunes", "Tipo / Prescripción": "Descanso Activo / Rodaje Z1", "Completado": False, "Km Real": 0.0, "RPE (1-10)": 1, "Sensaciones / Notas": ""},
    {"Día": "Martes", "Tipo / Prescripción": "Calidad / Series / Tempo", "Completado": False, "Km Real": 0.0, "RPE (1-10)": 1, "Sensaciones / Notas": ""},
    {"Día": "Miércoles", "Tipo / Prescripción": "Rodaje Regenerativo Z1-Z2", "Completado": False, "Km Real": 0.0, "RPE (1-10)": 1, "Sensaciones / Notas": ""},
    {"Día": "Jueves", "Tipo / Prescripción": "Rodaje de Estabilidad Z2", "Completado": False, "Km Real": 0.0, "RPE (1-10)": 1, "Sensaciones / Notas": ""},
    {"Día": "Viernes", "Tipo / Prescripción": "Descanso Total / Movilidad", "Completado": False, "Km Real": 0.0, "RPE (1-10)": 1, "Sensaciones / Notas": ""},
    {"Día": "Sábado", "Tipo / Prescripción": "Calidad Corta / Ritmo Objetivo", "Completado": False, "Km Real": 0.0, "RPE (1-10)": 1, "Sensaciones / Notas": ""},
    {"Día": "Domingo", "Tipo / Prescripción": "Tirada Larga (Long Run)", "Completado": False, "Km Real": 0.0, "RPE (1-10)": 1, "Sensaciones / Notas": ""}
]


def _ensure_data_dir_exists():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)


def load_all_plans() -> list:
    _ensure_data_dir_exists()
    if not os.path.exists(PLANS_FILE):
        return []

    try:
        with open(PLANS_FILE, "r", encoding="utf-8") as f:
            plans = json.load(f)
            # Asegurar compatibilidad si algún plan no tenía el diario diario
            for p in plans:
                if "diario_sesiones" not in p or not p["diario_sesiones"]:
                    p["diario_sesiones"] = DEFAULT_DAILY_LOG
            return plans
    except Exception as e:
        print(f"Error al cargar planes: {e}")
        return []


def save_new_plan(vdot: float, km_objetivo: float, plan_markdown: str, feedback_atleta: dict = None) -> dict:
    _ensure_data_dir_exists()
    plans = load_all_plans()

    new_entry = {
        "id": f"plan_{int(datetime.now().timestamp())}",
        "fecha_creacion": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "vdot_base": vdot,
        "km_objetivo": km_objetivo,
        "plan_markdown": plan_markdown,
        "feedback_inicial": feedback_atleta or {},
        "estado": "En Curso",
        "adherencia_pct": 0,
        "notas_seguimiento": "",
        "diario_sesiones": DEFAULT_DAILY_LOG  # 👈 Guardamos los 7 días listos para llenar
    }

    plans.insert(0, new_entry)

    with open(PLANS_FILE, "w", encoding="utf-8") as f:
        json.dump(plans, f, ensure_ascii=False, indent=4)

    return new_entry


def update_full_plan(plan_id: str, estado: str, adherencia: int, notas: str, diario_sesiones: list) -> bool:
    """Actualiza el estado general, % de adherencia y la tabla del diario de sesiones."""
    plans = load_all_plans()
    updated = False

    for plan in plans:
        if plan["id"] == plan_id:
            plan["estado"] = estado
            plan["adherencia_pct"] = adherencia
            plan["notas_seguimiento"] = notas
            plan["diario_sesiones"] = diario_sesiones
            updated = True
            break

    if updated:
        with open(PLANS_FILE, "w", encoding="utf-8") as f:
            json.dump(plans, f, ensure_ascii=False, indent=4)

    return updated
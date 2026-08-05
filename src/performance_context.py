"""
Funciones puras para readiness, estado mente-cuerpo y predicción de carrera.
"""

import pandas as pd


def calculate_training_readiness(acwr, rpe_promedio, dias_descanso_recientes=1):
    """
    Calcula un score de 0 a 100% de Predisposición al Entrenamiento.
    """
    if 0.8 <= acwr <= 1.3:
        score_acwr = 100
    elif 1.3 < acwr <= 1.5:
        score_acwr = 70
    elif acwr > 1.5:
        score_acwr = 30
    else:
        score_acwr = 85

    if rpe_promedio <= 4:
        score_rpe = 100
    elif rpe_promedio <= 6:
        score_rpe = 80
    elif rpe_promedio <= 8:
        score_rpe = 50
    else:
        score_rpe = 20

    score_rest = min(100, 50 + (dias_descanso_recientes * 25))
    readiness = (score_acwr * 0.40) + (score_rpe * 0.40) + (score_rest * 0.20)
    readiness_val = round(max(0, min(100, readiness)), 0)

    if readiness_val >= 80:
        estado = "Alto (¡Listo para entrenar fuerte!)"
        color_badge = "success"
    elif readiness_val >= 50:
        estado = "Moderado (Entrenamiento controlado)"
        color_badge = "warning"
    else:
        estado = "Bajo (Priorizar recuperación / Regenerativo)"
        color_badge = "error"

    return readiness_val, estado, color_badge


def calculate_mind_body_score(sleep_quality, mood, motivation, focus, soreness, stress_level):
    sleep_map = {
        "Mala": 35,
        "Regular": 60,
        "Buena": 80,
        "Excelente": 95,
    }
    mood_map = {
        "Muy bajo": 25,
        "Bajo": 45,
        "Neutral": 65,
        "Alto": 80,
        "Muy alto": 92,
    }
    stress_penalty_map = {
        "Bajo": 0,
        "Moderado": 10,
        "Alto": 20,
    }

    sleep_score = sleep_map.get(sleep_quality, 60)
    mood_score = mood_map.get(mood, 65)
    stress_penalty = stress_penalty_map.get(stress_level, 10)

    score = (
        sleep_score * 0.25
        + mood_score * 0.25
        + float(motivation) * 8.0
        + float(focus) * 7.0
        + (10.0 - float(soreness)) * 4.0
        - stress_penalty
    )
    return round(max(0, min(100, score)), 0)


def build_readiness_log_df(entries):
    if not entries:
        return pd.DataFrame()

    df = pd.DataFrame(entries).copy()
    if "fecha" in df.columns:
        df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
        df = df.dropna(subset=["fecha"]).sort_values("fecha")
    return df


def calculate_race_predictions(base_distance_km, base_time_min):
    """
    Calcula predicciones de tiempo para 5K, 10K, 15K y 21K usando la Fórmula de Riegel.
    """
    if base_distance_km <= 0 or base_time_min <= 0:
        return {}

    target_distances = {
        "5K": 5.0,
        "10K": 10.0,
        "15K": 15.0,
        "Media Maratón (21K)": 21.0975,
    }

    predictions = {}
    for name, d2 in target_distances.items():
        t2_min = base_time_min * ((d2 / base_distance_km) ** 1.06)
        pace_min_km = t2_min / d2
        pace_minutes = int(pace_min_km)
        pace_seconds = int((pace_min_km - pace_minutes) * 60)

        hours = int(t2_min // 60)
        mins = int(t2_min % 60)
        secs = int((t2_min - int(t2_min)) * 60)

        time_str = f"{hours:02d}:{mins:02d}:{secs:02d}" if hours > 0 else f"{mins:02d}:{secs:02d}"
        pace_str = f"{pace_minutes}:{pace_seconds:02d} min/km"

        predictions[name] = {
            "tiempo": time_str,
            "ritmo": pace_str,
        }

    return predictions
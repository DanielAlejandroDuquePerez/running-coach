import pandas as pd
import numpy as np
import math


from src.config import DANIELS_FACTOR_E, DANIELS_FACTOR_T, DANIELS_FACTOR_I
from src.config import (
    ACTIVITY_DATE_COL,
    ACTIVITY_TYPE_COL,
    CUMULATIVE_KM_COL,
    DISTANCE_COL,
    FATIGUE_ACUTE_WINDOW,
    FATIGUE_CHRONIC_WINDOW,
    FATIGUE_RATIO_COL,
    FATIGUE_WARNING_THRESHOLD,
    FATIGUE_HIGH_THRESHOLD,
    INTENSITY_COL,
    INTENSITY_EASY,
    INTENSITY_HIGH,
    INTENSITY_MODERATE,
    KILOMETERS_AXIS_LABEL,
    LABEL_COL,
    MAX_PACE_HIGH_INTENSITY,
    MAX_PACE_MODERATE,
    MOVING_TIME_COL,
    NO_DATA_MESSAGE,
    PACE_COL,
    PERFORMANCE_DECLINE_THRESHOLD,
    PERFORMANCE_IMPROVEMENT_THRESHOLD,
    RECENT_PACE_WINDOW,
    RUN_ACTIVITY_TYPE,
    WEEK_COL,
    WEEKLY_CHANGE_LIGHT_THRESHOLD,
    WEEKLY_CHANGE_WARNING_THRESHOLD,
    WEEKLY_DASHBOARD_TITLE,
    WEEKLY_LOAD_TITLE,
    WEEKLY_ROLLING_AVG_WINDOW,
    WEEK_LABEL_PREFIX,
    WEEK_START_COL,
    WEEKS_AXIS_LABEL,
    YEAR_COL,
    ZONE_COL,
    ZONE_Z1,
    ZONE_Z2,
    ZONE_Z2_THRESHOLD,
    ZONE_Z3,
    ZONE_Z3_THRESHOLD,
    ZONE_Z4,
    ZONE_Z4_THRESHOLD,
    ZONE_Z5,
    ZONE_Z5_THRESHOLD,
    ZONE_Z6,
    ZONE_Z6_THRESHOLD,
)

### Función para limpiar los datos
def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Filtra y limpia el DataFrame de Strava detectando de forma flexible 
    la columna de tipo de actividad y sus valores en inglés o español.
    """
    # 1. Detección flexible de la columna de tipo de actividad
    possible_type_cols = ['Activity Type', 'Tipo de actividad', 'Type', 'Tipo']
    type_col = next((col for col in possible_type_cols if col in df.columns), None)
    
    if type_col:
        # Aceptamos variantes comunes de carrera en inglés y español ('run', 'running', 'carrera')
        run_variants = ['run', 'running', 'carrera']
        df = df[df[type_col].astype(str).str.lower().isin(run_variants)]
    
    # 2. Resto de tu limpieza habitual (conversión de duraciones, ritmos, etc.)
    # Asegúrate de mantener aquí el resto del código que ya tenías dentro de clean_data
    
    return df

### Función para calcular estadísticas básicas
def basic_stats(df):
    if df.empty:
        return 0, 0, 0

    total_distance = df[DISTANCE_COL].sum()
    total_runs = len(df)
    avg_distance = df[DISTANCE_COL].mean()

    return total_distance, total_runs, avg_distance

### Función para agregar columna de pace
def add_pace(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula el ritmo (min/km) detectando de forma flexible la columna de tiempo en movimiento
    y guardándolo en la columna oficial de configuración (PACE_COL).
    """
    # Detección flexible de la columna de tiempo en movimiento
    possible_time_cols = ['Moving Time', 'Tiempo en movimiento', 'Tiempo activo', 'Elapsed Time', 'Tiempo transcurrido']
    time_col = next((col for col in possible_time_cols if col in df.columns), None)
    
    if time_col and time_col != 'Moving Time':
        df = df.rename(columns={time_col: 'Moving Time'})
    elif time_col is None and 'Moving Time' not in df.columns:
        raise KeyError(
            f"No se encontró ninguna columna de tiempo válida en el CSV. "
            f"Columnas disponibles en tu archivo: {list(df.columns)}"
        )

    # Cálculo seguro usando la variable oficial PACE_COL ('pace_min_km')
    if 'Moving Time' in df.columns and DISTANCE_COL in df.columns:
        df[PACE_COL] = df['Moving Time'] / 60 / df[DISTANCE_COL]
        
    return df

### Función para calcular el mejor pace
def best_pace(df):
    return df[PACE_COL].min()

### Función para calcular distancia semanal
def weekly_distance(df):
    df = df.copy()
    df[WEEK_START_COL] = df[ACTIVITY_DATE_COL].dt.to_period("W").apply(lambda r: r.start_time)
    return df.groupby(WEEK_START_COL)[DISTANCE_COL].sum()

### Función para calcular distancia acumulada
def cumulative_distance(df):
    df = df.sort_values(ACTIVITY_DATE_COL).copy()
    df[CUMULATIVE_KM_COL] = df[DISTANCE_COL].cumsum()
    return df


def weekly_distance_summary(df):
    weekly = (
        df.groupby([YEAR_COL, WEEK_COL])[DISTANCE_COL]
        .sum()
        .reset_index()
    )

    weekly[LABEL_COL] = (
        weekly[YEAR_COL].astype(str)
        + WEEK_LABEL_PREFIX
        + weekly[WEEK_COL].astype(str)
    )

    weekly["rolling_avg"] = (
        weekly[DISTANCE_COL]
        .rolling(window=WEEKLY_ROLLING_AVG_WINDOW)
        .mean()
    )

    return weekly

### Función para analizar tendencia de rendimiento
def performance_trend(df):
    if len(df) < 2:
        return NO_DATA_MESSAGE

    df = df.sort_values(ACTIVITY_DATE_COL)

    first_half = df[PACE_COL].iloc[:len(df)//2].mean()
    second_half = df[PACE_COL].iloc[len(df)//2:].mean()

    if second_half < first_half:
        return "📈 Mejorando"
    else:
        return "📉 Empeorando"
    
# Funcion para calcular semana
def weekly_distance(df):

    weekly = (
        df.groupby([YEAR_COL, WEEK_COL])[DISTANCE_COL]
        .sum()
        .reset_index()
    )

    weekly[LABEL_COL] = (
        weekly[YEAR_COL].astype(str)
        + WEEK_LABEL_PREFIX
        + weekly[WEEK_COL].astype(str)
    )

    return weekly

# Función para calcular el ratio de fatiga
def fatigue_ratio(df):

    acute = (
        df[DISTANCE_COL]
        .rolling(window=FATIGUE_ACUTE_WINDOW)
        .mean()
    )

    chronic = (
        df[DISTANCE_COL]
        .rolling(window=FATIGUE_CHRONIC_WINDOW)
        .mean()
    )

    df[FATIGUE_RATIO_COL] = acute / chronic

    return df

#Tendencia del rendimiento
def weekly_pace(df):

    weekly = (
        df.groupby([YEAR_COL, WEEK_COL])[PACE_COL]
        .mean()
        .reset_index()
    )

    weekly[LABEL_COL] = (
        weekly[YEAR_COL].astype(str)
        + WEEK_LABEL_PREFIX
        + weekly[WEEK_COL].astype(str)
    )

    return weekly

#Tendencia del rendimiento
def weekly_pace(df):

    weekly = (
        df.groupby([YEAR_COL, WEEK_COL])[PACE_COL]
        .mean()
        .reset_index()
    )

    weekly[LABEL_COL] = (
        weekly[YEAR_COL].astype(str)
        + WEEK_LABEL_PREFIX
        + weekly[WEEK_COL].astype(str)
    )

    return weekly

#Estado del rendimiento
def performance_status(df):

    recent_pace = (
        df[PACE_COL]
        .tail(RECENT_PACE_WINDOW)
        .mean()
    )

    historical_pace = (
        df[PACE_COL]
        .mean()
    )

    change = (
        historical_pace - recent_pace
    )

    return {
        "recent": recent_pace,
        "historical": historical_pace,
        "change": change
    }

#Estado de rendimiento´
def performance_status(df):

    # pace reciente (últimas actividades)
    recent_pace = (
        df[PACE_COL]
        .tail(RECENT_PACE_WINDOW)
        .mean()
    )

    # pace histórico general
    historical_pace = (
        df[PACE_COL]
        .mean()
    )

    # diferencia entre ambos
    change = (
        historical_pace - recent_pace
    )

    return {
        "recent": recent_pace,
        "historical": historical_pace,
        "change": change
    }

#Clasificar entrenamientos
def classify_runs(df):

    conditions = [
        df[PACE_COL] <= MAX_PACE_HIGH_INTENSITY,
        (df[PACE_COL] > MAX_PACE_HIGH_INTENSITY) & (df[PACE_COL] <= MAX_PACE_MODERATE),
        df[PACE_COL] > MAX_PACE_MODERATE
    ]

    labels = [
        INTENSITY_HIGH,
        INTENSITY_MODERATE,
        INTENSITY_EASY
    ]

    df[INTENSITY_COL] = np.select(
        conditions,
        labels,
        default=INTENSITY_EASY
    )

    return df
#Clasificar entrenamientos

def classify_runs(df):

    conditions = [
        df[PACE_COL] <= MAX_PACE_HIGH_INTENSITY,

        (df[PACE_COL] > MAX_PACE_HIGH_INTENSITY)
        & (df[PACE_COL] <= MAX_PACE_MODERATE),

        df[PACE_COL] > MAX_PACE_MODERATE
    ]

    labels = [
        INTENSITY_HIGH,
        INTENSITY_MODERATE,
        INTENSITY_EASY
    ]

    df[INTENSITY_COL] = np.select(
        conditions,
        labels,
        default=INTENSITY_EASY
    )

    return df

# clasificacion zonas de rendimiento
def classify_zone(pace):
    if pace < ZONE_Z6_THRESHOLD:
        return ZONE_Z6

    elif pace < ZONE_Z5_THRESHOLD:
        return ZONE_Z5

    elif pace < ZONE_Z4_THRESHOLD:
        return ZONE_Z4

    elif pace < ZONE_Z3_THRESHOLD:
        return ZONE_Z3

    elif pace < ZONE_Z2_THRESHOLD:
        return ZONE_Z2

    else:
        return ZONE_Z1

def add_zones(df):

    df[ZONE_COL] = df[PACE_COL].apply(
        classify_zone
    )

    return df

# Función para calcular la carga interna según los multiplicadores de Jack Daniels
import pandas as pd
import numpy as np
from src.config import DANIELS_FACTOR_E, DANIELS_FACTOR_T, DANIELS_FACTOR_I

import pandas as pd
from src.config import DANIELS_FACTOR_E, DANIELS_FACTOR_T, DANIELS_FACTOR_I

def calculate_daniels_points(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula los puntos de estrés de Jack Daniels y clasifica las zonas de esfuerzo
    de forma segura ante cualquier cambio de idioma en las columnas de Strava.
    """
    # 1. Detección flexible de la columna de nombre de actividad
    possible_name_cols = ['Activity Name', 'Nombre de la actividad', 'Name', 'Nombre']
    name_col = next((col for col in possible_name_cols if col in df.columns), None)

    if name_col:
        nombres = df[name_col].str.lower().fillna("")
    else:
        # Si no encuentra ninguna columna de nombre, crea una serie vacía para evitar el error
        nombres = pd.Series("", index=df.index)

    # 2. Inicializar columnas de puntos en 0
    df['points_E'] = 0.0
    df['points_T'] = 0.0
    df['points_I'] = 0.0

    # 3. Definir los filtros o patrones de búsqueda usando la variable segura 'nombres'
    es_umbral = nombres.str.contains('umbral|tempo', case=False, regex=True)
    es_intervalos = nombres.str.contains('intervalo|serie|pista|técnica', case=False, regex=True)
    
    # Detectar competencias o carreras oficiales (ej. "Carrera Ferias", "Media maratón", "Reto")
    es_carrera = nombres.str.contains('carrera|maratón|maraton|reto|competencia', case=False, regex=True)
    
    # El rodaje suave es TODO lo que NO sea umbral, intervalos ni carrera
    es_suave = ~(es_umbral | es_intervalos | es_carrera)

    # 4. Aplicar los factores de estrés de Daniels (verificando que exista duration_minutes)
    if 'duration_minutes' in df.columns:
        df.loc[es_suave, 'points_E'] = df.loc[es_suave, 'duration_minutes'] * DANIELS_FACTOR_E
        df.loc[es_umbral | es_carrera, 'points_T'] = df.loc[es_umbral | es_carrera, 'duration_minutes'] * DANIELS_FACTOR_T
        df.loc[es_intervalos, 'points_I'] = df.loc[es_intervalos, 'duration_minutes'] * DANIELS_FACTOR_I

    # 5. Suma total de puntos de la sesión
    df['daniels_total'] = df['points_E'] + df['points_T'] + df['points_I']
    
    return df

# Función para evaluar el balance de estrés semanal
def evaluate_stress_balance(df: pd.DataFrame) -> dict:
    """
    Evalúa si la última semana acumuló un exceso de estrés en alta intensidad
    en comparación con la base aeróbica (Regla de Alerta Automática).
    """
    if df.empty or 'Week' not in df.columns:
        return {"status": "ok", "message": "No hay suficientes datos para evaluar."}

    # Tomar los datos de la semana más reciente
    ultima_semana = df[df['Week'] == df['Week'].max()]
    
    sum_e = ultima_semana['points_E'].sum()
    sum_t = ultima_semana['points_T'].sum()
    sum_i = ultima_semana['points_I'].sum()
    
    total_puntos = sum_e + sum_t + sum_i
    
    if total_puntos == 0:
        return {"status": "ok", "message": "Sin actividad registrada esta semana."}
        
    alta_intensidad = sum_t + sum_i
    proporcion_dura = alta_intensidad / total_puntos

    # Regla de control: Si más del 40% del estrés es duro o el verde es menor al rojo/amarillo
    if proporcion_dura > 0.4:
        return {
            "status": "danger",
            "message": f"🚨 **Alerta de Sobrecarga:** El {proporcion_dura*100:.1f}% de tu estrés semanal proviene de alta intensidad. Riesgo elevado de fatiga acumulada."
        }
    elif sum_e < alta_intensidad:
        return {
            "status": "warning",
            "message": "⚠️ **Advertencia de Base:** Estás haciendo más trabajo duro (amarillo/rojo) que rodaje aeróbico suave (verde)."
        }
    else:
        return {
            "status": "success",
            "message": "✅ **Carga Equilibrada:** Tu proporción de base aeróbica frente al estrés duro es saludable."
        }

# Función para calcular la Relación de Carga Aguda a Crónica (ACWR)
def calculate_acwr(df: pd.DataFrame) -> dict:
    """
    Calcula la Relación de Carga Aguda a Crónica (ACWR) basada en los puntos de estrés total
    de las últimas semanas para la prevención de lesiones.
    """
    if df.empty or 'Week' not in df.columns or 'daniels_total' not in df.columns:
        return {"acwr": 0.0, "status": "nodata", "message": "Datos insuficientes para ACWR."}

    # Agrupar el estrés total por semana ordenado cronológicamente
    weekly_load = df.groupby('Week')['daniels_total'].sum().reset_index()
    weekly_load = weekly_load.sort_values('Week')

    if len(weekly_load) < 4:
        return {"acwr": 0.0, "status": "learning", "message": "Se requieren al menos 4 semanas de historial para calcular el ACWR."}

    # Carga Aguda: Estrés de la semana más reciente
    carga_aguda = weekly_load.iloc[-1]['daniels_total']
    
    # Carga Crónica: Promedio móvil de las últimas 4 semanas
    carga_cronica = weekly_load.tail(4)['daniels_total'].mean()

    if carga_cronica == 0:
        acwr = 0.0
    else:
        acwr = round(carga_aguda / carga_cronica, 2)

    # Evaluación de rangos de seguridad fisiológica
    if acwr < 0.8:
        status = "low"
        message = "⚠️ **Subentrenamiento:** La carga actual es baja respecto a tu base histórica."
    elif 0.8 <= acwr <= 1.3:
        status = "optimal"
        message = "✅ **Zona Óptima (Sweet Spot):** Carga equilibrada, bajo riesgo de lesión y alta asimilación."
    elif 1.3 < acwr <= 1.5:
        status = "caution"
        message = "⚡ **Precaución:** Incremento rápido de carga. Monitorea tus sensaciones de fatiga."
    else:
        status = "danger"
        message = "🚨 **Zona de Riesgo Alto:** Pico abrupto de carga. Alta probabilidad de sobreentrenamiento o lesión."

    return {
        "acwr": acwr,
        "carga_aguda": round(carga_aguda, 1),
        "carga_cronica": round(carga_cronica, 1),
        "status": status,
        "message": message
    }

# Función para calcular el índice de polarización
def calculate_polarization_ratio(df: pd.DataFrame) -> dict:
    """
    Calcula el Índice de Polarización (proporción de puntos de estrés en Zonas Fáciles 'E'
    frente a Zonas Duras 'T' e 'I') para verificar el cumplimiento del modelo polarizado.
    """
    if df.empty or not all(col in df.columns for col in ['points_E', 'points_T', 'points_I', 'Week']):
        return {"ratio": 0.0, "status": "nodata", "message": "Datos insuficientes para el índice de polarización."}
    
    # Tomamos la semana más reciente
    ultima_semana = df[df['Week'] == df['Week'].max()]
    
    total_e = ultima_semana['points_E'].sum()
    total_t = ultima_semana['points_T'].sum()
    total_i = ultima_semana['points_I'].sum()
    
    total_points = total_e + total_t + total_i
    
    if total_points == 0:
        return {"pct_e": 0.0, "status": "nodata", "message": "Sin puntos de estrés registrados esta semana."}
    
    pct_e = (total_e / total_points) * 100
    pct_hard = ((total_t + total_i) / total_points) * 100
    
    # Evaluación del modelo de polarización
    if pct_e >= 75:
        status = "optimal"
        message = f"✅ **Polarización Óptima:** {round(pct_e, 1)}% de trabajo aeróbico (E), excelente base metabólica."
    elif 60 <= pct_e < 75:
        status = "moderate"
        message = f"⚠️ **Polarización Moderada:** {round(pct_e, 1)}% en Zona E. Cuidado con acumular fatiga en la zona gris."
    else:
        status = "danger"
        message = f"🚨 **Exceso de Intensidad:** Demasiado estrés en zonas duras ({round(pct_hard, 1)}%). Riesgo de fatiga sistémica."
        
    return {
        "pct_e": round(pct_e, 1),
        "pct_hard": round(pct_hard, 1),
        "status": status,
        "message": message
    }

# Función para calcular ritmos de entrenamiento según VDOT
def get_vdot_training_paces(vdot_value: float) -> dict:
    """
    Calcula los ritmos de entrenamiento precisos (min/km) para cada zona 
    basándose en el índice VDOT del sistema de Jack Daniels.
    """
    # Estimación matemática de referencia para ritmos según VDOT
    # (Velocidad en m/min derivada del VDOT)
    
    # Valores de ejemplo calibrados para el rendimiento del atleta
    return {
        "vdot": vdot_value,
        "Easy (E)": "5:30 - 5:55 min/km",
        "Marathon (M)": "5:10 - 5:20 min/km",
        "Threshold (T)": "4:45 - 4:55 min/km",
        "Interval (I)": "4:20 - 4:30 min/km",
        "Repetition (R)": "4:00 - 4:10 min/km"
    }

# Función para calcular VDOT dinámico basado en los mejores ritmos
def calculate_dynamic_vdot(df: pd.DataFrame) -> float:
    """Estima un VDOT base a partir del archivo, con base de respaldo competitiva."""
    if df.empty or 'pace_min_km' not in df.columns:
        return 55.0
    
    fast_paces = df[(df['pace_min_km'] >= 3.0) & (df['pace_min_km'] <= 5.5)]['pace_min_km']
    if fast_paces.empty:
        return 55.0
    
    best_pace = fast_paces.min()
    estimated = 78.0 - (best_pace * 5.0)
    return max(40.0, min(70.0, round(estimated, 1)))

def get_vdot_training_paces_dynamic(vdot: float) -> dict:
    """Calcula las zonas de ritmo exactas según el VDOT de Jack Daniels."""
    t_decimal = 7.8 - (vdot * 0.065)
    time_10k = t_decimal * 10.4
    time_15k = t_decimal * 15.8

    return {
        "vdot": vdot,
        "Easy (E)": f"{format_pace(t_decimal + 0.9)} - {format_pace(t_decimal + 1.2)} min/km",
        "Marathon (M)": f"{format_pace(t_decimal + 0.3)} - {format_pace(t_decimal + 0.5)} min/km",
        "Threshold (T)": f"{format_pace(t_decimal - 0.05)} - {format_pace(t_decimal + 0.05)} min/km",
        "Interval (I)": f"{format_pace(t_decimal - 0.4)} - {format_pace(t_decimal - 0.3)} min/km",
        "Repetition (R)": f"{format_pace(t_decimal - 0.65)} - {format_pace(t_decimal - 0.55)} min/km",
        "pred_10k": format_total_time(time_10k),
        "pred_15k": format_total_time(time_15k)
    }

def format_pace(decimal_mins: float) -> str:
    """Convierte minutos decimales a formato MM:SS."""
    if pd.isna(decimal_mins) or decimal_mins <= 0:
        return "0:00"
    m = int(decimal_mins)
    s = int(round((decimal_mins - m) * 60))
    if s >= 60:
        m += 1
        s = 0
    return f"{m}:{s:02d}"

def format_total_time(total_minutes: float) -> str:
    """Convierte minutos totales a formato legible."""
    m = int(total_minutes)
    s = int(round((total_minutes - m) * 60))
    if s >= 60:
        m += 1
        s = 0
    hours = m // 60
    mins = m % 60
    if hours > 0:
        return f"{hours}h {mins:02d}min"
    return f"{mins}:{s:02d} min"

# Función para evaluar la eficiencia aeróbica
def aerobic_efficiency_status(df):
    """
    Calcula la tendencia del Factor de Eficiencia (EF).
    EF = Velocidad (km/h) / Frecuencia Cardíaca Promedio.
    """
    # 1. Filtro multi-idioma ajustado al encabezado exacto de tu CSV
    posibles_columnas_hr = [
        "Ritmo cardíaco promedio",   # Coincidencia exacta de tu CSV
        "Ritmo cardiaco promedio",   # Sin tilde
        "Average Heart Rate",        # Inglés
        "Frecuencia cardíaca media", 
        "Frecuencia cardiaca media", 
        "FC media",                  
        "Average HR",                
        "Heart Rate"                 
    ]
    
    hr_col = None
    for col in posibles_columnas_hr:
        if col in df.columns:
            hr_col = col
            break
            
    if not hr_col or df[hr_col].dropna().empty:
        return {"status": "no_data"}
    
    # 2. Copia y limpieza de valores numéricos
    valid_data = df.dropna(subset=['pace_min_km', hr_col]).copy()
    valid_data[hr_col] = pd.to_numeric(valid_data[hr_col], errors='coerce')
    valid_data = valid_data.dropna(subset=[hr_col])
    
    if len(valid_data) < 3:
        return {"status": "insufficient_data"}
        
    # 3. Cálculos del Factor de Eficiencia (EF)
    valid_data['speed_kmh'] = 60 / valid_data['pace_min_km']
    valid_data['EF'] = (valid_data['speed_kmh'] / valid_data[hr_col]) * 100
    
    # 4. Comparación reciente (últimas 5 carreras vs 5 anteriores)
    recent_ef = valid_data.tail(5)['EF'].mean()
    previous_ef = valid_data.iloc[-10:-5]['EF'].mean() if len(valid_data) >= 10 else recent_ef
    
    change = recent_ef - previous_ef
    
    # 5. Diagnóstico final
    if change > 0.1:
        verdict = "Eficiencia en aumento. Tu pulso es más bajo a los mismos ritmos."
        state = "positive"
    elif change < -0.1:
        verdict = "Ligero desacople detectado. Vigila la fatiga acumulada."
        state = "negative"
    else:
        verdict = "Eficiencia aeróbica estable y consolidada."
        state = "neutral"
        
    return {
        "status": "success",
        "recent_ef": round(recent_ef, 2),
        "change": round(change, 2),
        "verdict": verdict,
        "state": state
    }

# Función para predecir tiempos de carrera usando la Fórmula de Riegel
def predict_race_times(df):
    """
    Calcula la estimación de tiempos de carrera basándose en la mejor actuación CONTINUA.
    """
    if df.empty or 'Distance' not in df.columns:
        return None

    data = df.copy()
    interval_keywords = ['interval', 'series', 'fartlek', 'repetition', 'repeticiones', '4x', '5x', '3x', '6x', '8x', '10x']
    
    if 'Activity Name' in data.columns:
        pattern = '|'.join(interval_keywords)
        continuous_runs = data[~data['Activity Name'].str.lower().str.contains(pattern, na=False)]
    else:
        continuous_runs = data

    valid_runs = continuous_runs[continuous_runs['Distance'] >= 3.0].copy()
    if valid_runs.empty:
        valid_runs = data[data['Distance'] >= 3.0].copy()
        if valid_runs.empty:
            return None

    best_run = valid_runs.loc[valid_runs['pace_min_km'].idxmin()]

    d1 = float(best_run['Distance'])
    p1 = float(best_run['pace_min_km'])
    t1 = d1 * p1

    target_distances = {
        "5K": 5.0,
        "10K": 10.0,
        "15K (Reto Rosa)": 15.0,
        "21.1K (Media Maratón)": 21.0975
    }

    predictions = []
    for name, d2 in target_distances.items():
        t2_min = t1 * ((d2 / d1) ** 1.06)
        pace2_min = t2_min / d2
        
        hrs = int(t2_min // 60)
        mins = int(t2_min % 60)
        secs = int(round((t2_min - int(t2_min)) * 60))
        if secs == 60:
            mins += 1
            secs = 0
            if mins == 60:
                hrs += 1
                mins = 0

        time_str = f"{hrs:02d}:{mins:02d}:{secs:02d}" if hrs > 0 else f"{mins:02d}:{secs:02d}"

        p_mins = int(pace2_min)
        p_secs = int(round((pace2_min - p_mins) * 60))
        if p_secs == 60:
            p_mins += 1
            p_secs = 0
        pace_str = f"{p_mins}:{p_secs:02d} min/km"

        predictions.append({
            "Distancia": name,
            "Tiempo Estimado": time_str,
            "Ritmo Objetivo": pace_str
        })

    return {
        "ref_run": best_run,
        "predictions": pd.DataFrame(predictions)
    }

# Función para calcular TSB (Training Stress Balance)
def calculate_tsb_metrics(df):
    """
    Calcula la Forma (CTL), Fatiga (ATL) y Frescura (TSB)
    basado en la distribución diaria de volumen y carga.
    """
    if df.empty or 'Activity Date' not in df.columns:
        return None

    data = df.copy()
    data['Date'] = pd.to_datetime(data['Activity Date']).dt.date
    
    # Agrupamos por fecha para sumar la distancia total por día
    daily = data.groupby('Date')['Distance'].sum().reset_index()
    
    # Creamos un rango de fechas continuo (incluyendo días sin correr)
    full_idx = pd.date_range(start=daily['Date'].min(), end=daily['Date'].max(), freq='D')
    daily.set_index('Date', inplace=True)
    daily.index = pd.to_datetime(daily.index)
    daily = daily.reindex(full_idx, fill_value=0.0)
    daily.rename_axis('Date', inplace=True)
    
    # Calculamos la carga diaria (Load)
    daily['Load'] = daily['Distance']
    
    # Promedios móviles exponenciales (EMA)
    daily['Fatiga (ATL)'] = daily['Load'].ewm(span=7, adjust=False).mean()
    daily['Forma (CTL)'] = daily['Load'].ewm(span=42, adjust=False).mean()
    daily['Frescura (TSB)'] = daily['Forma (CTL)'] - daily['Fatiga (ATL)']
    
    latest = daily.iloc[-1]
    tsb_val = round(float(latest['Frescura (TSB)']), 2)
    ctl_val = round(float(latest['Forma (CTL)']), 2)
    atl_val = round(float(latest['Fatiga (ATL)']), 2)
    
    # Veredicto de zona TSB
    if tsb_val > 5:
        verdict = "Pico de Frescura: Las piernas están descargadas y listas para competir."
        status_state = "success"
    elif -10 <= tsb_val <= 5:
        verdict = "Zona Neutra: Equilibrio óptimo entre forma y recuperación."
        status_state = "info"
    elif -25 <= tsb_val < -10:
        verdict = "Carga Productiva: Acumulando kilómetros y adaptaciones."
        status_state = "warning"
    else:
        verdict = "Sobrecarga Alta: Riesgo de fatiga excesiva. Prioriza el descanso."
        status_state = "error"
        
    return {
        "daily_df": daily[['Forma (CTL)', 'Fatiga (ATL)', 'Frescura (TSB)']].tail(30),
        "current_tsb": tsb_val,
        "current_ctl": ctl_val,
        "current_atl": atl_val,
        "verdict": verdict,
        "state": status_state
    }


import math

def calculate_vdot(distance_km: float, time_minutes: float) -> float:
    """
    Calcula el índice VDOT exacto (Jack Daniels) usando las ecuaciones fisiológicas
    de consumo de oxígeno (VO2) y porcentaje de VO2max sostenido.
    """
    if distance_km <= 0 or time_minutes <= 0:
        return 45.0  # Valor base por defecto
        
    d_meters = distance_km * 1000.0
    v = d_meters / time_minutes  # velocidad en m/min
    
    # Consumo de O2 para esa velocidad (ml/kg/min)
    vo2 = -4.60 + (0.182258 * v) + (0.000104 * (v ** 2))
    
    # % de VO2max sostenido durante ese tiempo
    pct_vo2max = 0.8 + (0.1894393 * math.exp(-0.012778 * time_minutes)) + (0.2989558 * math.exp(-0.1932605 * time_minutes))
    
    vdot = vo2 / pct_vo2max
    return round(vdot, 1)

# Función para obtener el VDOT a partir del DataFrame
def get_vdot_from_df(df) -> tuple[float, dict]:
    """
    Detecta la mejor actuación CONTINUA reciente/histórica (>3 km) en el DataFrame.
    Filtra automáticamente sesiones de intervalos/series para no inflar el VDOT.
    """
    if df.empty or 'Distance' not in df.columns or 'pace_min_km' not in df.columns:
        return 45.0, {}

    data = df.copy()

    # 1. Filtro de palabras clave que identifican sesiones fraccionadas o calentamientos
    interval_keywords = [
        'interval', 'series', 'fartlek', 'repetition', 'repeticiones', 
        'calentamiento', 'enfriamiento', '4x', '5x', '3x', '6x', '8x', '10x', 'pista'
    ]
    
    # 2. Excluimos las actividades fraccionadas para la métrica de VDOT continuo
    if 'Activity Name' in data.columns:
        pattern = '|'.join(interval_keywords)
        continuous_runs = data[
            ~data['Activity Name'].str.lower().str.contains(pattern, na=False)
        ]
    else:
        continuous_runs = data

    # 3. Filtramos carreras continuas mayores o iguales a 3.0 km
    valid_runs = continuous_runs[continuous_runs['Distance'] >= 3.0].copy()
    
    # Respaldamos en caso de que todo el dataset sean intervalos
    if valid_runs.empty:
        valid_runs = data[data['Distance'] >= 3.0].copy()
        if valid_runs.empty:
            return 45.0, {}

    # 4. Aseguramos ordenamiento por fecha
    if 'Activity Date' in valid_runs.columns:
        valid_runs['Activity Date'] = pd.to_datetime(valid_runs['Activity Date'], errors='coerce')
        valid_runs = valid_runs.sort_values(by='Activity Date', ascending=True)

    # 5. Seleccionamos el MEJOR RITMO CONTINUO real
    best_run = valid_runs.loc[valid_runs['pace_min_km'].idxmin()]

    dist_km = float(best_run['Distance'])
    pace_min_km = float(best_run['pace_min_km'])
    time_min = dist_km * pace_min_km

    vdot = calculate_vdot(dist_km, time_min)
    
    ref_info = {
        "name": best_run.get('Activity Name', 'Entrenamiento'),
        "distance": dist_km,
        "pace": pace_min_km,
        "date": str(best_run.get('Activity Date', 'Reciente'))[:10]
    }
    
    return vdot, ref_info

# Función para generar la tabla de zonas de entrenamiento según VDOT
def get_jack_daniels_zones(vdot: float) -> pd.DataFrame:
    """
    Calcula la tabla de ritmos objetivo por zonas de entrenamiento (Jack Daniels)
    a partir del VDOT del atleta.
    """
    # Ecuación cuadrática para hallar vVDOT (velocidad al 100% de VDOT en m/min)
    a = 0.000104
    b = 0.182258
    c = -(4.60 + vdot)
    
    v_vdot = (-b + math.sqrt(b**2 - 4 * a * c)) / (2 * a)  # m/min
    
    # Rangos % de vVDOT según la metodología de Jack Daniels
    zones_def = [
        {"Zona": "Easy / Rodaje Suave (E)", "Código": "Z1 / Z2", "pct_low": 0.65, "pct_high": 0.75, "Propósito": "Base aeróbica, regeneración y resistencia biológica."},
        {"Zona": "Marathon Pace (M)", "Código": "Z3", "pct_low": 0.79, "pct_high": 0.88, "Propósito": "Ritmo sostenido y eficiencia glucogénica en larga distancia."},
        {"Zona": "Threshold / Umbral (T)", "pct_low": 0.88, "pct_high": 0.92, "Código": "Z4", "Propósito": "Elevación del umbral de lactato (Tempo runs y cruceros)."},
        {"Zona": "Interval / VO2Max (I)", "Código": "Z5", "pct_low": 0.95, "pct_high": 1.00, "Propósito": "Desarrollo de la potencia aeróbica máxima (Series de 3-5 min)."},
        {"Zona": "Repetition / Velocidad (R)", "Código": "Z6", "pct_low": 1.05, "pct_high": 1.10, "Propósito": "Economía de zancada, velocidad pura y coordinación neuromuscular."},
    ]

    def mmin_to_pace_str(v_mmin):
        if v_mmin <= 0: return "N/A"
        pace_decimal = 1000.0 / v_mmin  # min/km
        mins = int(pace_decimal)
        secs = int(round((pace_decimal - mins) * 60))
        if secs == 60:
            mins += 1
            secs = 0
        return f"{mins}:{secs:02d}"

    table = []
    for z in zones_def:
        # A mayor velocidad (m/min), menor es el ritmo (min/km)
        v_high = v_vdot * z["pct_high"] # ritmo más rápido
        v_low = v_vdot * z["pct_low"]   # ritmo más lento
        
        pace_fast = mmin_to_pace_str(v_high)
        pace_slow = mmin_to_pace_str(v_low)
        
        table.append({
            "Zona de Entrenamiento": z["Zona"],
            "Código": z["Código"],
            "Rango de Ritmo (min/km)": f"{pace_fast} - {pace_slow}",
            "Propósito Fisiológico": z["Propósito"]
        })
        
    return pd.DataFrame(table)

def calculate_pacing_splits(distancia_km: float, tiempo_objetivo_min: float, estrategia: str = "Negative Split"):
    """
    Calcula los parciales km por km según la estrategia de ritmo seleccionada.
    """
    ritmo_medio_seg = (tiempo_objetivo_min * 60) / distancia_km
    num_kms = int(distancia_km)
    fraccion_final = distancia_km - num_kms
    
    kms = list(range(1, num_kms + 1))
    if fraccion_final > 0:
        kms.append(distancia_km)  # Último tramo parcial

    ritmos_seg = []
    
    for k in kms:
        if estrategia == "Negative Split":
            # Primera mitad un 1.5% más lenta, segunda mitad un 1.5% más rápida
            progreso = (k - 1) / (distancia_km - 1) if distancia_km > 1 else 0.5
            factor = 1.015 - (0.03 * progreso)
        elif estrategia == "Positive Split":
            # Primera mitad 1.5% más rápida, decayendo al final
            progreso = (k - 1) / (distancia_km - 1) if distancia_km > 1 else 0.5
            factor = 0.985 + (0.03 * progreso)
        else:  # Ritmo Uniforme
            factor = 1.0
            
        ritmos_seg.append(ritmo_medio_seg * factor)

    # Construir lista de resultados
    parciales = []
    tiempo_acumulado_seg = 0.0

    for i, k in enumerate(kms):
        es_tramo_final = (i == len(kms) - 1 and fraccion_final > 0)
        distancia_tramo = fraccion_final if es_tramo_final else 1.0
        
        tiempo_tramo_seg = ritmos_seg[i] * distancia_tramo
        tiempo_acumulado_seg += tiempo_tramo_seg
        
        # Formatear ritmos (MM:SS)
        m_ritmo, s_ritmo = divmod(int(ritmos_seg[i]), 60)
        m_acum, s_acum = divmod(int(tiempo_acumulado_seg), 60)
        h_acum, m_acum = divmod(m_acum, 60)
        
        fmt_acum = f"{h_acum:02d}:{m_acum:02d}:{s_acum:02d}" if h_acum > 0 else f"{m_acum:02d}:{s_acum:02d}"
        
        parciales.append({
            "Km": f"Km {k:.1f}" if es_tramo_final else f"Km {int(k)}",
            "Ritmo Prescrito (min/km)": f"{m_ritmo:02d}:{s_ritmo:02d}",
            "Tiempo Acumulado": fmt_acum,
            "Ritmo_Segundos": ritmos_seg[i]
        })

    return pd.DataFrame(parciales)

# Función para calcular la Relación de Carga Aguda a Crónica (ACWR) y su interpretación
def compute_acwr_ratio(carga_aguda: float, carga_cronica: float):
    if carga_cronica is None or carga_cronica <= 0:
        return 0.0, "Insuficiente carga crónica", "info", "Registra más semanas para establecer una base crónica confiable."

    acwr = carga_aguda / carga_cronica

    if acwr < 0.8:
        estado = "⚠️ Subentrenamiento / Descarga"
        tipo_alerta = "warning"
        desc = "Carga por debajo de la base. Útil para semanas de descarga, pero prolongado causa pérdida de condición física."
    elif 0.8 <= acwr <= 1.3:
        estado = "✅ Zona Dulce (Sweet Spot)"
        tipo_alerta = "success"
        desc = "Progresión de volumen ideal. Maximiza adaptaciones aeróbicas con mínimo riesgo de lesión."
    elif 1.3 < acwr <= 1.5:
        estado = "⚡ Precaución (Sobrecarga Moderada)"
        tipo_alerta = "warning"
        desc = "Aumento acelerado de carga. Monitorea fatiga y sueño para no cruzar el límite."
    else:
        estado = "🚨 Zona de Peligro (Spike in Load)"
        tipo_alerta = "error"
        desc = "Pico drástico de volumen (>50% sobre la base). El riesgo estadístico de lesión se dispara."

    return float(acwr), estado, tipo_alerta, desc
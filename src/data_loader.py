import pandas as pd
from src.metrics import calculate_daniels_points
from src.config import (
    ACTIVITY_DATE_COL,
    CSV_ENCODING,
    DATA_PATH,
    DISTANCE_COL,
    WEEK_COL,
    YEAR_COL,
)

def load_data(path=DATA_PATH):
    # 1. Leer datos
    df = pd.read_csv(path, encoding=CSV_ENCODING)

    # 1.1 Mapeo inteligente para estandarizar columnas de Strava (Español e Inglés)
    column_mappings = {
        'Fecha': ACTIVITY_DATE_COL,
        'Fecha de la actividad': ACTIVITY_DATE_COL,
        'Date': ACTIVITY_DATE_COL,
        'Activity Date': ACTIVITY_DATE_COL,
        
        'Nombre de la actividad': 'Activity Name',
        'Nombre': 'Activity Name',
        'Name': 'Activity Name',
        'Activity Name': 'Activity Name',
        
        'Distancia': DISTANCE_COL,
        'distance': DISTANCE_COL,
        'Distance': DISTANCE_COL,
        
        'Tiempo en movimiento': 'Moving Time',
        'Moving Time': 'Moving Time',
        
        'Tipo de actividad': 'Activity Type',
        'Activity Type': 'Activity Type'
    }

    df = df.rename(columns={col: column_mappings[col] for col in df.columns if col in column_mappings})

    if ACTIVITY_DATE_COL not in df.columns:
        raise KeyError(f"No se encontró la columna de fecha. Columnas disponibles: {list(df.columns)}")
    
    if 'Activity Name' not in df.columns:
        df['Activity Name'] = "Entrenamiento sin nombre"

    # 2. Limpiar y convertir fechas
    df[ACTIVITY_DATE_COL] = pd.to_datetime(df[ACTIVITY_DATE_COL], errors="coerce")
    df = df.dropna(subset=[ACTIVITY_DATE_COL])

    # 3. Convertir distancia y tiempo a formatos numéricos útiles
    if DISTANCE_COL in df.columns:
        df[DISTANCE_COL] = pd.to_numeric(df[DISTANCE_COL], errors="coerce")

    if 'Moving Time' in df.columns:
        df['Moving Time'] = pd.to_numeric(df['Moving Time'], errors="coerce")
        # 🔑 CLAVE: Creamos duration_minutes para que los puntos de Daniels no queden en 0
        df['duration_minutes'] = df['Moving Time'] / 60

    # 4. Columnas temporales por semana
    df[YEAR_COL] = df[ACTIVITY_DATE_COL].dt.year
    df[WEEK_COL] = df[ACTIVITY_DATE_COL].dt.isocalendar().week

    # 5. Calcular Puntos de Estrés de Daniels
    df = calculate_daniels_points(df)

    return df
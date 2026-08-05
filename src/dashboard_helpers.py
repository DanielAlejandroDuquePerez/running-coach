import pandas as pd
import streamlit as st


def render_hud_metric(label, value, delta=None, tone="cyan", subtitle=None):
    """Renderiza tarjetas de métricas visuales con estilos inline inmunes a fallos de CSS externo."""
    tone_styles = {
        "cyan": "#00D2FF",
        "lime": "#00E676",
        "amber": "#FFB300",
        "red": "#FF3366",
        "slate": "#8A99AD",
        "purple": "#A855F7",
    }
    accent = tone_styles.get(tone, tone_styles["cyan"])
    
    delta_html = f'<div style="font-size:0.85rem;font-weight:600;color:{accent};margin-top:2px;">{delta}</div>' if delta else ""
    subtitle_html = f'<div style="font-size:0.75rem;color:#9CA3AF;margin-top:4px;">{subtitle}</div>' if subtitle else ""
    
    html_str = (
        f'<div style="background-color:#111827;border:1px solid #1F2937;border-left:4px solid {accent};'
        f'border-radius:8px;padding:12px 16px;margin-bottom:10px;">'
        f'<div style="font-size:0.75rem;font-weight:700;color:#8A99AD;text-transform:uppercase;letter-spacing:0.5px;">{label}</div>'
        f'<div style="font-size:1.5rem;font-weight:800;color:#FFFFFF;line-height:1.2;margin-top:4px;">{value}</div>'
        f'{delta_html}'
        f'{subtitle_html}'
        f'</div>'
    )
    st.markdown(html_str, unsafe_allow_html=True)


def render_status_badge(text, tone="success", icon="●"):
    """Renderiza insignias e indicadores de estado estilizados."""
    tone_styles = {
        "success": ("#00E676", "rgba(0, 230, 118, 0.12)"),
        "warning": ("#FFB300", "rgba(255, 179, 0, 0.12)"),
        "danger": ("#FF3366", "rgba(255, 51, 102, 0.12)"),
        "info": ("#00D2FF", "rgba(0, 210, 255, 0.12)"),
    }
    color, bg = tone_styles.get(tone, tone_styles["info"])
    
    html_badge = (
        f'<div style="display:inline-flex;align-items:center;gap:8px;background-color:{bg};'
        f'border:1px solid {color}44;color:{color};padding:6px 12px;border-radius:6px;'
        f'font-size:0.85rem;font-weight:600;margin-bottom:8px;">'
        f'<span>{icon}</span><span>{text}</span>'
        f'</div>'
    )
    st.markdown(html_badge, unsafe_allow_html=True)


def ensure_upload_state():
    if "df_actividades" not in st.session_state:
        st.session_state["df_actividades"] = None
    if "df_actividades_tabla" not in st.session_state:
        st.session_state["df_actividades_tabla"] = None
    if "df_semanal" not in st.session_state:
        st.session_state["df_semanal"] = None
    if "upload_notice" not in st.session_state:
        st.session_state["upload_notice"] = None


def set_upload_notice(message, tone="info", icon="i"):
    st.session_state["upload_notice"] = {"message": message, "tone": tone, "icon": icon}


def render_upload_notice():
    notice = st.session_state.get("upload_notice")
    if notice:
        render_status_badge(
            notice.get("message", ""),
            tone=notice.get("tone", "info"),
            icon=notice.get("icon", "i"),
        )


def process_uploaded_activities(file):
    try:
        if file.name.lower().endswith(".csv"):
            df = pd.read_csv(file)
        else:
            df = pd.read_excel(file, sheet_name=0)

        df.columns = [str(col).strip() for col in df.columns]
        lower_map = {col.lower(): col for col in df.columns}

        fecha_col = next((lower_map[key] for key in lower_map if "fecha" in key or "date" in key), None)
        dist_col = next((lower_map[key] for key in lower_map if "distancia" in key or "distance" in key or key == "km"), None)

        if not fecha_col or not dist_col:
            return None, "El archivo debe incluir al menos una columna de fecha y una de distancia."

        df[fecha_col] = pd.to_datetime(df[fecha_col], errors="coerce")
        df[dist_col] = pd.to_numeric(df[dist_col], errors="coerce")
        df = df.dropna(subset=[fecha_col]).copy()
        df = df.sort_values(by=fecha_col, ascending=False)

        display_df = df[[fecha_col, dist_col]].copy()
        display_df.columns = ["Fecha", "Distancia"]
        if "Activity Name" in df.columns:
            display_df.insert(1, "Actividad", df["Activity Name"].astype(str).values)

        weekly_df = build_daniels_weekly_summary(df)

        return {"df_actividades": df, "display_df": display_df, "df_semanal": weekly_df}, None
    except Exception as exc:
        return None, f"Error al procesar archivo: {exc}"


def build_daniels_weekly_summary(df):
    if df is None or df.empty:
        return pd.DataFrame()

    source = df.copy()
    source.columns = [str(col).strip().lower() for col in source.columns]

    fecha_col = next((col for col in source.columns if "fecha" in col or "date" in col), None)
    dist_col = next((col for col in source.columns if "distancia" in col or "km" in col or "distance" in col), None)
    time_col = next((col for col in source.columns if "tiempo en movimiento" in col or "moving time" in col or "duracion" in col or "duration" in col), None)
    rpe_col = next((col for col in source.columns if "rpe" in col), None)

    if not fecha_col or not dist_col:
        return pd.DataFrame()

    source[fecha_col] = pd.to_datetime(source[fecha_col], errors="coerce")
    source[dist_col] = pd.to_numeric(source[dist_col], errors="coerce").fillna(0)
    source = source.dropna(subset=[fecha_col]).copy()

    if source.empty:
        return pd.DataFrame()

    source = source.rename(columns={fecha_col: "fecha", dist_col: "distancia_km"})

    if time_col and time_col != "duracion_min":
        source[time_col] = pd.to_numeric(source[time_col], errors="coerce")
        source["duracion_min"] = source[time_col] / 60.0
    elif "duracion_min" not in source.columns:
        source["duracion_min"] = source["distancia_km"] * 5.5

    if rpe_col and rpe_col != "rpe":
        source["rpe"] = pd.to_numeric(source[rpe_col], errors="coerce").fillna(4.0)
    elif "rpe" not in source.columns:
        source["rpe"] = 4.0

    source["semana"] = source["fecha"].dt.to_period("W").dt.start_time

    pts_df = source.apply(calculate_daniels_points_row, axis=1)
    source = pd.concat([source, pts_df], axis=1)

    weekly = (
        source.groupby("semana", as_index=False)[["distancia_km", "pts_e", "pts_m", "pts_t", "pts_i", "pts_r"]]
        .sum()
        .sort_values("semana")
    )

    return weekly


def calculate_daniels_points_row(row):
    factors = {"E": 0.20, "M": 0.35, "T": 0.60, "I": 0.90, "R": 1.30}

    if all(col in row for col in ["min_e", "min_m", "min_t", "min_i", "min_r"]):
        pts_e = row.get("min_e", 0) * factors["E"]
        pts_m = row.get("min_m", 0) * factors["M"]
        pts_t = row.get("min_t", 0) * factors["T"]
        pts_i = row.get("min_i", 0) * factors["I"]
        pts_r = row.get("min_r", 0) * factors["R"]
        return pd.Series([pts_e, pts_m, pts_t, pts_i, pts_r], index=["pts_e", "pts_m", "pts_t", "pts_i", "pts_r"])

    duration_min = row.get("duracion_min", row.get("distancia_km", 0) * 5.5)
    rpe = row.get("rpe", 4.0)
    total_pts = duration_min * ((rpe / 10.0) ** 1.6) * 1.1

    if rpe <= 3:
        return pd.Series([total_pts, 0, 0, 0, 0], index=["pts_e", "pts_m", "pts_t", "pts_i", "pts_r"])
    elif rpe <= 5:
        return pd.Series([0, total_pts, 0, 0, 0], index=["pts_e", "pts_m", "pts_t", "pts_i", "pts_r"])
    elif rpe <= 7:
        return pd.Series([0, 0, total_pts, 0, 0], index=["pts_e", "pts_m", "pts_t", "pts_i", "pts_r"])
    elif rpe <= 8:
        return pd.Series([0, 0, 0, total_pts, 0], index=["pts_e", "pts_m", "pts_t", "pts_i", "pts_r"])
    else:
        return pd.Series([0, 0, 0, 0, total_pts], index=["pts_e", "pts_m", "pts_t", "pts_i", "pts_r"])
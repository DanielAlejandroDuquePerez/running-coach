import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from src.metrics import calculate_acwr


def make_responsive_chart(fig, height=320, title=""):
    """Aplica formato optimizado para touch y pantallas móviles."""
    fig.update_layout(
        title=dict(text=title, font=dict(size=14)),
        height=height,
        margin=dict(l=10, r=10, t=35, b=20),
        legend=dict(orientation="h", y=-0.2, x=0.5, xanchor="center"),
        hovermode="x unified",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#FFFFFF", family="Inter, Segoe UI, Arial, sans-serif"),
        title_font=dict(color="#FFFFFF", size=15),
    )
    fig.update_xaxes(
        gridcolor="rgba(255, 255, 255, 0.05)",
        zerolinecolor="rgba(255, 255, 255, 0.05)",
        linecolor="rgba(255, 255, 255, 0.08)",
        tickfont=dict(color="#8A99AD"),
    )
    fig.update_yaxes(
        gridcolor="rgba(255, 255, 255, 0.05)",
        zerolinecolor="rgba(255, 255, 255, 0.05)",
        linecolor="rgba(255, 255, 255, 0.08)",
        tickfont=dict(color="#8A99AD"),
    )
    return fig


def create_hero_chart(df_weekly):
    """Genera el gráfico combinado de volumen semanal y ACWR."""
    if df_weekly is None or df_weekly.empty:
        return go.Figure()

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    if "semana" in df_weekly.columns and "volumen_km" in df_weekly.columns:
        fig.add_trace(
            go.Bar(
                x=df_weekly["semana"],
                y=df_weekly["volumen_km"],
                name="Volumen (km)",
                marker_color="rgba(0, 210, 255, 0.75)",
                marker_line_color="#00D2FF",
                marker_line_width=1.5,
                hovertemplate="<b>Semana:</b> %{x}<br><b>Volumen:</b> %{y:.1f} km<extra></extra>",
            ),
            secondary_y=False,
        )

    if "acwr" in df_weekly.columns:
        fig.add_trace(
            go.Scatter(
                x=df_weekly["semana"],
                y=df_weekly["acwr"],
                name="Ratio ACWR",
                mode="lines+markers",
                line=dict(color="#FFD600", width=3),
                marker=dict(size=7, color="#FFD600", symbol="circle"),
                hovertemplate="<b>ACWR:</b> %{y:.2f}<extra></extra>",
            ),
            secondary_y=True,
        )

    fig.add_hrect(
        y0=0.80,
        y1=1.30,
        fillcolor="rgba(0, 230, 118, 0.12)",
        layer="below",
        line_width=0,
        secondary_y=True,
        annotation_text="Zona Óptima (0.80 - 1.30)",
        annotation_position="top left",
        annotation_font=dict(size=11, color="#00E676", weight="bold"),
    )

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=30, b=10),
        height=340,
        legend=dict(orientation="h", yanchor="bottom", y=1.03, xanchor="right", x=1, font=dict(color="#8A99AD", size=12)),
        hovermode="x unified",
        hoverlabel=dict(bgcolor="#121824", font_size=12, font_color="#FFFFFF", bordercolor="#1E2A38"),
    )
    fig.update_xaxes(showgrid=True, gridcolor="rgba(255, 255, 255, 0.05)", tickfont=dict(color="#8A99AD"))
    fig.update_yaxes(
        title_text="Volumen (km)",
        title_font=dict(color="#00D2FF", size=11),
        tickfont=dict(color="#8A99AD"),
        showgrid=True,
        gridcolor="rgba(255, 255, 255, 0.05)",
        secondary_y=False,
    )
    fig.update_yaxes(
        title_text="Ratio ACWR",
        title_font=dict(color="#FFD600", size=11),
        tickfont=dict(color="#8A99AD"),
        showgrid=False,
        range=[0.4, 1.8],
        secondary_y=True,
    )
    return fig


def calculate_daniels_points_row(row):
    """Calcula los puntos Daniels de una actividad."""
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
        values = [total_pts, 0, 0, 0, 0]
    elif rpe <= 5:
        values = [0, total_pts, 0, 0, 0]
    elif rpe <= 7:
        values = [0, 0, total_pts, 0, 0]
    elif rpe <= 8:
        values = [0, 0, 0, total_pts, 0]
    else:
        values = [0, 0, 0, 0, total_pts]

    return pd.Series(values, index=["pts_e", "pts_m", "pts_t", "pts_i", "pts_r"])


def build_daniels_weekly_summary(df):
    """Convierte un historial de actividades en una tabla semanal con puntos Daniels."""
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
    weekly = weekly.rename(columns={"distancia_km": "volumen_km"})

    weekly["cronica"] = weekly["volumen_km"].rolling(window=4, min_periods=1).mean()
    weekly["acwr"] = weekly["volumen_km"] / weekly["cronica"].replace(0, 1)
    return weekly


def create_internal_load_chart(df_semanal_pts):
    """Genera el gráfico de barras apiladas de Puntos de Estrés Semanales."""
    fig = go.Figure()

    zones = [
        ("pts_e", "Zona E (Fácil)", "#00E676"),
        ("pts_m", "Zona M (Maratón)", "#00D2FF"),
        ("pts_t", "Zona T (Umbral)", "#FFB300"),
        ("pts_i", "Zona I (Intervalos)", "#FF6D00"),
        ("pts_r", "Zona R (Repeticiones)", "#FF3366"),
    ]

    for col, name, color in zones:
        if col in df_semanal_pts.columns:
            fig.add_trace(
                go.Bar(
                    x=df_semanal_pts["semana"],
                    y=df_semanal_pts[col],
                    name=name,
                    marker_color=color,
                    hovertemplate="<b>%{x}</b><br>" + name + ": <b>%{y:.1f} pts</b><extra></extra>",
                )
            )

    fig.update_layout(
        barmode="stack",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=30, b=10),
        height=350,
        legend=dict(orientation="h", yanchor="bottom", y=1.03, xanchor="right", x=1, font=dict(color="#8A99AD", size=11)),
        hovermode="x unified",
        hoverlabel=dict(bgcolor="#121824", font_size=12, font_color="#FFFFFF", bordercolor="#1E2A38"),
    )
    fig.update_xaxes(showgrid=True, gridcolor="rgba(255, 255, 255, 0.05)", tickfont=dict(color="#8A99AD"))
    fig.update_yaxes(title_text="Puntos de Estrés (Daniels)", title_font=dict(color="#8A99AD", size=11), tickfont=dict(color="#8A99AD"), showgrid=True, gridcolor="rgba(255, 255, 255, 0.05)")
    return fig


def render_interactive_ecosystem_chart(df):
    if df is None or df.empty:
        return

    df_copy = df.copy()
    col_fecha = next((col for col in df_copy.columns if "fecha" in col or "date" in col), None)
    col_dist = next((col for col in df_copy.columns if "distancia" in col or "km" in col or "distance" in col), None)

    if not col_fecha or not col_dist:
        return

    df_copy[col_fecha] = pd.to_datetime(df_copy[col_fecha])
    df_copy["semana"] = df_copy[col_fecha].dt.to_period("W").dt.start_time
    df_weekly = df_copy.groupby("semana")[col_dist].sum().reset_index()

    df_weekly["cronica"] = df_weekly[col_dist].rolling(window=4, min_periods=1).mean()
    df_weekly["acwr"] = df_weekly[col_dist] / df_weekly["cronica"].replace(0, 1)

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Bar(
            x=df_weekly["semana"],
            y=df_weekly[col_dist],
            name="Volumen Semanal (Km)",
            marker_color="rgba(0, 210, 255, 0.80)",
            opacity=0.8,
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=df_weekly["semana"],
            y=df_weekly["acwr"],
            name="Ratio ACWR",
            mode="lines+markers",
            line=dict(color="#FFD600", width=3),
        ),
        secondary_y=True,
    )
    fig.add_hline(y=1.5, line_dash="dot", line_color="#FF3366", secondary_y=True)
    fig.add_hline(y=0.8, line_dash="dot", line_color="#00E676", secondary_y=True)
    fig = make_responsive_chart(fig, height=320, title="Evolución de Carga: Volumen Semanal vs ACWR")
    fig.update_xaxes(showgrid=True, gridcolor="rgba(255, 255, 255, 0.05)")
    fig.update_yaxes(showgrid=True, gridcolor="rgba(255, 255, 255, 0.05)")
    st.plotly_chart(fig, use_container_width=True, key="hero_chart")

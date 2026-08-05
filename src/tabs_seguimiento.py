import pandas as pd
import plotly.express as px
import streamlit as st

from src.dashboard_helpers import render_hud_metric, render_status_badge
from src.charts import make_responsive_chart
from src.storage import load_all_plans, update_full_plan


def render_seguimiento_tab(state):
    st.subheader("📍 Diario del Atleta y Registro de Adherencia")
    st.caption("Evalúa cada sesión de la semana, registra tus sensaciones y calcula automáticamente tu adherencia real.")

    saved_plans = load_all_plans()

    if not saved_plans:
        render_status_badge("Aún no has guardado ningún plan. Genera uno en Coach IA y guárdalo.", tone="info", icon="i")
        return

    hist_data = []
    for p in reversed(saved_plans):
        fecha_corta = p.get("fecha_creacion", "").split(" ")[0]
        hist_data.append({
            "Fecha": fecha_corta,
            "Adherencia (%)": p.get("adherencia_pct", 0),
            "VDOT": p.get("vdot_base", 0),
        })

    df_hist = pd.DataFrame(hist_data)

    if not df_hist.empty:
        fig_adh = px.bar(
            df_hist,
            x="Fecha",
            y="Adherencia (%)",
            text="Adherencia (%)",
            title="📈 Evolución Histórica de Adherencia Semanal",
            color="Adherencia (%)",
            color_continuous_scale="RdYlGn",
            range_y=[0, 105],
        )
        fig_adh.update_traces(texttemplate="%{text}%", textposition="outside")
        fig_adh = make_responsive_chart(fig_adh, height=280, title="Evolución Histórica de Adherencia Semanal")
        st.markdown("---")

        with st.expander("📊 Ver historial de adherencia", expanded=False):
            fig_adh.update_xaxes(type="category")
            fig_adh.update_traces(texttemplate="%{text}%", textposition="outside")
            st.plotly_chart(fig_adh, use_container_width=True, key="seguimiento_adherence_chart")

    plan_options = {f"{p['fecha_creacion']} | VDOT: {p['vdot_base']} | Estado: {p['estado']}": p['id'] for p in saved_plans}
    selected_label = st.selectbox("📋 Seleccionar Plan Guardado:", options=list(plan_options.keys()))
    selected_id = plan_options[selected_label]
    selected_plan = next(p for p in saved_plans if p["id"] == selected_id)

    df_diario = pd.DataFrame(selected_plan.get("diario_sesiones", []))

    st.markdown("### 📓 Registro Sesión por Sesión (Lunes a Domingo)")
    st.caption("Edita directamente en las celdas: marca qué días cumpliste, tus kilómetros reales y tu RPE.")

    edited_df = st.data_editor(
        df_diario,
        column_config={
            "Día": st.column_config.TextColumn("Día", disabled=True),
            "Tipo / Prescripción": st.column_config.TextColumn("Prescripción / Foco", width="medium"),
            "Completado": st.column_config.CheckboxColumn("¿Completado?", default=False),
            "Km Real": st.column_config.NumberColumn("Km Reales", min_value=0.0, max_value=50.0, step=0.5, format="%.1f km"),
            "RPE (1-10)": st.column_config.NumberColumn("RPE (1-10)", min_value=1, max_value=10, step=1),
            "Sensaciones / Notas": st.column_config.TextColumn("Notas de la Sesión", width="large"),
        },
        hide_index=True,
        use_container_width=True,
        num_rows="fixed",
    )

    dias_completados = edited_df["Completado"].sum() if "Completado" in edited_df.columns else 0
    km_totales_reales = edited_df["Km Real"].sum() if "Km Real" in edited_df.columns else 0.0
    adherencia_calculada = int((dias_completados / 7) * 100)

    st.markdown("---")
    st.markdown("### 🎯 Métricas Semanales de Cumplimiento")

    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    with col_m1:
        render_hud_metric("Sesiones Cumplidas", f"{dias_completados} / 7 días", tone="lime")
    with col_m2:
        render_hud_metric("Volumen Real Acumulado", f"{km_totales_reales:.1f} km", tone="cyan")
    with col_m3:
        render_hud_metric("Adherencia Automática", f"{adherencia_calculada}%", tone="amber")
    with col_m4:
        nuevo_estado = st.selectbox(
            "Estado General",
            options=["En Curso", "Completado", "Archivado"],
            index=["En Curso", "Completado", "Archivado"].index(selected_plan.get("estado", "En Curso")),
        )

    notas_globales = st.text_input(
        "📝 Resumen/Conclusión general de la semana:",
        value=selected_plan.get("notas_seguimiento", ""),
        placeholder="Ej: Buena semana de carga, el domingo completé la tirada sin molestias.",
    )

    if st.button("💾 Guardar Cambios en el Diario", type="primary", use_container_width=True):
        diario_actualizado = edited_df.to_dict(orient="records")
        if update_full_plan(selected_id, nuevo_estado, adherencia_calculada, notas_globales, diario_actualizado):
            render_status_badge("Diario y métricas de adherencia guardados con éxito.", tone="success", icon="✓")
            st.rerun()

    st.markdown("---")
    st.markdown("### 📄 Plan Semanal Original Generado por IA")
    st.markdown(selected_plan["plan_markdown"])

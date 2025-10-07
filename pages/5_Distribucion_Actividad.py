import streamlit as st
import plotly.express as px
import pandas as pd
import numpy as np

# Utilidades del proyecto
from utils.datos import init_data, get_data_copy
from utils.filtros import filtros_locales
from utils.estilos import aplicar_tema_plotly, mostrar_tarjeta_nota

# Aplicar tema global
aplicar_tema_plotly()

# 1️⃣ Título
st.title("🏢 Distribución por Actividad Empresa")

# 2️⃣ Carga de datos
init_data()
df_grad = get_data_copy("Graduados")
df_lab = get_data_copy("DataLaboral")

# Normalizar columnas
df_grad.columns = df_grad.columns.str.strip().str.lower()
df_lab.columns = df_lab.columns.str.strip().str.lower()

# 3️⃣ Filtros
df_grad_filtrado, cedulas_filtradas, selections = filtros_locales(df_grad)
if df_grad_filtrado.empty:
    st.warning("No hay datos disponibles con los filtros seleccionados.")
    st.stop()

cedulas_validas = set(cedulas_filtradas)
if not cedulas_validas:
    st.warning("No hay cédulas válidas tras aplicar los filtros.")
    st.stop()

# 4️⃣ Filtrar DataLaboral
dfl = df_lab[df_lab["cedula"].isin(cedulas_validas)].copy()

# Solo empleados activos
if "labora_actualmente" in dfl.columns:
    dfl["labora_actualmente"] = (
        dfl["labora_actualmente"].astype(str).str.upper().str.strip()
    )
    dfl = dfl[dfl["labora_actualmente"] == "S"]

if dfl.empty:
    st.warning("No hay registros laborales activos para las cédulas filtradas.")
    st.stop()

# 5️⃣ Contar personas únicas por actividad económica
dfl = dfl.dropna(subset=["actividad_empresa"]).copy()
conteo = (
    dfl.groupby("actividad_empresa")["cedula"]
    .nunique()
    .reset_index(name="total_personas")
    .sort_values("total_personas", ascending=False)
)

if conteo.empty:
    st.warning("No hay datos válidos en la columna 'actividad_empresa'.")
    st.stop()

# 7️⃣ Mantener solo Top 10
top_actividades = conteo.head(10)

# 6️⃣ Calcular porcentaje basado solo en los top 10
total_top10 = top_actividades["total_personas"].sum()
top_actividades["porcentaje"] = (
    top_actividades["total_personas"] / total_top10 * 100
).round(1)

# 8️⃣ Gráfico de barras horizontales (orden descendente)
fig = px.bar(
    top_actividades.sort_values("total_personas", ascending=True),
    x="total_personas",
    y="actividad_empresa",
    orientation="h",
    text="porcentaje",
    labels={
        "actividad_empresa": "Actividad económica de la empresa",
        "total_personas": "Número de empleados",
        "porcentaje": "% del total de empleados",
    },
)

fig.update_traces(
    texttemplate="%{text}%",
    textposition="outside",
    hovertemplate="<b>%{y}</b><br>"
    "Empleados: %{x}<br>"
    "Porcentaje: %{text}%<br>"
    "<extra></extra>",
)

fig.update_layout(
    title="Top 10 Actividades Económicas donde Laboran los Graduados",
    xaxis_title="Número de empleados",
    yaxis_title="Actividad económica",
    showlegend=False,
    height=520,
    margin=dict(l=10, r=10, t=60, b=10),
)

st.plotly_chart(fig, use_container_width=True)

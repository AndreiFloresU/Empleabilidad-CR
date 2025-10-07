import streamlit as st
import plotly.express as px
import pandas as pd
import numpy as np

# Utilidades del proyecto
from utils.datos import init_data, get_data_copy
from utils.filtros import filtros_locales
from utils.estilos import aplicar_tema_plotly, mostrar_tarjeta_nota

# Tema
aplicar_tema_plotly()

# 1️⃣ Nombre de página
st.title("👥 Tasa de Multiempleo")

# 2️⃣ Cargar datos
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

# 4️⃣ Filtrar data laboral solo a esas cédulas
df_lab_filtrado = df_lab[df_lab["cedula"].isin(cedulas_validas)].copy()

# Considerar solo empleados activos si existe el campo
if "labora_actualmente" in df_lab_filtrado.columns:
    df_lab_filtrado["labora_actualmente"] = (
        df_lab_filtrado["labora_actualmente"].astype(str).str.upper().str.strip()
    )
    df_lab_filtrado = df_lab_filtrado[df_lab_filtrado["labora_actualmente"] == "S"]

if df_lab_filtrado.empty:
    st.warning("No hay registros laborales para calcular multiempleo.")
    st.stop()

# 5️⃣ Contar registros laborales por persona
conteo = df_lab_filtrado.groupby("cedula").size().reset_index(name="num_empleos")

# Clasificar en multiempleado o no
conteo["multiempleo"] = np.where(
    conteo["num_empleos"] > 1, "Sí (más de 1 empleo)", "No (1 empleo)"
)

# 6️⃣ Calcular totales y porcentaje
resumen = (
    conteo.groupby("multiempleo")["cedula"].count().reset_index(name="total_personas")
)

total = resumen["total_personas"].sum()
resumen["porcentaje"] = (resumen["total_personas"] / total * 100).round(1)

# 7️⃣ Gráfico de barras
fig = px.bar(
    resumen,
    x="multiempleo",
    y="porcentaje",
    text="porcentaje",
    color="multiempleo",
    color_discrete_sequence=["#224d67", "#F58518"],
    labels={
        "multiempleo": "Condición de empleo",
        "porcentaje": "Porcentaje (%)",
    },
    custom_data=[
        "total_personas",
        "porcentaje",
    ],  # Correctly pass customdata through px.bar
)

fig.update_traces(
    texttemplate="%{text}%",
    textposition="outside",
    hovertemplate="<b>%{x}</b><br>"
    "Personas: %{customdata[0]}<br>"
    "Porcentaje: %{customdata[1]}%<br>"
    "<extra></extra>",
)

fig.update_layout(
    title="Tasa de multiempleo — % con más de un registro laboral",
    yaxis_title="Porcentaje de personas",
    xaxis_title="Condición laboral",
    height=450,
    showlegend=False,
    margin=dict(l=10, r=10, t=60, b=10),
)

st.plotly_chart(fig, use_container_width=True)

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

# 1) Título
st.title("🏢 Top 10 empleadores")

# 2) Carga de datos
init_data()
df_grad = get_data_copy("Graduados")
df_lab = get_data_copy("DataLaboral")

# Normalizar columnas
df_grad.columns = df_grad.columns.str.strip().str.lower()
df_lab.columns = df_lab.columns.str.strip().str.lower()

# 3) Filtros base (una universidad)
df_grad_filtrado, cedulas_filtradas, selections = filtros_locales(df_grad)
if df_grad_filtrado.empty:
    st.warning("No hay datos disponibles con los filtros seleccionados.")
    st.stop()

cedulas_validas = set(cedulas_filtradas)
if not cedulas_validas:
    st.warning("No hay cédulas válidas tras aplicar los filtros.")
    st.stop()

# 4) Subconjunto laboral (solo cédulas filtradas)
df_lab_ok = df_lab[df_lab["cedula"].isin(cedulas_validas)].copy()

# Si existe labora_actualmente, filtrar a 'S'
if "labora_actualmente" in df_lab_ok.columns:
    df_lab_ok["labora_actualmente"] = (
        df_lab_ok["labora_actualmente"].astype(str).str.upper().str.strip()
    )
    df_lab_ok = df_lab_ok[df_lab_ok["labora_actualmente"] == "S"]

# Validaciones mínimas
if "nombre_patrono" not in df_lab_ok.columns:
    st.error("No se encontró la columna 'nombre_patrono' en DataLaboral.")
    st.stop()
if "tipo_patrono" not in df_lab_ok.columns:
    df_lab_ok["tipo_patrono"] = (
        np.nan
    )  # si no existe, la creamos vacía para evitar errores

# 5) Limpieza de nombre de patrono
df_lab_ok["nombre_patrono"] = df_lab_ok["nombre_patrono"].astype(str).str.strip()
df_lab_ok = df_lab_ok.replace(
    {"nombre_patrono": {"": np.nan, "SIN INFORMACION": np.nan, "NA": np.nan}}
)
df_lab_ok = df_lab_ok.dropna(subset=["nombre_patrono"])

if df_lab_ok.empty:
    st.warning(
        "No hay registros laborales con nombre de empleador para el filtro actual."
    )
    st.stop()

# 6) Conteo de empleados únicos por patrono
#    (una persona cuenta una vez por empleador aunque tenga múltiples filas)
conteo = (
    df_lab_ok.groupby("nombre_patrono")["cedula"]
    .nunique()
    .reset_index(name="empleados_unicos")
)

# 7) Tipo de patrono (más frecuente por empleador)
tipo_pref = (
    df_lab_ok.groupby(["nombre_patrono", "tipo_patrono"])["cedula"]
    .count()
    .rename("n")
    .reset_index()
    .sort_values(["nombre_patrono", "n"], ascending=[True, False])
    .drop_duplicates(subset=["nombre_patrono"])[["nombre_patrono", "tipo_patrono"]]
)

top = conteo.merge(tipo_pref, on="nombre_patrono", how="left")

# 8) Top 10 y % recalculado sobre el top (suma = 100 %)
# Excluir patronos 'None' o vacíos
top = top[top["nombre_patrono"].notna()]
top = top[top["nombre_patrono"].str.lower() != "none"]

if top.empty:
    st.warning("No hay empleadores válidos después de limpiar los nombres.")
    st.stop()

# Ordenar por empleados y seleccionar los 10 mayores
top = top.sort_values("empleados_unicos", ascending=False).head(10)

# Recalcular % solo dentro del top 10
total_top = top["empleados_unicos"].sum()
top["porcentaje"] = (top["empleados_unicos"] / total_top * 100).round(1)

# Orden para barras horizontales (menor arriba)
top = top.sort_values("empleados_unicos", ascending=True)

# Texto a mostrar en la barra (solo porcentaje)
top["label_bar"] = top["porcentaje"].astype(str) + "%"


# 9) Gráfico de barras horizontales
fig = px.bar(
    top,
    x="empleados_unicos",
    y="nombre_patrono",
    orientation="h",
    text="label_bar",
    labels={
        "empleados_unicos": "Empleados únicos",
        "nombre_patrono": "Empleador",
    },
)

# Hover con tipo_patrono y % del total
fig.update_traces(
    hovertemplate="<b>%{y}</b><br>"
    "Empleados: %{x}<br>"
    "Porcentaje: %{customdata[0]}%<br>"
    "Tipo de patrono: %{customdata[1]}<br>"
    "<extra></extra>",
    customdata=np.stack([top["porcentaje"], top["tipo_patrono"].fillna("—")], axis=-1),
    textposition="outside",
)

fig.update_layout(
    title="Top 10 empleadores — número y % del total de empleados",
    xaxis_title="Empleados únicos (cédulas)",
    yaxis_title="Empleador",
    height=550,
    margin=dict(l=10, r=10, t=60, b=10),
)

st.plotly_chart(fig, use_container_width=True)

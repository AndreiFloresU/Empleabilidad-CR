import streamlit as st
import plotly.express as px
import pandas as pd
import numpy as np

# Importar utilidades
from utils.datos import init_data, get_data_copy
from utils.filtros import filtros_locales
from utils.estilos import aplicar_tema_plotly, mostrar_tarjeta_nota

aplicar_tema_plotly()

st.title("📊 Empleabilidad por Año de Graduacion")

# Initialize data
init_data()
df_graduados = get_data_copy("Graduados")
df_laboral = get_data_copy("DataLaboral")

# Normalizar columnas
df_graduados.columns = df_graduados.columns.str.strip().str.lower()
df_laboral.columns = df_laboral.columns.str.strip().str.lower()

# 2. Filtros
df_grad_filtrado, cedulas_filtradas, selections = filtros_locales(df_graduados)

if df_grad_filtrado.empty:
    st.warning("No hay datos disponibles con los filtros seleccionados.")
    st.stop()


# 3. Cálculo de empleabilidad
@st.cache_data
def calcular_empleabilidad_por_cohorte(df_grad, df_lab, cedulas_validas):
    """
    Calcula la tasa de empleabilidad por cohorte (una sola universidad ya filtrada).
    """
    # Filtrar solo graduados válidos
    df_grad_valido = df_grad[df_grad["cedula"].isin(cedulas_validas)].copy()

    # Contar graduados por cohorte
    graduados_por_cohorte = (
        df_grad_valido.groupby("anio_graduacion")["cedula"]
        .nunique()
        .reset_index(name="total_graduados")
    )

    # Filtrar empleados (solo cédulas válidas)
    df_lab_valido = df_lab[df_lab["cedula"].isin(cedulas_validas)].copy()

    # Unir con cohorte para cada empleado
    df_empleados = df_lab_valido.merge(
        df_grad_valido[["cedula", "anio_graduacion"]],
        on="cedula",
        how="left",
    )

    # Contar empleados por cohorte
    empleados_por_cohorte = (
        df_empleados.groupby("anio_graduacion")["cedula"]
        .nunique()
        .reset_index(name="total_empleados")
    )

    # Combinar datos
    resultado = graduados_por_cohorte.merge(
        empleados_por_cohorte, on="anio_graduacion", how="left"
    )
    resultado["total_empleados"] = resultado["total_empleados"].fillna(0)
    resultado["tasa_empleabilidad"] = (
        resultado["total_empleados"] / resultado["total_graduados"] * 100
    ).round(1)

    return resultado


# Calcular empleabilidad
df_empleabilidad = calcular_empleabilidad_por_cohorte(
    df_grad_filtrado, df_laboral, cedulas_filtradas
)

if df_empleabilidad.empty:
    st.warning("No hay datos de empleabilidad para mostrar con los filtros aplicados.")
    st.stop()

# Ordenar por cohorte cronológicamente
df_empleabilidad = df_empleabilidad.sort_values("anio_graduacion")

universidad_seleccionada = selections.get("Universidad", "Universidad")
df_empleabilidad["universidad"] = universidad_seleccionada

# 4. Gráfico
fig = px.line(
    df_empleabilidad,
    x="anio_graduacion",
    y="tasa_empleabilidad",
    color="universidad",
    title="Evolución de la Empleabilidad por Año de Graduacion",
    labels={
        "tasa_empleabilidad": "Tasa de Empleabilidad (%)",
        "anio_graduacion": "Año de Graduación",
        "universidad": "Universidad",
    },
    markers=True,
    hover_data={
        "total_graduados": True,
        "total_empleados": True,
        "anio_graduacion": False,
        "universidad": False,
    },
)

fig.update_traces(
    mode="lines+markers+text",
    textposition="top center",
    texttemplate="%{y}%",
    hovertemplate="<b>%{fullData.name}</b><br>"
    + "Año de Graduacion: %{x}<br>"
    + "Empleabilidad: %{y}%<br>"
    + "Graduados: %{customdata[0]}<br>"
    + "Empleados: %{customdata[1]}<br>"
    + "<extra></extra>",
)

años_unicos = sorted(df_empleabilidad["anio_graduacion"].unique())

fig.update_layout(
    height=500,
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    xaxis_title="Año de Graduación",
    yaxis_title="Tasa de Empleabilidad (%)",
    xaxis_tickangle=-45,
    xaxis=dict(
        tickmode="array",
        tickvals=años_unicos,
        ticktext=[str(año) for año in años_unicos],
        dtick=1,
    ),
)

st.plotly_chart(fig, use_container_width=True)

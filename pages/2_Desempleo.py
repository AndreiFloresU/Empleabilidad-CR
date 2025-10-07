import streamlit as st
import plotly.express as px
import pandas as pd
import numpy as np

# Importar utilidades
from utils.datos import init_data, get_data_copy
from utils.filtros import filtros_locales
from utils.estilos import aplicar_tema_plotly, mostrar_tarjeta_nota

# ALWAYS apply custom theme
aplicar_tema_plotly()

# 1. Nombre Página
st.title("📉 Desempleabilidad por Año de Graduacion")

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


# 3. Cálculo de desempleabilidad
@st.cache_data
def calcular_desempleabilidad_por_cohorte(df_grad, df_lab, cedulas_validas):
    """
    Calcula la tasa de desempleabilidad por cohorte (una sola universidad ya filtrada).
    DataLaboral contiene únicamente personas empleadas al corte.
    """
    # 1) Graduados válidos (denominador)
    df_grad_valido = df_grad[df_grad["cedula"].isin(cedulas_validas)].copy()

    graduados_por_cohorte = (
        df_grad_valido.groupby("anio_graduacion")["cedula"]
        .nunique()
        .reset_index(name="total_graduados")
    )

    # 2) Empleados (numerador para empleo) → luego derivamos no empleados
    df_lab_valido = df_lab[df_lab["cedula"].isin(cedulas_validas)].copy()

    df_empleados = df_lab_valido.merge(
        df_grad_valido[["cedula", "anio_graduacion"]],
        on="cedula",
        how="left",
    )

    empleados_por_cohorte = (
        df_empleados.groupby("anio_graduacion")["cedula"]
        .nunique()
        .reset_index(name="total_empleados")
    )

    # 3) Combinar y calcular no empleados y tasa de desempleabilidad
    resultado = graduados_por_cohorte.merge(
        empleados_por_cohorte, on="anio_graduacion", how="left"
    )
    resultado["total_empleados"] = resultado["total_empleados"].fillna(0)

    # Asegurar no negativos si hubiera alguna inconsistencia
    resultado["total_no_empleados"] = (
        resultado["total_graduados"] - resultado["total_empleados"]
    ).clip(lower=0)

    # Evitar división por cero
    resultado["tasa_desempleabilidad"] = np.where(
        resultado["total_graduados"] > 0,
        (resultado["total_no_empleados"] / resultado["total_graduados"] * 100).round(1),
        0.0,
    )

    return resultado


# Calcular
df_desempleabilidad = calcular_desempleabilidad_por_cohorte(
    df_grad_filtrado, df_laboral, cedulas_filtradas
)

if df_desempleabilidad.empty:
    st.warning(
        "No hay datos de desempleabilidad para mostrar con los filtros aplicados."
    )
    st.stop()

# Ordenar por cohorte
df_desempleabilidad = df_desempleabilidad.sort_values("anio_graduacion")

# Etiqueta de universidad para color/leyenda (columna constante)
universidad_seleccionada = selections.get("Universidad", "Universidad")
df_desempleabilidad["universidad"] = universidad_seleccionada

# 4. Gráfico
fig = px.line(
    df_desempleabilidad,
    x="anio_graduacion",
    y="tasa_desempleabilidad",
    color="universidad",
    title="Evolución de la Desempleabilidad por Año de Graduacion",
    labels={
        "tasa_desempleabilidad": "Tasa de Desempleabilidad (%)",
        "anio_graduacion": "Año de Graduación",
        "universidad": "Universidad",
    },
    markers=True,
    custom_data=["total_graduados", "total_no_empleados"],
    hover_data={
        "total_graduados": True,
        "total_no_empleados": True,
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
    + "Desempleabilidad: %{y}%<br>"
    + "Graduados: %{customdata[0]}<br>"
    + "No empleados: %{customdata[1]}<br>"
    + "<extra></extra>",
)

# Eje X con todos los años presentes
años_unicos = sorted(df_desempleabilidad["anio_graduacion"].unique())
fig.update_layout(
    height=500,
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    xaxis_title="Año de Graduación",
    yaxis_title="Tasa de Desempleabilidad (%)",
    xaxis_tickangle=-45,
    xaxis=dict(
        tickmode="array",
        tickvals=años_unicos,
        ticktext=[str(a) for a in años_unicos],
        dtick=1,
    ),
)

st.plotly_chart(fig, use_container_width=True)

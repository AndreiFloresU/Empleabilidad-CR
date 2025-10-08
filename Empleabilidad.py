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


@st.cache_data
def calcular_empleabilidad_general(
    df_grad,
    df_lab,
    universidad=None,
    nivel=None,
    facultad=None,
    carrera=None,
    enfasis=None,
):
    """
    Calcula la tasa de empleabilidad general considerando los filtros seleccionados.
    """
    # Filtrar según los filtros especificados
    filtered_df = df_grad.copy()

    if universidad and universidad != "Todos":
        filtered_df = filtered_df[filtered_df["universidad"] == universidad]
    if nivel and nivel != "Todos":
        filtered_df = filtered_df[filtered_df["grado"] == nivel]
    if facultad and facultad != "Todos":
        filtered_df = filtered_df[filtered_df["facultad"] == facultad]
    if carrera and carrera != "Todos":
        filtered_df = filtered_df[filtered_df["carrera"] == carrera]
    if enfasis and enfasis != "Todos":
        filtered_df = filtered_df[filtered_df["enfasis"] == enfasis]

    # Obtener cédulas únicas de graduados filtrados
    cedulas_validas = set(filtered_df["cedula"].dropna().astype(str).unique().tolist())

    # Contar total de graduados
    total_graduados = len(cedulas_validas)

    if total_graduados == 0:
        return 0, 0, 0

    # Contar graduados empleados
    cedulas_empleados = set(df_lab["cedula"].dropna().astype(str).unique().tolist())
    empleados = len(cedulas_validas.intersection(cedulas_empleados))

    # Calcular tasas
    tasa_empleabilidad = (empleados / total_graduados) * 100
    tasa_desempleo = 100 - tasa_empleabilidad

    return round(tasa_empleabilidad, 1), round(tasa_desempleo, 1), total_graduados


# Obtener valores de los filtros seleccionados
universidad_seleccionada = selections.get("Universidad")
nivel_seleccionado = selections.get("Nivel")
facultad_seleccionada = selections.get("Facultad")
carrera_seleccionada = selections.get("Carrera")
enfasis_seleccionado = selections.get("Enfasis")

# Calcular empleabilidad general aplicando todos los filtros
tasa_empleo, tasa_desempleo, total_graduados = calcular_empleabilidad_general(
    df_graduados,
    df_laboral,
    universidad=universidad_seleccionada,
    nivel=nivel_seleccionado,
    facultad=facultad_seleccionada,
    carrera=carrera_seleccionada,
    enfasis=enfasis_seleccionado,
)

# === 4. Visualización en tarjetas
st.markdown("### 📊 Resultados")


def tarjeta(title, value, color="#ffffff", icon="✅"):
    st.markdown(
        f"""
    <div style='background-color:{color};padding:1.2rem 1rem;border-radius:12px;
                box-shadow: 0 2px 6px rgba(0,0,0,0.1);text-align:center;
                border-left: 8px solid #6C63FF; margin-bottom:15px'>
        <div style='font-size:1.1rem;font-weight:bold;margin-bottom:5px;'>{icon} {title}</div>
        <div style='font-size:2rem;color:#333'>{value}</div>
    </div>
    """,
        unsafe_allow_html=True,
    )


col1, col2 = st.columns(2)
with col1:
    tarjeta(
        "Tasa de Empleabilidad",
        f"{tasa_empleo}%",
        icon="📈",
    )
with col2:
    tarjeta(
        "Tasa de Desempleo",
        f"{tasa_desempleo}%",
        icon="📉",
    )

col3, col4 = st.columns(2)
with col3:
    tarjeta(
        "Total de Graduados",
        f"{total_graduados:,}",
        icon="🎓",
    )
with col4:
    tarjeta(
        "Total de Empleados",
        f"{int(total_graduados * tasa_empleo / 100):,}",
        icon="💼",
    )

# 5. Calcular empleabilidad por cohorte para el gráfico
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

# Gráfico
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

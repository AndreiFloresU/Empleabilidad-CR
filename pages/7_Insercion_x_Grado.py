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
st.title("📚 Inserción por nivel de grado")

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

# 4) Columna de grado a usar
if "grado" in df_grad_filtrado.columns:
    col_grado = "grado"
elif "cod_grado" in df_grad_filtrado.columns:
    col_grado = "cod_grado"
else:
    st.error(
        "No se encontró una columna de grado ('grado' o 'cod_grado') en Graduados."
    )
    st.stop()

# 5) Denominador: graduados únicos por grado
dfg = (
    df_grad_filtrado[df_grad_filtrado["cedula"].isin(cedulas_validas)][
        ["cedula", col_grado]
    ]
    .dropna(subset=[col_grado])
    .copy()
)

denominador = (
    dfg.groupby(col_grado)["cedula"].nunique().reset_index(name="total_graduados")
)

# 6) Numerador: empleados únicos por grado
dfl = df_lab[df_lab["cedula"].isin(cedulas_validas)].copy()
if "labora_actualmente" in dfl.columns:
    dfl["labora_actualmente"] = (
        dfl["labora_actualmente"].astype(str).str.upper().str.strip()
    )
    dfl = dfl[dfl["labora_actualmente"] == "S"]

empleos = dfl.merge(dfg, on="cedula", how="inner")

numerador = (
    empleos.groupby(col_grado)["cedula"].nunique().reset_index(name="total_empleados")
)

# 7) Combinar y calcular no empleados y % empleados (manual, sin barnorm)
res = denominador.merge(numerador, on=col_grado, how="left").fillna(
    {"total_empleados": 0}
)
res["total_no_empleados"] = (res["total_graduados"] - res["total_empleados"]).clip(
    lower=0
)
res["pct_empleados"] = np.where(
    res["total_graduados"] > 0,
    (res["total_empleados"] / res["total_graduados"] * 100).round(1),
    0.0,
)
res["pct_no_empleados"] = (100 - res["pct_empleados"]).round(1)

# 8) Formato largo para barras apiladas (y=pct; hover con cantidades)
stack_df = pd.concat(
    [
        res[[col_grado]].assign(
            condicion="Empleados",
            pct=res["pct_empleados"],
            cnt=res["total_empleados"],
            total=res["total_graduados"],
        ),
        res[[col_grado]].assign(
            condicion="No empleados",
            pct=res["pct_no_empleados"],
            cnt=res["total_no_empleados"],
            total=res["total_graduados"],
        ),
    ],
    ignore_index=True,
)

if stack_df.empty or stack_df["pct"].fillna(0).sum() == 0:
    st.warning(
        "No hay datos suficientes para construir el gráfico con la configuración actual."
    )
    st.stop()

# 9) Gráfico (sin barnorm; usamos y=pct y apilado)
fig = px.bar(
    stack_df,
    x=col_grado,
    y="pct",
    color="condicion",
    barmode="stack",
    text="pct",  # mostramos el % sobre la barra
    labels={
        col_grado: "Grado",
        "pct": "% dentro del grado",
        "condicion": "Condición",
    },
    # Omitimos hover_data para evitar el bug de versiones viejas (no pasar bool aquí)
)

# Texto de las barras como porcentaje
fig.update_traces(
    texttemplate="%{text}%",
    textposition="outside",
    cliponaxis=False,  # permite que el texto salga del área si es >100% de ancho
)

# Hover con cantidades y % claros (cnt y total vienen en customdata)
customdata = stack_df[["cnt", "total", "pct"]].values
fig.update_traces(
    customdata=customdata,
    hovertemplate="<b>%{x}</b> — %{fullData.name}<br>"
    "Cantidad: %{customdata[0]}<br>"
    "Graduados en el grado: %{customdata[1]}<br>"
    "Porcentaje: %{customdata[2]}%<br>"
    "<extra></extra>",
)

fig.update_layout(
    title="Inserción por nivel de grado — % empleados por grado",
    xaxis_title="Grado",
    yaxis_title="% dentro del grado",
    yaxis=dict(range=[0, 100]),  # eje de 0 a 100
    legend_title="Condición",
    height=520,
    margin=dict(l=10, r=10, t=60, b=10),
)

st.plotly_chart(fig, use_container_width=True)

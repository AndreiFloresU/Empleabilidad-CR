import streamlit as st
import plotly.express as px
import pandas as pd
import numpy as np

# Importar utilidades del proyecto
from utils.datos import init_data, get_data_copy
from utils.filtros import filtros_locales
from utils.estilos import aplicar_tema_plotly, mostrar_tarjeta_nota

# Aplicar tema personalizado
aplicar_tema_plotly()

# 1️⃣ Nombre Página
st.title("🔥 Heatmap Empleabilidad")

# 2️⃣ Cargar datos
init_data()
df_grad = get_data_copy("Graduados")
df_lab = get_data_copy("DataLaboral")

# Normalizar columnas
df_grad.columns = df_grad.columns.str.strip().str.lower()
df_lab.columns = df_lab.columns.str.strip().str.lower()

# 3️⃣ Filtros base
df_grad_filtrado, cedulas_filtradas, selections = filtros_locales(df_grad)
if df_grad_filtrado.empty:
    st.warning("No hay datos disponibles con los filtros seleccionados.")
    st.stop()

# 4️⃣ Control: seleccionar eje de columnas
col_dim = st.radio(
    "Columnas del heatmap",
    options=["Año de Graduacion", "Grado"],
    index=0,
    horizontal=True,
)

columna_columnas = "anio_graduacion" if "Año de Graduacion" in col_dim else "grado"

# 5️⃣ Crear columna combinada Carrera — Énfasis (si existe)
df_grad_filtrado = df_grad_filtrado.copy()
if "enfasis" in df_grad_filtrado.columns:
    df_grad_filtrado["carrera_enfasis"] = (
        df_grad_filtrado["carrera"].astype(str).str.strip()
        + " — "
        + df_grad_filtrado["enfasis"].fillna("").astype(str).str.strip()
    ).str.replace(r"\s+—\s*$", "", regex=True)
else:
    df_grad_filtrado["carrera_enfasis"] = df_grad_filtrado["carrera"]

columna_filas = "carrera_enfasis"

# 6️⃣ Cédulas válidas
cedulas_validas = set(cedulas_filtradas)
if not cedulas_validas:
    st.warning("No hay cédulas válidas tras aplicar los filtros.")
    st.stop()

# 7️⃣ Denominador: graduados únicos
dfg = (
    df_grad_filtrado[df_grad_filtrado["cedula"].isin(cedulas_validas)][
        [columna_filas, columna_columnas, "cedula", "facultad"]
    ]
    .dropna(subset=[columna_filas, columna_columnas])
    .copy()
)

graduados = (
    dfg.groupby([columna_filas, columna_columnas])["cedula"]
    .nunique()
    .reset_index(name="total_graduados")
)

# 8️⃣ Numerador: empleados únicos (mapeo por cédula)
dfl = df_lab[df_lab["cedula"].isin(cedulas_validas)].copy()
empleos = dfl.merge(
    dfg[[columna_filas, columna_columnas, "cedula"]].drop_duplicates(),
    on="cedula",
    how="inner",
)

empleados = (
    empleos.groupby([columna_filas, columna_columnas])["cedula"]
    .nunique()
    .reset_index(name="total_empleados")
)

# 9️⃣ Combinar y calcular tasa
tabla = graduados.merge(
    empleados, on=[columna_filas, columna_columnas], how="left"
).fillna({"total_empleados": 0})

tabla["tasa_empleabilidad"] = np.where(
    tabla["total_graduados"] > 0,
    (tabla["total_empleados"] / tabla["total_graduados"] * 100).round(1),
    np.nan,
)

# 🔟 Pivotar a matriz (filas=carrera/enfasis, columnas=cohortes o grados)
matriz = tabla.pivot(
    index=columna_filas, columns=columna_columnas, values="tasa_empleabilidad"
)

# 🔹 Ordenar filas por facultad (automático)
mapa_fac = (
    dfg.groupby([columna_filas, "facultad"])["cedula"]
    .count()
    .reset_index()
    .sort_values([columna_filas, "cedula"], ascending=[True, False])
    .drop_duplicates(subset=[columna_filas])
    .set_index(columna_filas)["facultad"]
)
orden_index = (
    pd.DataFrame({"fila": matriz.index})
    .assign(facultad=matriz.index.map(mapa_fac).fillna(""))
    .sort_values(["facultad", "fila"], kind="mergesort")["fila"]
    .tolist()
)
matriz = matriz.loc[orden_index]
matriz = matriz.reindex(sorted(matriz.columns, key=lambda x: str(x)), axis=1)

if matriz.empty:
    st.warning(
        "No hay datos suficientes para construir el heatmap con la configuración actual."
    )
    st.stop()

# 🔹 Customdata con conteos
tabla_full = tabla.pivot_table(
    index=columna_filas,
    columns=columna_columnas,
    values=["total_graduados", "total_empleados"],
    aggfunc="first",
).reindex(
    index=matriz.index,
    columns=pd.MultiIndex.from_product(
        [["total_graduados", "total_empleados"], matriz.columns]
    ),
)
custom_data = np.dstack(
    [
        tabla_full.xs("total_graduados", level=0, axis=1).values,
        tabla_full.xs("total_empleados", level=0, axis=1).values,
    ]
)

# 🔟.5️⃣ Top N por tasa global (ponderada) a lo largo del eje X
# Opcional: controles
top_n = 10
min_graduados_total = 1  # ajusta si quieres filtrar carreras con muy pocos graduados

# 1) Determinar las columnas del eje X que quedaron en la matriz
cols_x = list(matriz.columns)

# 2) Traer los totales por fila y por cada columna x (cohorte/grado) desde 'tabla'
#    y quedarnos solo con las columnas en cols_x
tot_grads_wide = tabla.pivot(
    index=columna_filas, columns=columna_columnas, values="total_graduados"
)
tot_emps_wide = tabla.pivot(
    index=columna_filas, columns=columna_columnas, values="total_empleados"
)

# Alinear a lo que está en la matriz (mismas filas y columnas)
tot_grads_wide = tot_grads_wide.reindex(index=matriz.index, columns=cols_x)
tot_emps_wide = tot_emps_wide.reindex(index=matriz.index, columns=cols_x)

# 3) Sumar por fila a lo largo de TODO el eje X
sum_grads = tot_grads_wide.sum(axis=1, skipna=True)
sum_emps = tot_emps_wide.sum(axis=1, skipna=True)

# 4) Calcular tasa global ponderada (penaliza faltantes al no aportar graduados/empleados)
tasa_global = (sum_emps / sum_grads * 100).replace([np.inf, -np.inf], np.nan)

# 5) (Opcional) filtrar por cobertura mínima de graduados
validas_rank = tasa_global[sum_grads >= min_graduados_total].dropna()

if validas_rank.empty:
    st.warning("No hay suficientes datos para calcular el Top con el criterio global.")
    st.stop()

# 6) Tomar Top N según tasa global
top_idx = (
    validas_rank.sort_values(ascending=False).head(min(top_n, len(validas_rank))).index
)

# 7) Filtrar todo al Top N y mantener orden por ranking
matriz = matriz.loc[top_idx]
tabla_full = tabla_full.loc[top_idx]
tot_grads_wide = tot_grads_wide.loc[top_idx, cols_x]
tot_emps_wide = tot_emps_wide.loc[top_idx, cols_x]

# 8) Reconstruir custom_data (en el mismo orden y columnas)
custom_data = np.dstack(
    [
        tot_grads_wide.values,
        tot_emps_wide.values,
    ]
)


# 11️⃣ Heatmap
fig = px.imshow(
    matriz,
    text_auto=True,
    aspect="auto",
    origin="upper",
    color_continuous_scale="Blues",
    labels=dict(color="% empleados"),
)

hover_template = (
    f"{columna_filas}: %{{y}}<br>"
    f"{'Año de Graduacion' if columna_columnas=='anio_graduacion' else 'Grado'}: %{{x}}<br>"
    "Empleabilidad: %{z}%<br>"
    "Graduados: %{customdata[0]}<br>"
    "Empleados: %{customdata[1]}<br>"
    "<extra></extra>"
)
fig.update_traces(customdata=custom_data, hovertemplate=hover_template)

fig.update_layout(
    title=f"Empleabilidad por {columna_filas.capitalize()} × "
    f"{'Año de Graduacion' if columna_columnas=='anio_graduacion' else 'Grado'}",
    xaxis_title=(
        "Año de Graduacion" if columna_columnas == "anio_graduacion" else "Grado"
    ),
    yaxis_title="Carrera / Énfasis",
    coloraxis_colorbar=dict(title="% empleados"),
    height=600,
)

st.plotly_chart(fig, use_container_width=True)

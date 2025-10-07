import streamlit as st
import plotly.express as px
import pandas as pd
import numpy as np
from pandas.tseries.offsets import DateOffset

# Utilidades del proyecto
from utils.datos import init_data, get_data_copy
from utils.filtros import filtros_locales
from utils.estilos import aplicar_tema_plotly, mostrar_tarjeta_nota

# === Tema ===
aplicar_tema_plotly()

# === 1) Título ===
st.title("⏱️ Tiempo al primer empleo")

# === 2) Carga de datos ===
init_data()
df_grad = get_data_copy("Graduados")
df_lab = get_data_copy("DataLaboral")

# Normalizar columnas
df_grad.columns = df_grad.columns.str.strip().str.lower()
df_lab.columns = df_lab.columns.str.strip().str.lower()

# === 3) Filtros base (una universidad) ===
df_grad_filtrado, cedulas_filtradas, selections = filtros_locales(df_grad)
if df_grad_filtrado.empty:
    st.warning("No hay datos disponibles con los filtros seleccionados.")
    st.stop()

# --- Cohorte fija: 2024 ---
df_grad_filtrado = df_grad_filtrado[
    df_grad_filtrado["anio_graduacion"].astype(str) == "2024"
].copy()
if df_grad_filtrado.empty:
    st.warning(
        "No hay graduados en el Año de Graduacion 2024 con los filtros seleccionados."
    )
    st.stop()

cedulas_validas = set(cedulas_filtradas)
if not cedulas_validas:
    st.warning("No hay cédulas válidas tras aplicar los filtros.")
    st.stop()

# Mantener solo cédulas válidas de la cohorte 2024
cedulas_2024 = set(
    df_grad_filtrado[df_grad_filtrado["cedula"].isin(cedulas_validas)]["cedula"]
    .dropna()
    .astype(str)
    .unique()
    .tolist()
)
if not cedulas_2024:
    st.warning(
        "No hay cédulas válidas en el Año de Graduacion 2024 para calcular el tiempo al primer empleo."
    )
    st.stop()

# === 4) Fechas fijas del ejercicio ===
FECHA_GRAD_FIJA = pd.Timestamp("2024-03-01")  # todas las personas
FECHA_SNAPSHOT = pd.Timestamp("2025-04-01")  # fecha de extracción de DataLaboral

# === 5) Subconjunto laboral: solo esas cédulas y empleo vigente (si existe el campo) ===
dfl = df_lab[df_lab["cedula"].isin(cedulas_2024)].copy()
if dfl.empty:
    st.warning(
        "No hay registros laborales para las cédulas del Año de Graduacion 2024."
    )
    st.stop()

if "labora_actualmente" in dfl.columns:
    dfl["labora_actualmente"] = (
        dfl["labora_actualmente"].astype(str).str.upper().str.strip()
    )
    dfl = dfl[dfl["labora_actualmente"] == "S"]

if dfl.empty:
    st.warning("No hay empleos vigentes para las cédulas del Año de Graduacion 2024.")
    st.stop()

# Requerimos antiguedad_meses para estimar fecha de inicio del empleo
if "antiguedad_meses" not in dfl.columns:
    st.error(
        "No se encontró la columna 'antiguedad_meses' en DataLaboral. No es posible estimar la fecha de inicio."
    )
    st.stop()

# Limpiar y calcular fecha de inicio estimada
dfl = dfl.copy()
dfl["antiguedad_meses"] = pd.to_numeric(dfl["antiguedad_meses"], errors="coerce")
dfl = dfl.dropna(subset=["antiguedad_meses"])
dfl["antiguedad_meses"] = dfl["antiguedad_meses"].astype(int).clip(lower=0)

# fecha_inicio_empleo = FECHA_SNAPSHOT - antiguedad_meses
dfl["fecha_inicio_empleo"] = FECHA_SNAPSHOT - dfl["antiguedad_meses"].apply(
    lambda m: DateOffset(months=int(m))
)

# Mantener solo empleos que comienzan en/tras la graduación (excluir empleos previos a graduación)
dfl = dfl[dfl["fecha_inicio_empleo"] >= FECHA_GRAD_FIJA].copy()
if dfl.empty:
    st.warning(
        "Todos los empleos comienzan antes de la fecha de graduación fija (2024-03-01). No hay datos para mostrar."
    )
    st.stop()

# Para cédulas con múltiples empleos post-graduacion, tomar el más antiguo; si hay empate:
# 1) el de mayor ingreso, y si persiste,
# 2) el primero que aparece en el dataset original.

# Asegurar ingreso numérico
dfl["ingreso_aproximado"] = pd.to_numeric(
    dfl.get("ingreso_aproximado"), errors="coerce"
)

# Guardar el orden original (para desempate final)
dfl = dfl.reset_index(drop=False).rename(columns={"index": "orden_original"})

primer_empleo = (
    dfl.sort_values(
        ["fecha_inicio_empleo", "ingreso_aproximado", "orden_original"],
        ascending=[True, False, True],
        na_position="last",
    )
    .groupby("cedula", as_index=False)
    .first()[["cedula", "fecha_inicio_empleo"]]
)


# Calcular meses desde la graduación al primer empleo
# Diferencia en meses calendario: (año*12 + mes) + ajuste por días
def diff_meses(d_ini: pd.Timestamp, d_fin: pd.Timestamp) -> float:
    # meses completos entre fechas, con ajuste parcial según día
    months = (d_fin.year - d_ini.year) * 12 + (d_fin.month - d_ini.month)
    # ajustar por día del mes (si el día de fin es anterior al día de inicio, restar un mes)
    if d_fin.day < d_ini.day:
        months -= 1
    return float(months)


primer_empleo["meses_al_primer_empleo"] = (
    primer_empleo["fecha_inicio_empleo"]
    .apply(lambda d: diff_meses(FECHA_GRAD_FIJA, d))
    .clip(lower=0)
)

# Quitar outliers imposibles (por si hay datos corruptos)
primer_empleo = primer_empleo[
    primer_empleo["meses_al_primer_empleo"] <= 24
]  # por ejemplo, máx 2 años
if primer_empleo.empty:
    st.warning("No quedaron registros válidos tras limpiar outliers.")
    st.stop()

# === 6) KPIs básicos ===
n_personas = primer_empleo["cedula"].nunique()
mediana_meses = float(primer_empleo["meses_al_primer_empleo"].median())
promedio_meses = round(float(primer_empleo["meses_al_primer_empleo"].mean()), 1)

c1, c2, c3 = st.columns(3)
c1.metric("Personas con empleo post-graduación", f"{n_personas}")
c2.metric("Mediana (meses)", f"{mediana_meses:.1f}")
c3.metric("Promedio (meses)", f"{promedio_meses:.1f}")

# === 7) Histograma / distribución ===
fig = px.histogram(
    primer_empleo,
    x="meses_al_primer_empleo",
    nbins=12,
    labels={"meses_al_primer_empleo": "Meses al primer empleo"},
    title="Distribución: meses al primer empleo (Año de Graduacion 2024)",
)
fig.update_traces(hovertemplate="Meses: %{x}<br>Personas: %{y}<extra></extra>")
fig.update_layout(
    xaxis=dict(dtick=1),
    height=450,
    margin=dict(l=10, r=10, t=60, b=10),
)
st.plotly_chart(fig, use_container_width=True)

# === 8) Tabla resumida opcional (por si deseas revisar) ===
with st.expander("Ver tabla (cedula, fecha_inicio_empleo, meses)"):
    st.dataframe(
        primer_empleo.sort_values("meses_al_primer_empleo").reset_index(drop=True)
    )

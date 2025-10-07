import json
import os
import unicodedata

import streamlit as st
import plotly.express as px
import pandas as pd
import numpy as np

# Utilidades del proyecto
from utils.datos import init_data, get_data_copy
from utils.filtros import filtros_locales
from utils.estilos import aplicar_tema_plotly, mostrar_tarjeta_nota

# === Tema ===
aplicar_tema_plotly()

# === 1) Título ===
st.title("🗺️ Mapa de Empleo por Provincia")

# === 2) Carga de datos ===
init_data()
df_grad = get_data_copy("Graduados")
df_lab = get_data_copy("DataLaboral")
df_loc = get_data_copy("DataLocalizacion")

# Normalizar columnas
for df in (df_grad, df_lab, df_loc):
    df.columns = df.columns.str.strip().str.lower()

# === 3) Filtros base (una universidad) ===
df_grad_filtrado, cedulas_filtradas, selections = filtros_locales(df_grad)
if df_grad_filtrado.empty:
    st.warning("No hay datos disponibles con los filtros seleccionados.")
    st.stop()

cedulas_validas = set(cedulas_filtradas)
if not cedulas_validas:
    st.warning("No hay cédulas válidas tras aplicar los filtros.")
    st.stop()


# === 4) Helper: normalizar nombres de provincia ===
def _norm_str(s: str) -> str:
    if pd.isna(s):
        return ""
    s = str(s).strip()
    s = "".join(
        c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn"
    )
    return s.upper()


# === 5) Denominador: graduados (únicos por provincia) ===
# Tomamos la provincia desde DataLocalizacion para las cédulas válidas.
df_loc_ok = df_loc[df_loc["cedula"].isin(cedulas_validas)].copy()
if "provincia" not in df_loc_ok.columns:
    st.error("No se encontró la columna 'provincia' en DataLocalizacion.")
    st.stop()

df_loc_ok["provincia_norm"] = df_loc_ok["provincia"].apply(_norm_str)
df_loc_ok = df_loc_ok.replace({"provincia_norm": {"": np.nan}}).dropna(
    subset=["provincia_norm"]
)

# Si hay múltiples filas por persona en Localizacion, nos quedamos con la provincia más frecuente por cédula
loc_prefer = (
    df_loc_ok.groupby(["cedula", "provincia_norm"])["provincia_norm"]
    .count()
    .rename("n")
    .reset_index()
    .sort_values(["cedula", "n"], ascending=[True, False])
    .drop_duplicates(subset=["cedula"])
)[["cedula", "provincia_norm"]]

# Graduados de la universidad filtrada (por cédula válidas) con su provincia “preferida”
grad_con_prov = (
    df_grad_filtrado[df_grad_filtrado["cedula"].isin(cedulas_validas)][["cedula"]]
    .drop_duplicates()
    .merge(loc_prefer, on="cedula", how="left")
    .dropna(subset=["provincia_norm"])
)

denominador = (
    grad_con_prov.groupby("provincia_norm")["cedula"]
    .nunique()
    .reset_index(name="total_graduados")
)

# === 6) Numerador: empleados únicos por provincia ===
df_lab_ok = df_lab[df_lab["cedula"].isin(cedulas_validas)].copy()
# Si existe labora_actualmente, filtramos a 'S'
if "labora_actualmente" in df_lab_ok.columns:
    df_lab_ok = df_lab_ok[
        df_lab_ok["labora_actualmente"].astype(str).str.upper().str.strip() == "S"
    ]

# Mapear provincia a cada empleado (usando la provincia preferida por cédula)
empleados_con_prov = (
    df_lab_ok[["cedula"]]
    .drop_duplicates()
    .merge(loc_prefer, on="cedula", how="left")
    .dropna(subset=["provincia_norm"])
)

numerador = (
    empleados_con_prov.groupby("provincia_norm")["cedula"]
    .nunique()
    .reset_index(name="total_empleados")
)

# === 7) Combinar y calcular tasa ===
res = denominador.merge(numerador, on="provincia_norm", how="left").fillna(
    {"total_empleados": 0}
)
res["tasa_empleabilidad"] = np.where(
    res["total_graduados"] > 0,
    (res["total_empleados"] / res["total_graduados"] * 100).round(1),
    np.nan,
)

# === 8) Intentar dibujar coroplético con GeoJSON ===
GEO_PATH = "db/cr_provincias.geojson"  # <-- coloca tu archivo aquí


def _cargar_geo(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _elegir_featureidkey(geojson, provincias_norm_set):
    """
    Intenta detectar qué propiedad del GeoJSON contiene los nombres de provincia.
    Devuelve la clave 'featureidkey' compatible con plotly (e.g., 'properties.NOMBRE').
    """
    candidatos = [
        "properties.NOMBRE",
        "properties.NOMBRE_PROV",
        "properties.PROVINCIA",
        "properties.Provincia",
        "properties.name",
        "properties.admin_name",
        "properties.nombre",
    ]
    # Construir sets de nombres por candidato
    for cand in candidatos:
        parts = cand.split(".")
        ok_vals = []
        for feat in geojson.get("features", []):
            v = feat
            for p in parts:
                v = v.get(p) if isinstance(v, dict) else None
                if v is None:
                    break
            if v is not None:
                ok_vals.append(_norm_str(v))
        inter = set(ok_vals) & provincias_norm_set
        # Si hay intersección razonable, nos quedamos con este cand
        if len(inter) >= max(1, min(3, len(provincias_norm_set) // 2)):
            return cand
    # Si no encontramos una buena, devolvemos el primero por defecto
    return candidatos[0]


def _choropleth(res_df):
    provincias_set = set(res_df["provincia_norm"])
    geo = _cargar_geo(GEO_PATH)
    featureidkey = _elegir_featureidkey(geo, provincias_set)

    fig = px.choropleth(
        res_df,
        geojson=geo,
        locations="provincia_norm",
        color="tasa_empleabilidad",
        featureidkey=featureidkey,
        color_continuous_scale="Blues",
        range_color=(0, 100),
        labels={"tasa_empleabilidad": "% empleados"},
        hover_data={
            "total_graduados": True,
            "total_empleados": True,
            "provincia_norm": False,
        },
    )
    fig.update_traces(
        hovertemplate="Provincia: %{location}<br>"
        "Empleabilidad: %{z}%<br>"
        "Graduados: %{customdata[0]}<br>"
        "Empleados: %{customdata[1]}<br>"
        "<extra></extra>"
    )
    fig.update_geos(fitbounds="locations", visible=False)
    fig.update_layout(
        title="Empleabilidad por provincia (%)",
        coloraxis_colorbar=dict(title="% empleados"),
        height=600,
        margin=dict(l=0, r=0, t=60, b=0),
    )
    return fig


# === 9) Mostrar mapa o fallback ===
try:
    if not os.path.exists(GEO_PATH):
        raise FileNotFoundError(GEO_PATH)
    fig = _choropleth(res)
    st.plotly_chart(fig, use_container_width=True)
except Exception as e:
    st.info(
        f"No se pudo cargar el mapa coroplético ({e}). Se muestra vista alternativa (barras)."
    )
    # Fallback: barras ordenadas
    res_bars = res.sort_values("tasa_empleabilidad", ascending=False)
    fig_bar = px.bar(
        res_bars,
        x="provincia_norm",
        y="tasa_empleabilidad",
        text="tasa_empleabilidad",
        labels={
            "provincia_norm": "Provincia",
            "tasa_empleabilidad": "Tasa de Empleabilidad (%)",
        },
    )
    fig_bar.update_traces(texttemplate="%{text}%", textposition="outside")
    fig_bar.update_layout(
        title="Empleabilidad por provincia (%)",
        yaxis_range=[0, max(100, (res_bars["tasa_empleabilidad"].max() or 0) + 5)],
        height=500,
    )
    st.plotly_chart(fig_bar, use_container_width=True)

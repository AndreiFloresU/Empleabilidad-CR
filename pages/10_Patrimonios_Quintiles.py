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
st.title("💰 Distribución por quintiles de patrimonio")

# === 2) Carga de datos ===
init_data()
df_grad = get_data_copy("Graduados")
df_lab = get_data_copy("DataLaboral")
df_inm = get_data_copy("DataInmueble")
df_mue = get_data_copy("DataMueble")

# Normalizar columnas
for df in (df_grad, df_lab, df_inm, df_mue):
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

# Mantener solo cédulas válidas del universo filtrado
cedulas_df = (
    df_grad_filtrado[df_grad_filtrado["cedula"].isin(cedulas_validas)][["cedula"]]
    .drop_duplicates()
    .copy()
)


# === 4) Helper: convertir números con coma/decimal a float robusto ===
def to_float_safe(s):
    """
    Convierte valores tipo decimal con posibles formatos de Excel/SQL:
    - '9.470.000,00' -> 9470000.00
    - '15100,00'     -> 15100.00
    - 25900.0        -> 25900.0
    - None/NaN       -> NaN
    """
    if pd.isna(s):
        return np.nan
    try:
        # Si ya es numérico
        if isinstance(s, (int, float, np.number)):
            return float(s)
        s = str(s).strip()
        if s == "":
            return np.nan
        # eliminar separadores de miles '.', cambiar coma decimal por punto
        s = s.replace(".", "").replace(",", ".")
        return float(s)
    except Exception:
        return np.nan


# === 5) Agregar ingresos laborales por persona (suma de TODOS sus empleos) ===
ingresos = pd.DataFrame({"cedula": [], "ingreso_aproximado": []})
if not df_lab.empty and "ingreso_aproximado" in df_lab.columns:
    dfl = df_lab[df_lab["cedula"].isin(cedulas_validas)][
        ["cedula", "ingreso_aproximado"]
    ].copy()
    dfl["ingreso_aproximado"] = dfl["ingreso_aproximado"].apply(to_float_safe)
    dfl = dfl.dropna(subset=["ingreso_aproximado"])
    if not dfl.empty:
        ingresos = (
            dfl.groupby("cedula", as_index=False)["ingreso_aproximado"]
            .sum()
            .rename(columns={"ingreso_aproximado": "ingresos"})
        )

# === 6) Agregar valor de inmuebles por persona (suma) ===
inmuebles = pd.DataFrame({"cedula": [], "valor_fiscal": []})
if not df_inm.empty and "valor_fiscal" in df_inm.columns:
    dfi = df_inm[df_inm["cedula"].isin(cedulas_validas)][
        ["cedula", "valor_fiscal"]
    ].copy()
    dfi["valor_fiscal"] = dfi["valor_fiscal"].apply(to_float_safe)
    dfi = dfi.dropna(subset=["valor_fiscal"])
    if not dfi.empty:
        inmuebles = (
            dfi.groupby("cedula", as_index=False)["valor_fiscal"]
            .sum()
            .rename(columns={"valor_fiscal": "valor_inmueble"})
        )

# === 7) Agregar valor de muebles por persona (suma) ===
muebles = pd.DataFrame({"cedula": [], "valor_contrato": []})
if not df_mue.empty and "valor_contrato" in df_mue.columns:
    dfm = df_mue[df_mue["cedula"].isin(cedulas_validas)][
        ["cedula", "valor_contrato"]
    ].copy()
    dfm["valor_contrato"] = dfm["valor_contrato"].apply(to_float_safe)
    dfm = dfm.dropna(subset=["valor_contrato"])
    if not dfm.empty:
        muebles = (
            dfm.groupby("cedula", as_index=False)["valor_contrato"]
            .sum()
            .rename(columns={"valor_contrato": "valor_mueble"})
        )

# === 8) Unir todo al universo de cédulas filtradas ===
patrimonio = (
    cedulas_df.merge(ingresos, on="cedula", how="left")
    .merge(inmuebles, on="cedula", how="left")
    .merge(muebles, on="cedula", how="left")
)

for col in ["ingresos", "valor_inmueble", "valor_mueble"]:
    if col not in patrimonio.columns:
        patrimonio[col] = 0.0
    patrimonio[col] = patrimonio[col].fillna(0.0)

patrimonio["patrimonio_total"] = (
    patrimonio["ingresos"] + patrimonio["valor_inmueble"] + patrimonio["valor_mueble"]
)

if (
    patrimonio["patrimonio_total"].sum() == 0
    and patrimonio["patrimonio_total"].nunique() == 1
):
    st.warning(
        "Todos los patrimonios resultaron en 0. No es posible calcular quintiles."
    )
    st.stop()

# === 9) Asignar quintiles robustos (Q1 = patrimonio 0; Q2–Q5 = cuartiles sobre positivos) ===
labels_all = ["Q1", "Q2", "Q3", "Q4", "Q5"]
patrimonio["quintil"] = pd.NA  # inicializar

vals = patrimonio[["cedula", "patrimonio_total"]].copy()
mask_zero = vals["patrimonio_total"] <= 0
mask_pos = ~mask_zero

n_zero = int(mask_zero.sum())
n_pos = int(mask_pos.sum())

if n_zero > 0 and n_pos > 0:
    # Q1: todos los ceros
    patrimonio.loc[mask_zero, "quintil"] = "Q1"

    # Q2–Q5: repartir positivos en 4 cuartiles por frecuencia (estable con rank)
    pos_vals = vals.loc[mask_pos].copy()
    try:
        pos_vals["qpos"] = pd.qcut(
            pos_vals["patrimonio_total"].rank(method="average"),
            4,
            labels=["Q2", "Q3", "Q4", "Q5"],
        )
    except ValueError:
        # Fallback si hay muchos empates: partición equitativa del orden
        pos_vals = pos_vals.sort_values(
            "patrimonio_total", kind="mergesort"
        ).reset_index(drop=True)
        k = min(4, len(pos_vals))  # si hay pocos, menos grupos
        bins = np.array_split(np.arange(len(pos_vals)), k)
        lab = ["Q2", "Q3", "Q4", "Q5"][:k]
        labels_per_index = np.empty(len(pos_vals), dtype=object)
        for i, idxs in enumerate(bins):
            labels_per_index[idxs] = lab[i]
        pos_vals["qpos"] = labels_per_index

    patrimonio = patrimonio.merge(pos_vals[["cedula", "qpos"]], on="cedula", how="left")
    patrimonio["quintil"] = patrimonio["quintil"].fillna(patrimonio.pop("qpos"))

else:
    # No hay ceros o no hay positivos: repartir todo en hasta 5 grupos por frecuencia
    try:
        patrimonio["quintil"] = pd.qcut(
            patrimonio["patrimonio_total"].rank(method="average"), 5, labels=labels_all
        )
    except ValueError:
        pat_sorted = (
            patrimonio[["cedula", "patrimonio_total"]]
            .sort_values("patrimonio_total", kind="mergesort")
            .reset_index(drop=True)
        )
        k = min(5, len(pat_sorted))
        bins = np.array_split(np.arange(len(pat_sorted)), k)
        lab = labels_all[:k]
        labels_per_index = np.empty(len(pat_sorted), dtype=object)
        for i, idxs in enumerate(bins):
            labels_per_index[idxs] = lab[i]
        pat_sorted["quintil"] = labels_per_index
        patrimonio = patrimonio.merge(
            pat_sorted[["cedula", "quintil"]],
            on="cedula",
            how="left",
            suffixes=("", "_new"),
        )
        patrimonio["quintil"] = patrimonio["quintil"].fillna(
            patrimonio.pop("quintil_new")
        )

# Asegurar orden Q1..Q5 para gráficos y tablas
patrimonio["quintil"] = pd.Categorical(
    patrimonio["quintil"], categories=labels_all, ordered=True
)

# === 9.1) Mostrar rangos por quintil en consola ===
import numpy as np

print("\n[Rangos por quintil - basado en datos asignados]")

rangos_quintil = (
    patrimonio.groupby("quintil")["patrimonio_total"]
    .agg(
        n="count",
        min_val="min",
        p25=lambda x: np.nanpercentile(x, 25),
        mediana="median",
        p75=lambda x: np.nanpercentile(x, 75),
        max_val="max",
    )
    .reset_index()
    .sort_values("quintil")
)

for _, r in rangos_quintil.iterrows():
    if pd.isna(r["min_val"]):
        continue
    print(
        f"{r['quintil']}: "
        f"n={int(r['n'])} | "
        f"min={r['min_val']:.2f} | p25={r['p25']:.2f} | mediana={r['mediana']:.2f} | "
        f"p75={r['p75']:.2f} | max={r['max_val']:.2f}"
    )

# (Opcional) Bordes teóricos para solo valores positivos
pos_vals = patrimonio.loc[patrimonio["patrimonio_total"] > 0, "patrimonio_total"]
if not pos_vals.empty:
    qtiles = np.nanpercentile(pos_vals, [0, 25, 50, 75, 100])
    print("\n[Bordes teóricos entre positivos]")
    print(f"P0–P25 : [{qtiles[0]:.2f}, {qtiles[1]:.2f})")
    print(f"P25–P50: [{qtiles[1]:.2f}, {qtiles[2]:.2f})")
    print(f"P50–P75: [{qtiles[2]:.2f}, {qtiles[3]:.2f})")
    print(f"P75–P100:[{qtiles[3]:.2f}, {qtiles[4]:.2f}]")
else:
    print("\n[No hay patrimonios positivos para calcular bordes teóricos]")


# === 10) Resumen por quintil (conteo y %) ===
resumen = (
    patrimonio.groupby("quintil")["cedula"]
    .nunique()
    .reset_index(name="personas")
    .sort_values("quintil")  # Q1..Q5
)
total_personas = resumen["personas"].sum()
resumen["porcentaje"] = (resumen["personas"] / total_personas * 100).round(1)

# Para hover: stats por quintil
stats_q = (
    patrimonio.groupby("quintil")["patrimonio_total"]
    .agg(
        p25=lambda x: np.nanpercentile(x, 25),
        p50="median",
        p75=lambda x: np.nanpercentile(x, 75),
        promedio="mean",
        min="min",
        max="max",
    )
    .reset_index()
)
resumen = resumen.merge(stats_q, on="quintil", how="left")

# === 11) Gráfico: barras verticales por quintil ===
fig = px.bar(
    resumen,
    x="quintil",
    y="personas",
    text="porcentaje",
    labels={"quintil": "Quintil de patrimonio", "personas": "Personas"},
    title="Distribución por quintiles de patrimonio",
)

fig.update_traces(
    texttemplate="%{text}%",
    textposition="outside",
    customdata=np.stack(
        [
            resumen["porcentaje"],
            resumen["min"].round(0),
            resumen["p25"].round(0),
            resumen["p50"].round(0),
            resumen["p75"].round(0),
            resumen["max"].round(0),
            resumen["promedio"].round(0),
        ],
        axis=-1,
    ),
    hovertemplate="<b>%{x}</b><br>"
    "Personas: %{y}<br>"
    "Porcentaje: %{customdata[0]}%<br>"
    "Mín: %{customdata[1]:,.0f}<br>"
    "P25: %{customdata[2]:,.0f}<br>"
    "Mediana: %{customdata[3]:,.0f}<br>"
    "P75: %{customdata[4]:,.0f}<br>"
    "Máx: %{customdata[5]:,.0f}<br>"
    "Promedio: %{customdata[6]:,.0f}<br>"
    "<extra></extra>",
)

fig.update_layout(
    yaxis_title="Personas",
    xaxis_title="Quintil",
    height=520,
    margin=dict(l=10, r=10, t=60, b=10),
)

st.plotly_chart(fig, use_container_width=True)

# === 12) Detalle opcional ===
with st.expander("Ver tabla de patrimonio por persona"):
    cols_show = [
        "cedula",
        "ingresos",
        "valor_inmueble",
        "valor_mueble",
        "patrimonio_total",
        "quintil",
    ]
    st.dataframe(patrimonio[cols_show].sort_values("patrimonio_total"))

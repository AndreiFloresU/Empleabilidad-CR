# utils/filtros.py
from __future__ import annotations
import streamlit as st
import pandas as pd

# Mapeo etiqueta -> nombre de columna real
ORDER = [
    ("Universidad", "universidad"),
    ("Nivel", "grado"),
    ("Facultad", "facultad"),
    ("Carrera", "carrera"),
    ("Enfasis", "enfasis"),
    ("Año de Graduacion", "anio_graduacion"),
    ("Periodo", "cod_graduacion"),
]
COL_ID = "cedula"


def _norm(df):
    d = df.copy()
    d.columns = d.columns.str.strip().str.lower()
    return d


def _options(df, col):
    if col not in df.columns:
        return []
    vals = df[col].dropna().astype(str).sort_values().unique().tolist()
    return ["Todos"] + vals


def _options_universidad(df, col):
    """Opciones especiales para Universidad: sin 'Todos', con ULATINA por defecto."""
    if col not in df.columns:
        return []
    vals = df[col].dropna().astype(str).sort_values().unique().tolist()
    return vals


def _apply(df, col, selected):
    if (selected is None) or (selected == "Todos") or (col not in df.columns):
        return df
    return df[df[col].astype(str) == str(selected)]


def filtros_locales(df_graduados):
    """
    Renderiza filtros en cascada y retorna:
      - df_grad_filtrado
      - set de cédulas filtradas
      - dict {EtiquetaFiltro: valor_seleccionado o 'Todos'}
    """
    df = _norm(df_graduados)

    # Validaciones mínimas
    missing = [c for _, c in ORDER if c not in df.columns] + (
        [COL_ID] if COL_ID not in df.columns else []
    )
    if missing:
        st.error(f"Faltan columnas en Graduados: {', '.join(missing)}")
        st.stop()

    st.markdown(f"### Filtros")

    selections = {}
    df_step = df

    # Procesar filtros en grupos de 2
    for i in range(0, len(ORDER), 2):
        cols = st.columns(2)
        for j in range(2):
            idx = i + j
            if idx >= len(ORDER):
                break

            label, col = ORDER[idx]
            with cols[j]:
                if label == "Universidad":
                    opts = _options_universidad(df_step, col)
                    if not opts:
                        selected = None
                    else:
                        default_index = 0
                        if "Universidad Latina" in opts:
                            default_index = opts.index("Universidad Latina")
                        selected = st.selectbox(
                            label, options=opts, index=default_index, key=f"flt_{label}"
                        )
                else:
                    opts = _options(df_step, col)
                    if not opts:
                        selected = "Todos"
                    else:
                        selected = st.selectbox(
                            label, options=opts, index=0, key=f"flt_{label}"
                        )

                selections[label] = selected
                df_step = _apply(df_step, col, selected)

    df_filtrado = df_step
    cedulas = set(df_filtrado[COL_ID].dropna().astype(str).unique().tolist())
    return df_filtrado, cedulas, selections

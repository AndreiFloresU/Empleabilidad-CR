import streamlit as st
import pandas as pd
from utils.conn import cargar_datos, get_engine

TABLAS = [
    "Graduados",
    "DataLaboral",
    "DataInmueble",
    "DataMueble",
    "DataLocalizacion",
    "DataSociedades",
]


@st.cache_data(show_spinner=False)
def _load_all_tables():
    """Carga TODAS las tablas 1 sola vez y las retorna en un dict."""
    data = {}
    for t in TABLAS:
        df = cargar_datos(t)
        data[t] = df
    return data


def init_data():
    """Garantiza que los datos originales estén en session_state."""
    if "_data_original" not in st.session_state:
        st.session_state["_data_original"] = _load_all_tables()


def get_data_copy(tabla):
    """Devuelve una **copia** de una tabla para uso en la página actual."""
    init_data()
    return st.session_state["_data_original"][tabla].copy(deep=True)


def refresh_data():
    """
    Permite refrescar datos desde la BD
    Limpia el cache y vuelve a cargar.
    """
    _load_all_tables.clear()  # limpia cache de datos
    st.session_state.pop("_data_original", None)
    init_data()

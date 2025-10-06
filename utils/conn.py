import pandas as pd
import urllib.parse
from sqlalchemy import create_engine, text
import streamlit as st

server = r"CU-LPAFLORES\SQLEXPRESS"
database = "CR"

# Cadena ODBC y URL-encode para usarla en SQLAlchemy
_ODBC_STR = (
    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
    f"SERVER={server};"
    f"DATABASE={database};"
    "Trusted_Connection=yes;"
)
_ODBC_ENCODED = urllib.parse.quote_plus(_ODBC_STR)


@st.cache_resource(show_spinner=False)
def get_engine():
    # Crea y cachea un único engine para toda la sesión
    engine = create_engine(f"mssql+pyodbc:///?odbc_connect={_ODBC_ENCODED}")
    return engine


def cargar_datos(tabla):
    """
    Lee una tabla de SQL Server
    """
    engine = get_engine()

    # Construir query con filtro para excluir cohorte 2025 en tabla Graduados
    if tabla.lower() == "graduados":
        query = text(f"SELECT * FROM {tabla} WHERE anio_graduacion != '2025';")
    else:
        query = text(f"SELECT * FROM {tabla};")

    try:
        with engine.connect() as conn:
            df = pd.read_sql_query(query, conn)
        return df
    except Exception as e:
        print(f"Error al cargar la tabla {tabla}: {e}")
        return pd.DataFrame()

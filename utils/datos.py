import streamlit as st
import pandas as pd
import copy
import os

# Import the new Excel data loader instead of SQL connection
from utils.excel_data import load_excel_table

# Define the key tables required by the application
REQUIRED_TABLES = [
    "Graduados",
    "DataLaboral",
    "DataInmueble",
    "DataMueble",
    "DataLocalizacion",
    "DataSociedades",
]


def init_data():
    """
    Initialize and cache all required data tables in session state.
    Loads data from Excel files in the db directory.
    """
    if "_data_original" not in st.session_state:
        st.session_state["_data_original"] = {}

        # Check if db directory exists
        db_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "db"
        )

        if not os.path.exists(db_dir):
            st.error(f"¡Error! No se encontró la carpeta de datos: {db_dir}")
            st.info(
                "Por favor, crea una carpeta 'db' en el directorio raíz y coloca los archivos Excel con los datos."
            )
            # Add instructions for required files
            st.code("\n".join([f"{table}.xlsx" for table in REQUIRED_TABLES]))
            return

        # Check and list available files
        available_files = os.listdir(db_dir)

        # Check which required files are missing
        excel_files = [f for f in available_files if f.endswith(".xlsx")]
        missing_files = [
            f"{table}.xlsx"
            for table in REQUIRED_TABLES
            if f"{table}.xlsx" not in excel_files
        ]

        if missing_files:
            st.warning(
                f"Faltan algunos archivos Excel necesarios: {', '.join(missing_files)}"
            )
            st.info(
                "Asegúrate de que los nombres de los archivos coincidan exactamente con los nombres de las tablas."
            )

        # Load all required tables from Excel
        for table in REQUIRED_TABLES:
            df = load_excel_table(table)

            # Ensure we have data
            if df.empty:
                st.error(f"No se pudieron cargar los datos para {table} desde Excel.")
                continue

            # Normalize column names (consistent with SQL version)
            df.columns = df.columns.str.strip().str.lower()

            # Store in session state
            st.session_state["_data_original"][table] = df

        # Check if all tables were loaded successfully
        loaded_tables = list(st.session_state["_data_original"].keys())

        if len(loaded_tables) < len(REQUIRED_TABLES):
            st.error(
                "Algunos datos no pudieron ser cargados. La aplicación puede funcionar incorrectamente."
            )
            st.info(f"Tablas requeridas: {REQUIRED_TABLES}")
            st.info(f"Tablas cargadas: {loaded_tables}")
        else:
            st.success("Datos cargados correctamente desde archivos Excel.")


def get_data_copy(table_name):
    """
    Get a deep copy of a data table from session state.

    Parameters:
    -----------
    table_name : str
        Name of the table to retrieve

    Returns:
    --------
    pandas.DataFrame
        A copy of the requested data table
    """
    # Ensure data is initialized
    init_data()

    if (
        "_data_original" in st.session_state
        and table_name in st.session_state["_data_original"]
    ):
        df = copy.deepcopy(st.session_state["_data_original"][table_name])
        return df
    else:
        if "_data_original" in st.session_state:
            pass
        st.error(f"La tabla {table_name} no existe en los datos cargados.")
        return pd.DataFrame()

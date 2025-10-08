import os
import pandas as pd
import logging

# Path to the Excel files
EXCEL_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "db"
)


def load_excel_table(tabla):
    """
    Load a table from an Excel file in the db directory.

    Parameters:
    -----------
    tabla : str
        Name of the table to load (without file extension)

    Returns:
    --------
    pandas.DataFrame
        The loaded table data or empty DataFrame if file not found
    """
    try:
        # Check if db directory exists
        if not os.path.exists(EXCEL_DIR):
            return pd.DataFrame()

        # List available files for debugging
        excel_files = [f for f in os.listdir(EXCEL_DIR) if f.endswith(".xlsx")]

        # Construct file path with proper case handling
        # Try with exact case first
        file_path = os.path.join(EXCEL_DIR, f"{tabla}.xlsx")

        # If file doesn't exist, try case-insensitive search
        if not os.path.exists(file_path):
            # Try to find a case-insensitive match
            for file in excel_files:
                if file.lower() == f"{tabla.lower()}.xlsx":
                    file_path = os.path.join(EXCEL_DIR, file)
                    break

        # Check if file exists after case-insensitive search
        if not os.path.exists(file_path):
            return pd.DataFrame()

        # Read Excel file
        df = pd.read_excel(file_path)

        # Check if DataFrame is empty
        if df.empty:
            return pd.DataFrame()

        # Normalize column names to match SQL data format
        df.columns = df.columns.str.strip().str.lower()

        # Ensure cedula is a string type for consistent comparisons
        if "cedula" in df.columns:
            df["cedula"] = df["cedula"].astype(str).str.strip()

        # Filter out 2025 graduates if this is the Graduados table (matching SQL behavior)
        if tabla.lower() == "graduados" and "anio_graduacion" in df.columns:
            df["anio_graduacion"] = df["anio_graduacion"].astype(str).str.strip()
            df = df[df.anio_graduacion != "2025"]

        return df
    except Exception:
        return pd.DataFrame()

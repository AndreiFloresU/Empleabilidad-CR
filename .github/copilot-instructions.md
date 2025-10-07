# Empleabilidad CR - Gráficos: AI Development Guide

## Overview

This is a Streamlit-based analytics dashboard for Costa Rica employment data, analyzing graduate employment rates from two universities: **UNIVERSIDAD LATINA DE COSTA RICA** and **UNIVERSIDAD AMERICANA**. The app connects to a local SQL Server instance and provides interactive filtering and visualization to generate valuable insights about graduate employability.

## Data Schema & Business Context

### Database Structure

The analysis works with 6 interconnected tables in SQL Server (`CU-LPAFLORES\SQLEXPRESS`, database "CR"):

1. **`Graduados`** - Core graduate information with university hierarchy (universidad → sede → facultad → carrera)
2. **`DataLaboral`** - Employment records (only employed graduates, `labora_actualmente = 'S'`)
3. **`DataInmueble`** - Real estate properties associated with graduates
4. **`DataMueble`** - Personal assets/movable property data
5. **`DataLocalizacion`** - Geographic and contact information
6. **`DataSociedades`** - Corporate relationships and positions

### Key Business Rules

- **Primary Key**: `cedula` (unique person identifier) – multiple records per person possible
- **Employment Logic**: `DataLaboral` contains only currently employed individuals
- **Data Snapshot**: Employment data as of 2025-04-01
- **Multi-University**: Analysis covers graduates from two Costa Rican universities

## Architecture & Data Flow

### Core Data Pipeline

- **Database**: SQL Server with Windows authentication via SQLAlchemy
- **Connection**: `utils/conn.py` handles ODBC connectivity with proper encoding
- **Caching**: Global data loading via `@st.cache_data` in `utils/datos.py`
- **Tables**: All 6 tables loaded once and cached in session state

### Key Components

1. **`utils/datos.py`**: Centralized data management with session state caching
2. **`utils/filtros.py`**: Cascading filter system with standardized UI patterns
3. **`utils/conn.py`**: Database connectivity layer
4. **`utils/estilos.py`**: Custom Plotly theming
5. **`Tasa_Empleabilidad.py`**: Main analysis page (employment rate calculations)

## Critical Patterns

### Data Access Pattern

```python
# Always use this pattern for data access:
init_data()  # Ensures data is loaded in session_state
df_grad = get_data_copy("Graduados")  # Gets a deep copy for manipulation
```

### Filter Implementation

All pages should use `filtros_locales()` from `utils/filtros.py`:

- Returns filtered DataFrame, **cedula set**, and selection dict
- Uses cascading selectboxes with "(Todos)" default option
- Expects normalized column names (lowercase, stripped)
- Fixed filter order: Universidad → Nivel → Sede → Facultad → Carrera → Cohorte

### Column Normalization

Always normalize DataFrame columns before operations:

```python
df.columns = df.columns.str.strip().str.lower()
```

### Employment Rate Calculation Pattern

1. **Denominator**: Unique graduates from `Graduados` table (post-filtering)
2. **Numerator**: Graduates found in `DataLaboral` (employment data, snapshot 2025-04-01)
3. **Key Logic**: `DataLaboral` contains only employed people (`labora_actualmente = 'S'`)

### Table Schema Details

#### `Graduados` – Graduate Registry

**Fields:**

- `cod_universidad`: int
- `universidad`: nvarchar(50)
- `cod_sede`: int
- `sede`: nvarchar(100)
- `cod_facultad`: nvarchar(25)
- `facultad`: nvarchar(255)
- `cod_carrera`: nvarchar(25)
- `carrera`: nvarchar(255)
- `cod_enfasis`: nvarchar(25)
- `enfasis`: nvarchar(255)
- `cod_plan`: nvarchar(25)
- `cod_grado`: nvarchar(25)
- `cedula`: nvarchar(50)
- `nombre`: nvarchar(100)
- `sexo`: char(1)
- `correo`: nvarchar(255)
- `periodo_graduacion`: nvarchar(100)
- `anio_graduacion`: varchar(4)
- `codigo_graduacion`: nvarchar(25)

Primary dimension for filtering and aggregation. All graduates from both universities included.

---

#### `DataLaboral` – Employment Information

**Fields:**

- `cedula`: nvarchar(50)
- `actividad_empresa`: nvarchar(255)
- `nombre_patrono`: nvarchar(255)
- `salario_base`: decimal(19,2)
- `labora_actualmente`: char(1)
- `ocupacion`: nvarchar(255)
- `porcentaje_variacion`: decimal(19,2)
- `patrono_es_moroso`: char(2)
- `tipo_patrono`: nvarchar(255)
- `antiguedad_meses`: int
- `clasificacion`: nvarchar(255)
- `ingreso_aproximado`: decimal(19,2)

May contain multiple records per person (`cedula`) when a graduate holds more than one job at the snapshot date.

---

#### `DataInmueble` – Real Estate Properties

**Fields:**

- `cedula`: nvarchar(50)
- `horizontal`: char(1)
- `naturaleza`: nvarchar(255)
- `medida`: decimal(19,2)
- `valor_fiscal`: decimal(19,2)
- `duplicado`: char(1)

A person may own multiple properties. Used for real estate asset analysis.

---

#### `DataMueble` – Personal Assets

**Fields:**

- `cedula`: nvarchar(50)
- `valor_fiscal`: decimal(19,2)
- `categoria`: nvarchar(255)
- `fecha_adquisicion`: date
- `valor_contrato`: decimal(19,2)

Tracks movable property (vehicles, equipment, etc.). Multiple records per `cedula` possible.

---

#### `DataLocalizacion` – Geographic Data

**Fields:**

- `cedula`: nvarchar(50)
- `provincia`: nvarchar(255)
- `canton`: nvarchar(255)
- `distrito`: nvarchar(255)
- `telefono`: nvarchar(max)

Used for geographic and contact information. May include several rows per person if multiple addresses or phone sources exist.

---

#### `DataSociedades` – Corporate Relationships

**Fields:**

- `cedula`: nvarchar(50)
- `nombre`: nvarchar(255)
- `puesto`: nvarchar(255)
- `representacion`: nvarchar(255)

Captures business or corporate affiliations. Multiple records per `cedula` are expected.

## Development Workflows

### Running the Application

```bash
streamlit run Tasa_Empleabilidad.py
```

### Database Requirements

- Requires local SQL Server Express instance
- Uses Windows Trusted Authentication
- Must have ODBC Driver 17 for SQL Server installed

### Adding New Pages

1. Create file in `pages/` directory (numbered: `2_pag.py`, `3_pag.py`, etc.)
2. Follow data access pattern with `init_data()` and `get_data_copy()`
3. Use `filtros_locales()` for consistent filtering UI
4. Apply custom theme with `aplicar_tema_plotly()` if using Plotly

### Required Page Structure

All analytics pages must follow this **exact format**:

1. **Nombre Página** - Title with relevant emoji and descriptive text
2. **Filtros** - Use `filtros_locales()` function for consistent filtering interface
3. **Gráfico** - Data visualization with custom theme applied
4. **Tarjeta con explicación** - Use `mostrar_tarjeta_nota()` function for insights explanation

#### Page Template Pattern:

```python
import streamlit as st
import plotly.express as px
import pandas as pd

# Importar utilidades
from utils.datos import init_data, get_data_copy
from utils.filtros import filtros_locales
from utils.estilos import aplicar_tema_plotly, mostrar_tarjeta_nota

# ALWAYS apply custom theme
aplicar_tema_plotly()

# 1. Nombre Página
st.title("📊 [Page Title]")

# Initialize data
init_data()
df_data = get_data_copy("[TableName]")

# 2. Filtros
df_filtered, cedulas_filtered, selections = filtros_locales(df_data)

# 3. Gráfico
# [Create visualization with filtered data]
fig = px.[chart_type]([data], [parameters])
st.plotly_chart(fig, use_container_width=True)

# 4. Tarjeta con explicación
texto_explicacion = """[Insight explanation with HTML formatting]"""
mostrar_tarjeta_nota(texto_explicacion, [filter_name], [filter_description])
```

#### Mandatory Requirements:

- **Theme**: ALWAYS call `aplicar_tema_plotly()` at the beginning
- **Filters**: Use `filtros_locales()` for consistent filtering experience
- **Insights**: Use `mostrar_tarjeta_nota()` for explanation cards
- **Structure**: Follow the 4-part format without exceptions

## Key Conventions

### Naming & Structure

- **Main identifier**: `cedula` (unique person identifier)
- **Aggregation dimensions**: `universidad`, `facultad`, `carrera` (standard hierarchy)
- **Date format**: Employment data snapshot is 2025-04-01
- **File naming**: Main page is `Tasa_Empleabilidad.py`, additional pages use numbered format

### UI Patterns

- **Page Structure**: All pages must follow the 4-part format: Nombre → Filtros → Gráfico → Tarjeta explicación
- **Theme Application**: ALWAYS call `aplicar_tema_plotly()` at the start of every page
- **Filter Integration**: Use `filtros_locales()` for consistent filtering across all pages
- **Insight Cards**: Use `mostrar_tarjeta_nota()` for all explanatory content
- Use `st.columns(3)` for KPI metrics display
- Standard color palette defined in `PALETA_PASTEL`
- Download buttons use UTF-8-BOM encoding: `.encode("utf-8-sig")`
- Format percentages with 1 decimal in displays, 2 in downloads

### Error Handling

- Missing columns trigger `st.error()` and `st.stop()`
- Database errors are caught and return empty DataFrames
- Graceful handling of null/empty filter cascades

## Integration Points

### External Dependencies

- **SQL Server**: Local instance with specific connection string
- **ODBC Driver**: Version 17 required for SQL Server connectivity
- **Streamlit**: Multi-page app structure with `pages/` directory

### Cross-Component Communication

- Data shared via Streamlit session state (`_data_original`)
- No shared filter state between pages (intentional isolation)
- Cache invalidation available via `refresh_data()` function

## Analytics Guidelines

### Insight Generation Strategy

- **Employment Analysis**: Use `Graduados` + `DataLaboral` for employment rates by dimension
- **Wealth Analysis**: Combine `DataInmueble` + `DataMueble` for asset distribution
- **Geographic Patterns**: Use `DataLocalizacion` for regional employment distribution
- **Corporate Engagement**: Leverage `DataSociedades` for leadership and representation roles
- **Cross-Table Insights**: Join tables via `cedula` for comprehensive graduate profiles

### Key Analysis Dimensions

- **University Hierarchy**: `universidad` → `sede` → `facultad` → `carrera`
- **Temporal**: `anio_graduacion` (graduation cohorts)
- **Demographic**: `sexo` (gender analysis)
- **Geographic**: `provincia` → `canton` → `distrito`
- **Economic**: Salary ranges, asset values, property ownership

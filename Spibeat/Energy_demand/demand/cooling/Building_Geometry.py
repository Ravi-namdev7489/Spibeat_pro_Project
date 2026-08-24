import os
import warnings
import numpy as np
import pandas as pd
import pvlib
import geopandas as gpd
from shapely.geometry import Polygon
from pvlib.iotools import read_epw
from ..constants import (RHO_AIR,P_ATM,C_A,H_WE,SIMULATION_YEAR)
#  Cell 1 code 
def safe_float(x, default=np.nan):
    try:
        v = float(x)
        return default if np.isnan(v) else v
    except Exception:
        return default
def load_csv_if_exists(path):
    if path and os.path.exists(path):
        for enc in ["utf-8", "cp1252", "latin1"]:
            try:
                df = pd.read_csv(path, encoding=enc)
                # clean non-breaking spaces
                df.columns = df.columns.str.replace("\xa0", " ").str.strip()
                return df
            except Exception:
                continue
        warnings.warn(f"Failed to read CSV {path} with all attempted encodings")
    return None


# ------------------------------------------------------------
# LOAD LOOKUP TABLES
# ------------------------------------------------------------
def building_info(BUILDINGS_SHP,EPW_FILE,USE_TYPE_FILE,building_types,ENVELOPE_DIR):
    use_df = load_csv_if_exists(USE_TYPE_FILE)
    WALL_AS1 = load_csv_if_exists(os.path.join(ENVELOPE_DIR, "ENVELOPE_WALL.csv"))
    ROOF_AS1 = load_csv_if_exists(os.path.join(ENVELOPE_DIR, "ENVELOPE_ROOF.csv"))
    WINDOW_AS1 = load_csv_if_exists(os.path.join(ENVELOPE_DIR, "ENVELOPE_WINDOW.csv"))
    env_floor = load_csv_if_exists(os.path.join(ENVELOPE_DIR, "ENVELOPE_FLOOR.csv"))
    env_wall = load_csv_if_exists(os.path.join(ENVELOPE_DIR, "ENVELOPE_WALL.csv"))
    env_roof = load_csv_if_exists(os.path.join(ENVELOPE_DIR, "ENVELOPE_ROOF.csv"))
    env_win = load_csv_if_exists(os.path.join(ENVELOPE_DIR, "ENVELOPE_WINDOW.csv"))
    env_shading = load_csv_if_exists(os.path.join(ENVELOPE_DIR, "ENVELOPE_SHADING.csv"))
    env_tight = load_csv_if_exists(os.path.join(ENVELOPE_DIR, "ENVELOPE_TIGHTNESS.csv"))

    if use_df is None:
        raise FileNotFoundError("❌ USE_TYPES.csv not found")

    # ------------------------------------------------------------
    # LOAD BUILDINGS (EXPLICIT SHAPEFILE ONLY)
    # ------------------------------------------------------------
    if not os.path.exists(BUILDINGS_SHP):
        raise FileNotFoundError(f"❌ Shapefile not found: {BUILDINGS_SHP}")

    buildings = gpd.read_file(BUILDINGS_SHP)

    if buildings.empty:
        raise ValueError("❌ Shapefile loaded but contains no buildings")

    print(f"Loaded {len(buildings)} buildings from shapefile")

    # Optional sanity checks
    print("Geometry types:")
    print(buildings.geometry.geom_type.value_counts())
    print("CRS:", buildings.crs)

    # ------------------------------------------------------------
    # READ EPW (ONCE)
    # ------------------------------------------------------------
    if not os.path.exists(EPW_FILE):
        raise FileNotFoundError(f"❌ EPW file not found: {EPW_FILE}")

    epw, meta = pvlib.iotools.read_epw(EPW_FILE)
    timestamps = epw.index
    n_hours = len(timestamps)

    ghi = epw.get(
        "ghi",
        epw.get("global_horizontal_irradiance", np.zeros(n_hours))
    ).values

    Tout = epw["temp_air"].values
    RH_out = epw["relative_humidity"].values / 100.0

    print("EPW hours:", n_hours)
    wall_type=building_types.get('wall_type')
    roof_type=building_types.get('roof_type')
    window_type=building_types.get('window_type')
    floor_type=building_types.get('floor_types')
    
    # ============================================================
    # LOOP OVER BUILDINGS (GEOMETRY ONLY)
    # ============================================================
    building_geoms = {}

    for b_id, b in buildings.iterrows():
        # ---------- FOOTPRINT AREA ----------
        if "floor_area" in buildings.columns and not pd.isna(b.get("floor_area")):
            footprint_area = float(b["floor_area"])
        else:
            if b.geometry is not None:
                footprint_area = float(b.geometry.area)
            else:
                footprint_area = safe_float(b.get("footprint_area"), 0.0)

        # ---------- HEIGHT ----------
        height = safe_float(b.get("height_ag"))
        if np.isnan(height):
            height = safe_float(b.get("floors_ag"), 1) * 3.0

        floors_ag = int(safe_float(b.get("floors_ag"), 1))
        floor_area = footprint_area * floors_ag
        volume_m3 = floor_area * height

        # ---------- WALL AREA ----------
        try:
            if "wall_area" in buildings.columns and not pd.isna(b.get("wall_area")):
                wall_area = float(b["wall_area"])
            else:
                wall_area = b.geometry.length * height if b.geometry is not None else 2.0 * footprint_area
        except Exception:
            wall_area = 2.0 * footprint_area

        roof_area = footprint_area
        window_area = 0.1 * wall_area  # fallback WWR = 10%

        # ---------- NAME ----------
        name = b.get("name", b.get("Name", f"Building_{b_id}"))

        # ---------- STORE ----------
        building_geoms[b_id] = {
            "footprint_area": footprint_area,
            "floor_area": floor_area,
            "height": height,
            "volume_m3": volume_m3,
            "wall_area": wall_area,
            "roof_area": roof_area,
            "window_area": window_area,
            "name": name,
            # cooling para
            'wall':wall_type,
            'window':window_type,
            'floor':floor_type,
            'roof':roof_type
        }

        print(
            f"✔ {name}: "
            f"floor_area={floor_area:.1f} m², "
            f"volume={volume_m3:.1f} m³ ,"
        f"footprint_area={footprint_area} m2 ,"
        f"height={height} m "
        )
    return building_geoms


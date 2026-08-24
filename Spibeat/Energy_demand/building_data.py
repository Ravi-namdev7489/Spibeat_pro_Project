# ============================================================
# IMPORTS
# ============================================================
import os
import warnings
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import mapping

from .demand.constants import (
    RHO_AIR, P_ATM, C_A, H_WE, SIMULATION_YEAR
)

# ============================================================
# 🔧 HELPERS
# ============================================================

def safe_float(x, default=np.nan):
    """Safely convert a value to float."""
    try:
        v = float(x)
        return default if np.isnan(v) else v
    except Exception:
        return default


def to_decimal(val, digits=6):
    """Convert number to normal decimal (no scientific notation)."""
    try:
        return float(f"{float(val):.{digits}f}")
    except Exception:
        return 0.0


def load_csv_if_exists(path):
    """Load CSV safely."""
    if path and os.path.exists(path):
        for enc in ["utf-8", "cp1252", "latin1"]:
            try:
                df = pd.read_csv(path, encoding=enc)
                df.columns = df.columns.str.replace("\xa0", " ").str.strip()
                return df
            except Exception:
                continue
        warnings.warn(f"Failed to read CSV {path}")
    return None


# ============================================================
# DISTRIBUTION (FOR MIXED)
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import mapping



def building_info(locator, use_type,per_commercial=0.3,per_residential=0.7):
    shp_path = locator.get_buildings_shp()
    print('residential percentage',per_residential)
    print('commercial percentage',per_commercial)
    buildings = gpd.read_file(shp_path)
    USE_TYPE_DISTRIBUTION = {
    "RESIDENTIAL":per_residential,
    "COMMERCIAL":per_commercial
}

    print("📂 Total buildings:", len(buildings))

    if buildings.empty:
        return []

    buildings.columns = buildings.columns.str.lower()

    # normalize
    buildings["sub_class"] = buildings["sub_class"].astype(str).str.strip().str.upper()
    use_type_clean = str(use_type).strip().upper()

    if buildings.crs is None:
        raise ValueError("❌ CRS missing")

    buildings_latlon = buildings.to_crs(epsg=4326)
    buildings_metric = buildings

    zone_data = []

    for b_id, b in buildings.iterrows():
        try:
            geom_original = buildings_latlon.loc[b_id].geometry
            geom_metric = buildings_metric.loc[b_id].geometry

            if geom_original is None or geom_original.is_empty:
                continue

            sub_class_clean = str(b.get("sub_class", "")).strip().upper()

            # ===========================
            # MIXED MODE
            # ===========================
            if use_type_clean == "MIXED":

                # only mixed buildings
                if sub_class_clean != "MIXED":
                    continue

                assigned_use_type = np.random.choice(
                    list(USE_TYPE_DISTRIBUTION.keys()),
                    p=list(USE_TYPE_DISTRIBUTION.values())
                )

            # ===========================
            # NORMAL MODE
            # ===========================
            else:

                # match subtype OR class fallback
                if sub_class_clean not in use_type_clean:
                    continue

                assigned_use_type = use_type_clean

            # ✅ FORCE PYTHON STRING (IMPORTANT FIX)
            assigned_use_type = str(assigned_use_type)

            name = str(b.get("name", "")).strip()
            if not name:
                continue

            b_class = str(b.get("class", "")).strip()

            geom_simple = geom_original.simplify(0.0001, preserve_topology=True)

            footprint_area = (
                float(b["footprint_area"])
                if "footprint_area" in buildings.columns and pd.notna(b.get("footprint_area"))
                else float(geom_metric.area)
            )

            height = (
                float(b["height_ag"])
                if pd.notna(b.get("height_ag"))
                else float(b.get("floors_ag", 1)) * 3.0
            )

            floors_ag = max(int(float(b.get("floors_ag", 1))), 1)

            floor_area = footprint_area * floors_ag
            volume_m3 = footprint_area * height

            wall_area = (
                float(b["wall_area"])
                if "wall_area" in buildings.columns and pd.notna(b.get("wall_area"))
                else float(geom_metric.length * height)
            )

            roof_area = footprint_area
            window_area = 0.1 * wall_area

            centroid = geom_original.representative_point()

            row_data = {
                "name": name,
                "class": b_class,
                "sub_class": sub_class_clean,
                "use_type": assigned_use_type,

                "footprint_area": round(footprint_area, 2),
                "floor_area": round(floor_area, 2),
                "height": round(height, 2),
                "floors": floors_ag,
                "volume_m3": round(volume_m3, 2),
                "wall_area": round(wall_area, 2),
                "roof_area": round(roof_area, 2),
                "window_area": round(window_area, 2),

                "lat": round(centroid.y, 8),
                "lon": round(centroid.x, 8),

                "geometry": mapping(geom_simple),
            }

            zone_data.append(row_data)

        except Exception as e:
            print("❌ Error:", e)
            continue

    print("\n===================================")
    print(f"🏭 Buildings returned for '{use_type}':", len(zone_data))
    print("===================================\n")

    return zone_data
def info_all_buildings(locator):
    shp_path = locator.get_buildings_shp()

    # Load shapefile
    buildings = gpd.read_file(shp_path)

    print("📂 Total buildings in shapefile:", len(buildings))

    if buildings.empty:
        print("⚠ No buildings found")
        return []

    # --------------------------------------------------------
    # ✅ STEP 1: KEEP ORIGINAL CRS (for lat/lon)
    # --------------------------------------------------------
    if buildings.crs is None:
        raise ValueError("❌ Shapefile CRS is missing")
    buildings_latlon = buildings.to_crs(epsg=4326)   # for map
    buildings_metric = buildings   # for area (meters)
    zone_data = []
    # ========================================================
    # LOOP BUILDINGS
    # ========================================================
    for b_id, b in buildings.iterrows():
        try:
            geom_original = buildings_latlon.loc[b_id].geometry
            geom_metric = buildings_metric.loc[b_id].geometry

            if geom_original is None or geom_original.is_empty:
                continue

            # ------------------------------------------------
            # FILTER BY USE TYPE
            # ------------------------------------------------
            b_class = str(b.get("Class", "")).strip()
            sub_class = b.get("Sub_Class")

            if pd.isna(sub_class):
                continue
            sub_class_clean = str(sub_class).strip().lower()
           
           
            print('Class',b_class)
            print('sub class',sub_class)
           
            # ------------------------------------------------
            # NAME
            # ------------------------------------------------
            name = b.get("Name")
            if name is None or str(name).strip() == "":
                continue

            name = str(name).strip()

            # ------------------------------------------------
            # GEOMETRY (simplified only for output)
            # ------------------------------------------------
            geom_simple = geom_original.simplify(0.0001, preserve_topology=True)

            # ------------------------------------------------
            # FOOTPRINT AREA (m² - accurate)
            # ------------------------------------------------
            if "footprint_area" in buildings.columns and not pd.isna(b.get("footprint_area")):
                footprint_area = safe_float(b.get("footprint_area"), 0.0)
                print('footprint area',footprint_area)
            else:
                footprint_area = safe_float(geom_metric.area, 0.0)
                print('foot area from geometri',footprint_area)

            # ------------------------------------------------
            # HEIGHT & FLOORS
            # ------------------------------------------------
            height = safe_float(b.get("height_ag"))

            if np.isnan(height):
                height = safe_float(b.get("floors_ag"), 1) * 3.0  # fallback

            floors_ag = max(int(safe_float(b.get("floors_ag"), 1)), 1)

            # ------------------------------------------------
            # DERIVED VALUES (CORRECTED)
            # ------------------------------------------------
            floor_area = footprint_area * floors_ag
            shape=b.get('Shape_Area')
            print('Shape',shape)
            print('floor_area',floor_area)
            print('footprint_area',footprint_area)
            volume_m3 = footprint_area * height   # ✅ FIXED

            # ------------------------------------------------
            # WALL AREA (using perimeter in meters)
            # ------------------------------------------------
            try:
                if "wall_area" in buildings.columns and not pd.isna(b.get("wall_area")):
                    wall_area = safe_float(b.get("wall_area"))
                else:
                    perimeter = geom_metric.length
                    wall_area = safe_float(perimeter * height)
            except Exception:
                wall_area = safe_float(2.0 * footprint_area)

            roof_area = footprint_area
            window_area = 0.1 * wall_area

            # ------------------------------------------------
            # LOCATION (safe centroid)
            # ------------------------------------------------
            centroid = geom_original.representative_point()

            # ------------------------------------------------
            # FINAL OUTPUT
            # ------------------------------------------------
            row_data = {
                "name": name,
                "class": b_class,
                "sub_class": sub_class,

                "footprint_area": to_decimal(footprint_area),
                "floor_area": to_decimal(floor_area),
                "height": to_decimal(height),
                "floors": floors_ag,
                "volume_m3": to_decimal(volume_m3),
                "wall_area": to_decimal(wall_area),
                "roof_area": to_decimal(roof_area),
                "window_area": to_decimal(window_area),

                "lat": to_decimal(centroid.y, 8),
                "lon": to_decimal(centroid.x, 8),

                "geometry": mapping(geom_simple),  # simplified for frontend
            }

            zone_data.append(row_data)

            print(f"✔ Added Building: {name}")

        except Exception as e:
            print("❌ Row Error:", e)
            continue
    print("\n===================================")
    print("🏭 TOTAL BUILDINGS SENT:", len(zone_data))
    print("===================================\n")
    return zone_data
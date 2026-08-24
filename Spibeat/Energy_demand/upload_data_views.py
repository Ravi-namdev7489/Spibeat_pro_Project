from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import geopandas as gpd
import pandas as pd
import json
from .demand.inputLocator import InputLocator
import os
from django.conf import settings
import os, zipfile, uuid, json, shutil
import pandas as pd
import os, zipfile, uuid, json
import pandas as pd
from .building_data import building_info,info_all_buildings
from .views_supportor import *
from rest_framework.decorators import api_view
import tempfile
class GetBuildingShape(APIView):
    def get(self, request):
        try:
            user = request.user  # ✅ logged-in user
            print(user)
            # ✅ SOURCE PATH
            building_dir_src = r'C:\RaviNamdev\India Database for Building simulator\chandigardh_shape_file'

            if not os.path.exists(building_dir_src):
                return Response(
                    {"error": "Building shapefile folder not found"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # ✅ USER BASED PATH
            user_folder = get_user_folder(user)
            building_dir = os.path.join(user_folder, "building")

            # ✅ IF ALREADY EXISTS → DO NOT RECREATE
            if os.path.exists(building_dir) and os.listdir(building_dir):
                return Response({
                    "status": "existing",
                    "building_path": building_dir,
                    "message": "Using existing shapefile"
                }, status=status.HTTP_200_OK)

            # ✅ CREATE ONLY FIRST TIME
            os.makedirs(building_dir, exist_ok=True)

            # ✅ COPY FILES
            for file_name in os.listdir(building_dir_src):
                src_path = os.path.join(building_dir_src, file_name)
                dst_path = os.path.join(building_dir, file_name)

                if os.path.isfile(src_path):
                    shutil.copy(src_path, dst_path)

            # ✅ VALIDATE SHAPEFILE
            missing = validate_shapefile(building_dir)
            if missing:
                return Response(
                    {"error": f"Missing shapefile parts: {missing}"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            return Response({
                "status": "created",
                "building_path": building_dir,
                "message": "Building shapefile loaded successfully"
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
class GetWeatherFile(APIView):
    
    def get(self, request):
        try:
            user= request.user
            print('user',user.id)
            # ✅ SOURCE PATH
            weather_dir_src = r'C:\RaviNamdev\India Database for Building simulator\Chandigargh_Weather_file'

            if not os.path.exists(weather_dir_src):
                return Response(
                    {"error": "Weather folder not found"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # ✅ TARGET PROJECT FOLDER
            user_folder = get_user_folder(user)
            weather_dir = os.path.join(user_folder, "weather")
            os.makedirs(weather_dir, exist_ok=True)

            # ✅ COPY EPW FILE
            epw_found = False

            for file_name in os.listdir(weather_dir_src):
                if file_name.endswith(".epw"):
                    src_path = os.path.join(weather_dir_src, file_name)
                    dst_path = os.path.join(weather_dir, file_name)

                    shutil.copy(src_path, dst_path)
                    epw_found = True
                    break

            if not epw_found:
                return Response(
                    {"error": "EPW file not found"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # ✅ VALIDATE EPW
            epw = find_epw(weather_dir)
            if not epw:
                return Response(
                    {"error": "EPW validation failed"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            return Response({
                "status": "success",
                "weather_path": weather_dir,
                "message": "Weather file loaded successfully"
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
def read_csv_safe(path):
    
    # ❌ File not exists
    if not os.path.exists(path):
        print("❌ File not found:", path)
        return {"columns": [], "rows": []}

    # ❌ Empty file
    if os.path.getsize(path) == 0:
        print("⚠️ Empty file:", path)
        return {"columns": [], "rows": []}

    # ✅ Try multiple encodings
    encodings = ["utf-8", "latin1", "cp1252"]

    for enc in encodings:
        try:
            df = pd.read_csv(path, encoding=enc)
            break
        except UnicodeDecodeError:
            continue
        except pd.errors.EmptyDataError:
            print("⚠️ No columns:", path)
            return {"columns": [], "rows": []}

    # ❌ If all encodings fail
    if df is None:
        return {"columns": [], "rows": []}

    # ==========================================
    # ✅ HANDLE BLANK VALUES
    # ==========================================

    # Replace NaN, None, empty strings with 0
    df = df.fillna(0)
    df = df.replace(r'^\s*$', 0, regex=True)

    # Optional: strip column names
    df.columns = df.columns.str.strip()

    # ==========================================

    return {
        "columns": df.columns.tolist(),
        "rows": df.to_dict(orient="records")
    }
# ==========================================
# INPUT LOCATOR API
# ==========================================
# function for get name_type .list file 
def get_unique_values(path, column_name):
    try:
        df = pd.read_csv(path, encoding="latin1")

        if column_name not in df.columns:
            print(f"{column_name} not found in CSV")
            return []

        values = df[column_name].dropna().unique().tolist()
        return values

    except Exception as e:
        print(f"{column_name} error:", e)
        return []
class InputLocatorView(APIView):
    
    def get(self, request):
        try:
            locator = get_locator_from_user(request.user)
            # =============================
            # USE TYPES
            # =============================
            use_list = get_unique_values(locator.get_use_types(), "use_type")

            floor_list = get_unique_values(locator.get_envelope_floor(), "floor_type")
            tightness_list = get_unique_values(locator.get_envelope_tightness(), "tightness_type")
            window_list = get_unique_values(locator.get_envelope_window(), "window_type")
            wall_list = get_unique_values(locator.get_envelope_wall(), "wall_type")
            roof_list = get_unique_values(locator.get_envelope_roof(), "roof_type")
            shading_list = get_unique_values(locator.get_envelope_shading(), "shading_type")
            hotwater_list = get_unique_values(locator.get_hvac_hotwater(), "class_dhw")
            cooling_list = get_unique_values(locator.get_hvac_cooling(), "class_cs")

            # =============================
            # ENVELOPE FILES
            # =============================
            mass = read_csv_safe(locator.get_envelope_mass())
            wall = read_csv_safe(locator.get_envelope_wall())
            roof = read_csv_safe(locator.get_envelope_roof())
            shading = read_csv_safe(locator.get_envelope_shading())
            tightness = read_csv_safe(locator.get_envelope_tightness())
            window = read_csv_safe(locator.get_envelope_window())
            floor = read_csv_safe(locator.get_envelope_floor())

            # =============================
            # HVAC FILES
            # =============================
            controller = read_csv_safe(locator.get_hvac_controller())
            cooling = read_csv_safe(locator.get_hvac_cooling())
            hotwater = read_csv_safe(locator.get_hvac_hotwater())
            heating = read_csv_safe(locator.get_hvac_heating())
            ventilation = read_csv_safe(locator.get_hvac_ventilation())

            # =============================
            # SUPPLY FILES
            # =============================
            supply_cooling = read_csv_safe(locator.get_supply_cooling())
            supply_electricity = read_csv_safe(locator.get_supply_electricity())
            supply_heating = read_csv_safe(locator.get_supply_heating())
            supply_hotwater = read_csv_safe(locator.get_supply_hotwater())

            photovoltaic = read_csv_safe(locator.get_conversion_photovoltaic_panels())

            # =============================
            # FINAL RESPONSE
            # =============================
            data = {
                "database_path": locator.database_root,
                "archetypes": locator.get_archetypes(),
                "assemblies": locator.get_assemblies(),
                "components": locator.get_components(),
                "envelope_dir": locator.get_envelope_dir(),
                "hvac_dir": locator.get_hvac_dir(),
                "supply_dir": locator.get_supply_dir(),

                "mass": mass,
                "wall": wall,
                "roof": roof,
                "floor": floor,
                "shading": shading,
                "tightness": tightness,
                "window": window,

                "use_types": use_list,

                "hvac_controller": controller,
                "hvac_cooling": cooling,
                "hvac_heating": heating,
                "hvac_ventilation": ventilation,
                "hvac_hotwater": hotwater,

                "supply_cooling": supply_cooling,
                "supply_electricity": supply_electricity,
                "supply_heating": supply_heating,
                "supply_hotwater": supply_hotwater,

                "photovoltaic": photovoltaic,

                # Dynamic types
                "floor_types": floor_list,
                "wall_types": wall_list,
                "window_types": window_list,
                "tightness_types": tightness_list,
                "roof_types": roof_list,
                "shading_types": shading_list,
                "hotwater_types": hotwater_list,
                "cooling_types": cooling_list
            }

            return Response(data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
# =========================================
# 🔧 GLOBAL CLEAN FUNCTION (VERY IMPORTANT)
# =========================================
def clean_nan(obj):
    if isinstance(obj, dict):
        return {k: clean_nan(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_nan(i) for i in obj]
    elif isinstance(obj, float) and np.isnan(obj):
        return None
    return obj


class GetUseDataView(APIView):

    def get(self, request):
        

        use = request.query_params.get("use")
        if not use:
            return Response(
                {"error": "No use type provided"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            locator =get_locator_from_user(request.user)
            # =============================
            # 1. LOAD use_types.csv
            # =============================
            use_df = pd.read_csv(locator.get_use_types())
            use_df.columns = use_df.columns.str.strip()

            row = use_df[use_df["use_type"] == use]

            if row.empty:
                return Response(
                    {"error": "Use type not found"},
                    status=status.HTTP_404_NOT_FOUND
                )

            # ✅ FIX: remove NaN
            use_row = row.iloc[0].replace({np.nan: None}).to_dict()

            # =============================
            # 2. LOAD schedule CSV
            # =============================
            schedule_file = os.path.join(
                locator.get_schedule_library(),
                f"{use}.csv"
            )

            if os.path.exists(schedule_file):
                schedule_df = pd.read_csv(schedule_file)

                # ✅ FIX: remove NaN
                schedule_df = schedule_df.replace({np.nan: None})

                schedule_data = {
                    "columns": schedule_df.columns.tolist(),
                    "rows": schedule_df.to_dict(orient="records")
                }
            else:
                schedule_data = {"columns": [], "rows": []}

            # =============================
            # 3. LOAD multipliers
            # =============================
            def read_multiplier(type_name):
                path = locator.get_monthly_multiplier(type_name)

                if not os.path.exists(path):
                    return {}

                df = pd.read_csv(path)
                df.columns = df.columns.str.strip()

                row = df[df["use_type"] == use]

                # ✅ FIX: remove NaN
                return (
                    row.iloc[0].replace({np.nan: None}).to_dict()
                    if not row.empty else {}
                )

            # =============================
            # FINAL RESPONSE
            # =============================
            response = {
                "use_row": use_row,
                "schedule": schedule_data,
                "mul_HW_row": read_multiplier("HW"),
                "mul_AC_row": read_multiplier("AC"),
                "mul_AUX_row": read_multiplier("AUX"),
                "mul_EaEl_row": read_multiplier("EaEl")
            }

            # ✅ FINAL SAFETY CLEAN
            return Response(clean_nan(response), status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
class SaveUseDataView(APIView):

    def post(self, request):

        try:
            locator = get_locator_from_user(request.user)
            # ✅ DRF automatically parses JSON
            body = request.data
            print("Incoming Data:", body)
        except Exception as e:
            return Response(
                {"error": f"Invalid request: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        # ===============================
        # GET DATA FROM FRONTEND
        # ===============================
        archetypes = body.get("archetypes", {})
        assemblies = body.get("assemblies", {})
        components = body.get("components", {})

        # =====================================================
        # 1️⃣ SAVE ARCHETYPE DATA
        # =====================================================
        try:
            use = archetypes.get("use_type")
            per_commercial = archetypes.get("per_commercial")
            per_residential = archetypes.get("per_residential")
            row_data = archetypes.get("row_data", {})
            multipliers = archetypes.get("multipliers", {})
            schedule_rows = archetypes.get("schedule_rows", [])

            if use:
                save_use_type(request.user, use, per_residential, per_commercial)

                # Save row data
                save_use_type_row(locator, use, row_data)

                # Multipliers
                update_multiplier(locator, use, "HW", multipliers.get("HW", {}))
                update_multiplier(locator, use, "AC", multipliers.get("AC", {}))
                update_multiplier(locator, use, "AUX", multipliers.get("AUX", {}))
                update_multiplier(locator, use, "EaEl", multipliers.get("EaEl", {}))

                # Schedule
                if schedule_rows:
                    save_schedule(locator, use, schedule_rows)

        except Exception as e:
            print("❌ Archetype error:", e)
            return Response(
                {"error": "Archetype save failed"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # =====================================================
        # 2️⃣ SAVE ASSEMBLIES DATA
        # =====================================================
        try:
            def save_if_not_empty(data, path):
                if data and len(data) > 0:
                    df = pd.DataFrame(data)
                    df.to_csv(path, index=False)

            # ENVELOPE
            save_if_not_empty(assemblies.get("floor"), locator.get_envelope_floor())
            save_if_not_empty(assemblies.get("wall"), locator.get_envelope_wall())
            save_if_not_empty(assemblies.get("roof"), locator.get_envelope_roof())
            save_if_not_empty(assemblies.get("window"), locator.get_envelope_window())
            save_if_not_empty(assemblies.get("tightness"), locator.get_envelope_tightness())
            save_if_not_empty(assemblies.get("shading"), locator.get_envelope_shading())
            save_if_not_empty(assemblies.get("mass"), locator.get_envelope_mass())

            # HVAC
            save_if_not_empty(assemblies.get("hvac_controller"), locator.get_hvac_controller())
            save_if_not_empty(assemblies.get("hvac_cooling"), locator.get_hvac_cooling())
            save_if_not_empty(assemblies.get("hvac_heating"), locator.get_hvac_heating())
            save_if_not_empty(assemblies.get("hvac_hotwater"), locator.get_hvac_hotwater())
            save_if_not_empty(assemblies.get("hvac_ventilation"), locator.get_hvac_ventilation())

            # SUPPLY
            save_if_not_empty(assemblies.get("supply_cooling"), locator.get_supply_cooling())
            save_if_not_empty(assemblies.get("supply_electricity"), locator.get_supply_electricity())
            save_if_not_empty(assemblies.get("supply_heating"), locator.get_supply_heating())
            save_if_not_empty(assemblies.get("supply_hotwater"), locator.get_supply_hotwater())

        except Exception as e:
            print("❌ Assemblies error:", e)
            return Response(
                {"error": "Assemblies save failed"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # =====================================================
        # 3️⃣ SAVE COMPONENTS
        # =====================================================
        try:
            photovoltaic = components.get("photovoltaic", [])

            if photovoltaic:
                df = pd.DataFrame(photovoltaic)
                path = locator.get_conversion_photovoltaic_panels()
                df.to_csv(path, index=False)

        except Exception as e:
            print("❌ Components error:", e)
            return Response(
                {"error": "Components save failed"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # =====================================================
        # SUCCESS RESPONSE
        # =====================================================
        return Response(
            {"message": "All data saved successfully"},
            status=status.HTTP_200_OK
        )
import numpy as np
def clean_numpy(obj):
    if isinstance(obj, dict):
        return {k: clean_numpy(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_numpy(i) for i in obj]
    elif isinstance(obj, (np.generic,)):
        return obj.item()
    return obj

class DataManagerView(APIView):

    def get(self, request):
        try:
            user=request.user
            locator = get_locator_from_user(user)
            data = get_use_type(user)
            use_type = data['use_type']
            per_commercial = data["per_commercial"]
            per_residential = data["per_residential"]

            # BUILDING DATA
            zone_data = building_info(locator, use_type, per_commercial, per_residential)

            # ✅ Clean numpy
            zone_data = clean_numpy(zone_data)

            return Response({
                "zone": zone_data,
                "total_buildings": len(zone_data),
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
class MapLocatorView(APIView):
    
    def get(self, request):
        try:
            user=request.user
            locator = get_locator_from_user(user)
            all_buildings = info_all_buildings(locator)
            return Response({
                "buildings": all_buildings
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
class SaveLocatorView(APIView):
    
    def post(self, request):

        user=request.user
        try:
            # ✅ DRF handles JSON automatically
            body = request.data

            selected = body.get("selected_buildings", [])
            params = body.get("parameters", {})

            data = save_locator_json(user, selected, params)

            return Response({
                "message": "save successfully ",
                "data": data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"status": "error", "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
import traceback
@api_view(['POST'])
def dt_wise_building(request):
    try:
        # -----------------------------
        # GET FILE NAME FROM FRONTEND
      

        shp_path = None
        # -----------------------------
        # OPTION 1: PATH
        # -----------------------------
        dt_path = request.data.get("dt_file")

        if dt_path:
            print("Using PATH:", dt_path)

            if not os.path.exists(dt_path):
                return Response({"error": "Path not found"}, status=404)

            shp_path = dt_path

        # -----------------------------
        # OPTION 2: MULTI FILE UPLOAD
        # -----------------------------
        elif request.FILES.getlist("dt_files"):

            print("Using MULTI FILE upload")

            files = request.FILES.getlist("dt_files")
            print('files',files)
            temp_dir = tempfile.mkdtemp()

            shp_file_name = None

            # Save all files
            for f in files:
                file_path = os.path.join(temp_dir, f.name)

                with open(file_path, "wb+") as dest:
                    for chunk in f.chunks():
                        dest.write(chunk)

                if f.name.endswith(".shp"):
                    shp_file_name = f.name

            if not shp_file_name:
                return Response({"error": ".shp file missing"}, status=400)

            shp_path = os.path.join(temp_dir, shp_file_name)

            os.environ["SHAPE_RESTORE_SHX"] = "YES"

        else:
            return Response(
                {"error": "Provide path OR upload shapefile"},
                status=400
            )

        # -----------------------------
        # READ SHAPEFILE
        # -----------------------------
        dt = gpd.read_file(shp_path)

        # -----------------------------
        # BUILDINGS FIXED PATH
        # -----------------------------
        buildings = gpd.read_file(
            r"C:\RaviNamdev\India Database for Building simulator\reidential_sub_div5\Buildings_with_peak_dem.shp"
        )


        # -----------------------------
        # CLEAN
        # -----------------------------
        dt.columns = dt.columns.str.strip()
        buildings.columns = buildings.columns.str.strip()

        if "Sub_Class" not in buildings.columns:
            buildings["Sub_Class"] = "Unknown"

        buildings["Sub_Class"] = buildings["Sub_Class"].fillna("Unknown")

        capacity_field = "Rating_Num"
        building_load_field = "peakdemand"

        # -----------------------------
        # CRS FIX
        # -----------------------------
        if dt.crs is None:
            dt.set_crs(epsg=4326, inplace=True)

        if buildings.crs is None:
            buildings.set_crs(epsg=4326, inplace=True)

        # -----------------------------
        # GEOMETRY CLEAN
        # -----------------------------
        dt = dt[dt.geometry.notnull()]
        buildings = buildings[buildings.geometry.notnull()]

        buildings[building_load_field] = pd.to_numeric(
            buildings[building_load_field],
            errors="coerce"
        ).fillna(0)

        # -----------------------------
        # IDS
        # -----------------------------
        dt["DT_ID"] = range(1, len(dt) + 1)

        dt = dt[["DT_ID", capacity_field, "geometry"]]
        buildings = buildings[
            ["Name", "Class", "Sub_Class", building_load_field, "geometry"]
        ]

        # -----------------------------
        # PROJECT CRS
        # -----------------------------
        dt = dt.to_crs(epsg=32643)
        buildings = buildings.to_crs(epsg=32643)

        dt["geometry"] = dt.geometry.centroid
        b_centroids = buildings.copy()
        b_centroids["geometry"] = b_centroids.geometry.centroid

        # -----------------------------
        # BUFFER + JOIN
        # -----------------------------
        dt_buffer = dt.copy()
        dt_buffer["geometry"] = dt_buffer.geometry.buffer(200)

        all_matches = gpd.sjoin(
            b_centroids,
            dt_buffer,
            how="inner",
            predicate="within"
        )

        # -----------------------------
        # DISTANCE
        # -----------------------------
        all_matches["distance"] = all_matches.apply(
            lambda row: row.geometry.distance(
                dt.loc[dt["DT_ID"] == row["DT_ID"], "geometry"].values[0]
            ),
            axis=1
        )

        # -----------------------------
        # ASSIGNMENT
        # -----------------------------
        dt["current_load"] = 0.0
        assignment = {}

        all_matches = all_matches.sort_values(
            building_load_field, ascending=False
        )

        for b_id, group in all_matches.groupby("Name"):

            best_score = float("inf")
            best_dt = None
            building_load = group.iloc[0][building_load_field]

            for _, row in group.iterrows():

                dt_id = row["DT_ID"]

                capacity = dt.loc[
                    dt["DT_ID"] == dt_id, capacity_field
                ].values[0]

                current_load = dt.loc[
                    dt["DT_ID"] == dt_id, "current_load"
                ].values[0]

                remaining = (capacity * 0.9) - current_load

                if remaining < building_load:
                    continue

                score = (row["distance"] / 200) - (
                    remaining / (capacity * 0.9)
                )

                if score < best_score:
                    best_score = score
                    best_dt = dt_id

            if best_dt:
                assignment[b_id] = best_dt
                dt.loc[
                    dt["DT_ID"] == best_dt,
                    "current_load"
                ] += building_load

        # -----------------------------
        # FINAL
        # -----------------------------
        buildings["assigned_dt"] = buildings["Name"].map(assignment)
        selected = buildings.dropna(subset=["assigned_dt"])

        dt["utilization_pct"] = (
            dt["current_load"] / (dt[capacity_field] * 0.9)
        ) * 100

        dt = dt.to_crs(epsg=4326)
        selected = selected.to_crs(epsg=4326)

        return Response({
            "dt": json.loads(dt.to_json()),
            "buildings": json.loads(selected.to_json()),
            "center": [
                float(dt.geometry.y.mean()),
                float(dt.geometry.x.mean())
            ]
        })

    except Exception as e:
        print(traceback.format_exc())
        return Response({"error": str(e)}, status=500)
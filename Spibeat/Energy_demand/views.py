from django.http import HttpResponse, JsonResponse
import geopandas as gpd
import pandas as pd
import json
from django.views.decorators.csrf import ensure_csrf_cookie
from .demand.total_demand import total_demand
from .demand.inputLocator import InputLocator
from django.views.decorators.csrf import csrf_exempt
from .demand.cooling_load import run_cooling_cal
from .demand.peak_load import peak_load
from .demand.Hot_water import run_dhw
from .demand.Auxialary import run_aux_cal
from .demand.Ea_El import run_ea_el
from .demand.total_demand import total_demand
from .demand.Final_total_demand import final_total_demand
import os
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.conf import settings
import os, zipfile, uuid, json, shutil
import pandas as pd
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import os, zipfile, uuid, json
import pandas as pd
from .building_data import building_info,info_all_buildings
from .views_supportor import *
@csrf_exempt
def demand_home(request):
    return JsonResponse({"status": "Demand API working"})
@csrf_exempt
def upload_weather_and_shapefile_files(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=400)
    try:
        weather = request.FILES.get("weather")
        building_zip = request.FILES.get("building")
        building_files = request.FILES.getlist("building_files")
        output_root = request.POST.get("output_path")
        # VALIDATION
        if not weather:
            return JsonResponse({"error": "Weather file required"}, status=400)
        
        if not building_zip and not building_files:
            return JsonResponse({"error": "Building files required"}, status=400)

        if not output_root:
            return JsonResponse({"error": "output_path required"}, status=400)

        # CREATE PROJECT
        project_id = str(uuid.uuid4())
        project_folder = os.path.join(get_upload_dir(), f"project_{project_id}")

        building_dir = os.path.join(project_folder, "building")
        weather_dir = os.path.join(project_folder, "weather")

        # USER OUTPUT PATH
        output_dir = os.path.join(output_root)

        os.makedirs(building_dir, exist_ok=True)
        os.makedirs(weather_dir, exist_ok=True)
        os.makedirs(output_dir, exist_ok=True)

        # SAVE OUTPUT PATH
        with open(os.path.join(project_folder, "output_path.txt"), "w") as f:
            f.write(output_dir)

        # BUILDING FILES
        if building_zip:
            extract_zip(building_zip, building_dir)
        else:
            for f in building_files:
                path = os.path.join(building_dir, f.name)
                os.makedirs(os.path.dirname(path), exist_ok=True)

                with open(path, "wb+") as dest:
                    for chunk in f.chunks():
                        dest.write(chunk)

        missing = validate_shapefile(building_dir)
        if missing:
            return JsonResponse({"error": f"Missing shapefile parts: {missing}"}, status=400)

        # WEATHER FILE
        if weather.name.endswith(".zip"):
            extract_zip(weather, weather_dir)
        else:
            with open(os.path.join(weather_dir, weather.name), "wb+") as f:
                for chunk in weather.chunks():
                    f.write(chunk)

        epw = find_epw(weather_dir)
        if not epw:
            return JsonResponse({"error": "EPW file not found"}, status=400)

        return JsonResponse({
            "status": "success",
            "project_id": project_id,
            "output_path": output_dir
        })

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

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
def input_locator(request):
    project_id = request.GET.get("project_id")
    if not project_id:
            return JsonResponse({"error": "project_id required"}, status=400)

    locator = get_locator_from_project(project_id)
    # =============================
    # USE TYPES
    # =============================  
    use_list = get_unique_values(locator.get_use_types(), "use_type")
    # Envelope list
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
    print('foor path',mass)
    
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
    cooling= read_csv_safe(locator.get_hvac_cooling())
    hotwater= read_csv_safe(locator.get_hvac_hotwater())
    heating = read_csv_safe(locator.get_hvac_heating())
    ventilation= read_csv_safe(locator.get_hvac_ventilation())
    # SUPPLY FILES
    supply_cooling= read_csv_safe(locator.get_supply_cooling())
    supply_electricity= read_csv_safe(locator.get_supply_electricity())
    supply_heating= read_csv_safe(locator.get_supply_heating())
    supply_hotwater= read_csv_safe(locator.get_supply_hotwater())
    # Componants photovoltaic_panel .csv
    photovoltaic= read_csv_safe(locator.get_conversion_photovoltaic_panels())
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
        "floor":floor,
        "shading": shading,
        "tightness": tightness,
        "window": window,
        "use_types": use_list,
        #"floor_types":floor_list,
        "hvac_controller":controller,
        
        "hvac_cooling":cooling,
        "hvac_heating":heating,
        "hvac_ventilation":ventilation,
        "hvac_hotwater":hotwater  ,
        "supply_cooling":supply_cooling,
        "supply_electricity":supply_electricity,
        "supply_heating":supply_heating,
        "supply_hotwater":supply_hotwater,
        # photovoltaic.csv
        "photovoltaic": photovoltaic,
        # load demand dynamic parameter
        "floor_types": floor_list,
        "wall_types":wall_list,
        "window_types":window_list,
        "tightness_types":tightness_list,
        "roof_types":roof_list,
        "shading_types":shading_list,
        "hotwater_types":hotwater_list,
        "cooling_types":cooling_list
         
    }

    return JsonResponse(data)
# ======================================================
# GET DATA
# ======================================================
import os
import json
import pandas as pd
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
def get_use_data(request):
    project_id = request.GET.get("project_id")

    if not project_id:
            return JsonResponse({"error": "project_id required"}, status=400)

    locator = get_locator_from_project(project_id)
    use = request.GET.get("use")
    if not use:
        return JsonResponse({"error": "No use type provided"})

    # 1. Load use_types.csv
    use_df = pd.read_csv(locator.get_use_types())
    use_df.columns = use_df.columns.str.strip()
    row = use_df[use_df["use_type"] == use]
    if row.empty:
        return JsonResponse({"error": "Use type not found"})
    use_row = row.iloc[0].to_dict()

    # 2. Load schedule CSV
    schedule_file = os.path.join(locator.get_schedule_library(), f"{use}.csv")
    if os.path.exists(schedule_file):
        schedule_df = pd.read_csv(schedule_file)
        schedule_data = {
            "columns": schedule_df.columns.tolist(),
            "rows": schedule_df.to_dict(orient="records")
        }
    else:
        schedule_data = {"columns": [], "rows": []}

    # 3. Load multipliers
    def read_multiplier(type_name):
        path = locator.get_monthly_multiplier(type_name)
        if not os.path.exists(path):
            return {}
        df = pd.read_csv(path)
        df.columns = df.columns.str.strip()
        row = df[df["use_type"] == use]
        return row.iloc[0].to_dict() if not row.empty else {}
    response = {
        "use_row": use_row,
        "schedule": schedule_data,
        "mul_HW_row": read_multiplier("HW"),
        "mul_AC_row": read_multiplier("AC"),
        "mul_AUX_row": read_multiplier("AUX"),
        "mul_EaEl_row": read_multiplier("EaEl")
    }
    return JsonResponse(response)



@csrf_exempt
def save_use_data(request):
    
    # ===============================
    # VALIDATE METHOD
    # ===============================
    if request.method != "POST":
        return JsonResponse({"error": "POST request required"})


        # ===============================
    # READ JSON BODY
    # ===============================
    try:
        project_id = request.GET.get("project_id")

        if not project_id:
            return JsonResponse({"error": "project_id required"}, status=400)

        locator = get_locator_from_project(project_id)
        body = json.loads(request.body)
        print("Incoming Data:", body)
    except Exception as e:
        print("JSON ERROR:", e)
        return JsonResponse({"error": "Invalid JSON"})


    # ===============================
    # GET DATA FROM FRONTEND
    # ===============================
    archetypes = body.get("archetypes", {})
    assemblies = body.get("assemblies", {})
    components = body.get("components", {})



    # =====================================================
    # 1️⃣ SAVE ARCHETYPE DATA
    # =====================================================

    use = archetypes.get("use_type")
    per_commercial = archetypes.get("per_commercial")
    per_residential = archetypes.get("per_residential")
    row_data = archetypes.get("row_data", {})
    multipliers = archetypes.get("multipliers", {})
    schedule_rows = archetypes.get("schedule_rows", [])
 
    print(" global Use Type:", use)
    print('per_residential',per_residential)
    print('per_commercial',per_commercial)
    print('row data',row_data)
    print('multiplier',multipliers)
    print('schedule_rows',schedule_rows)
    print()

    if use:
        save_use_type(project_id, use,per_residential,per_commercial)
          
        # ---------------------------
        # UPDATE use_types.csv
        # ---------------------------


            # Save row data
        save_use_type_row(locator, use, row_data)
        
        # UPDATE MONTHLY MULTIPLIERS
        # ---------------------------
        update_multiplier(locator,use,"HW", multipliers.get("HW", {}))
        update_multiplier(locator,use,"AC", multipliers.get("AC", {}))
        update_multiplier(locator,use,"AUX", multipliers.get("AUX", {}))
        update_multiplier(locator,use,"EaEl", multipliers.get("EaEl", {}))
        # ---------------------------
        # SAVE SCHEDULE CSV
        # ---------------------------
        try:
            if schedule_rows:
                save_schedule(locator,use,schedule_rows)     
        except Exception as e:
            print("Schedule error:", e)



    # =====================================================
    # 2️⃣ SAVE ASSEMBLIES DATA
    # =====================================================
    try:
        print("===== ASSEMBLIES RECEIVED =====")
        # Helper function
        def save_if_not_empty(data, path, name):
            if data and len(data) > 0:
                df = pd.DataFrame(data)
                print(f"Saving {name}: {df.shape}")
                df.to_csv(path, index=False)
            else:
                print(f"⚠️ Skipped empty data for {name}")

        # ---------------- ENVELOPE ----------------
        save_if_not_empty(assemblies.get("floor"), locator.get_envelope_floor(), "floor")
        save_if_not_empty(assemblies.get("wall"), locator.get_envelope_wall(), "wall")
        save_if_not_empty(assemblies.get("roof"), locator.get_envelope_roof(), "roof")
        save_if_not_empty(assemblies.get("window"), locator.get_envelope_window(), "window")
        save_if_not_empty(assemblies.get("tightness"), locator.get_envelope_tightness(), "tightness")
        save_if_not_empty(assemblies.get("shading"), locator.get_envelope_shading(), "shading")
        save_if_not_empty(assemblies.get("mass"), locator.get_envelope_mass(), "mass")

        # ---------------- HVAC ----------------
        save_if_not_empty(assemblies.get("hvac_controller"), locator.get_hvac_controller(), "hvac_controller")
        save_if_not_empty(assemblies.get("hvac_cooling"), locator.get_hvac_cooling(), "hvac_cooling")
        save_if_not_empty(assemblies.get("hvac_heating"), locator.get_hvac_heating(), "hvac_heating")
        save_if_not_empty(assemblies.get("hvac_hotwater"), locator.get_hvac_hotwater(), "hvac_hotwater")
        save_if_not_empty(assemblies.get("hvac_ventilation"), locator.get_hvac_ventilation(), "hvac_ventilation")

        # ---------------- SUPPLY ----------------
        save_if_not_empty(assemblies.get("supply_cooling"), locator.get_supply_cooling(), "supply_cooling")
        save_if_not_empty(assemblies.get("supply_electricity"), locator.get_supply_electricity(), "supply_electricity")
        save_if_not_empty(assemblies.get("supply_heating"), locator.get_supply_heating(), "supply_heating")
        save_if_not_empty(assemblies.get("supply_hotwater"), locator.get_supply_hotwater(), "supply_hotwater")

    except Exception as e:
        print("❌ Assemblies save error:", e)


    # COMPONANTS
    try:

        photovoltaic= components.get("photovoltaic", [])

        if components:

            photovoltaic_df = pd.DataFrame(photovoltaic)
            path = locator.get_conversion_photovoltaic_panels()
            photovoltaic_df.to_csv(path, index=False)

    except Exception as e:

        print("Components save error:", e)



    # =====================================================
    # SUCCESS RESPONSE
    # =====================================================

    return JsonResponse({
        "status": "All data saved successfully"
    })
# @csrf_exempt
# def data_manager(request):
#     try:
#         project_id = request.GET.get("project_id")

#         if not project_id:
#             return JsonResponse({"error": "project_id required"}, status=400)

#         # -------------------------
#         # Get data
#         # -------------------------
#         locator = get_locator_from_project(project_id)

#         zone_data = building_info(locator)
#         use_type = get_use_type(project_id)
#         use_type_row = get_use_type_row(locator, use_type)
#         schedule_df=get_schedule(locator,use_type)
#         print("📌 use_type:", use_type)
#         print("📌 use_type_row:", use_type_row)
#         print('schedule type',schedule_df)
        

#                     # -------------------------
#             # Send to frontend
#         # -------------------------
#         return JsonResponse({
#             "zone": zone_data,
#             "indoor_comfort":use_type_row,
#             "schedule_rows": schedule_df.to_dict(orient="records"),
#             "schedule_columns": schedule_df.columns.tolist()
#             })
            
#     except Exception as e:
#         import traceback
#         traceback.print_exc()
#         return JsonResponse({"error": str(e)}, status=500)
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import numpy as np

# ============================================================
# SAFE CONVERTER (IMPORTANT)
# ============================================================
def clean_numpy(obj):
    if isinstance(obj, dict):
        return {k: clean_numpy(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_numpy(i) for i in obj]
    elif isinstance(obj, (np.generic,)):
        return obj.item()
    return obj


# ============================================================
# API
# ============================================================
@csrf_exempt
def data_manager(request):
    try:
        project_id = request.GET.get("project_id")

        if not project_id:
            return JsonResponse({"error": "project_id required"}, status=400)

        locator = get_locator_from_project(project_id)
        data= get_use_type(project_id)
        use_type=data['use_type']
        per_commercial=data["per_commercial"]
        per_residential=data["per_residential"]
        
        # -------------------------------
        # BUILDING DATA
        # -------------------------------
        zone_data = building_info(locator, use_type,per_commercial,per_residential)

        # 🔥 CRITICAL FIX: clean numpy types
        zone_data = clean_numpy(zone_data)

        print("\n🚀 SENDING TO FRONTEND")
        print("📄 Sample:", zone_data[:1])
        print("📦 Count:", len(zone_data))

        # -------------------------------
        # FINAL RESPONSE (ONLY ZONE)
        # -------------------------------
        return JsonResponse({
            "zone": zone_data,
            "total_buildings": len(zone_data),
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({"error": str(e)}, status=500)
@csrf_exempt
def map_locator(request):
    try:
        project_id = request.GET.get("project_id")
        if not project_id:
            return JsonResponse({"error": "project_id required"}, status=400)
        locator = get_locator_from_project(project_id)
        all_buildings= info_all_buildings(locator)
        print("\n🚀 SENDING TO FRONTEND")
        print("📄 Sample first building:",all_buildings  [:1])  # first building preview
        print("📦 Buildings count:", len(all_buildings  ))
        return JsonResponse({
            "buildings": all_buildings     
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({"error": str(e)}, status=500)
from django.views.decorators.csrf import csrf_exempt
import json
from django.http import JsonResponse
@csrf_exempt
def save_locator(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request"}, status=400)

    try:
        body = json.loads(request.body)

        project_id = request.GET.get("project_id")
        selected = body.get("selected_buildings", [])
        params = body.get("parameters", {})
       

        if not project_id:
            return JsonResponse({"status": "error", "message": "Missing project_id"})

        data = save_locator_json(project_id, selected, params)

        return JsonResponse({
            "status": "success",
            "data": data
        })

    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)})

@csrf_exempt
def run_cooling(request):

    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=400)

    try:
        project_id = request.GET.get("project_id")
        use_type=get_use_type(project_id)
        if not project_id:
            return JsonResponse({"error": "project_id required"}, status=400)

        locator = get_locator_from_project(project_id)
        building_json = get_locator_json(project_id)
        building_data= building_json["parameters"]
        print('building_info',building_info)
        print("EPW:", locator.get_epw())
        COOL_DIR  = run_cooling_cal(
            locator,
            building_data
        )
        return JsonResponse({"success": "cooling run successfully", "cooling_dir": COOL_DIR },status=200)
    except Exception as e:
        return JsonResponse({"error cooling failed ": str(e)}, status=500)

# ================================
# API ENDPOINTS
# ================================
@csrf_exempt
def run_hotwater(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=400)

    # Get project_id from GET parameters
    project_id = request.GET.get("project_id")
    if not project_id:
        return JsonResponse({"error": "project_id required"}, status=400)

    try:
        # Get locator for this project
        locator = get_locator_from_project(project_id)
        use_type=get_use_type(project_id)
        building_json = get_locator_json(project_id)
        building_data=building_json["parameters"]
        # Run the hotwater calculation
        # Assuming run_dhw is your helper function
        DHW_DIR= run_dhw(locator,building_data)
        return JsonResponse({"status": "success", "data":  DHW_DIR})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
@csrf_exempt
def run_eael(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=400)

    project_id = request.GET.get("project_id")
    if not project_id:
        return JsonResponse({"error": "project_id required"}, status=400)

    try:
        locator = get_locator_from_project(project_id)
        use_type=get_use_type(project_id)
        print("EPW PATH:")
        building_json = get_locator_json(project_id)
        building_data=building_json["parameters"]
        # ✅ FIXED CALL
        EAEL_DIR = run_ea_el(use_type,locator, building_data)

        return JsonResponse({"status": "success", "data": EAEL_DIR})

    except Exception as e:
        import traceback
        traceback.print_exc()   # 🔥 VERY IMPORTANT
        return JsonResponse({"error": str(e)}, status=500)
@csrf_exempt
def run_aux(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=400)

    project_id = request.GET.get("project_id")
    use_type=get_use_type(project_id)
    building_json = get_locator_json(project_id)
    building_data=building_json["parameters"]
    print('use_type',use_type)
    if not project_id:
        return JsonResponse({"error": "project_id required"}, status=400)

    try:
        locator = get_locator_from_project(project_id)

        print("EPW PATH:", locator.get_epw())

        AUX_DIR= run_aux_cal(use_type,locator,building_data)
        return JsonResponse({"status": "success", "data":  AUX_DIR})

    except Exception as e:
        print("❌ AUX ERROR:", str(e))  

        return JsonResponse({"error": str(e)}, status=500)
@csrf_exempt
def run_total(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=400)

    project_id = request.GET.get("project_id")
    if not project_id:
        return JsonResponse({"error": "project_id required"}, status=400)

    try:
        use_type=get_use_type(project_id)
        if not project_id:
            return JsonResponse({"error": "project_id required"}, status=400)
        hotwater_type = "HIGH_TEMP"
        locator = get_locator_from_project(project_id)
        building_json = get_locator_json(project_id)
        building_data= building_json["parameters"]
        demand_output= total_demand(use_type,locator)
        final_demand=final_total_demand(demand_output,locator)
        return JsonResponse({
            "status": "success",
            "demand_output_dir": demand_output,
            "final_total_demand_output_dir":final_demand
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({"error": str(e)}, status=500)
@csrf_exempt
def peak_demand(request):

    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=400)

    project_id = request.GET.get("project_id")
    if not project_id:
        return JsonResponse({"error": "project_id required"}, status=400)

    try:
        locator = get_locator_from_project(project_id)

        file_path,df_peak= peak_load(locator)

        return JsonResponse({
            "message": "Peak load calculated successfully 📈",
            "file": file_path,
            "data": df_peak.to_dict(orient="records")
        },status=200)

    except Exception as e:
        return JsonResponse({
            "status": "error",
            "message": str(e)
        }, status=500)
@csrf_exempt
def search_eael(request):
    try:
        # ================= METHOD CHECK =================
        if request.method != "POST":
            return JsonResponse({"error": "POST required"}, status=400)

        # ================= PROJECT =================
        project_id = request.GET.get("project_id")
        if not project_id:
            return JsonResponse({"error": "project_id required"}, status=400)

        locator = get_locator_from_project(project_id)

        # ================= BODY =================
        try:
            data = json.loads(request.body)
        except Exception:
            return JsonResponse({"error": "Invalid JSON body"}, status=400)

        building_name = data.get("building_name")
        start_date = data.get("start_date")
        end_date = data.get("end_date")

        # ================= VALIDATION =================
        if not building_name:
            return JsonResponse({"error": "building_name required"}, status=400)

        folder = locator.get_ea_el_output_dir()
        file_path = os.path.join(folder, f"Ea_El_FULL_YEAR_{building_name}.csv")

        # ================= FILE CHECK =================
        if not os.path.exists(file_path):
            return JsonResponse({
                "error": f"Building '{building_name}' not found"
            }, status=404)

        # ================= READ CSV =================
        try:
            df = pd.read_csv(file_path)
        except Exception as e:
            return JsonResponse({
                "error": "Error reading CSV file",
                "details": str(e)
            }, status=500)

        # ================= EMPTY FILE =================
        if df.empty:
            return JsonResponse({
                "error": "CSV file is empty"
            }, status=404)

        # ================= DATE RANGE FILTER (DATE ONLY) =================
        if start_date and end_date:
            try:
                # Convert timestamps safely
                if "timestamps" not in df.columns:
                    return JsonResponse({
                        "error": "timestamps column missing in CSV"
                    }, status=500)

                df["timestamps"] = pd.to_datetime(df["timestamps"], errors="coerce")

                # Remove invalid rows
                df = df.dropna(subset=["timestamps"])

                # Extract DATE ONLY (IMPORTANT FIX)
                df["date_only"] = df["timestamps"].dt.date

                start = pd.to_datetime(start_date).date()
                end = pd.to_datetime(end_date).date()

            except Exception:
                return JsonResponse({
                    "error": "Invalid date format. Use YYYY-MM-DD"
                }, status=400)

            # ✅ VALIDATE RANGE
            if start > end:
                return JsonResponse({
                    "error": "Start date cannot be after end date"
                }, status=400)

            # ✅ FILTER USING DATE ONLY
            df = df[
                (df["date_only"] >= start) &
                (df["date_only"] <= end)
            ]

            # ✅ NO DATA
            if df.empty:
                return JsonResponse({
                    "error": f"No data found from {start_date} to {end_date}"
                }, status=404)

        # ================= FINAL RESPONSE =================
        results = df.to_dict(orient="records")

        return JsonResponse({
            "data": results,
            "count": len(results),
            "building": building_name,
            "range": {
                "start": start_date,
                "end": end_date
            }
        })

    except Exception as e:
        return JsonResponse({
            "error": "Unexpected server error",
            "details": str(e)
        }, status=500)
import os
import json
import pandas as pd
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def search_hotwater(request):
    try:
        # ================= METHOD CHECK =================
        if request.method != "POST":
            return JsonResponse({"error": "POST required"}, status=400)

        # ================= PROJECT =================
        project_id = request.GET.get("project_id")
        if not project_id:
            return JsonResponse({"error": "project_id required"}, status=400)

        locator = get_locator_from_project(project_id)

        # ================= BODY =================
        try:
            data = json.loads(request.body)
        except Exception:
            return JsonResponse({"error": "Invalid JSON body"}, status=400)

        building_name = data.get("building_name")
        start_date = data.get("start_date")
        end_date = data.get("end_date")

        # ================= VALIDATION =================
        if not building_name:
            return JsonResponse({"error": "building_name required"}, status=400)

        # ================= FILE PATH =================
        folder = locator.get_hotwater_output_dir()
        file_path = os.path.join(folder, f"{building_name}_DHW_YEAR.csv")

        # DEBUG (optional)
        print("Reading file:", file_path)

        # ================= FILE CHECK =================
        if not os.path.exists(file_path):
            return JsonResponse({
                "error": f"Building '{building_name}' not found"
            }, status=404)

        # ================= READ CSV =================
        try:
            df = pd.read_csv(file_path)
        except Exception as e:
            return JsonResponse({
                "error": "Error reading CSV file",
                "details": str(e)
            }, status=500)

        # ================= EMPTY CHECK =================
        if df.empty:
            return JsonResponse({
                "error": "CSV file is empty"
            }, status=404)

        # ================= FIX TIMESTAMP COLUMN =================
        if "timestamps" not in df.columns:
            for col in df.columns:
                if "time" in col.lower() or "date" in col.lower():
                    df.rename(columns={col: "timestamps"}, inplace=True)
                    break

        if "timestamps" not in df.columns:
            return JsonResponse({
                "error": "No timestamp column found in CSV"
            }, status=500)

        # Convert to datetime
        df["timestamps"] = pd.to_datetime(df["timestamps"], errors="coerce")
        df = df.dropna(subset=["timestamps"])

        # ================= FIX HOT WATER COLUMN =================
        if "DHW_el_kWh" in df.columns:
            df["hotwater_kW"] = df["DHW_el_kWh"]
        else:
            return JsonResponse({
                "error": "DHW_el_kWh column missing in CSV"
            }, status=500)

        # ================= DATE FILTER =================
        if start_date and end_date:
            try:
                df["date_only"] = df["timestamps"].dt.date

                start = pd.to_datetime(start_date).date()
                end = pd.to_datetime(end_date).date()

            except Exception:
                return JsonResponse({
                    "error": "Invalid date format (use YYYY-MM-DD)"
                }, status=400)

            if start > end:
                return JsonResponse({
                    "error": "Start date cannot be after end date"
                }, status=400)

            df = df[
                (df["date_only"] >= start) &
                (df["date_only"] <= end)
            ]

            if df.empty:
                return JsonResponse({
                    "error": f"No data found from {start_date} to {end_date}"
                }, status=404)

        # ================= FINAL RESPONSE =================
        results = df[["timestamps", "hotwater_kW"]].to_dict(orient="records")

        return JsonResponse({
            "data": results,
            "count": len(results),
            "building": building_name,
            "range": {
                "start": start_date,
                "end": end_date
            }
        })

    except Exception as e:
        return JsonResponse({
            "error": "Unexpected server error",
            "details": str(e)
        }, status=500)
        
@csrf_exempt
def search_aux(request):
    try:
        # ================= METHOD CHECK =================
        if request.method != "POST":
            return JsonResponse({"error": "POST required"}, status=400)

        # ================= PROJECT =================
        project_id = request.GET.get("project_id")
        if not project_id:
            return JsonResponse({"error": "project_id required"}, status=400)

        locator = get_locator_from_project(project_id)

        # ================= BODY =================
        try:
            data = json.loads(request.body)
        except Exception:
            return JsonResponse({"error": "Invalid JSON body"}, status=400)

        building_name = data.get("building_name")
        start_date = data.get("start_date")
        end_date = data.get("end_date")

        # ================= VALIDATION =================
        if not building_name:
            return JsonResponse({"error": "building_name required"}, status=400)

        # ================= FILE PATH =================
        folder = locator.get_aux_output_dir()
        file_path = os.path.join(folder, f"aux_{building_name}.csv")

        # DEBUG (optional)
        print("Reading file:", file_path)

        # ================= FILE CHECK =================
        if not os.path.exists(file_path):
            return JsonResponse({
                "error": f"Building '{building_name}' not found"
            }, status=404)

        # ================= READ CSV =================
        try:
            df = pd.read_csv(file_path)
        except Exception as e:
            return JsonResponse({
                "error": "Error reading CSV file",
                "details": str(e)
            }, status=500)

        # ================= EMPTY CHECK =================
        if df.empty:
            return JsonResponse({
                "error": "CSV file is empty"
            }, status=404)

        # ================= FIX TIMESTAMP COLUMN =================
        if "timestamps" not in df.columns:
            for col in df.columns:
                if "time" in col.lower() or "date" in col.lower():
                    df.rename(columns={col: "timestamps"}, inplace=True)
                    break

        if "timestamps" not in df.columns:
            return JsonResponse({
                "error": "No timestamp column found in CSV"
            }, status=500)

        # Convert to datetime
        df["timestamps"] = pd.to_datetime(df["timestamps"], errors="coerce")
        df = df.dropna(subset=["timestamps"])
        # ================= DATE FILTER =================
        if start_date and end_date:
            try:
                df["date_only"] = df["timestamps"].dt.date

                start = pd.to_datetime(start_date).date()
                end = pd.to_datetime(end_date).date()

            except Exception:
                return JsonResponse({
                    "error": "Invalid date format (use YYYY-MM-DD)"
                }, status=400)

            if start > end:
                return JsonResponse({
                    "error": "Start date cannot be after end date"
                }, status=400)

            df = df[
                (df["date_only"] >= start) &
                (df["date_only"] <= end)
            ]

            if df.empty:
                return JsonResponse({
                    "error": f"No data found from {start_date} to {end_date}"
                }, status=404)

        # ================= FINAL RESPONSE =================
        results = df.to_dict(orient="records")

        return JsonResponse({
            "data": results,
            "count": len(results),
            "building": building_name,
            "range": {
                "start": start_date,
                "end": end_date
            }
        })

    except Exception as e:
        return JsonResponse({
            "error": "Unexpected server error",
            "details": str(e)
        }, status=500)
@csrf_exempt
def search_cooling(request):
    try:
        # ================= METHOD CHECK =================
        if request.method != "POST":
            return JsonResponse({"error": "POST required"}, status=400)

        # ================= PROJECT =================
        project_id = request.GET.get("project_id")
        if not project_id:
            return JsonResponse({"error": "project_id required"}, status=400)

        locator = get_locator_from_project(project_id)

        # ================= BODY =================
        try:
            data = json.loads(request.body)
        except Exception:
            return JsonResponse({"error": "Invalid JSON body"}, status=400)

        building_name = data.get("building_name")
        start_date = data.get("start_date")
        end_date = data.get("end_date")

        # ================= VALIDATION =================
        if not building_name:
            return JsonResponse({"error": "building_name required"}, status=400)

        # ================= FILE PATH =================
        folder = locator.get_cooling_output_dir()
        file_path = os.path.join(folder, f"HVAC_hourly_YEAR_{building_name}.csv")

        # DEBUG (optional)
        print("Reading file:", file_path)

        # ================= FILE CHECK =================
        if not os.path.exists(file_path):
            return JsonResponse({
                "error": f"Building '{building_name}' not found"
            }, status=404)

        # ================= READ CSV =================
        try:
            df = pd.read_csv(file_path)
        except Exception as e:
            return JsonResponse({
                "error": "Error reading CSV file",
                "details": str(e)
            }, status=500)

        # ================= EMPTY CHECK =================
        if df.empty:
            return JsonResponse({
                "error": "CSV file is empty"
            }, status=404)

        # ================= FIX TIMESTAMP COLUMN =================
        if "timestamps" not in df.columns:
            for col in df.columns:
                if "time" in col.lower() or "date" in col.lower():
                    df.rename(columns={col: "timestamps"}, inplace=True)
                    break

        if "timestamps" not in df.columns:
            return JsonResponse({
                "error": "No timestamp column found in CSV"
            }, status=500)

        # Convert to datetime
        df["timestamps"] = pd.to_datetime(df["timestamps"], errors="coerce")
        df = df.dropna(subset=["timestamps"])
        # ================= DATE FILTER =================
        if start_date and end_date:
            try:
                df["date_only"] = df["timestamps"].dt.date

                start = pd.to_datetime(start_date).date()
                end = pd.to_datetime(end_date).date()

            except Exception:
                return JsonResponse({
                    "error": "Invalid date format (use YYYY-MM-DD)"
                }, status=400)

            if start > end:
                return JsonResponse({
                    "error": "Start date cannot be after end date"
                }, status=400)

            df = df[
                (df["date_only"] >= start) &
                (df["date_only"] <= end)
            ]

            if df.empty:
                return JsonResponse({
                    "error": f"No data found from {start_date} to {end_date}"
                }, status=404)

        # ================= FINAL RESPONSE =================
        results = df.to_dict(orient="records")

        return JsonResponse({
            "data": results,
            "count": len(results),
            "building": building_name,
            "range": {
                "start": start_date,
                "end": end_date
            }
            
        })

    except Exception as e:
        return JsonResponse({
            "error": "Unexpected server error",
            "details": str(e)
        }, status=500)
@csrf_exempt
def search_load(request):
    try:
        # ================= METHOD CHECK =================
        if request.method != "POST":
            return JsonResponse({"error": "POST required"}, status=400)

        # ================= PROJECT =================
        project_id = request.GET.get("project_id")
        if not project_id:
            return JsonResponse({"error": "project_id required"}, status=400)

        locator = get_locator_from_project(project_id)

        # ================= BODY =================
        try:
            data = json.loads(request.body)
        except Exception:
            return JsonResponse({"error": "Invalid JSON body"}, status=400)

        building_name = data.get("building_name")
        start_date = data.get("start_date")
        end_date = data.get("end_date")

        # ================= VALIDATION =================
        if not building_name:
            return JsonResponse({"error": "building_name required"}, status=400)

        # ================= FILE PATH =================
        folder = locator.get_building_wise_total_output_dir()
        file_path = os.path.join(
            folder,
            f"TOTAL_LOAD_REQUIRED_{building_name}_FULL_YEAR.csv"
        )

        print("📂 Reading file:", file_path)

        # ================= FILE CHECK =================
        if not os.path.exists(file_path):
            return JsonResponse({
                "error": f"Building '{building_name}' not found"
            }, status=404)

        # ================= READ CSV =================
        try:
            df = pd.read_csv(file_path)
        except Exception as e:
            return JsonResponse({
                "error": "Error reading CSV file",
                "details": str(e)
            }, status=500)

        # ================= EMPTY CHECK =================
        if df.empty:
            return JsonResponse({
                "error": "CSV file is empty"
            }, status=404)

        print("🧾 CSV Columns:", df.columns.tolist())

        # ================= FIND TIMESTAMP COLUMN =================
        timestamp_col = None
        for col in df.columns:
            col_lower = col.lower()
            if "time" in col_lower or "date" in col_lower:
                timestamp_col = col
                break

        if not timestamp_col:
            return JsonResponse({
                "error": "No timestamp/date column found in CSV"
            }, status=500)

        # ================= CONVERT TO DATETIME =================
        df["timestamps"] = pd.to_datetime(df[timestamp_col], errors="coerce")
        df = df.dropna(subset=["timestamps"])

        # ================= DATE FILTER =================
        if start_date and end_date:
            try:
                df["date_only"] = df["timestamps"].dt.date

                start = pd.to_datetime(start_date).date()
                end = pd.to_datetime(end_date).date()

            except Exception:
                return JsonResponse({
                    "error": "Invalid date format (use YYYY-MM-DD)"
                }, status=400)

            if start > end:
                return JsonResponse({
                    "error": "Start date cannot be after end date"
                }, status=400)

            df = df[
                (df["date_only"] >= start) &
                (df["date_only"] <= end)
            ]

            if df.empty:
                return JsonResponse({
                    "error": f"No data found from {start_date} to {end_date}"
                }, status=404)

        # ================= OPTIONAL: SELECT ONLY REQUIRED COLUMNS =================
        # (Uncomment and adjust if needed)
        # df = df[["timestamps", "TOTAL_LOAD"]]

        # ================= LIMIT RESPONSE (IMPORTANT FOR PERFORMANCE) =================
        df = df.sort_values("timestamps")
        results = df.head(1000).to_dict(orient="records")

        # ================= RESPONSE =================
        return JsonResponse({
            "data": results,
            "count": len(results),
            "building": building_name,
            "range": {
                "start": start_date,
                "end": end_date
            }
        })

    except Exception as e:
        print("🔥 ERROR:", str(e))
        return JsonResponse({
            "error": "Unexpected server error",
            "details": str(e)
        }, status=500)
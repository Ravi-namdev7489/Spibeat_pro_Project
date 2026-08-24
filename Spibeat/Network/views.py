import geopandas as gpd
import pandas as pd
from rest_framework.views import APIView
from rest_framework.response import Response
from django.conf import settings
import json
from rest_framework import status
import os
from .network_input_files.baseline_network_input import *
from .network_input_files.timeseries import generate_dt_timeseries
import pypsa
import os
from rest_framework import status
class ProcessDataDTwiseBuilding(APIView):

    def get(self, request):

        # -----------------------------
        # LOAD SHAPEFILES
        # -----------------------------
        dt = gpd.read_file(
            r"C:\RaviNamdev\India Database for Building simulator\reidential_sub_div5\DT_extracted.shp"
        )

        buildings = gpd.read_file(
            r"C:\RaviNamdev\India Database for Building simulator\reidential_sub_div5\Buildings_with_peak_dem.shp"
        )

        # -----------------------------
        # FIELD NAMES
        # -----------------------------
        dt_name_field = "DT_ID"
        capacity_field = "Rating_Num"
        building_load_field = "peakdemand"

        # -----------------------------
        # CLEAN GEOMETRY
        # -----------------------------
        dt["geometry"] = dt.geometry.force_2d()
        buildings["geometry"] = buildings.geometry.force_2d()

        dt = dt[dt.geometry.notnull() & ~dt.geometry.is_empty]
        buildings = buildings[buildings.geometry.notnull() & ~buildings.geometry.is_empty]

        # -----------------------------
        # CLEAN NUMERIC DATA
        # -----------------------------
        buildings[building_load_field] = pd.to_numeric(
            buildings[building_load_field], errors="coerce"
        ).fillna(0)

        dt[dt_name_field] = dt[dt_name_field].astype(str)

        # -----------------------------
        # KEEP REQUIRED COLUMNS
        # -----------------------------
        dt = dt[[dt_name_field, capacity_field, "geometry"]].copy()

        buildings = buildings[
            ["Name", "Class", "Sub_Class", building_load_field, "geometry"]
        ].copy()

        buildings = buildings.rename(columns={"Sub_Class": "Use_type"})

        # -----------------------------
        # PROJECT CRS (METERS)
        # -----------------------------
        dt = dt.to_crs(epsg=32643)
        buildings = buildings.to_crs(epsg=32643)

        # -----------------------------
        # CENTROIDS
        # -----------------------------
        dt["geometry"] = dt.geometry.centroid

        b_centroids = buildings.copy()
        b_centroids["geometry"] = b_centroids.geometry.centroid

        # -----------------------------
        # BUFFER AROUND DT
        # -----------------------------
        dt_buffer = dt.copy()
        dt_buffer["geometry"] = dt_buffer.geometry.buffer(200)

        # -----------------------------
        # SPATIAL JOIN
        # -----------------------------
        all_matches = gpd.sjoin(
            b_centroids,
            dt_buffer,
            how="inner",
            predicate="within"
        )

        # -----------------------------
        # DISTANCE CALC
        # -----------------------------
        all_matches["distance"] = all_matches.apply(
            lambda row: row.geometry.distance(
                dt.loc[
                    dt[dt_name_field] == row[dt_name_field],
                    "geometry"
                ].values[0]
            ),
            axis=1
        )

        # -----------------------------
        # ASSIGNMENT LOGIC
        # -----------------------------
        dt["current_load"] = 0.0
        assignment = {}

        distance_weight = 0.7
        capacity_weight = 0.3

        all_matches = all_matches.sort_values(
            building_load_field,
            ascending=False
        )

        for b_id, group in all_matches.groupby("Name"):

            best_score = float("inf")
            best_dt = None

            building_load = group.iloc[0][building_load_field]
            if pd.isna(building_load):
                building_load = 0

            for _, row in group.iterrows():

                dt_id = row[dt_name_field]

                capacity = dt.loc[
                    dt[dt_name_field] == dt_id,
                    capacity_field
                ].values[0]

                current_load = dt.loc[
                    dt[dt_name_field] == dt_id,
                    "current_load"
                ].values[0]

                remaining_capacity = (capacity * 0.9) - current_load

                if remaining_capacity < building_load:
                    continue

                normalized_distance = row["distance"] / 200
                remaining_ratio = remaining_capacity / (capacity * 0.9)

                score = (
                    distance_weight * normalized_distance
                ) - (
                    capacity_weight * remaining_ratio
                )

                if score < best_score:
                    best_score = score
                    best_dt = dt_id

            if best_dt:
                assignment[b_id] = best_dt
                dt.loc[
                    dt[dt_name_field] == best_dt,
                    "current_load"
                ] += building_load

        # -----------------------------
        # APPLY ASSIGNMENT
        # -----------------------------
        buildings["Assigned_DT"] = buildings["Name"].map(assignment)

        selected_buildings = buildings.dropna(subset=["Assigned_DT"]).copy()

        # -----------------------------
        # UTILIZATION
        # -----------------------------
        dt["utilization_pct"] = (
            dt["current_load"] / (dt[capacity_field] * 0.9)
        ) * 100

        # -----------------------------
        # CSV EXPORT
        # -----------------------------
        csv_path = os.path.join(
            settings.MEDIA_ROOT,
            "DT_Wise_Buildings.csv"
        )

        table = selected_buildings[
            ["Assigned_DT", "Name", "peakdemand", "Use_type"]
        ].copy()

        table.to_csv(csv_path, index=False)

        # -----------------------------
        # CONVERT TO SAFE GEOJSON (IMPORTANT FIX)
        # -----------------------------
        dt = dt.to_crs(epsg=4326)
        buildings = buildings.to_crs(epsg=4326)
        selected_buildings = selected_buildings.to_crs(epsg=4326)

        dt_geojson = json.loads(dt.to_json())
        buildings_geojson = json.loads(buildings.to_json())
        selected_geojson = json.loads(selected_buildings.to_json())

        # -----------------------------
        # RESPONSE
        # -----------------------------
        return Response({
            "dt_geojson": dt_geojson,
            "all_buildings_geojson": buildings_geojson,
            "selected_buildings_geojson": selected_geojson,
            "csv_url": "/media/DT_Wise_Buildings.csv",
            "table": table.to_dict(orient="records")
        })

from rest_framework.views import APIView
from rest_framework.response import Response

from rest_framework.views import APIView
from rest_framework.response import Response
from datetime import datetime

class BaselineNetwork(APIView):

    def post(self, request):
        start_date = request.data.get("start_date")
        end_date= request.data.get("end_date")
        print('start_date',start_date)
        print('end date',end_date)
        Output_Dir= r"C:\RaviNamdev\India Database for Building simulator\Baseline_Scanario_Input"
        Input_Dir= r"C:\RaviNamdev\FinalSpibeat\ShapeFile_to_pypsa_Input\shape_to_pypsa_formate_output"
        os.makedirs(Output_Dir,exist_ok=True)
        # ✅ Generate timeseries
        timeseries = generate_dt_timeseries(start_date,end_date)
        # ✅ If valid → generate all data
        buses = generate_buses_data(Input_Dir,Output_Dir)
        generators = generate_generators_data(Input_Dir,Output_Dir)
        loads = generate_loads_data(Input_Dir,Output_Dir)
        transformers = generate_transformers(Input_Dir,Output_Dir)
        transformer_types = generate_transformer_types(Input_Dir,Output_Dir)
        lines = generate_lines_data(Input_Dir,Output_Dir)

        load_p_q_set = generate_load_pset_qset(Input_Dir,Output_Dir)
        load_p_set = load_p_q_set.get("p_set", [])
        load_q_set = load_p_q_set.get("q_set", [])

        snapshots = generate_snapshots(Input_Dir,Output_Dir)
        generator_pmax = generate_generator_pmax(Input_Dir,Output_Dir)

        return Response({
            "status": "success",
            "message": "Baseline generated successfully ✅",
            "buses": buses,
            "generators": generators,
            "loads": loads,
            "transformers": transformers,
            "transformer_types": transformer_types,
            "lines": lines,
            "load_p_set": load_p_set,
            "load_q_set": load_q_set,
            "snapshots": snapshots,
            "generator_pmax": generator_pmax
        }, status=200)
from rest_framework.views import APIView
from rest_framework.response import Response
import pandas as pd
import os


class SaveBaselineInput(APIView):

    def post(self, request):

        try:
            
            BASE_DIR = r"C:\RaviNamdev\Baseline_for_prototype\Baseline_output"

            # ✅ Ensure directory exists
            os.makedirs(BASE_DIR, exist_ok=True)

            # 🔹 TABLE → FILE MAPPING
            file_map = {
                "buses": "buses.csv",
                "generators": "generators.csv",
                "loads": "loads.csv",
                "transformers": "transformers.csv",
                "transformer_types": "transformer_types.csv",
                "lines": "lines.csv",
                "load_p_set": "loads-p_set.csv",
                "load_q_set": "loads-q_set.csv",
                "snapshots": "snapshots.csv",
                "generator_pmax": "generators-p_max_pu.csv",
                "generators-p_set":"generators-p_set.csv"
            }

            results = {}
            errors = {}
            print("Incoming keys:", request.data.keys())
            # 🔥 LOOP THROUGH PAYLOAD
            for table_name, table_data in request.data.items():
               
                # ❌ Skip invalid tables
                if table_name not in file_map:
                    errors[table_name] = "Invalid table name"
                    continue

                # ❌ Empty data check
                if not table_data:
                    errors[table_name] = "Empty data"
                    continue

                try:
                    # ✅ Convert to DataFrame
                    df = pd.DataFrame(table_data)

                    # ✅ Save CSV
                    file_path = os.path.join(BASE_DIR, file_map[table_name])
                    df.to_csv(file_path, index=False)

                    results[table_name] = {
                        "status": "saved",
                        "rows": len(df),
                        "file": file_path
                    }
                    print('result',results)
                except Exception as e:
                    errors[table_name] = str(e)

            # 🔥 FINAL RESPONSE
            return Response({
                "status": "success" ,
                "message": "Tables processed",
                "saved": results,
                "errors": errors
            })

        except Exception as e:
            return Response({
                "status": "error",
                "message": str(e)
            }, status=500)
import os
import pypsa

from django.conf import settings

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import NetworkResult



# class OptimizeBaselineNetwork(APIView):

#     def get(self, request):

#         try:

#             input_folder = (
#                 r'C:\RaviNamdev\Baseline_for_prototype\Baseline_output'
#             )
    

#             network = pypsa.Network()

#             network.import_from_csv_folder(
#                 input_folder
#             )


#             network.buses["carrier"] = (
#                 network.buses["carrier"]
#                 .fillna("AC")
#             )


#             network.lines["carrier"] = (
#                 network.lines["carrier"]
#                 .fillna("AC")
#             )


#             if "AC" not in network.carriers.index:
#                 network.add(
#                     "Carrier",
#                     "AC"
#                 )


#             # Run power flow
#             network.pf()


#             # Save CSV network

#             save_folder = os.path.join(
#                 settings.MEDIA_ROOT,
#                 "networks",
#                 "latest"
#             )


#             os.makedirs(
#                 save_folder,
#                 exist_ok=True
#             )


#             network.export_to_csv_folder(
#                 save_folder
#             )


#             # Update database

#             NetworkResult.objects.update(
#                 is_latest=False
#             )


#             NetworkResult.objects.create(
#                 name="latest",
#                 network_path=save_folder,
#                 is_latest=True
#             )


#             return Response(
#                 {
#                     "status":"success",
#                     "message":"Network optimized"
#                 }
#             )


#         except Exception as e:

#             return Response(
#                 {
#                     "error":str(e)
#                 },
#                 status=500
#             )
import os
import pypsa

from django.conf import settings

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import NetworkResult


# ============================================================
# BASELINE OPTIMIZATION
# ============================================================
# ============================================================
# MAIN OPTIMIZE API
# ============================================================
import os
import pypsa

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .network_store import (
    run_baseline,
    run_solar,
    run_storage,
    save_optimized_network
)

class OptimizeNetwork(APIView):

    def get(self, request, network_type):

        try:

            input_folders = {

                "baseline":
                    r"C:\RaviNamdev\Baseline_for_prototype\Baseline_output",

                "solar":
                    r"C:\RaviNamdev\Baseline_for_prototype\Solar_output",

                "storage":
                    r"C:\RaviNamdev\Baseline_for_prototype\Storage_output"
            }

            print("Network type:", network_type)
            print("Input folders:", input_folders)

            # ==================================================
            # VALIDATE TYPE
            # ==================================================

            if network_type not in input_folders:

                return Response(
                    {
                        "status": "error",
                        "error": (
                            f"Invalid network type "
                            f"'{network_type}'. "
                            "Allowed: baseline, solar, storage"
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            # ==================================================
            # GET INPUT FOLDER
            # ==================================================

            input_folder = input_folders[network_type]

            print("Input folder:", input_folder)

            # ==================================================
            # CHECK INPUT FOLDER
            # ==================================================

            if not os.path.exists(input_folder):

                return Response(
                    {
                        "status": "error",
                        "error": (
                            f"Input folder does not exist: "
                            f"{input_folder}"
                        )
                    },
                    status=status.HTTP_404_NOT_FOUND
                )

            # ==================================================
            # LOAD NETWORK
            # ==================================================

            print("Loading PyPSA network...")

            network = pypsa.Network()

            network.import_from_csv_folder(
                input_folder
            )

            print("Network loaded")

            # ==================================================
            # CARRIER SETUP
            # ==================================================

            if "carrier" not in network.buses.columns:

                network.buses["carrier"] = "AC"

            else:

                network.buses["carrier"] = (
                    network.buses["carrier"]
                    .fillna("AC")
                )

            if "carrier" not in network.lines.columns:

                network.lines["carrier"] = "AC"

            else:

                network.lines["carrier"] = (
                    network.lines["carrier"]
                    .fillna("AC")
                )

            if "AC" not in network.carriers.index:

                network.add(
                    "Carrier",
                    "AC"
                )

            # ==================================================
            # TYPE BASED OPTIMIZATION
            # ==================================================

            print(
                "Starting optimization:",
                network_type
            )

            if network_type == "baseline":

                print("Running baseline PF")

                network = run_baseline(
                    network
                )

            elif network_type == "solar":

                print("Running solar PF")

                network = run_solar(
                    network
                )

            elif network_type == "storage":

                print("Running storage LOPF")

                network = run_storage(
                    network
                )
                p_generators = network.generators_t.p.groupby(network.generators.carrier, axis=1).sum()
                p_storage_units = network.storage_units_t.p.groupby(network.storage_units.carrier, axis=1).sum()

                # Add '(storage)' to the carrier name directly in the storage DataFrame
                p_storage_units.columns = [f"{col}Storage" for col in p_storage_units.columns]

                # Combine generator and storage data
                p_by_carrier = p_generators.join(p_storage_units, how='outer')
                print("p_by_carrier",p_by_carrier)

            # ==================================================
            # SAVE RESULT
            # ==================================================

            print("Saving optimized network...")

            result, save_folder = (
                save_optimized_network(
                    network,
                    network_type
                )
            )

            print(
                "Network saved:",
                save_folder
            )

            # ==================================================
            # FINAL RESPONSE
            # ==================================================

            return Response(
                {
                    "status": "success",

                    "message": (
                        f"{network_type.capitalize()} "
                        "network optimized successfully"
                    ),

                    "type": network_type,

                    "result_id": result.id,

                    "network_path": save_folder
                },
                status=status.HTTP_200_OK
            )

        except Exception as e:

            print(
                "OPTIMIZATION ERROR:",
                repr(e)
            )

            return Response(
                {
                    "status": "error",

                    "type": network_type,

                    "error": str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import NetworkResult
from .network_store import load_latest_network
class RealPower(APIView):
    def get(self, request,result_type):
        print('rusult type ',result_type)
        try:
            print('result type',result_type)
            match result_type:
                case "baseline":
                    result = NetworkResult.objects.get(result_type=result_type,is_latest=True)
                    optimized_network = load_latest_network(result.network_path)
                    # Get line real power
                    p0_df = optimized_network.lines_t.p0
                                # Convert dataframe to JSON
                    data = ( p0_df.reset_index().to_dict( orient="records"))
                    return Response(
                    {
                        "message":"success",
                        "count":len(data),
                        "data":data,
                        "result_type":result_type
                    },
                    status=status.HTTP_200_OK
                    )
                case "solar":
                    result = NetworkResult.objects.get(result_type=result_type,is_latest=True)
                    optimized_network = load_latest_network(result.network_path)
                    optimized_network.pf()
                    # Get line real power
                    p0_df = optimized_network.lines_t.p0
                                # Convert dataframe to JSON
                    data = ( p0_df.reset_index().to_dict( orient="records"))
                    return Response(
                    {
                        "message":"success",
                        "count":len(data),
                        "data":data,
                        "result_type":result_type
                    },
                    status=status.HTTP_200_OK
                    )

                case "storage":
                    result = NetworkResult.objects.get(result_type=result_type,is_latest=True)
                    optimized_network = load_latest_network(result.network_path)
                    # Get line real power
                    p0_df = optimized_network.lines_t.p0
                                # Convert dataframe to JSON
                    data = ( p0_df.reset_index().to_dict( orient="records"))
                    return Response(
                    {
                        "message":"success",
                        "count":len(data),
                        "data":data,
                        "result_type":result_type
                    },
                    status=status.HTTP_200_OK
                    )
                case _:
                    return Response({
                        "error": f"Invalid '{result_type}'"
                    }, status=400)

        except Exception as e:

            return Response(
                {
                    
                    "error":str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import NetworkResult
from .network_store import load_latest_network


class ReactivePower(APIView):

    def get(self, request, result_type):

        print("Reactive Power result type:", result_type)

        try:

            # ==================================================
            # TYPE BASED RESULT
            # ==================================================

            match result_type:

                # ==================================================
                # BASELINE
                # ==================================================

                case "baseline":

                    result = NetworkResult.objects.get(
                        result_type=result_type,
                        is_latest=True
                    )

                    optimized_network = (
                        load_latest_network(
                            result.network_path
                        )
                    )
                    optimized_network.pf()
                    # Get line reactive power
                    q0_df = optimized_network.lines_t.q0

                    # Convert dataframe to JSON
                    data = (
                        q0_df
                        .reset_index()
                        .to_dict(
                            orient="records"
                        )
                    )

                    return Response(
                        {
                            "message": "success",
                            "count": len(data),
                            "data": data,
                            "result_type": result_type
                        },
                        status=status.HTTP_200_OK
                    )


                # ==================================================
                # SOLAR
                # ==================================================

                case "solar":

                    result = NetworkResult.objects.get(
                        result_type=result_type,
                        is_latest=True
                    )

                    optimized_network = (
                        load_latest_network(
                            result.network_path
                        )
                    )

                    # Get line reactive power
                    q0_df = optimized_network.lines_t.q0

                    # Convert dataframe to JSON
                    data = (
                        q0_df
                        .reset_index()
                        .to_dict(
                            orient="records"
                        )
                    )

                    return Response(
                        {
                            "message": "success",
                            "count": len(data),
                            "data": data,
                            "result_type": result_type
                        },
                        status=status.HTTP_200_OK
                    )


                # ==================================================
                # STORAGE
                # ==================================================

                case "storage":

                    result = NetworkResult.objects.get(
                        result_type=result_type,
                        is_latest=True
                    )

                    optimized_network = (
                        load_latest_network(
                            result.network_path
                        )
                    )
                    optimized_network.pf()
                    # Get line reactive power
                    q0_df = optimized_network.lines_t.q0

                    # Convert dataframe to JSON
                    data = (
                        q0_df
                        .reset_index()
                        .to_dict(
                            orient="records"
                        )
                    )

                    return Response(
                        {
                            "message": "success",
                            "count": len(data),
                            "data": data,
                            "result_type": result_type
                        },
                        status=status.HTTP_200_OK
                    )


                # ==================================================
                # INVALID TYPE
                # ==================================================

                case _:

                    return Response(
                        {
                            "status": "error",
                            "error": (
                                f"Invalid '{result_type}'. "
                                "Allowed: baseline, solar, storage"
                            )
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )


        # ======================================================
        # NO RESULT FOUND
        # ======================================================

        except NetworkResult.DoesNotExist:

            return Response(
                {
                    "status": "error",
                    "error": (
                        f"No latest {result_type} "
                        "network result found"
                    )
                },
                status=status.HTTP_404_NOT_FOUND
            )


        # ======================================================
        # OTHER ERROR
        # ======================================================

        except Exception as e:

            print(
                "Reactive Power Error:",
                str(e)
            )

            return Response(
                {
                    "status": "error",
                    "error": str(e),
                    "result_type": result_type
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import NetworkResult
from .network_store import load_latest_network


class VoltageMagnitude(APIView):

    def get(self, request, result_type):

        print("Voltage Magnitude result type:", result_type)

        try:

            # ==================================================
            # VALIDATE TYPE
            # ==================================================

            if result_type not in [
                "baseline",
                "solar",
                "storage"
            ]:

                return Response(
                    {
                        "status": "error",
                        "error": (
                            f"Invalid '{result_type}'. "
                            "Allowed: baseline, solar, storage"
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            # ==================================================
            # GET LATEST RESULT FOR SELECTED TYPE
            # ==================================================

            result = NetworkResult.objects.get(
                result_type=result_type,
                is_latest=True
            )


            print(
                "Network path:",
                result.network_path
            )


            # ==================================================
            # LOAD NETWORK
            # ==================================================

            optimized_network = (
                load_latest_network(
                    result.network_path
                )
            )
            optimized_network.pf()

            # ==================================================
            # VOLTAGE MAGNITUDE
            # ==================================================

            v_df = (
                optimized_network
                .buses_t
                .v_mag_pu
            )


            # ==================================================
            # DATAFRAME TO JSON
            # ==================================================

            data = (
                v_df
                .reset_index()
                .to_dict(
                    orient="records"
                )
            )


            # ==================================================
            # RESPONSE
            # ==================================================

            return Response(
                {
                    "status": "success",
                    "message": "Voltage magnitude data fetched",
                    "count": len(data),
                    "data": data,
                    "result_type": result_type
                },
                status=status.HTTP_200_OK
            )


        # ======================================================
        # RESULT NOT FOUND
        # ======================================================

        except NetworkResult.DoesNotExist:

            return Response(
                {
                    "status": "error",
                    "message": (
                        f"No latest {result_type} "
                        "network result found"
                    ),
                    "result_type": result_type
                },
                status=status.HTTP_404_NOT_FOUND
            )


        # ======================================================
        # OTHER ERROR
        # ======================================================

        except Exception as e:

            print(
                "Voltage Magnitude Error:",
                str(e)
            )

            return Response(
                {
                    "status": "error",
                    "message": str(e),
                    "result_type": result_type
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import NetworkResult
from .network_store import load_latest_network
class VoltageAngle(APIView):
    def get(self, request, result_type):
        print("Voltage Angle result type:", result_type)
        try:
            # ==================================================
            # VALIDATE TYPE
            # ==================================================
            if result_type not in [
                "baseline",
                "solar",
                "storage"
            ]:

                return Response(
                    {
                        "status": "error",
                        "error": (
                            f"Invalid '{result_type}'. "
                            "Allowed: baseline, solar, storage"
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )


            # ==================================================
            # GET LATEST RESULT FOR SELECTED TYPE
            # ==================================================

            result = NetworkResult.objects.get(
                result_type=result_type,
                is_latest=True
            )


            print(
                "Voltage Angle network path:",
                result.network_path
            )


            # ==================================================
            # LOAD NETWORK
            # ==================================================

            optimized_network = (
                load_latest_network(
                    result.network_path
                )
            )

            optimized_network.pf()
            # ==================================================
            # VOLTAGE ANGLE
            # ==================================================

            voltage_df = (
                optimized_network
                .buses_t
                .v_ang
            )


            # ==================================================
            # DATAFRAME TO JSON
            # ==================================================

            data = (
                voltage_df
                .reset_index()
                .to_dict(
                    orient="records"
                )
            )


            # ==================================================
            # RESPONSE
            # ==================================================

            return Response(
                {
                    "status": "success",
                    "message": "Voltage angle data fetched",
                    "count": len(data),
                    "data": data,
                    "result_type": result_type
                },
                status=status.HTTP_200_OK
            )


        # ======================================================
        # RESULT NOT FOUND
        # ======================================================

        except NetworkResult.DoesNotExist:

            return Response(
                {
                    "status": "error",
                    "message": (
                        f"No latest {result_type} "
                        "network result found"
                    ),
                    "result_type": result_type
                },
                status=status.HTTP_404_NOT_FOUND
            )


        # ======================================================
        # OTHER ERROR
        # ======================================================

        except Exception as e:

            print(
                "Voltage Angle Error:",
                str(e)
            )

            return Response(
                {
                    "status": "error",
                    "message": str(e),
                    "result_type": result_type
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import pandas as pd

# assume this is globally available after optimization
# optimized_network = ...
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import NetworkResult
from .network_store import load_latest_network
class LineLoading(APIView):

    def get(self, request, result_type):

        print("Line Loading result type:", result_type)

        try:

            # ==================================================
            # VALIDATE TYPE
            # ==================================================

            if result_type not in [
                "baseline",
                "solar",
                "storage"
            ]:

                return Response(
                    {
                        "status": "error",
                        "error": (
                            f"Invalid '{result_type}'. "
                            "Allowed: baseline, solar, storage"
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )


            # ==================================================
            # GET LATEST RESULT FOR SELECTED TYPE
            # ==================================================

            result = NetworkResult.objects.get(
                result_type=result_type,
                is_latest=True
            )


            print(
                "Line Loading network path:",
                result.network_path
            )


            # ==================================================
            # LOAD NETWORK
            # ==================================================

            optimized_network = (
                load_latest_network(
                    result.network_path
                )
            )


            # ==================================================
            # GET LINE POWER FLOW
            # ==================================================
            optimized_network.pf()
            p0 = optimized_network.lines_t.p0


            # ==================================================
            # GET LINE CAPACITY
            # ==================================================

            s_nom = optimized_network.lines.s_nom


            # ==================================================
            # CALCULATE LINE LOADING %
            # ==================================================

            line_loading_df = (
                p0.div(
                    s_nom,
                    axis=1
                ) * 100
            )


            # ==================================================
            # CONVERT DATAFRAME TO JSON
            # ==================================================

            data = (
                line_loading_df
                .reset_index()
                .to_dict(
                    orient="records"
                )
            )


            # ==================================================
            # RESPONSE
            # ==================================================

            return Response(
                {
                    "status": "success",
                    "message": "Line loading data fetched",
                    "count": len(data),
                    "data": data,
                    "result_type": result_type
                },
                status=status.HTTP_200_OK
            )


        # ======================================================
        # RESULT NOT FOUND
        # ======================================================

        except NetworkResult.DoesNotExist:

            return Response(
                {
                    "status": "error",
                    "message": (
                        f"No latest {result_type} "
                        "network result found"
                    ),
                    "result_type": result_type
                },
                status=status.HTTP_404_NOT_FOUND
            )


        # ======================================================
        # OTHER ERROR
        # ======================================================

        except Exception as e:

            print(
                "Line Loading Error:",
                str(e)
            )

            return Response(
                {
                    "status": "error",
                    "message": str(e),
                    "result_type": result_type
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import NetworkResult
from .network_store import load_latest_network


class OverloadedLineLoading(APIView):

    def get(self, request, result_type):

        print(
            "Overloaded Line Loading result type:",
            result_type
        )

        try:

            # ==================================================
            # VALIDATE TYPE
            # ==================================================

            if result_type not in [
                "baseline",
                "solar",
                "storage"
            ]:

                return Response(
                    {
                        "status": "error",
                        "message": (
                            f"Invalid '{result_type}'. "
                            "Allowed: baseline, solar, storage"
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )


            # ==================================================
            # GET LATEST NETWORK FOR SELECTED TYPE
            # ==================================================

            result = NetworkResult.objects.get(
                result_type=result_type,
                is_latest=True
            )


            print(
                "Network path:",
                result.network_path
            )


            # ==================================================
            # LOAD NETWORK
            # ==================================================

            optimized_network = (
                load_latest_network(
                    result.network_path
                )
            )


            # ==================================================
            # DATA
            # ==================================================
            optimized_network.pf()
            S0 = (
                optimized_network
                .lines_t
                .p0
                .abs()
            )


            s_nom = (
                optimized_network
                .lines
                .s_nom
                .replace(0, 1)
            )


            # ==================================================
            # OVERLOAD THRESHOLD
            # ==================================================

            threshold = 75


            # ==================================================
            # GET SNAPSHOT FROM QUERY PARAMETER
            # ==================================================

            snapshot = request.GET.get(
                "snapshot"
            )


            # ==================================================
            # MODE 1: SINGLE SNAPSHOT
            # ==================================================

            if snapshot is not None:

                try:

                    snapshot = int(snapshot)

                except (ValueError, TypeError):

                    return Response(
                        {
                            "status": "error",
                            "message": (
                                "Invalid snapshot index"
                            )
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )


                # ==========================================
                # SNAPSHOT RANGE CHECK
                # ==========================================

                if (
                    snapshot < 0
                    or snapshot >= len(S0.index)
                ):

                    return Response(
                        {
                            "status": "error",
                            "message": (
                                "Snapshot out of range"
                            )
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )


                # ==========================================
                # GET SNAPSHOT
                # ==========================================

                hour_to_analyze = (
                    S0.index[snapshot]
                )


                # ==========================================
                # CALCULATE LOADING
                # ==========================================

                line_loading = (
                    S0
                    .loc[hour_to_analyze]
                    .div(s_nom)
                    * 100
                )


                # ==========================================
                # GET OVERLOADED LINES
                # ==========================================

                overloaded = (
                    line_loading[
                        line_loading > threshold
                    ]
                )


                # ==========================================
                # FORMAT RESULT
                # ==========================================

                data = [

                    {
                        "snapshot": snapshot,
                        "timestamp": str(
                            hour_to_analyze
                        ),
                        "line": line,
                        "loading_percent": float(
                            value
                        )
                    }

                    for line, value
                    in overloaded.items()

                ]


                # ==========================================
                # RESPONSE
                # ==========================================

                return Response(
                    {
                        "status": "success",
                        "mode": "snapshot",
                        "result_type": result_type,
                        "snapshot": snapshot,
                        "timestamp": str(
                            hour_to_analyze
                        ),
                        "threshold": threshold,
                        "count": len(data),
                        "data": data
                    },
                    status=status.HTTP_200_OK
                )


            # ==================================================
            # MODE 2: FULL TIMELINE
            # ==================================================

            data = []


            for i, time in enumerate(S0.index):

                # ==========================================
                # CALCULATE LINE LOADING
                # ==========================================

                line_loading = (
                    S0
                    .loc[time]
                    .div(s_nom)
                    * 100
                )


                # ==========================================
                # GET OVERLOADED LINES
                # ==========================================

                overloaded = (
                    line_loading[
                        line_loading > threshold
                    ]
                )


                # ==========================================
                # ADD TO RESULT
                # ==========================================

                for line, value in overloaded.items():

                    data.append(
                        {
                            "snapshot": i,
                            "timestamp": str(time),
                            "line": line,
                            "loading_percent": float(
                                value
                            )
                        }
                    )


            # ==================================================
            # RESPONSE
            # ==================================================

            return Response(
                {
                    "status": "success",
                    "mode": "all",
                    "result_type": result_type,
                    "threshold": threshold,
                    "count": len(data),
                    "data": data
                },
                status=status.HTTP_200_OK
            )


        # ======================================================
        # NETWORK RESULT NOT FOUND
        # ======================================================

        except NetworkResult.DoesNotExist:

            return Response(
                {
                    "status": "error",
                    "message": (
                        f"No latest {result_type} "
                        "network result found"
                    ),
                    "result_type": result_type
                },
                status=status.HTTP_404_NOT_FOUND
            )


        # ======================================================
        # OTHER ERROR
        # ======================================================

        except Exception as e:

            print(
                "Overloaded Line Loading Error:",
                str(e)
            )

            return Response(
                {
                    "status": "error",
                    "message": str(e),
                    "result_type": result_type
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

class TransformerLoading(APIView):
    def get(self, request,result_type):
        try:
            result = NetworkResult.objects.get(
            result_type=result_type,
            is_latest=True
)
            optimized_network = load_latest_network(result.network_path )
            # ================= BASE DATA =================
            # transformer loading (p0-like power flow)
            optimized_network.pf()
            p0 = optimized_network.transformers_t.p0
            s_nom = optimized_network.transformers.s_nom

            # loading %
            transformer_loading_df = p0.div(s_nom, axis=1) * 100

            # ================= FILTERS =================
            transformer_name = request.GET.get("transformer")
            snapshot = request.GET.get("snapshot")

            if transformer_name:
                if transformer_name in transformer_loading_df.columns:
                    transformer_loading_df = transformer_loading_df[[transformer_name]]
                else:
                    return Response({
                        "status": "error",
                        "message": f"Transformer '{transformer_name}' not found"
                    }, status=status.HTTP_404_NOT_FOUND)

            if snapshot:
                try:
                    snapshot = int(snapshot)
                    transformer_loading_df = transformer_loading_df.iloc[[snapshot]]
                except:
                    return Response({
                        "status": "error",
                        "message": "Invalid snapshot index"
                    }, status=status.HTTP_400_BAD_REQUEST)

            # ================= NORMAL DATA =================
            data = transformer_loading_df.reset_index().to_dict(orient="records")

            # ================= RESPONSE =================
            return Response({
                "status": "success",
                "count": len(data),
                # chart data
                "data": data,
                # stats
                "total_transformers": len(transformer_loading_df.columns),

            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                "status": "error",
                "message": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
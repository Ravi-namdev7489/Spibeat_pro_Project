import pandas as pd
from rest_framework.views import APIView
from rest_framework.response import Response
from django.conf import settings
import json
from rest_framework import status
import os
from .network_input_files.baseline_network_input import *
from .network_input_files.solar_network_input import *
from .network_input_files.timeseries import generate_dt_timeseries

import pypsa
import os
from datetime import datetime
import os
from django.conf import settings


class SolarNetwork(APIView):

    def post(self, request):
        start_date = request.data.get("start_date")
        end_date= request.data.get("end_date")
        print('start_date',start_date)
        print('end date',end_date)
        Output_Dir= r"C:\RaviNamdev\India Database for Building simulator\Solar_Scanario_Input"
        Input_Dir= r"C:\RaviNamdev\FinalSpibeat\ShapeFile_to_pypsa_Input\shape_to_pypsa_formate_output"
        os.makedirs(Output_Dir,exist_ok=True)
                # ✅ Generate timeseries
        timeseries = generate_dt_timeseries(start_date,end_date)
       
        # ✅ If valid → generate all data
        buses = generate_buses_data(Input_Dir,Output_Dir)
        print('buses',buses)
        generators = generate_solar_generators_data(Input_Dir,Output_Dir)
        loads = generate_loads_data(Input_Dir,Output_Dir)
        transformers = generate_transformers(Input_Dir,Output_Dir)
        transformer_types = generate_transformer_types(Input_Dir,Output_Dir)
        lines = generate_lines_data(Input_Dir,Output_Dir)

        load_p_q_set = generate_load_pset_qset(Input_Dir,Output_Dir)
        load_p_set = load_p_q_set.get("p_set", [])
        load_q_set = load_p_q_set.get("q_set", [])

        snapshots = generate_snapshots(Input_Dir,Output_Dir)
        generator_pmax = generate_solar_generator_pmax_pu(Input_Dir,Output_Dir)
        generator_p_set=generate_solar_generator_p_set(Input_Dir,Output_Dir)

        return Response({
            "status": "success",
           
            "buses": buses,
            "generators": generators,
            "loads": loads,
            "transformers": transformers,
            "transformer_types": transformer_types,
            "lines": lines,
            "load-p_set": load_p_set,
            "load-q_set": load_q_set,
            "snapshots": snapshots,
            "generators-p_max_pu": generator_pmax,
            "generators-p_set":generator_p_set
        }, status=200)
from rest_framework.views import APIView
from rest_framework.response import Response
import pandas as pd
import os


class SaveSolarInput(APIView):

    def post(self, request):
        
            try:
                
                BASE_DIR = r"C:\RaviNamdev\Baseline_for_prototype\Solar_output"
    
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
                    "load-p_set": "loads-p_set.csv",
                    "load-q_set": "loads-q_set.csv",
                    "snapshots": "snapshots.csv",
                    "generators-p_max_pu": "generators-p_max_pu.csv",
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



class OptimizeSolarNetwork(APIView):

    def get(self, request):

        try:

            input_folder = (
                r'C:\RaviNamdev\Baseline_for_prototype\Solar_output'
            )
    

            network = pypsa.Network()

            network.import_from_csv_folder(
                input_folder
            )


            network.buses["carrier"] = (
                network.buses["carrier"]
                .fillna("AC")
            )


            network.lines["carrier"] = (
                network.lines["carrier"]
                .fillna("AC")
            )


            if "AC" not in network.carriers.index:
                network.add(
                    "Carrier",
                    "AC"
                )


            # Run power flow
            network.pf()


            # Save CSV network

            save_folder = os.path.join(
                settings.MEDIA_ROOT,
                "networks",
                "latest"
            )


            os.makedirs(
                save_folder,
                exist_ok=True
            )


            network.export_to_csv_folder(
                save_folder
            )


            # Update database

            NetworkResult.objects.update(
                is_latest=False
            )


            NetworkResult.objects.create(
                name="latest",
                network_path=save_folder,
                is_latest=True
            )


            return Response(
                {
                    "status":"success",
                    "message":"Network optimized"
                }
            )


        except Exception as e:

            return Response(
                {
                    "error":str(e)
                },
                status=500
            )
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .p_nom_data import set_generator_data


class UpdateSolarGenerator(APIView):

    def post(self, request):
        generator = request.data.get("generator")
        print('generator', generator)

        if not generator:
            return Response({
                "status": "error",
                "message": "No generator data provided ❌"
            }, status=status.HTTP_400_BAD_REQUEST)

        name = generator.get("name")
        p_nom = generator.get("p_nom")

        if not name:
            return Response({
                "status": "error",
                "message": "Generator name missing ❌"
            }, status=400)

        try:
            p_nom = float(p_nom)
        except:
            return Response({
                "status": "error",
                "message": "Invalid p_nom value ❌"
            }, status=400)

        # ✅ SAVE DATA
        saved = set_generator_data(name, p_nom)

        print("Saved:", saved)

        return Response({
            "status": "success",
            "message": f"{name} updated successfully ✅",
            "data": saved
        }, status=200)
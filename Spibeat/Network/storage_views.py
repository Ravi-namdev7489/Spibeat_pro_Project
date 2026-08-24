import pandas as pd
from rest_framework.views import APIView
from rest_framework.response import Response
from django.conf import settings
import json
from rest_framework import status
import os
from .network_input_files.baseline_network_input import *

from .network_input_files.timeseries import generate_dt_timeseries
from .network_input_files.storage_network_input import *
import pypsa
import os
from datetime import datetime
import os
from django.conf import settings


class StorageNetwork(APIView):

    def post(self, request):
        start_date = request.data.get("start_date")
        end_date= request.data.get("end_date")
        print('start_date storage',start_date)
        print('end date storage',end_date)
                # ✅ Generate timeseries
        timeseries = generate_dt_timeseries(start_date,end_date)
       
        OUTPUT_DIR = r"C:\RaviNamdev\India Database for Building simulator\Storage_Scanario_inputs"
        BASE_DIR = r"C:\RaviNamdev\FinalSpibeat\ShapeFile_to_pypsa_Input\shape_to_pypsa_formate_output"
        os.makedirs(OUTPUT_DIR,exist_ok=True)
        # ✅ If valid → generate all data
        buses = generate_buses_data(BASE_DIR,OUTPUT_DIR)
        print('buses',buses)
        generators=generate_storage_generators(OUTPUT_DIR,BASE_DIR)

        print("================================")
        print("FRONTEND RESPONSE DATA")
        print("================================")

        for row in generators.get("data", []):
            print(
                "name:",
                row.get("name"),
                "p_nom:",
                row.get("p_nom"),
                "type:",
                type(row.get("p_nom"))
            )
            
        storage_units=generate_storage_units_data(OUTPUT_DIR)
        carriers=generate_storage_carriers(OUTPUT_DIR)
        loads=generate_storage_loads( OUTPUT_DIR)
        generator_pmax=generate_storage_pmax_pu(OUTPUT_DIR,BASE_DIR)
        transformers = generate_transformers(BASE_DIR,OUTPUT_DIR)
        transformer_types = generate_transformer_types(BASE_DIR,OUTPUT_DIR)
        lines = generate_lines_data(BASE_DIR,OUTPUT_DIR)
    
        load_p_q_set = generate_load_pset_qset(BASE_DIR,OUTPUT_DIR)
        load_p_set = load_p_q_set.get("p_set", [])
        load_q_set = load_p_q_set.get("q_set", [])
        snapshots = generate_snapshots(BASE_DIR,OUTPUT_DIR)

        return Response({
            "status": "success",
            "message": "Storage generated successfully ✅",
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
            "storage_units":storage_units,
            "carriers": carriers
        }, status=200)

class SaveStorageInput(APIView):

    def post(self, request):
        
            try:
                
                BASE_DIR = r"C:\RaviNamdev\Baseline_for_prototype\Storage_output"
    
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
                    "storage_units":"storage_units.csv",
                    "carriers":"carriers.csv"
                    
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

from .network_store import *
class OptimalPowerGeneration(APIView):
    
    def get(self, request):
        try:

            # ==================================================
            # GET LATEST STORAGE NETWORK
            # ==================================================

            result = NetworkResult.objects.get(
                result_type="storage",
                is_latest=True
            )

            # ==================================================
            # LOAD NETWORK
            # ==================================================

            network = load_latest_network(
                result.network_path
            )

            # ==================================================
            # GENERATORS
            # Group generators by carrier
            # ==================================================

            p_generators = (
                network.generators_t.p
                .T
                .groupby(
                    network.generators.carrier
                )
                .sum()
                .T
            )

            # ==================================================
            # STORAGE UNITS
            # KEEP EACH STORAGE UNIT SEPARATE
            # ==================================================

            p_storage_units = (
                network.storage_units_t.p
                .copy()
            )

            # Add Storage to individual names
            p_storage_units.columns = [
                f"{name} (Storage)"
                for name in p_storage_units.columns
            ]

            # ==================================================
            # COMBINE
            # ==================================================

            p_by_carrier_df = (
                p_generators
                .join(
                    p_storage_units,
                    how="outer"
                )
                .fillna(0)
            )

            # ==================================================
            # JSON
            # ==================================================

            data = (
                p_by_carrier_df
                .reset_index()
                .to_dict(
                    orient="records"
                )
            )

            print(data)

            # ==================================================
            # RESPONSE
            # ==================================================

            return Response(
                {
                    "status": "success",
                    "message": "Optimal power generation data fetched",
                    "count": len(data),
                    "data": data,
                },
                status=status.HTTP_200_OK
            )

        except NetworkResult.DoesNotExist:

            return Response(
                {
                    "status": "error",
                    "message": "Latest storage network result not found."
                },
                status=status.HTTP_404_NOT_FOUND
            )

        except Exception as e:

            return Response(
                {
                    "status": "error",
                    "message": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class StorageChargingDischargingAPIView(APIView):

    def get(self, request):

        try:
            result = NetworkResult.objects.get(
                        result_type="storage",
                        is_latest=True
                    )
        
                    # ==================================================
                    # LOAD NETWORK
                    # ==================================================
        
            network = load_latest_network(
                        result.network_path
                    )
        
                    # ==================================================
            if network.storage_units.empty:
                return Response(
                    {
                        "success": False,
                        "message": "No storage units found."
                    },
                    status=status.HTTP_404_NOT_FOUND
                )

            # ------------------------------------------------
            # 4. Get unique storage types
            # ------------------------------------------------
            storage_types = (
                network.storage_units["type"]
                .dropna()
                .unique()
                .tolist()
            )

            result = []

            # ------------------------------------------------
            # 5. Process every storage type
            # ------------------------------------------------
            for storage_type in storage_types:

                # Storage units belonging to this type
                storage_indices = network.storage_units[
                    network.storage_units["type"] == storage_type
                ].index

                # ------------------------------------------------
                # Power dispatch
                # ------------------------------------------------
                p_storage = (
                    network.storage_units_t.p[storage_indices]
                    .sum(axis=1)
                )

                # ------------------------------------------------
                # State of charge
                # ------------------------------------------------
                state_of_charge = (
                    network.storage_units_t.state_of_charge[
                        storage_indices
                    ]
                    .sum(axis=1)
                )

                # ------------------------------------------------
                # Convert index to strings
                # ------------------------------------------------
                snapshots = [
                    str(snapshot)
                    for snapshot in p_storage.index
                ]

                # ------------------------------------------------
                # Create chart data
                # ------------------------------------------------
                chart_data = []

                for snapshot, power, soc in zip(
                    snapshots,
                    p_storage.tolist(),
                    state_of_charge.tolist()
                ):

                    chart_data.append(
                        {
                            "snapshot": snapshot,
                            "power": round(float(power), 5),
                            "soc": round(float(soc), 5)
                        }
                    )

                result.append(
                    {
                        "storage_type": str(storage_type),
                        "data": chart_data
                    }
                )

            # ------------------------------------------------
            # 6. API response
            # ------------------------------------------------
            return Response(
                {
                    "success": True,
                    "storage_types": storage_types,
                    "results": result
                },
                status=status.HTTP_200_OK
            )

        except Exception as e:

            return Response(
                {
                    "success": False,
                    "message": str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
class Opex(APIView):
    
    def get(self, request):

        try:
            result = NetworkResult.objects.get(
                        result_type="storage",
                        is_latest=True
                    )
        
                    # ==================================================
                    # LOAD NETWORK
                    # ==================================================
        
            network = load_latest_network(
                        result.network_path
                    )
            opex = network.snapshot_weightings.generators @ (
            network.generators_t.p * network.generators.marginal_cost)

# Group OPEX by carrier
            opex_by_carrier_df = opex.groupby(network.generators.carrier).sum()
            data = (
                    
                           opex_by_carrier_df .reset_index()
                            .to_dict(
                                orient="records"
                            )
                        )
                    # ==================================================
            # ------------------------------------------------
            # 6. API response
            # ------------------------------------------------
            return Response(
                {
                "success": True,
                "data":data
                },
                
                status=status.HTTP_200_OK
            )

        except Exception as e:

            return Response(
                {
                    "success": False,
                    "message": str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
class Capex(APIView):
    
    def get(self, request):

        try:
            result = NetworkResult.objects.get(
                        result_type="storage",
                        is_latest=True
                    )
        
                    # ==================================================
                    # LOAD NETWORK
                    # ==================================================
        
            network = load_latest_network(
                        result.network_path
                    )
            capex = (network.generators.p_nom_opt * network.generators.capital_cost)
            capex_by_carrier_df = capex.groupby(network.generators.carrier).sum()
            data = (
                    
                           capex_by_carrier_df .reset_index()
                            .to_dict(
                                orient="records"
                            )
                        )
                    # ==================================================
            # ------------------------------------------------
            # 6. API response
            # ------------------------------------------------
            return Response(
                {
                "success": True,
                "data":data
                },
                
                status=status.HTTP_200_OK
            )

        except Exception as e:

            return Response(
                {
                    "success": False,
                    "message": str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
class Total_Cost(APIView):
    
    def get(self, request):

        try:
            result = NetworkResult.objects.get(
                        result_type="storage",
                        is_latest=True
                    )
        
                    # ==================================================
                    # LOAD NETWORK
                    # ==================================================
        
            network = load_latest_network(
                        result.network_path
                    )
            capex = (network.generators.p_nom_opt * network.generators.capital_cost)
            capex_by_carrier_df = capex.groupby(network.generators.carrier).sum()
            opex = network.snapshot_weightings.generators @ (
            network.generators_t.p * network.generators.marginal_cost)
            
            # Group OPEX by carrier
            opex_by_carrier_df = opex.groupby(network.generators.carrier).sum()
            investment_cost_in_million_rs = (opex_by_carrier_df +  capex_by_carrier_df ) / 1e6

# Create a DataFrame to display the results
            total_df = pd.DataFrame({
                'Generators': investment_cost_in_million_rs.index,  # Generator names or carriers
                'Investment Cost in Million Rs': investment_cost_in_million_rs.values  # Costs divided by 10^6
            })
            data = (
                    
                           total_df.reset_index()
                            .to_dict(
                                orient="records"
                            )
                        )
                    # ==================================================
            # ------------------------------------------------
            # 6. API response
            # ------------------------------------------------
            return Response(
                {
                "success": True,
                "data":data
                },
                
                status=status.HTTP_200_OK
            )

        except Exception as e:

            return Response(
                {
                    "success": False,
                    "message": str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
class Emission(APIView):
    def get(self, request):

        try:
            result = NetworkResult.objects.get(
                        result_type="storage",
                        is_latest=True
                    )
        
                    # ==================================================
                    # LOAD NETWORK
                    # ==================================================
        
            network = load_latest_network(
                        result.network_path
                    )
            emission = (
    network.generators_t.p
    / network.generators.efficiency
    * network.generators.carrier.map(network.carriers.co2_emissions)
)

            # Sum emissions by carrier
            emission_by_carrier = emission.groupby(network.generators.carrier, axis=1).sum()

            # Create a DataFrame for emissions by carrier
            emission_df = pd.DataFrame({
                'Carrier': emission_by_carrier.columns,
                'Total Emissions (tons of CO2)': emission_by_carrier.sum().values
            })

            # Print the emissions table
            print(emission_df)

# Create a DataFrame to display the results
            
            data = (
                    
                           emission_df.reset_index()
                            .to_dict(
                                orient="records"
                            )
                        )
                    # ==================================================
            # ------------------------------------------------
            # 6. API response
            # ------------------------------------------------
            return Response(
                {
                "success": True,
                "data":data
                },
                
                status=status.HTTP_200_OK
            )

        except Exception as e:

            return Response(
                {
                    "success": False,
                    "message": str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
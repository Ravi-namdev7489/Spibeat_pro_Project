from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .demand.cooling_load import run_cooling_cal
from .demand.peak_load import peak_load
from .demand.Hot_water import run_dhw
from .demand.Auxialary import run_aux_cal
from .demand.Ea_El import run_ea_el
from .demand.total_demand import total_demand
from .demand.Final_total_demand import final_total_demand
from .views_supportor import *
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .demand.solar_potential import calculate_solar_potential
class RunSimulationAPIView(APIView):
    def post(self, request):

        user=request.user
        run_type = request.data.get("run_type")

        print("RUN TYPE RECEIVED:", run_type) 

        if not run_type:
            return Response({"error": "type required"}, status=400)

        try:
            locator = get_locator_from_user(user)
            use_type = get_use_type(user)
            building_json = get_locator_json(user)
            building_data = building_json.get("parameters", {})
            print(f"\n🚀 RUN TYPE: {run_type}")
            print("EPW:", locator.get_epw())
            match run_type:
                case "cooling":
                    result = run_cooling_cal(locator, building_data)
                    
                    return Response({
                        "status": "success",
                        "type": "cooling",
                        "cooling_dir": result,
                        "building_data":building_data,
                         "use_type":use_type
                    })

                case "hotwater":
                    result = run_dhw(locator, building_data)
                    return Response({
                        "status": "success",
                        "type": "hotwater",
                        "data": result,
                        "building_data":building_data,
                        "use_type":use_type
                    })

                case "eael":
                    result = run_ea_el(locator, building_data)
                    return Response({
                        "status": "success",
                        "type": "eael",
                        "data": result,
                        "building_data":building_data,
                        "use_type":use_type
                    })

                case "aux":
                    result = run_aux_cal( locator, building_data)
                    return Response({
                        "message": "success",
                        "type": "aux",
                        "data": result,
                        "building_data":building_data,
                        "use_type":use_type
                    },status=status.HTTP_200_OK)

                case "total":
                    run_cooling_cal(locator,building_data)
                    run_aux_cal(locator,building_data)
                    run_ea_el(locator,building_data)
                    run_dhw(locator,building_data)
                    
                    demand_output = total_demand( locator)
                    final_demand = final_total_demand(demand_output, locator),
                    

                    return Response({
                        "status": "success",
                        "type": "total",
                        "demand_output_dir": demand_output,
                        "final_total_demand_output_dir": final_demand,
                        "building_data":building_data,
                        "use_type":use_type
                    })

                case "peak":
                    file_path, df_peak = peak_load(locator)

                    return Response({
                        "message": "success",
                        "type": "peak",
                        "file": file_path,
                        "data": df_peak.to_dict(orient="records")
                        
                    },status=status.HTTP_200_OK)
                case "solar_potential":
                    result = calculate_solar_potential( locator, building_data)
                    return Response({
                        "status": "success",
                        "type": "solar_potential",
                        "data": result,
                        "building_data":building_data
                    })
                case _:
                    return Response({
                        "error": f"Invalid '{run_type}'"
                    }, status=400)

        except Exception as e:
            import traceback
            traceback.print_exc()

            return Response({
                
                "type": run_type,
                "error": str(e)
            }, status=500)
# solar/views.py


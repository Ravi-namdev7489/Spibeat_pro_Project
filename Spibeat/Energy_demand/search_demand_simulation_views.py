from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import os
import pandas as pd
from .views_supportor import *
class SearchDataView(APIView):

    def post(self, request):
        try:
            user=request.user
            locator = get_locator_from_user(user)
            # ================= BODY =================
            run_type = request.data.get("type")
            print('run type ',run_type)
            building_name = request.data.get("building_name")
            start_date = request.data.get("start_date")
            end_date = request.data.get("end_date")
            print('building name',building_name)
            print('start date',start_date)
            print('end date',end_date)

            if not run_type:
                return Response({"error": "type required"}, status=400)

            if not building_name:
                return Response({"error": "building_name required"}, status=400)

            # ================= MATCH CASE (🔥 CLEAN SWITCH) =================
            match run_type:

                case "eael":
                    folder = locator.get_ea_el_output_dir()
                    file_name = f"Ea_El_FULL_YEAR_{building_name}.csv"

                case "hotwater":
                    folder = locator.get_hotwater_output_dir()
                    file_name = f"{building_name}_DHW_YEAR.csv"

                case "aux":
                    folder = locator.get_aux_output_dir()
                    file_name = f"aux_{building_name}.csv"

                case "cooling":
                    folder = locator.get_cooling_output_dir()
                    file_name = f"HVAC_hourly_YEAR_{building_name}.csv"

                case "total":
                    folder = locator.get_building_wise_total_output_dir()
                    file_name = f"TOTAL_LOAD_REQUIRED_{building_name}_FULL_YEAR.csv"
                case "solar_potential":
                    folder = locator.get_solar_output_folder()
                    file_name = f"PV_solar_potential_building_{building_name}.csv"
                case _:
                    return Response(
                        {"error": f"Invalid type: {run_type}"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            file_path = os.path.join(folder, file_name)

            # ================= FILE CHECK =================
            if not os.path.exists(file_path):
                return Response(
                    {"error": f"{building_name} file not found"},
                    status=status.HTTP_404_NOT_FOUND
                )

            # ================= READ CSV =================
            df = pd.read_csv(file_path)

            if df.empty:
                return Response(
                    {"error": "CSV file is empty"},
                    status=status.HTTP_404_NOT_FOUND
                )

            # ================= TIMESTAMP FIX =================
            if "timestamps" not in df.columns:
                for col in df.columns:
                    if "time" in col.lower() or "date" in col.lower():
                        df.rename(columns={col: "timestamps"}, inplace=True)
                        break

            if "timestamps" not in df.columns:
                return Response(
                    {"error": "No timestamp column found"},
                    status=500
                )

            df["timestamps"] = pd.to_datetime(df["timestamps"], errors="coerce")
            df = df.dropna(subset=["timestamps"])

            # ================= DATE FILTER =================
            if start_date and end_date:
                try:
                    df["date_only"] = df["timestamps"].dt.date
                    start = pd.to_datetime(start_date).date()
                    end = pd.to_datetime(end_date).date()
                except Exception:
                    return Response(
                        {"error": "Invalid date format (YYYY-MM-DD)"},
                        status=400
                    )

                if start > end:
                    return Response(
                        {"error": "Start date cannot be after end date"},
                        status=400
                    )

                df = df[
                    (df["date_only"] >= start) &
                    (df["date_only"] <= end)
                ]

                if df.empty:
                    return Response(
                        {"error": "No data in selected range"},
                        status=404
                    )

            # ================= RESPONSE =================
            results = df.sort_values("timestamps").to_dict(orient="records")

            return Response({
                "status": "success",
                "type": run_type,
                "building": building_name,
                "count": len(results),
                "data": results
            })

        except Exception as e:
            return Response({
                "error": "Server error",
                "details": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

import os
import pandas as pd
import geopandas as gpd
from shapely.geometry import LineString
from rest_framework.views import APIView
from rest_framework.response import Response
from django.conf import settings

import os
import pandas as pd
import geopandas as gpd
from shapely.geometry import LineString
from rest_framework.views import APIView
from rest_framework.response import Response

class NetworkMap(APIView):

    def get(self, request):
        try:
            DATA_DIR = r"C:\RaviNamdev\India Database for Building simulator\Solar_Senario_output"

            buses = pd.read_csv(os.path.join(DATA_DIR, "buses.csv"))
            lines = pd.read_csv(os.path.join(DATA_DIR, "lines.csv"))

            buses = buses.set_index(buses.columns[0])
            lines = lines.set_index(lines.columns[0])

            # =========================
            # BUS GEO + ALL DATA
            # =========================
            gdf_buses = gpd.GeoDataFrame(
                buses,
                geometry=gpd.points_from_xy(buses["x"], buses["y"]),
                crs="EPSG:4326"
            )

            # add name column for frontend
            gdf_buses["name"] = gdf_buses.index

            # =========================
            # LINE GEO + DATA
            # =========================
            line_records = []
            line_labels = []

            for line_name, row in lines.iterrows():
                b0, b1 = row["bus0"], row["bus1"]

                if b0 in gdf_buses.index and b1 in gdf_buses.index:
                    p0 = gdf_buses.loc[b0].geometry
                    p1 = gdf_buses.loc[b1].geometry

                    geom = LineString([p0, p1])
                    midpoint = geom.interpolate(0.5, normalized=True)

                    record = row.to_dict()
                    record["line"] = line_name
                    record["geometry"] = geom

                    line_records.append(record)

                    line_labels.append({
                        "line": line_name,
                        "lat": midpoint.y,
                        "lon": midpoint.x
                    })

            gdf_lines = gpd.GeoDataFrame(line_records, crs="EPSG:4326")

            return Response({
                "buses": gdf_buses.to_json(),
                "lines": gdf_lines.to_json(),
                "line_labels": line_labels
            })

        except Exception as e:
            return Response({"error": str(e)}, status=500)
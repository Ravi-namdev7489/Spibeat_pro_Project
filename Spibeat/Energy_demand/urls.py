from django.urls import path

from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from .upload_data_views import *
from .demand_simulation_views import * 
from .search_demand_simulation_views import * 
urlpatterns = [
    # 🔹 Upload & Data
    # path("upload-files", UploadWeatherAndShapefileFiles.as_view(), name="upload_files"),
    path("get-weather", GetWeatherFile.as_view(), name="get_weather"),
    path("get-shapefile", GetBuildingShape.as_view(), name="get_shapefile"),
    path("data-manager", DataManagerView.as_view(), name="data_manager"),
    # 🔹 Locator & Project
    path("save-locator", SaveLocatorView.as_view(), name="save_locator"),
    path("locator", InputLocatorView.as_view(), name="locator"),
    path("map-locator", MapLocatorView.as_view(), name="map_locator"),
    # 🔹 Use Data
    path("use-data", GetUseDataView.as_view(), name="get_use_data"),
    path("save-use", SaveUseDataView.as_view(), name="save_use"),
    # 🔹 Run Demand Calculations
    path("run-simulation", RunSimulationAPIView.as_view()),
    path("search-simulation", SearchDataView.as_view()),
    # path("solar-potential", SolarPotential.as_view()),
    
]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
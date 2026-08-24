from django.urls import path
from Network.views import *
from .Solar_views import * 
from .storage_views import *
from .map_views import * 

urlpatterns = [
    # Baseline Scenario
    path("dt-buidlings", ProcessDataDTwiseBuilding.as_view()),
    path("baseline-network",BaselineNetwork.as_view()),
    path("save-baseline",SaveBaselineInput.as_view()),
    path("optimize-network/<str:network_type>",OptimizeNetwork.as_view()),
    path("save-solar",SaveSolarInput.as_view()),
    path("save-storage",SaveStorageInput.as_view()),
    # path("optimize-storage-network",OptimizeStorageNetwork.as_view()),
    # path("optimize-solar-network",OptimizeSolarNetwork.as_view()),
    path("real-power/<str:result_type>",RealPower.as_view()),
    # path("reactive-power-baseline",ReactivePower.as_view()),
    path("reactive-power/<str:result_type>",ReactivePower.as_view()),
    path("voltage-magnitude/<str:result_type>", VoltageMagnitude.as_view(), name="voltage-magnitude"),
    path("voltage-angle/<str:result_type>",VoltageAngle.as_view(),name="voltage-angle"),
    path("line-loading/<str:result_type>",LineLoading.as_view(),name="line-loading"),
    path("overloaded-lines/<str:result_type>",OverloadedLineLoading.as_view()),
    path("transformer-loading/<str:result_type>",TransformerLoading.as_view()),
    path("network-map", NetworkMap.as_view(), name="network-topology"),
    # Solar Scenario
    path("solar-network",SolarNetwork.as_view()),
    path("storage-network",StorageNetwork.as_view()),
    path("update-generator",UpdateSolarGenerator.as_view()),
    path("optimal-power-generation",OptimalPowerGeneration.as_view()),
    path("storage-charging-discharging",StorageChargingDischargingAPIView.as_view()),
    path("opex",Opex.as_view()),
    path("capex",Capex.as_view()),
    path("total-cost",Total_Cost.as_view()),
    path("emission",Emission.as_view()),
    
]
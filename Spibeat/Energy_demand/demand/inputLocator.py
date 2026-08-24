import os

from .constants import SIMULATION_YEAR
from pvlib.iotools import read_epw
class InputLocator:
    """
    InputLocator for Spibeat Backend
    Fully aligned with backend calls (envelope, HVAC, components, schedules, archetypes)
    """

    def __init__(self,path,shp,use_type):
        # Root database
        self.database_root = r"C:\RaviNamdev\India Database for Building simulator\Database"
        # EPW and SHP files
        self.epw_file = path
        self.buildings_shp = shp

        # Main sections
        self.archetypes = os.path.join(self.database_root, "ARCHETYPES")
        self.assemblies = os.path.join(self.database_root, "ASSEMBLIES")
        self.components = os.path.join(self.database_root, "COMPONENTS")

        # Subfolders
        self.schedules = os.path.join(self.archetypes, "SCHEDULE")
        self.envelope = os.path.join(self.assemblies, "ENVELOPE")
        self.hvac = os.path.join(self.assemblies, "HVAC")
        self.supply = os.path.join(self.assemblies, "SUPPLY")

        # Output
        self.output_root = fr"C:\RaviNamdev\India Database for Building simulator\Output_demand\{use_type}"
        self.solar_output_dir =r"C:\RaviNamdev\India Database for Building simulator\Solar_Potential"
        
        print("output path from input locator",self.output_root)
    # ============================
    # WEATHER + BUILDING
    # ============================
    def get_epw(self):
        print('backend ',self.epw_file)
        return self.epw_file
    
    def load_weather(self):
        weather, meta = read_epw(self.epw_file)
        weather.index = weather.index.map(lambda t: t.replace(year=SIMULATION_YEAR))
        return  {'weather':weather,'weather_index':weather.index,'meta':meta}
    def get_buildings_shp(self):
        return self.buildings_shp
    def get_output_root(self):
        return self.output_root
    # ============================
    # ARCHETYPES
    # ============================
    def get_use_types(self):
        return os.path.join(self.archetypes, "USE_TYPES.csv")

    def get_archetypes(self):
        return self.archetypes

    def get_assemblies(self):
        return self.assemblies
    
    def get_components(self):
        return self.components
    def get_constructor_type(self):
        return os.path.join(self.get_archetypes(), "CONSTRUCTION_TYPES.csv")
    def get_schedule_library(self):
        return os.path.join(self.schedules, "Schedules_Library")

    def get_monthly_multiplier(self, load_type):
        # HW, AC, AUX, EaEl
        return os.path.join(self.schedules, f"monthly_multiplier_{load_type}.csv")

    # ============================
    # ENVELOPE FILES
    # ============================
    def get_envelope_dir(self):
        return self.envelope

    def get_envelope_floor(self):
        return os.path.join(self.get_envelope_dir(), "ENVELOPE_FLOOR.csv")

    def get_envelope_wall(self):
        return os.path.join(self.get_envelope_dir(), "ENVELOPE_WALL.csv")

    def get_envelope_roof(self):
        return os.path.join(self.get_envelope_dir(), "ENVELOPE_ROOF.csv")

    def get_envelope_window(self):
        return os.path.join(self.get_envelope_dir(), "ENVELOPE_WINDOW.csv")

    def get_envelope_shading(self):
        return os.path.join(self.get_envelope_dir(), "ENVELOPE_SHADING.csv")

    def get_envelope_tightness(self):
        return os.path.join(self.get_envelope_dir(), "ENVELOPE_TIGHTNESS.csv")

    def get_envelope_mass(self):
        return os.path.join(self.get_envelope_dir(), "ENVELOPE_MASS.csv")

    # ============================
    # HVAC FILES
    # ============================
    def get_hvac_dir(self):
        return self.hvac

    def get_hvac_controller(self):
        return os.path.join(self.get_hvac_dir(), "HVAC_CONTROLLER.csv")

    def get_hvac_cooling(self):
        return os.path.join(self.get_hvac_dir(), "HVAC_COOLING.csv")

    def get_hvac_heating(self):
        return os.path.join(self.get_hvac_dir(), "HVAC_HEATING.csv")

    def get_hvac_ventilation(self):
        return os.path.join(self.get_hvac_dir(), "HVAC_VENTILATION.csv")

    def get_hvac_hotwater(self):
        return os.path.join(self.get_hvac_dir(), "HVAC_HOTWATER.csv")

    # ============================
    # SUPPLY
    # ============================
    def get_supply_dir(self):
        return self.supply
    
    def get_supply_cooling(self):
        return os.path.join(self.get_supply_dir(), "SUPPLY_COOLING.csv")    
    def get_supply_electricity(self):
        return os.path.join(self.get_supply_dir(), "SUPPLY_ELECTRICITY.csv")    
    def get_supply_heating(self):
        return os.path.join(self.get_supply_dir(), "SUPPLY_HEATING.csv")    
    def get_supply_hotwater(self):
        return os.path.join(self.get_supply_dir(), "SUPPLY_HOTWATER.csv")    
    # ============================
    # COMPONENTS
    # ============================
    def get_conversion_dir(self):
        return os.path.join(self.components, "Conversion")
    def get_conversion_photovoltaic_panels(self):
        return os.path.join(self.get_conversion_dir(), "PHOTOVOLTAIC_PANELS.csv")
    # ============================
    def get_distribution_dir(self):
        return os.path.join(self.components, "DISTRIBUTION")
    def get_thermal_grid(self):
        return os.path.join(self.get_distribution_dir(), "THERMAL_GRID.csv")
    # OUTPUT
    # ============================
        # ============================
    def get_solar_output_folder(self):
        folder = os.path.join(self.solar_output_dir)
        os.makedirs(folder, exist_ok=True)
        return folder
    def get_output_folder(self, load_type):
        folder = os.path.join(self.output_root, load_type)
        os.makedirs(folder, exist_ok=True)
        return folder
    # cooling
    def get_cooling_output_dir(self):
        cooling_path=os.path.join(self.output_root,'Hvac_Cooling_yearly')
        return cooling_path
    def get_aux_output_dir(self):
        aux_path=os.path.join(self.output_root,'Auxialary')
        return aux_path
    def get_hotwater_output_dir(self):
        dhw_path=os.path.join(self.output_root,'HW')
        return dhw_path
    def get_ea_el_output_dir(self):
        ea_el_path=os.path.join(self.output_root,'Ea_El')
        return ea_el_path
    def get_building_wise_total_output_dir(self):
        building_wise_total_path=os.path.join(self.output_root,'Total_Demand_Load_Buinding_wise_yearly')
        return building_wise_total_path
  

    def get_final_total_output_dir(self):
        folder = os.path.join(self.output_root, 'Final_total_load_yearly')

        files = [f for f in os.listdir(folder) if f.endswith(".csv")]

        if not files:
            raise FileNotFoundError("No final total CSV found")

        # pick latest file
        latest_file = sorted(files)[-1]

        return os.path.join(folder, latest_file)
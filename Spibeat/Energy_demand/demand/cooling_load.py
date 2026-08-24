from .inputLocator import InputLocator
from pvlib.iotools import read_epw
from .constants import SIMULATION_YEAR
from .cooling.schedule_72_h_yearly import schedule_72h_yearly
from .cooling.internal_gain import (
    internal_gain_due_people,
    internal_gain_due_lighting,
    internal_gain_due_applience
)
from .cooling.vantilation_infiltration import vantilation_and_infiltration
from .cooling.transmission_load import transmission_load
from .cooling.solar_gain import solar_gain
from .cooling.total_electrical_load import total_cooling_demand
from .cooling.calculating_hvac import (
    calculate_hvac_capacity,
    apply_hvac_capacity_limit,
    final_hvac_capacity_application,
    hvac_cooling_electricity,
    hvac_fan_electricity
)
from .cooling.total_Hvac_electrical_load import hvac_total_electricity_load

import os
import numpy as np
import pandas as pd
import traceback

# ----------------------------
# Helper function to expand 72h arrays to full year
# ----------------------------
def expand_to_year(array, target_len=8760):
    repeats = int(np.ceil(target_len / len(array)))
    return np.tile(array, repeats)[:target_len]

# ----------------------------
# Main cooling function
# ----------------------------
def run_cooling_cal(locator, building_data):
    try:
        print("✔ Starting run_cooling_cal")

        # ------------------------------
        # Load weather
        # ------------------------------
        EPW_FILE = locator.get_epw()
        print(f"✔ Loading EPW: {EPW_FILE}")

        weather, meta = read_epw(EPW_FILE)
        weather.index = weather.index.map(lambda t: t.replace(year=SIMULATION_YEAR))
        timestamps = weather.index
        n_hours = len(timestamps)

        # ------------------------------
        # Paths
        # ------------------------------
        Assemblies = locator.get_assemblies()
        SCHEDULE_DIR = locator.get_schedule_library()
        USE_TYPE_FILE = locator.get_use_types()
        ENVELOPE_DIR = locator.get_envelope_dir()
        MONTHLY_MULT_CSV = locator.get_monthly_multiplier("AC")

        OUT_DIR = locator.get_output_folder("Cooling_yearly")
        HVAC_OUT_DIR = locator.get_output_folder("Hvac_Cooling_yearly")

        os.makedirs(OUT_DIR, exist_ok=True)
        os.makedirs(HVAC_OUT_DIR, exist_ok=True)

        # ------------------------------
        # ✅ FIX: get building-wise schedules
        # ------------------------------
        schedule_results = schedule_72h_yearly(
            timestamps, SCHEDULE_DIR, MONTHLY_MULT_CSV, building_data
        )

        final_outputs = {}

        # =====================================================
        # 🔁 LOOP PER BUILDING (MAIN FIX)
        # =====================================================
        for b_id, sch in schedule_results.items():

            print(f"\n🚀 Running cooling for building: {b_id}")

            # ------------------------------
            # Extract schedules
            # ------------------------------
            cooling_72h = sch["cooling"]
            lighting_72h = sch["lighting"]
            ac_72h = sch["ac"]
            appliance_72h = sch["appliances"]
            people_72h = sch["people"]
            monthly_multiplier_8760 = sch["multiplier"]

            # ------------------------------
            # Expand to full year
            # ------------------------------
            cooling_schedule = expand_to_year(cooling_72h, n_hours)
            lighting_schedule = expand_to_year(lighting_72h, n_hours)
            ac_usage_schedule = expand_to_year(ac_72h, n_hours)
            appliance_schedule = expand_to_year(appliance_72h, n_hours)
            people_schedule = expand_to_year(people_72h, n_hours)
            monthly_multiplier_8760 = expand_to_year(monthly_multiplier_8760, n_hours)

            # ------------------------------
            # 👉 Single building dict
            # ------------------------------
            single_building = {b_id: building_data[b_id]}

            # ------------------------------
            # Internal gains
            # ------------------------------
            gains = internal_gain_due_people(
                people_schedule, timestamps, single_building, USE_TYPE_FILE
            )

            persons_hourly = gains["persons_hourly"]
            people_sensible_W = gains["people_sensible_W"]
            people_latent_W = gains["people_latent_W"]

            appliances_W = internal_gain_due_applience(
                appliance_schedule, timestamps, single_building, USE_TYPE_FILE
            )["appliances_W"]

            lights_W = internal_gain_due_lighting(
                lighting_schedule, timestamps, single_building, USE_TYPE_FILE
            )["lights_W"]

            # ------------------------------
            # Ventilation
            # ------------------------------
            vent = vantilation_and_infiltration(
                cooling_schedule, timestamps, single_building,
                USE_TYPE_FILE, EPW_FILE, ENVELOPE_DIR, persons_hourly
            )

            Tout = vent["Tout"]
            Tin_hourly = vent["Tin_hourly"]
            cooling_allowed = vent["cooling_allowed"]

            Q_inf_sensible_pos = vent["Q_inf_sensible_pos"]
            Q_inf_latent_pos = vent["Q_inf_latent_pos"]
            Q_vent_sensible_pos = vent["Q_vent_sensible_pos"]
            Q_vent_latent_pos = vent["Q_vent_latent_pos"]

            # ------------------------------
            # Transmission
            # ------------------------------
            trans = transmission_load(
                timestamps, single_building, USE_TYPE_FILE,
                ENVELOPE_DIR, Tout, Tin_hourly, cooling_allowed
            )

            Q_trans_cooling = {
                k: v.tolist() for k, v in trans["Q_transmission"].items()
            }

            # ------------------------------
            # Solar
            # ------------------------------
            solar = solar_gain(
                single_building, cooling_allowed, EPW_FILE, ENVELOPE_DIR
            )

            Q_solar = {
                k: v.tolist() for k, v in solar["Q_solar_windows_pos"].items()
            }

            # ------------------------------
            # Cooling demand
            # ------------------------------
            cooling = total_cooling_demand(
                timestamps, EPW_FILE, cooling_allowed, single_building,
                Q_trans_cooling, Q_inf_sensible_pos, Q_inf_latent_pos,
                Q_vent_sensible_pos, Q_vent_latent_pos,
                people_sensible_W, people_latent_W,
                appliances_W, lights_W,
                Q_solar, ac_usage_schedule, monthly_multiplier_8760,
                OUT_DIR
            )

            Q_coil_cooling_W = cooling["Q_coil_cooling_W"]

            # ------------------------------
            # HVAC
            # ------------------------------
            hvac_capacity_result = calculate_hvac_capacity(Assemblies, single_building)
            hvac_df = hvac_capacity_result["hvac_df"]

            hvac_limit = apply_hvac_capacity_limit(
                hvac_df,
                building_geoms=single_building,
                Q_coil_cooling_W=Q_coil_cooling_W
            )

            class_cs = hvac_limit["class_cs"]
            Qcsmax_Wm2 = hvac_limit["Qcsmax_Wm2"]

            hvac_final = final_hvac_capacity_application(
                single_building, Q_coil_cooling_W, Qcsmax_Wm2
            )

            hvac_elec = hvac_cooling_electricity(
                single_building,
                Q_coil_cooling_W,
                hvac_final["Q_coil_limited_W"],
                class_cs
            )

            fan = hvac_fan_electricity(
                single_building,
                Q_coil_cooling_W,
                hvac_final["Q_coil_limited_W"],
                class_cs
            )

            hvac_results = hvac_total_electricity_load(
                single_building,
                hvac_elec["P_AC_electric_W"],
                hvac_elec["P_AC_required_W"],
                fan["P_fan_served_W"],
                fan["P_fan_required_W"],
                hvac_final["Q_cs_max_W"],
                Q_coil_cooling_W,
                hvac_final["Q_coil_limited_W"],
                timestamps,
                HVAC_OUT_DIR,
                class_cs
            )

            # ------------------------------
            # Store result
            # ------------------------------
            final_outputs[b_id] = hvac_results["Hvac_Output_dir"]

        print("✔ run_cooling_cal completed successfully")

        return final_outputs

    except Exception:
        print("❌ ERROR in run_cooling_cal:")
        traceback.print_exc()
        return None
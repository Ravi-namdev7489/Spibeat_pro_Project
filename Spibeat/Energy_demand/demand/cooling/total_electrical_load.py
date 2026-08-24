import numpy as np
import pandas as pd
import os
from pvlib.iotools import read_epw


# ============================================================
# 🔥 TOTAL COOLING DEMAND (FINAL CONSISTENT ENGINE)
# ============================================================
def total_cooling_demand(
        timestamps,
        EPW_File,
        cooling_allowed,
        building_geoms,

        # Loads
        Q_trans_cooling,
        Q_inf_sensible_pos,
        Q_inf_latent_pos,
        Q_vent_sensible_pos,
        Q_vent_latent_pos,

        # Internal
        people_sensible_W,
        people_latent_W,
        appliances_W,
        lights_W,

        # Solar
        Q_solar_windows_pos,

        # Behaviour
        ac_usage_schedule,
        monthly_multiplier_8760,

        OUT_DIR
    ):

    print("\n❄️ RUNNING TOTAL COOLING DEMAND ENGINE")

    n_hours = len(timestamps)

    # ------------------------------------------------------------
    # WEATHER
    # ------------------------------------------------------------
    epw, _ = read_epw(EPW_File)

    Tout = epw["temp_air"].values

    if len(Tout) != n_hours:
        raise ValueError("❌ EPW length mismatch with timestamps")

    # ------------------------------------------------------------
    # FIXED THERMOSTAT
    # ------------------------------------------------------------
    Tin_fixed = 27.0
    Tin_set_arr = np.full(n_hours, Tin_fixed)

    # SAME LOGIC AS YOUR MODEL
    cooling_active = (cooling_allowed == 1) 

    # ------------------------------------------------------------
    # STORAGE
    # ------------------------------------------------------------
    Q_coil_cooling_W = {}
    building_hourly_results = {}

    # ============================================================
    # LOOP BUILDINGS
    # ============================================================
    for b_id, geom in building_geoms.items():

        name = geom["name"]
        USE_TYPE=geom["use_type"]
        print('multiplier',monthly_multiplier_8760)
        # --------------------------------------------------------
        # INTERNAL GAINS
        # --------------------------------------------------------
        Q_int_sensible_W = (
            people_sensible_W[b_id]
            + appliances_W[b_id]
            + lights_W[b_id]
        )

        Q_int_latent_W = people_latent_W[b_id]

        # --------------------------------------------------------
        # SOLAR
        # --------------------------------------------------------
        Q_solar_effective_W = Q_solar_windows_pos[b_id]

        # --------------------------------------------------------
        # SENSIBLE LOAD
        # --------------------------------------------------------
        Q_sensible_total_W = (
            Q_trans_cooling[b_id]
            + Q_inf_sensible_pos[b_id]
            + Q_vent_sensible_pos[b_id]
            + Q_int_sensible_W
            + Q_solar_effective_W
        )

        # --------------------------------------------------------
        # LATENT LOAD
        # --------------------------------------------------------
        Q_latent_total_W = (
            Q_inf_latent_pos[b_id]
            + Q_vent_latent_pos[b_id]
            + Q_int_latent_W
        )

        # --------------------------------------------------------
        # TOTAL COOLING LOAD
        # --------------------------------------------------------
        Q_cooling_total_W = Q_sensible_total_W + Q_latent_total_W

        # --------------------------------------------------------
        # THERMOSTAT CONTROL
        # --------------------------------------------------------
        Q_sensible_total_W = np.where(cooling_active, Q_sensible_total_W, 0.0)
        Q_latent_total_W   = np.where(cooling_active, Q_latent_total_W, 0.0)
        Q_cooling_total_W  = np.where(cooling_active, Q_cooling_total_W, 0.0)

        # --------------------------------------------------------
        # OPERATION + MONTHLY EFFECT
        # --------------------------------------------------------
        Q_cooling_modified = (
            Q_cooling_total_W
            * ac_usage_schedule
            * monthly_multiplier_8760
        )

        Q_coil_cooling_W[b_id] = Q_cooling_modified

        # --------------------------------------------------------
        # HOURLY OUTPUT
        # --------------------------------------------------------
        cooling_hourly_df = pd.DataFrame({

            "timestamp": timestamps,
            "building": name,

            "Tout_C": Tout,
            "Tin_set_C": Tin_set_arr,

            "cooling_allowed": cooling_allowed.astype(int),
            "cooling_active": cooling_active.astype(int),

            # TRANSMISSION
            "Q_transmission_W": Q_trans_cooling[b_id],

            # INFILTRATION
            "Q_inf_sensible_W": Q_inf_sensible_pos[b_id],
            "Q_inf_latent_W": Q_inf_latent_pos[b_id],

            # VENTILATION
            "Q_vent_sensible_W": Q_vent_sensible_pos[b_id],
            "Q_vent_latent_W": Q_vent_latent_pos[b_id],

            # INTERNAL
            "Q_people_sensible_W": people_sensible_W[b_id],
            "Q_people_latent_W": people_latent_W[b_id],
            "Q_appliances_W": appliances_W[b_id],
            "Q_lighting_W": lights_W[b_id],

            # SOLAR
            "Q_solar_effective_W": Q_solar_effective_W,

            # TOTALS
            "Q_sensible_total_W": Q_sensible_total_W,
            "Q_latent_total_W": Q_latent_total_W,

            # BEHAVIOUR
            "AC_usage_schedule": ac_usage_schedule,
            "Monthly_multiplier": monthly_multiplier_8760,

            # FINAL COIL LOAD
            "Q_coil_cooling_W": Q_cooling_modified

        }).set_index("timestamp")

        building_hourly_results[b_id] = cooling_hourly_df

        # --------------------------------------------------------
        # SAVE FILE
        # --------------------------------------------------------
        out_csv = os.path.join(
            OUT_DIR,
            f"cooling_hourly_{USE_TYPE}_{name}.csv"
        )

        cooling_hourly_df.to_csv(out_csv)
     
        print(f"✔ Saved cooling results → {name}")

    # ------------------------------------------------------------
    # RETURN
    # ------------------------------------------------------------
    return {
        "Q_coil_cooling_W": Q_coil_cooling_W,
        "hourly_results": building_hourly_results,
        "cooling_active": cooling_active
    }
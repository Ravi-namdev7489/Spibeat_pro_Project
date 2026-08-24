import os
import numpy as np
import pandas as pd


def hvac_total_electricity_load(
        building_geoms,
        P_AC_electric_W,
        P_AC_required_W,
        P_fan_served_W,
        P_fan_required_W,
        Q_cs_max_W,
        Q_coil_cooling_W,
        Q_coil_limited_W,
        timestamps,
        out_dir,
        hvac_class
):

    os.makedirs(out_dir, exist_ok=True)

    P_HVAC_el_W = {}
    P_HVAC_required_W = {}

    print("\n=== HVAC ELECTRICITY RESULTS (PER BUILDING) ===")

    for b_id, geom in building_geoms.items():

        name = geom["name"]

        # --------------------------------------------------------
        # Clean arrays
        # --------------------------------------------------------
        P_AC_served   = np.nan_to_num(P_AC_electric_W[b_id], nan=0.0)
        P_AC_required = np.nan_to_num(P_AC_required_W[b_id], nan=0.0)

        P_fan_served   = np.nan_to_num(P_fan_served_W[b_id], nan=0.0)
        P_fan_required = np.nan_to_num(P_fan_required_W[b_id], nan=0.0)

        # --------------------------------------------------------
        # Unserved electricity
        # --------------------------------------------------------
        P_AC_unserved  = P_AC_required - P_AC_served
        P_fan_unserved = P_fan_required - P_fan_served

        # --------------------------------------------------------
        # Total HVAC electricity
        # --------------------------------------------------------
        P_HVAC_el_W[b_id]       = P_AC_served + P_fan_served
        P_HVAC_required_W[b_id] = P_AC_required + P_fan_required

        P_unserved_total = P_AC_unserved + P_fan_unserved

        # --------------------------------------------------------
        # Peak values
        # --------------------------------------------------------
        peak_HVAC_served_kW   = P_HVAC_el_W[b_id].max() / 1000
        peak_HVAC_unserved_kW = P_unserved_total.max() / 1000

        # --------------------------------------------------------
        # Annual energy
        # --------------------------------------------------------
        annual_served_kWh   = P_HVAC_el_W[b_id].sum() / 1000
        annual_unserved_kWh = P_unserved_total.sum() / 1000

        # --------------------------------------------------------
        # Reporting
        # --------------------------------------------------------
        print(f"\n--- {name} ---")
        print(f" Cooling capacity (kW)          : {Q_cs_max_W[b_id]/1000:.2f}")
        print(f" Peak cooling demand (kW)       : {Q_coil_cooling_W[b_id].max()/1000:.2f}")
        print(f" Peak cooling served (kW)       : {Q_coil_limited_W[b_id].max()/1000:.2f}")
        print(f" Peak HVAC electric served (kW) : {peak_HVAC_served_kW:.2f}")
        print(f" Peak HVAC electric unserved (kW): {peak_HVAC_unserved_kW:.2f}")
        print(f" Annual HVAC electric served (kWh)   : {annual_served_kWh:.0f}")
        print(f" Annual HVAC electric unserved (kWh) : {annual_unserved_kWh:.0f}")

        # ========================================================
        # FULL YEAR DATA (8760 HOURS)
        # ========================================================

        P_required = P_HVAC_required_W[b_id]
        P_served   = P_HVAC_el_W[b_id]
        P_unserved = np.maximum(P_required - P_served, 0)

        hvac_year_df = pd.DataFrame({
            "HVAC_served_W": P_served,
            "HVAC_served_kW": P_served / 1000,
            "HVAC_required_W": P_required,
            "HVAC_required_kW": P_required / 1000,
            "HVAC_unserved_W": P_unserved,
            "HVAC_unserved_kW": P_unserved / 1000
        }, index=timestamps)

        hvac_year_df.index.name = "timestamps"

        # --------------------------------------------------------
        # Save CSV
        # --------------------------------------------------------
        out_csv = os.path.join(
            out_dir,
            f"HVAC_hourly_YEAR_{name}.csv"
        )

        hvac_year_df.to_csv(out_csv)

        print(f"✔ Saved 8760h HVAC electricity for {name}")

    print("\n✔ ALL BUILDINGS HVAC YEARLY FILES SAVED")

    return {
        "P_HVAC_el_W": P_HVAC_el_W,
        "P_HVAC_required_W": P_HVAC_required_W,
        "Hvac_Output_dir":out_dir
    }
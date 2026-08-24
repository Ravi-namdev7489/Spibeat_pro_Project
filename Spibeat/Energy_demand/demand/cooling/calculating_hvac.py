# ============================================================
# HVAC COOLING SYSTEM CAPACITY
# ============================================================

import os
import pandas as pd
import numpy as np
from ..constants import DEFAULT_QCSMAX

def calculate_hvac_capacity( ASSEMBLIES_DIR, building_geoms):
    
    
    # ------------------------------------------------------------
    # 4️⃣ Calculate cooling capacity per building
    # ------------------------------------------------------------
    hvac_capacity_W = {}

    for b_id, geom in building_geoms.items():

        floor_area = geom["floor_area"]
        USE_TYPE=geom["use_type"]
        # ------------------------------------------------------------
    # 1️⃣ Define directories
    # ------------------------------------------------------------
        HVAC_DIR = os.path.join(ASSEMBLIES_DIR, "HVAC")

        hvac_path = os.path.join(HVAC_DIR, "HVAC_COOLING.csv")

        if not os.path.exists(hvac_path):
            raise FileNotFoundError(f"HVAC file not found: {hvac_path}")

        # ------------------------------------------------------------
        # 2️⃣ Load HVAC database
        # ------------------------------------------------------------
        hvac_df = pd.read_csv(hvac_path)

        print("\nAvailable HVAC systems:")
        print(hvac_df[["code", "class_cs", "Qcsmax_Wm2"]])

        # ------------------------------------------------------------
        # 3️⃣ Select system based on USE_TYPE
        # ------------------------------------------------------------
        USE_TYPE_UP = USE_TYPE.upper()

        hvac_row = hvac_df[
            hvac_df["code"].str.upper() == USE_TYPE_UP
        ]

        DEFAULT_QCSMAX = 120.0

        if hvac_row.empty:

            print(f"\n⚠ No HVAC system found for USE_TYPE = {USE_TYPE}")
            print(f"Using default cooling capacity {DEFAULT_QCSMAX} W/m²")

            Qcsmax_Wm2 = DEFAULT_QCSMAX

        else:

            hvac_row = hvac_row.iloc[0]

            Qcsmax_Wm2 = hvac_row.get("Qcsmax_Wm2", DEFAULT_QCSMAX)

            try:
                Qcsmax_Wm2 = float(Qcsmax_Wm2)
            except (ValueError, TypeError):

                print(
                    f"\n⚠ Invalid Qcsmax_Wm2 in HVAC_COOLING.csv for {USE_TYPE}"
                )
                print(f"Using default {DEFAULT_QCSMAX} W/m²")

                Qcsmax_Wm2 = DEFAULT_QCSMAX

        print(f"\nSelected HVAC system for {USE_TYPE}")
        print(f"Cooling capacity = {Qcsmax_Wm2:.1f} W/m²")

        capacity = Qcsmax_Wm2 * floor_area

        hvac_capacity_W[b_id] = capacity

        print(f"✔ {geom['name']} | HVAC Capacity = {capacity/1000:.2f} kW")

    # ------------------------------------------------------------
    # 5️⃣ Return results
    # ------------------------------------------------------------
    return {
        "Qcsmax_Wm2": Qcsmax_Wm2,
        "hvac_capacity_W": hvac_capacity_W,
        "hvac_df":hvac_df
    }


def apply_hvac_capacity_limit(
        hvac_df,
        building_geoms,
        Q_coil_cooling_W):

   

    # ------------------------------------------------------------
    # 2️⃣ Storage dictionaries
    # ------------------------------------------------------------
    Q_cs_max_W = {}
    Q_coil_limited_W = {}
    Q_unserved_cooling_W = {}

    # ------------------------------------------------------------
    # 3️⃣ Loop buildings
    # ------------------------------------------------------------
    for b_id, geom in building_geoms.items():

        name = geom["name"]
        floor_area = geom["floor_area"]
        TARGET_CLASS=geom["cooling_temp"]
         # ------------------------------------------------------------
        # 1️⃣ Select AC system by class
        # ------------------------------------------------------------
        ac_rows = hvac_df.loc[
            hvac_df["class_cs"].str.upper() == TARGET_CLASS.upper()
        ]

        DEFAULT_QCSMAX = 120.0

        if ac_rows.empty:
            print(f"⚠ WARNING: {TARGET_CLASS} not found in HVAC table.")
            Qcsmax_Wm2 = DEFAULT_QCSMAX
            class_cs = "DEFAULT"

        else:
            ac_row = ac_rows.iloc[0]

            try:
                Qcsmax_Wm2 = float(ac_row["Qcsmax_Wm2"])
            except (ValueError, TypeError):
                print(
                    f"⚠ Invalid Qcsmax_Wm2 in CSV for {TARGET_CLASS}, "
                    f"using default {DEFAULT_QCSMAX} W/m²"
                )
                Qcsmax_Wm2 = DEFAULT_QCSMAX

            class_cs = ac_row["class_cs"]

        print("\nSelected AC system:")
        print(" Class:", class_cs)
        print(f" Qcsmax_Wm2: {Qcsmax_Wm2:.1f} W/m²")
        # Maximum HVAC capacity
        Q_cs_max_W[b_id] = Qcsmax_Wm2 * floor_area

        # Cooling served by system
        Q_coil_limited_W[b_id] = np.minimum(
            Q_coil_cooling_W[b_id],
            Q_cs_max_W[b_id]
        )

        # Cooling not served
        Q_unserved_cooling_W[b_id] = np.maximum(
            Q_coil_cooling_W[b_id] - Q_cs_max_W[b_id],
            0.0
        )

        print(
            f"✔ {name} | "
            f"Capacity = {Q_cs_max_W[b_id]/1000:.1f} kW | "
            f"Peak demand = {Q_coil_cooling_W[b_id].max()/1000:.1f} kW | "
            f"Peak served = {Q_coil_limited_W[b_id].max()/1000:.1f} kW"
        )

    # ------------------------------------------------------------
    # 4️⃣ Return results
    # ------------------------------------------------------------
    return {
        "class_cs": class_cs,
        "Qcsmax_Wm2": Qcsmax_Wm2,
        "Q_cs_max_W": Q_cs_max_W,
        "Q_coil_limited_W": Q_coil_limited_W,
        "Q_unserved_cooling_W": Q_unserved_cooling_W
    }
import numpy as np

def final_hvac_capacity_application(
        building_geoms,
        Q_coil_cooling_W,
        Qcsmax_Wm2
):
    """
    Apply HVAC capacity limits to cooling demand for multiple buildings.

    Returns:
        dict with:
        - Q_cs_max_W
        - Q_coil_limited_W
        - Q_unserved_cooling_W
    """

    # ------------------------------------------------------------
    # Storage dictionaries
    # ------------------------------------------------------------
    Q_cs_max_W = {}
    Q_coil_limited_W = {}
    Q_unserved_cooling_W = {}

    # ------------------------------------------------------------
    # Loop buildings
    # ------------------------------------------------------------
    for b_id, geom in building_geoms.items():

        name = geom["name"]
        floor_area = geom["floor_area"]

        # --------------------------------------------------------
        # 1️⃣ Installed HVAC capacity
        # --------------------------------------------------------
        Q_cs_max_W[b_id] = Qcsmax_Wm2 * floor_area

        # --------------------------------------------------------
        # 2️⃣ Clean cooling demand
        # --------------------------------------------------------
        demand = np.nan_to_num(Q_coil_cooling_W[b_id], nan=0.0)
        demand = np.maximum(demand, 0.0)

        # --------------------------------------------------------
        # 3️⃣ Served cooling
        # --------------------------------------------------------
        Q_coil_limited_W[b_id] = np.minimum(
            demand,
            Q_cs_max_W[b_id]
        )

        # --------------------------------------------------------
        # 4️⃣ Unserved cooling
        # --------------------------------------------------------
        Q_unserved_cooling_W[b_id] = np.maximum(
            demand - Q_cs_max_W[b_id],
            0.0
        )

        # --------------------------------------------------------
        # 5️⃣ Peak values
        # --------------------------------------------------------
        peak_demand_kW = demand.max() / 1000.0
        peak_served_kW = Q_coil_limited_W[b_id].max() / 1000.0
        peak_unserved_kW = Q_unserved_cooling_W[b_id].max() / 1000.0

        # --------------------------------------------------------
        # 6️⃣ Annual energy
        # --------------------------------------------------------
        annual_served_kWh = Q_coil_limited_W[b_id].sum() / 1000.0
        annual_unserved_kWh = Q_unserved_cooling_W[b_id].sum() / 1000.0

        # --------------------------------------------------------
        # Print summary
        # --------------------------------------------------------
        print(
            f"\n✔ {name}"
            f"\n  Capacity        : {Q_cs_max_W[b_id]/1000:.1f} kW"
            f"\n  Peak demand     : {peak_demand_kW:.1f} kW"
            f"\n  Peak served     : {peak_served_kW:.1f} kW"
            f"\n  Peak unserved   : {peak_unserved_kW:.1f} kW"
            f"\n  Annual served   : {annual_served_kWh:.0f} kWh"
            f"\n  Annual unserved : {annual_unserved_kWh:.0f} kWh"
        )

    # ------------------------------------------------------------
    # Return results
    # ------------------------------------------------------------
    return {
        "Q_cs_max_W": Q_cs_max_W,
        "Q_coil_limited_W": Q_coil_limited_W,
        "Q_unserved_cooling_W": Q_unserved_cooling_W
    }
    
import numpy as np

def hvac_cooling_electricity(
        building_geoms,
        Q_coil_cooling_W,
        Q_coil_limited_W,
        class_cs
):
    """
    Convert cooling load to electricity using COP.

    Returns:
        dict containing:
        - COP_AC
        - P_AC_electric_W (served electricity)
        - P_AC_required_W (electricity for full demand)
    """

    # ------------------------------------------------------------
    # COP mapping for HVAC systems
    # ------------------------------------------------------------
    COP_MAP = {
        "DECENTRALIZED_AC": 3.2,
        "CENTRAL_AC": 4.5,
        "FLOOR_COOLING": 5.5,
        "CEILING_COOLING": 4.0
    }

    COP_AC = COP_MAP.get(class_cs, 3.5)

    print(f"\nUsing COP for {class_cs}: {COP_AC}")

    # ------------------------------------------------------------
    # Storage
    # ------------------------------------------------------------
    P_AC_electric_W = {}
    P_AC_required_W = {}

    # ------------------------------------------------------------
    # Loop over buildings
    # ------------------------------------------------------------
    for b_id, geom in building_geoms.items():

        name = geom["name"]

        # --------------------------------------------------------
        # Cooling loads
        # --------------------------------------------------------
        Q_total_W = Q_coil_cooling_W[b_id]
        Q_served_W = Q_coil_limited_W[b_id]
        Q_unserved_W = Q_total_W - Q_served_W

        # --------------------------------------------------------
        # Electricity
        # --------------------------------------------------------
        P_AC_electric_W[b_id] = Q_served_W / COP_AC
        P_AC_required_W[b_id] = Q_total_W / COP_AC

        # --------------------------------------------------------
        # Peak values
        # --------------------------------------------------------
        peak_total_kW = Q_total_W.max() / 1000.0
        peak_served_kW = Q_served_W.max() / 1000.0
        peak_unserved_kW = Q_unserved_W.max() / 1000.0

        # --------------------------------------------------------
        # Annual energy
        # --------------------------------------------------------
        annual_total_kWh = Q_total_W.sum() / 1000.0
        annual_served_kWh = Q_served_W.sum() / 1000.0
        annual_unserved_kWh = Q_unserved_W.sum() / 1000.0

        # --------------------------------------------------------
        # Print summary
        # --------------------------------------------------------
        print(
            f"\n✔ {name}"
            f"\n  Peak cooling demand        : {peak_total_kW:.2f} kW"
            f"\n  Peak AC electric (served)  : {peak_served_kW:.2f} kW"
            f"\n  Peak AC electric (unserved): {peak_unserved_kW:.2f} kW"
            f"\n  Annual cooling demand      : {annual_total_kWh:.0f} kWh"
            f"\n  Annual AC electric (served): {annual_served_kWh:.0f} kWh"
            f"\n  Annual AC electric unserved: {annual_unserved_kWh:.0f} kWh"
        )

    # ------------------------------------------------------------
    # Return results
    # ------------------------------------------------------------
    return {
        "COP_AC": COP_AC,
        "P_AC_electric_W": P_AC_electric_W,
        "P_AC_required_W": P_AC_required_W
    }
import numpy as np

def hvac_fan_electricity(
        building_geoms,
        Q_coil_cooling_W,
        Q_coil_limited_W,
        class_cs
):
    """
    Calculate fan electricity load for HVAC systems.

    Returns:
        dict:
            fan_Wm2
            P_fan_served_W
            P_fan_required_W
    """

    # ------------------------------------------------------------
    # Fan power density mapping (W/m²)
    # ------------------------------------------------------------
    FAN_WM2_MAP = {
        "DECENTRALIZED_AC": 0.5,
        "CENTRAL_AC": 2.5,
        "FLOOR_COOLING": 0.2,
        "CEILING_COOLING": 1.0
    }

    fan_Wm2 = FAN_WM2_MAP.get(class_cs, 0.5)

    print(f"\nUsing fan power density for {class_cs}: {fan_Wm2} W/m²")

    # ------------------------------------------------------------
    # Storage
    # ------------------------------------------------------------
    P_fan_served_W = {}
    P_fan_required_W = {}

    # ------------------------------------------------------------
    # Loop over buildings
    # ------------------------------------------------------------
    for b_id, geom in building_geoms.items():

        name = geom["name"]
        floor_area = geom["floor_area"]

        # Hourly cooling arrays
        Q_total_W = Q_coil_cooling_W[b_id]
        Q_served_W = Q_coil_limited_W[b_id]

        # --------------------------------------------------------
        # Fan runs when cooling is delivered
        # --------------------------------------------------------
        fan_served_on = Q_served_W > 0.0
        P_fan_served_W[b_id] = fan_Wm2 * floor_area * fan_served_on.astype(float)

        # --------------------------------------------------------
        # Fan equivalent for full demand
        # --------------------------------------------------------
        fan_required_on = Q_total_W > 0.0
        P_fan_required_W[b_id] = fan_Wm2 * floor_area * fan_required_on.astype(float)

        # --------------------------------------------------------
        # Peak values
        # --------------------------------------------------------
        peak_served_W = P_fan_served_W[b_id].max()
        peak_required_W = P_fan_required_W[b_id].max()

        # --------------------------------------------------------
        # Annual energy
        # --------------------------------------------------------
        annual_served_kWh = P_fan_served_W[b_id].sum() / 1000.0
        annual_required_kWh = P_fan_required_W[b_id].sum() / 1000.0

        print(
            f"\n✔ Fan | {name}"
            f"\n  Peak served     : {peak_served_W:.1f} W"
            f"\n  Peak total req  : {peak_required_W:.1f} W"
            f"\n  Annual served   : {annual_served_kWh:.0f} kWh"
            f"\n  Annual total req: {annual_required_kWh:.0f} kWh"
        )

    # ------------------------------------------------------------
    # Return results
    # ------------------------------------------------------------
    return {
        "fan_Wm2": fan_Wm2,
        "P_fan_served_W": P_fan_served_W,
        "P_fan_required_W": P_fan_required_W
    }
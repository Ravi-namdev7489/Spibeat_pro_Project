
from .Building_Geometry import safe_float
import numpy as np
import pandas as pd
from ..constants import H_WE
import pandas as pd
import numpy as np

H_WE = 2501000  # J/kg (latent heat of vaporization)

def safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def internal_gain_due_people(
        people_schedule,
        timestamps,
        building_geoms,
        USE_TYPE_FILE
):
    """
    Calculate internal gains due to people for multiple buildings.

    Returns:
        dict containing:
            persons_design
            persons_hourly
            people_sensible_W
            people_latent_W
    """


    # ------------------------------------------------------------
   
    # ------------------------------------------------------------
    # 4️⃣ Storage dictionaries
    # ------------------------------------------------------------
    persons_design_dict = {}
    persons_hourly = {}
    people_sensible_W = {}
    people_latent_W = {}

    # ------------------------------------------------------------
    # 5️⃣ Loop over buildings
    # ------------------------------------------------------------
    for b_id, geom in building_geoms.items():

        floor_area = geom["floor_area"]
        USE_TYPE=geom["use_type"]
        # ------------------------------------------------------------
        # 1️⃣ Load USE_TYPE file
        # ------------------------------------------------------------
        use_df = pd.read_csv(USE_TYPE_FILE)
        use_df["use_type"] = use_df["use_type"].str.strip().str.upper()
        USE_TYPE = USE_TYPE.strip().upper()

        n_hours = len(timestamps)

        if len(people_schedule) != n_hours:
            raise ValueError("❌ people_schedule length mismatch with EPW hours.")

        # ------------------------------------------------------------
        # 2️⃣ Extract use-type row safely
        # ------------------------------------------------------------
        use_row = use_df[use_df["use_type"] == USE_TYPE]

        if use_row.empty:
            raise ValueError(f"❌ USE_TYPE '{USE_TYPE}' not found in USE_TYPE_FILE")

        use_row = use_row.iloc[0]
         # 3️⃣ Parameters
        # ------------------------------------------------------------
        Occ_m2p = safe_float(use_row.get("Occ_m2p", np.nan), default=3.0)
        Qs_Wp   = safe_float(use_row.get("Qs_Wp", np.nan), default=60.0)
        X_ghp   = safe_float(use_row.get("X_ghp", np.nan), default=33.33)

        if Occ_m2p <= 0:
            raise ValueError("❌ Occ_m2p must be > 0")

        # Design occupants
        persons_design = floor_area / Occ_m2p
        persons_design_dict[b_id] = persons_design

        # Hourly occupants
        persons_hourly[b_id] = persons_design * people_schedule

        # Sensible gains
        people_sensible_W[b_id] = persons_hourly[b_id] * Qs_Wp

        # Latent gains
        people_latent_W[b_id] = (
            persons_hourly[b_id]
            * (X_ghp / 1000.0 / 3600.0)
            * H_WE
        )

    # ------------------------------------------------------------
    # 6️⃣ Return structured dictionary
    # ------------------------------------------------------------
    return {
        "persons_design": persons_design_dict,
        "persons_hourly": persons_hourly,
        "people_sensible_W": people_sensible_W,
        "people_latent_W": people_latent_W
    }
    
def internal_gain_due_applience(
        appliance_schedule,
        timestamps,
        building_geoms,
        USE_TYPE_FILE):

    
    # ------------------------------------------------------------
    # 2️⃣ Storage dictionary
    # ------------------------------------------------------------
    appliances_W = {}

    # ------------------------------------------------------------
    # 3️⃣ Loop buildings
    # ------------------------------------------------------------
    for b_id, geom in building_geoms.items():

        floor_area = geom["floor_area"]
        USE_TYPE=geom["use_type"]
        n_hours = len(timestamps)

        use_df = pd.read_csv(USE_TYPE_FILE)

        if len(appliance_schedule) != n_hours:
            raise ValueError("❌ appliance_schedule length mismatch with EPW hours.")

        use_row = use_df[
            use_df['use_type'].str.upper() == USE_TYPE.upper()
        ].iloc[0]

        # ------------------------------------------------------------
        # 1️⃣ Appliance intensity
        # ------------------------------------------------------------
        Ea_Wm2 = safe_float(use_row.get("Ea_Wm2", np.nan), default=0.0)

        print(f"\nUsing USE_TYPE: {USE_TYPE}")
        print(f"Ea_Wm2 = {Ea_Wm2} W/m²")

        # Hourly appliance load
        appliances = Ea_Wm2 * floor_area * appliance_schedule

        appliances_W[b_id] = appliances

        print(f"✔ {geom['name']}: floor_area={floor_area:.1f} m²")

    # ------------------------------------------------------------
    # 4️⃣ Sanity check
    # ------------------------------------------------------------
    b0 = list(building_geoms.keys())[0]

    print("\nSample building:", building_geoms[b0]["name"])
    print("Max appliance load (kW):", appliances_W[b0].max() / 1000)
    print("First 24 h:", appliances_W[b0][:24])

    # ------------------------------------------------------------
    # 5️⃣ RETURN FOR NEXT MODULE
    # ------------------------------------------------------------
    return {
        "appliances_W": appliances_W,
        "Ea_Wm2": Ea_Wm2
    }
# ------------------------------------------------------------
def internal_gain_due_lighting(lighting_schedule,timestamps,building_geoms,USE_TYPE_FILE):
  
    lights_W = {}

    # ------------------------------------------------------------
    # 4️⃣ Loop over buildings
    # ------------------------------------------------------------
    for b_id, geom in building_geoms.items():

        floor_area = geom["floor_area"]
        USE_TYPE=geom["use_type"]
        n_hours = len(timestamps)
        use_df = pd.read_csv(USE_TYPE_FILE)
        if len(lighting_schedule) != n_hours:
            raise ValueError("❌ appliance_schedule length mismatch with EPW hours.")
        use_row = use_df[
            use_df['use_type'].str.upper() == USE_TYPE.upper()
        ].iloc[0]
        
        if len(lighting_schedule) != n_hours:
            raise ValueError("❌ lighting_schedule length mismatch with EPW hours.")

        # ------------------------------------------------------------
        # 2️⃣ Extract lighting intensity from USE_TYPE
        # ------------------------------------------------------------
        El_Wm2 = safe_float(use_row.get("El_Wm2", np.nan), default=0.0)

        print(f"\nUsing USE_TYPE: {USE_TYPE}")
        print(f"El_Wm2 = {El_Wm2} W/m²")

    # ------------------------------------------------------------
    # 3️⃣ Storage
    # ------------------------------------------------------------

        # ---------- Scheduled lighting load (W) ----------
        lighting = El_Wm2 * floor_area * lighting_schedule

        lights_W[b_id] = lighting

        print(f"✔ {geom['name']}: floor_area={floor_area:.1f} m²")

    # ------------------------------------------------------------
    # 5️⃣ Sanity check
    # ------------------------------------------------------------
    b0 = list(building_geoms.keys())[0]

    print("\nSample building:", building_geoms[b0]["name"])
    print(" Max lighting load (kW):", lights_W[b0].max() / 1000)
    print(" First 24 h:", lights_W[b0][:24])
    return {
        "lights_W": lights_W,
        "El_Wm2": El_Wm2
    }


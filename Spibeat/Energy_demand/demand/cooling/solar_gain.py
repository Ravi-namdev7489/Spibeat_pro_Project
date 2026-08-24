import numpy as np
import pandas as pd
import os
from pvlib.iotools import read_epw
from .Building_Geometry import load_csv_if_exists
from ..constants import (
    VERTICAL_IRRADIANCE_FACTOR,
    DEFAULT_SHGC
)
def solar_gain(building_geoms, cooling_allowed, EPW_File, ENVELOPE_DIR):
    # ------------------------------------------------------------
    # 1️⃣ Weather
    # ------------------------------------------------------------
    EPW_data, _ = read_epw(EPW_File)
    ghi = EPW_data["ghi"].values

    # ------------------------------------------------------------
    # 2️⃣ Shading DB
    # ------------------------------------------------------------
    env_shading = load_csv_if_exists(
        os.path.join(ENVELOPE_DIR, "ENVELOPE_SHADING.csv")
    )

    # Default factor
    default_shading_factor = 1.0

    # ------------------------------------------------------------
    # 3️⃣ Irradiance
    # ------------------------------------------------------------
    incident_vertical = ghi * VERTICAL_IRRADIANCE_FACTOR

    # ------------------------------------------------------------
    # 4️⃣ Solar Gain
    # ------------------------------------------------------------
    Q_solar_windows_pos = {}

    for b_id, geom in building_geoms.items():
        window_area = geom["window_area"]
        building_shading_type = geom.get("shading", "SHADE_NONE")

        # Lookup shading factor
        shading_factor = default_shading_factor
        if env_shading is not None:
            row = env_shading[env_shading["shading_type"] == building_shading_type]
            if not row.empty:
                shading_factor = float(row.iloc[0]["shading_factor"])
            else:
                print(f"⚠️ Shading type '{building_shading_type}' not found → using default")

        # Solar gain
        Q_solar = window_area * DEFAULT_SHGC * incident_vertical * shading_factor

        Q_solar_windows_pos[b_id] = np.where(
            cooling_allowed == 1,
            np.maximum(Q_solar, 0.0),
            0.0
        )

        print(f"✔ {b_id}: shading_type={building_shading_type}, shading_factor={shading_factor}")

    # ------------------------------------------------------------
    return {
        "Q_solar_windows_pos": Q_solar_windows_pos,
        "incident_vertical": incident_vertical
    }
   
# ============================================================
# Cell 7: Transmission loads (MULTI-BUILDING)
# ============================================================

import numpy as np
import pandas as pd
import os

from .internal_gain import safe_float
from .Building_Geometry import load_csv_if_exists


# ------------------------------------------------------------
# 1️⃣ U-value helper (SAME AS CELL 7)
# ------------------------------------------------------------
def get_u_from_df(env_df, prefer_u_cols=['u_value_W_m2K', 'u_value', 'u']):

    if env_df is None:
        return None

    for c in prefer_u_cols:
        if c in env_df.columns:
            return float(env_df.iloc[0][c])

    numeric = env_df.select_dtypes(include=[np.number])
    if numeric.shape[1] >= 1:
        return float(numeric.iloc[0, 0])

    return None


# ------------------------------------------------------------
# 2️⃣ MAIN FUNCTION
# ------------------------------------------------------------
def transmission_load(
    timestamps,
    building_geoms,
    USE_TYPE_FILE,
    ENVELOPE_DIR,
    Tout,
    Tin_hourly,
    cooling_allowed
):

    print("\n🔥 RUNNING TRANSMISSION LOAD (CELL 7 STYLE)")

    
    # ------------------------------------------------------------
    # STORAGE
    # ------------------------------------------------------------
    Q_trans_cooling = {}

    # ------------------------------------------------------------
    # LOOP BUILDINGS
    # ------------------------------------------------------------
    for b_id, geom in building_geoms.items():

        wall_area   = geom["wall_area"]
        roof_area   = geom["roof_area"]
        window_area = geom["window_area"]
        floor_area  = geom["floor_area"]
        USE_TYPE=geom["use_type"]
        n_hours = len(timestamps)

        if not building_geoms:
            raise ValueError("❌ building_geoms is EMPTY")

        # ------------------------------------------------------------
        # USE TYPE
        # ------------------------------------------------------------
        use_df = pd.read_csv(USE_TYPE_FILE)
        use_df.columns = use_df.columns.str.strip()

        use_df["use_type"] = use_df["use_type"].str.strip().str.upper()
        USE_TYPE = USE_TYPE.strip().upper()

        use_rows = use_df[use_df["use_type"] == USE_TYPE]

        if use_rows.empty:
            raise ValueError(f"❌ USE_TYPE '{USE_TYPE}' not found")

        use_row = use_rows.iloc[0]

        Tin_set = safe_float(
            use_row.get("Tcs_set_C", use_row.get("Tin_set_C", 28.0)),
            default=28.0
        )

        # ------------------------------------------------------------
        # ENVELOPE FILES
        # ------------------------------------------------------------
        env_wall  = load_csv_if_exists(os.path.join(ENVELOPE_DIR, "ENVELOPE_WALL.csv"))
        env_roof  = load_csv_if_exists(os.path.join(ENVELOPE_DIR, "ENVELOPE_ROOF.csv"))
        env_floor = load_csv_if_exists(os.path.join(ENVELOPE_DIR, "ENVELOPE_FLOOR.csv"))
        env_win   = load_csv_if_exists(os.path.join(ENVELOPE_DIR, "ENVELOPE_WINDOW.csv"))

        # ------------------------------------------------------------
        # TEMPERATURE DIFFERENCE (CELL 7 EXACT LOGIC)
        # ------------------------------------------------------------
        dT = np.zeros(n_hours)

        mask = (cooling_allowed == 1) & (~np.isnan(Tin_hourly))

        dT[mask] = np.maximum(Tout[mask] - Tin_hourly[mask], 0)

        # --------------------------------------------------------
        # U-values (CELL 7 STYLE FIXED VALUES)
        # --------------------------------------------------------
        U_wall = get_u_from_df(env_wall) or 1.5
        U_roof = get_u_from_df(env_roof) or 1.2
        U_floor = get_u_from_df(env_floor) or 1.0
        U_win = get_u_from_df(env_win) or 5.6

        print(f"✔ {geom['name']} | U_wall={U_wall}, U_roof={U_roof}, U_win={U_win}")

        # --------------------------------------------------------
        # TRANSMISSION LOADS
        # --------------------------------------------------------
        Q_wall = U_wall * wall_area * dT
        Q_roof = U_roof * roof_area * dT
        Q_win  = U_win * window_area * dT

        # FLOOR (same as Cell 7)
        T_ground = 28

        dT_floor = np.zeros(n_hours)
        mask_floor = (cooling_allowed == 1) & (~np.isnan(Tin_hourly))

        dT_floor[mask_floor] = np.maximum(
            T_ground - Tin_hourly[mask_floor],
            0
        )

        Q_floor = U_floor * floor_area * dT_floor

        # --------------------------------------------------------
        # TOTAL LOAD
        # --------------------------------------------------------
        Q_total = Q_wall + Q_roof + Q_win + Q_floor

        Q_trans_cooling[b_id] = Q_total

    # ------------------------------------------------------------
    # FINAL CHECK
    # ------------------------------------------------------------
    b0 = list(building_geoms.keys())[0]

    print("\nSample building:", building_geoms[b0]["name"])
    print(" Max transmission (kW):", Q_trans_cooling[b0].max() / 1000)
    print(" First 24h:", Q_trans_cooling[b0][:24])

    print("\n✅ TRANSMISSION LOAD COMPLETE")

    return {"Q_transmission": Q_trans_cooling}
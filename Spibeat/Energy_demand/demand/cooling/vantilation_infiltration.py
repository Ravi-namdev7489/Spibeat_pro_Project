import os
import numpy as np
import pandas as pd
from .Building_Geometry import safe_float, load_csv_if_exists
from ..constants import RHO_AIR, C_A, P_ATM, H_WE
from pvlib.iotools import read_epw


def vantilation_and_infiltration(
    cooling_schedule,
    timestamps,
    building_geoms,
    USE_TYPE_FILE,
    EPW_File,
    ENVELOPE_DIR,
    persons_hourly
):

    print("\n🌬️ RUNNING VENTILATION & INFILTRATION (CELL 6 MATCH)")

    
    # ------------------------------------------------------------
    # STORAGE
    # ------------------------------------------------------------
    INF_m3_s = {}
    Q_inf_sensible_pos = {}
    Q_inf_latent_pos = {}
    Q_vent_sensible_pos = {}
    Q_vent_latent_pos = {}
    vent_flow_m3_s = {}

    # ------------------------------------------------------------
    # LOOP BUILDINGS
    # ------------------------------------------------------------
    for b_id, geom in building_geoms.items():


        volume_m3 = float(geom["volume_m3"])
        USE_TYPE=geom["use_type"]
        n_hours = len(timestamps)

        if not building_geoms:
            raise ValueError("❌ building_geoms is EMPTY")

        # ------------------------------------------------------------
        # WEATHER
        # ------------------------------------------------------------
        EPW_data, _ = read_epw(EPW_File)

        Tout = EPW_data["temp_air"].values
        RH_out = EPW_data["relative_humidity"].values / 100.0

        if len(Tout) != n_hours:
            raise ValueError("❌ EPW mismatch with timestamps")

        # ------------------------------------------------------------
        # USE TYPE
        # ------------------------------------------------------------
        use_df = pd.read_csv(USE_TYPE_FILE)
        use_df.columns = use_df.columns.str.strip()

        use_df["use_type"] = use_df["use_type"].str.strip().str.upper()
        USE_TYPE = USE_TYPE.strip().upper()

        use_row = use_df[use_df["use_type"] == USE_TYPE]

        if use_row.empty:
            raise ValueError(f"❌ USE_TYPE '{USE_TYPE}' not found")

        use_row = use_row.iloc[0]

        # ------------------------------------------------------------
        # SAME AS CELL 6: Cooling parameters
        # ------------------------------------------------------------
        SETPOINT_TEMP = safe_float(use_row.get("Tcs_set_C", 26.0), 26.0)
        SETBACK_TEMP = safe_float(use_row.get("Tcs_setb_C", 28.0), 28.0)
        Ve_lsp = safe_float(use_row.get("Ve_lsp", np.nan), np.nan)

        # ------------------------------------------------------------
        # SAME COOLING LOGIC AS CELL 6 (IMPORTANT)
        # ------------------------------------------------------------
        if USE_TYPE.upper() != "RES_LIG":

            cooling_allowed = (cooling_schedule == 1).astype(int)

            Tin_hourly = np.full(n_hours, np.nan)
            Tin_hourly[cooling_allowed == 1] = SETPOINT_TEMP

        else:
            cooling_allowed = np.zeros(n_hours)
            Tin_hourly = np.full(n_hours, np.nan)

        # ------------------------------------------------------------
        # Tightness (SAME AS CELL 6 SIMPLE VERSION)
        # ------------------------------------------------------------
        env_tight = load_csv_if_exists(
            os.path.join(ENVELOPE_DIR, "ENVELOPE_TIGHTNESS.csv")
        )

        ACH50 = 7.0
        ACH_infil = ACH50 / 20.0

        # ------------------------------------------------------------
        # Psychrometrics (SAME)
        # ------------------------------------------------------------
        def sat_vapor_pressure(T_C):
            return 610.94 * np.exp((17.625 * T_C) / (T_C + 243.04))

        def humidity_ratio_from_RH(T_C, RH):
            p_ws = sat_vapor_pressure(T_C)
            p_v = RH * p_ws
            return 0.622 * p_v / (P_ATM - p_v)

        W_out = np.array([
            humidity_ratio_from_RH(t, rh)
            for t, rh in zip(Tout, RH_out)
        ])

        persons = persons_hourly[b_id]
        

        # --------------------------------------------------------
        # INFILTRATION FLOW (SAME FORMULA)
        # --------------------------------------------------------
        INF_flow = (ACH_infil * volume_m3) / 3600.0
        INF_m3_s[b_id] = INF_flow

        # --------------------------------------------------------
        # SAME DELTA T LOGIC
        # --------------------------------------------------------
        dT = np.where(
            cooling_allowed == 1,
            np.maximum(Tout - Tin_hourly, 0),
            0
        )

        # --------------------------------------------------------
        # INFILTRATION SENSIBLE
        # --------------------------------------------------------
        Q_inf_sensible_pos[b_id] = RHO_AIR * C_A * INF_flow * dT

        # --------------------------------------------------------
        # INFILTRATION LATENT (SAME LOGIC)
        # --------------------------------------------------------
        W_in_hourly = humidity_ratio_from_RH(SETPOINT_TEMP, 0.50)

        mdot_inf = RHO_AIR * INF_flow

        Q_inf_latent = mdot_inf * H_WE * (W_out - W_in_hourly)

        Q_inf_latent_pos[b_id] = np.where(
            cooling_allowed == 1,
            np.maximum(Q_inf_latent, 0),
            0
        )

        # --------------------------------------------------------
        # VENTILATION FLOW (SAME LOGIC AS CELL 6)
        # --------------------------------------------------------
        if not np.isnan(Ve_lsp):
            vent_flow = persons * (Ve_lsp / 1000.0)
        else:
            ACH_vent = safe_float(use_row.get("ach", 0.5), 0.5)
            vent_flow = (ACH_vent * volume_m3) / 3600.0 * np.ones(n_hours)

        vent_flow_m3_s[b_id] = vent_flow

        # --------------------------------------------------------
        # VENTILATION SENSIBLE
        # --------------------------------------------------------
        Q_vent_sensible_pos[b_id] = RHO_AIR * C_A * vent_flow * dT

        # --------------------------------------------------------
        # VENTILATION LATENT
        # --------------------------------------------------------
        mdot_vent = RHO_AIR * vent_flow

        Q_vent_latent_pos[b_id] = np.where(
            cooling_allowed == 1,
            np.maximum(mdot_vent * H_WE * (W_out - W_in_hourly), 0),
            0
        )

        print(f"✔ {geom['name']} | INF = {INF_flow:.5f} m³/s")

    print("\n✅ VENTILATION COMPLETE (CELL 6 MATCHED)")

    return {
        "Tout": Tout,
        "RH_out": RH_out,
        "Tin_hourly": Tin_hourly,
        "cooling_allowed": cooling_allowed,
        "W_out": W_out,
        "INF_m3_s": INF_m3_s,
        "Q_inf_sensible_pos": Q_inf_sensible_pos,
        "Q_inf_latent_pos": Q_inf_latent_pos,
        "Q_vent_sensible_pos": Q_vent_sensible_pos,
        "Q_vent_latent_pos": Q_vent_latent_pos,
        "vent_flow_m3_s": vent_flow_m3_s
    }
# ============================================================
# MULTI-BUILDING AUXILIARY ELECTRICITY (CEA STYLE | 1 YEAR)
# ============================================================

import os
import numpy as np
import pandas as pd
import geopandas as gpd
import pvlib 
from .inputLocator import InputLocator
from pvlib.iotools import read_epw
from .constants import (RHO,G,ETA,FLOOR_HEIGHT_M,SIMULATION_YEAR)

def load_weather(epw_path):
    weather, meta = read_epw(epw_path)
    weather.index = weather.index.map(lambda t: t.replace(year=SIMULATION_YEAR))
    return  weather.index

def expand_schedule_year(col_name,timestamps,sched_df):
    out = np.zeros(len(timestamps))
    if col_name not in sched_df.columns:
        print(f"⚠ Column '{col_name}' not found in schedule → using zeros")
        return out

    for i, ts in enumerate(timestamps):
        hour_str = f"{ts.hour:02d}"
        if ts.weekday() < 5:
            key = f"Weekday_{hour_str}"
        elif ts.weekday() == 5:
            key = f"Saturday_{hour_str}"
        else:
            key = f"Sunday_{hour_str}"

        row_sched = sched_df[sched_df["hour"] == key]
        if not row_sched.empty:
            out[i] = float(row_sched.iloc[0][col_name])
        else:
            out[i] = 0.0
    return out


# LOAD EPW (FULL YEAR)
def run_aux_cal(locator,buildings):
    EPW_PATH  = locator.get_epw()
    USE_TYPES_CSV= locator.get_use_types()
    MONTHLY_MULT_CSV= locator.get_monthly_multiplier("AUX")
    SCHEDULE_DIR = locator.get_schedule_library()
    OUT_DIR=locator.get_output_folder("Auxialary")
    os.makedirs(OUT_DIR, exist_ok=True)
   
    
    # ------------------------------------------------------------
    # STORAGE
    aux_year = []
    
    # ============================================================
        # LOOP OVER BUILDINGS (DICT VERSION)
    for i, b in buildings.items():
        name= b.get("name")
        USE_TYPE= b.get("use_type")
        timestamps= load_weather(EPW_PATH)

 
    # ------------------------------------------------------------
        # LOAD USE TYPE DATA
        use_df = pd.read_csv(USE_TYPES_CSV)
        use_df.index = use_df["use_type"].str.upper().str.strip()
        row = use_df.loc[USE_TYPE]

        Epro_Wm2 = float(row["Epro_Wm2"])
        Ed_Wm2 = float(row["Ed_Wm2"])
        Occ_m2p = float(row["Occ_m2p"])
        Vw_ldp = float(row["Vw_ldp"])
        Vww_ldp = float(row["Vww_ldp"])

        # ------------------------------------------------------------
        # MONTHLY MULTIPLIER (FULL YEAR)
        monthly_df = pd.read_csv(MONTHLY_MULT_CSV, index_col=0)
        monthly_df.index = monthly_df.index.str.upper().str.strip()
        month_vals = monthly_df.loc[USE_TYPE].values.astype(float)

        month_mult_year = np.array([month_vals[t.month - 1] for t in timestamps])
        
        # ------------------------------------------------------------
        # LOAD SCHEDULE
        sched_df = pd.read_csv(os.path.join(SCHEDULE_DIR, f"{USE_TYPE}.csv"))
        sched_df.columns = sched_df.columns.str.lower().str.strip()
        sched_df["hour"] = sched_df["hour"].str.strip()
        
        sched_proc  = expand_schedule_year("processes",timestamps,sched_df)        # processes column
        sched_dc    = expand_schedule_year("servers",timestamps,sched_df)          # servers column
        sched_water = expand_schedule_year("electromobility",timestamps,sched_df)  # electromobility column

        # ----------------------------------------------------
        # GFA (floor area handling)
        A=b.get("floor_area")
        height=b.get("height")
        # ----------------------------------------------------
       
        # ----------------------------------------------------
        # HEIGHT
        # ----------------------------------------------------
      
        # ----------------------------------------------------
        # PEOPLE
        # ----------------------------------------------------
        people = A / Occ_m2p
        # --------------------------------------------------------
        # ELECTRICITY (FULL YEAR)
        Epro_W = Epro_Wm2 * A * sched_proc * month_mult_year
        Edc_W  = Ed_Wm2   * A * sched_dc   * month_mult_year

        Vfw_m3ph = (Vw_ldp  * people / 1000.0) / 24.0 * sched_water * month_mult_year
        Vww_m3ph = (Vww_ldp * people / 1000.0) / 24.0 * sched_water * month_mult_year

        Eaux_fw_W = (RHO * G * height * Vfw_m3ph / 3600.0) / ETA
        Eaux_ww_W = (RHO * G * height * Vww_m3ph / 3600.0) / ETA

        df_out = pd.DataFrame({
            "timestamps": timestamps,
            "Name":name,
            "Epro_kW": Epro_W / 1000.0,
            "Edc_kW": Edc_W / 1000.0,
            "Eaux_fw_kW": Eaux_fw_W / 1000.0,
            "Eaux_ww_kW": Eaux_ww_W / 1000.0,
        })

        df_out["Eaux_total_kW"] = df_out[
            ["Epro_kW", "Edc_kW", "Eaux_fw_kW", "Eaux_ww_kW"]
        ].sum(axis=1)
        df_out.to_csv(os.path.join(OUT_DIR, f"aux_{name}.csv"), index=False,   encoding="utf-8-sig")
        aux_year.append(df_out)
        print(f"✔ {name} auxiliary electricity saved")
    # ------------------------------------------------------------
    # TOTAL AUXILIARY (ALL BUILDINGS)
    total_df = pd.concat(aux_year).groupby("timestamps", as_index=False).sum()
    total_path = os.path.join(OUT_DIR, f"TOTAL_aux.csv")
    total_df.to_csv(total_path, index=False,   encoding="utf-8-sig")
    # ------------------------------------------------------------
    # PEAK CHECK
    peak_idx = total_df["Eaux_total_kW"].idxmax()
    print("\n=== PEAK AUXILIARY ELECTRICITY (ALL BUILDINGS) ===")
    print(f"Peak load : {total_df.loc[peak_idx, 'Eaux_total_kW']:.2f} kW")
    print(f"Hour      : {total_df.loc[peak_idx, 'timestamps']}")
    print(f"\n✔ TOTAL auxiliary electricity saved →")
    return OUT_DIR
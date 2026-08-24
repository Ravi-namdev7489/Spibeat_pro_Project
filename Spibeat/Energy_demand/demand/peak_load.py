import os
import pandas as pd
from .constants import SIMULATION_YEAR


def peak_load(locator):

    OUTPUT_DIR = locator.get_output_folder('peak load')
    Final_load = locator.get_final_total_output_dir()

    df = pd.read_csv(Final_load)

    # ============================================================
    # TIME COLUMN
    # ============================================================

    time_col = df.columns[0]
    df[time_col] = pd.to_datetime(df[time_col], errors="coerce")

    # ============================================================
    # DROP TOTAL COLUMN IF EXISTS
    # ============================================================

    last_col = df.columns[-1]
    if "total" in last_col.lower():
        df = df.drop(columns=[last_col])

    # ============================================================
    # BUILDING COLUMNS ONLY
    # ============================================================

    building_df = df.drop(columns=[time_col])

    # ============================================================
    # 🔥 BUILDING-WISE PEAK (WITH TIME)
    # ============================================================

    results = []

    for building in building_df.columns:

        # max value index
        idx = building_df[building].idxmax()

        peak_value = building_df.loc[idx, building]
        peak_time = df.loc[idx, time_col]

        results.append({
            "Building": building,
            "Peak_Load_kW": peak_value,
            "Peak_Time": peak_time
        })

    df_peak = pd.DataFrame(results)

    # ============================================================
    # SAVE FILE
    # ============================================================

    peak_output = os.path.join(
        OUTPUT_DIR,
        f"Building_Wise_Peak_{SIMULATION_YEAR}.csv"
    )

    df_peak.to_csv(peak_output, index=False)

    print("====================================")
    print("BUILDING WISE PEAK CALCULATED")
    print(df_peak)
    print("Saved at:", peak_output)
    print("====================================")

    return peak_output,df_peak
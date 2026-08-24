import os
import numpy as np
import pandas as pd
import geopandas as gpd
import pvlib

# ============================================================
# SCHEDULE HELPERS
# ============================================================

def load_schedule(schedule_dir, use_type):
    path = os.path.join(schedule_dir, f"{use_type}.csv")

    if not os.path.exists(path):
        raise FileNotFoundError(f"Schedule file not found: {path}")

    df = pd.read_csv(path)
    df.columns = df.columns.str.lower().str.strip()
    df["hour"] = df["hour"].astype(str).str.lower().str.strip()

    def extract(prefix):
        block = df[df["hour"].str.startswith(prefix)]
        if len(block) < 24:
            raise ValueError(f"{use_type}: {prefix} schedule incomplete")
        return block.iloc[:24].reset_index(drop=True)

    weekday = extract("weekday_")

    saturday = df[df["hour"].str.startswith("saturday_")]
    saturday = saturday.iloc[:24].reset_index(drop=True) if len(saturday) >= 24 else weekday.copy()

    sunday = df[df["hour"].str.startswith("sunday_")]
    sunday = sunday.iloc[:24].reset_index(drop=True) if len(sunday) >= 24 else weekday.copy()

    return {"weekday": weekday, "saturday": saturday, "sunday": sunday}


def expand_schedule_to_year(sched, timestamps):
    cols = [c for c in sched["weekday"].columns if c != "hour"]
    out = {c: np.zeros(len(timestamps)) for c in cols}

    for i, ts in enumerate(timestamps):
        h = ts.hour
        wd = ts.weekday()

        if wd < 5:
            row = sched["weekday"].iloc[h]
        elif wd == 5:
            row = sched["saturday"].iloc[h]
        else:
            row = sched["sunday"].iloc[h]

        for c in cols:
            try:
                out[c][i] = float(row[c])
            except:
                out[c][i] = 0.0

    return out


# ============================================================
# MAIN SERVICE FUNCTION (CEA STYLE)
# ============================================================

def run_ea_el( locator, buildings):

    use_types_csv = locator.get_use_types()
    monthly_mult_csv = locator.get_monthly_multiplier("EaEl")
    schedule_dir = locator.get_schedule_library()
    out_dir = locator.get_output_folder("Ea_El")
    os.makedirs(out_dir, exist_ok=True)
    print("📁 Output directory:", out_dir)

   

    combined_results = []

    # ------------------------------------------------------------
    # BUILDING LOOP
    # ------------------------------------------------------------
    for i, b in buildings.items():
        name = b.get("name")
        use_type=b.get("use_type").upper()
        weather_data = locator.load_weather()
        timestamps=weather_data['weather_index']
        # ------------------------------------------------------------
        # USE TYPE DATA
        # ------------------------------------------------------------
        use_df = pd.read_csv(use_types_csv)
        use_df.index = use_df["use_type"].str.upper().str.strip()

        use_row = use_df.loc[use_type.upper()]

        Ea_Wm2 = float(use_row["Ea_Wm2"])
        El_Wm2 = float(use_row["El_Wm2"])

        # ------------------------------------------------------------
        # MONTHLY MULTIPLIERS
        # ------------------------------------------------------------
        monthly_df = pd.read_csv(monthly_mult_csv, index_col=0)
        monthly_df.index = monthly_df.index.str.upper().str.strip()

        monthly_vals = monthly_df.loc[use_type.upper()].values[:12].astype(float)

        month_mult = np.array([monthly_vals[t.month - 1] for t in timestamps])

        # ------------------------------------------------------------
        # SCHEDULE
        # ------------------------------------------------------------
        sched = load_schedule(schedule_dir, use_type)
        sched_year = expand_schedule_to_year(sched, timestamps)

        sched_app = sched_year["appliances"]
        sched_lig = sched_year["lighting"]
        area = float(b.get("floor_area"))
        Ea_W = Ea_Wm2 * area * sched_app * month_mult
        El_W = El_Wm2 * area * sched_lig * month_mult
        df = pd.DataFrame({
            "timestamps": timestamps,
            "Name": name,
            "Ea_kW": Ea_W / 1000.0,
            "El_kW": El_W / 1000.0,
        })

        # =========================================================
        # ✅ CLEAN NUMERIC OUTPUT (MAIN FIX)
        # =========================================================
        df["Ea_kW"] = df["Ea_kW"].round(6).astype(float)
        df["El_kW"] = df["El_kW"].round(6).astype(float)

        combined_results.append(df)

        # Save individual file
        df.to_csv(
            os.path.join(out_dir, f"Ea_El_FULL_YEAR_{name}.csv"),
            index=False,
            float_format="%.6f"
        )

        print('building', name)
    # ------------------------------------------------------------
    # COMBINED FILE
    # ------------------------------------------------------------
    combined_df = pd.concat(combined_results, ignore_index=True)

    output_csv = os.path.join(
        out_dir,
        "ALL_BUILDINGS_Ea_El_FULL_YEAR.csv"
    )

    combined_df.to_csv(
        output_csv,
        index=False,
        float_format="%.6f"
    )

    return out_dir
import os
import pandas as pd


def final_total_demand(TOTAL_LOAD, locator):

    # ============================================================
    # OUTPUT DIR
    # ============================================================
    epw_file = locator.get_epw()
    OUTPUT_DIR = locator.get_output_folder("Final_total_load_yearly")
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    TOTAL_LOAD_DIR = TOTAL_LOAD

    if os.path.isfile(TOTAL_LOAD_DIR):
        TOTAL_LOAD_DIR = os.path.dirname(TOTAL_LOAD_DIR)

    # ============================================================
    # MASTER TIMESTAMPS (SAFE)
    # ============================================================
    weather_data = locator.load_weather()
    timestamps=weather_data['weather_index']
    timestamp_index = pd.to_datetime(timestamps).floor("H")

    YEAR = timestamp_index[0].year

    # ============================================================
    # FIND FILES
    # ============================================================
    all_files = os.listdir(TOTAL_LOAD_DIR)

    files = [
        f for f in all_files
        if f.endswith(".csv") and "TOTAL_LOAD" in f
    ]

    files = sorted(files)

    if not files:
        raise ValueError("❌ No valid TOTAL_LOAD files found")

    print(f"✔ Found {len(files)} building files")

    # ============================================================
    # BUILDING DATA STORAGE
    # ============================================================
    building_dict = {}

    # ============================================================
    # PROCESS EACH FILE
    # ============================================================
    for f in files:

        file_path = os.path.join(TOTAL_LOAD_DIR, f)

        # ========================================================
        # FIX 1: SAFE BUILDING NAME EXTRACTION
        # ========================================================
        building_name = (
            f.replace("TOTAL_LOAD_REQUIRED_", "")
             .replace("_FULL_YEAR.csv", "")
             .replace(".csv", "")
        )

        print(f"🔹 Processing {building_name}")

        df = pd.read_csv(file_path)

        # ========================================================
        # COLUMN VALIDATION + SAFETY
        # ========================================================
        df.columns = df.columns.str.strip()

        if "timestamp" not in df.columns:
            raise ValueError(f"❌ Missing timestamp in {file_path}")

        if "TOTAL_LOAD_kW" not in df.columns:
            raise ValueError(f"❌ Missing TOTAL_LOAD_kW in {file_path}")

        # ========================================================
        # TIMESTAMP CLEANING
        # ========================================================
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        df = df.dropna(subset=["timestamp"])

        # FIX: avoid duplicate loss → SUM instead of drop
        df = df.groupby("timestamp", as_index=False).sum()

        df = df.set_index("timestamp")

        # ========================================================
        # ALIGN TO MASTER TIMESTAMPS
        # ========================================================
        series = df["TOTAL_LOAD_kW"].reindex(
            timestamp_index,
            fill_value=0
        )

        building_dict[building_name] = series.values

    # ============================================================
    # FINAL HOURLY DATAFRAME
    # ============================================================
    df_total = pd.DataFrame(building_dict)
    df_total.insert(0, "timestamp", timestamp_index)

    # System total load
    df_total["Total_Load_DT3_kW"] = df_total.drop(
        columns=["timestamp"]
    ).sum(axis=1)

    # ============================================================
    # SAVE HOURLY FILE
    # ============================================================
    hourly_output = os.path.join(
        OUTPUT_DIR,
        f"Total_Load_DT3_FULL_YEAR_{YEAR}.csv"
    )

    df_total.to_csv(hourly_output, index=False)

    print("\n====================================")
    print("✅ TOTAL LOAD FILE CREATED")
    print("📄 Hours:", len(df_total))
    print("📁 Saved:", hourly_output)
    print("====================================")

    # ============================================================
    # YEARLY ENERGY PER BUILDING
    # ============================================================
    yearly_totals = df_total.drop(
        columns=["timestamp", "Total_Load_DT3_kW"]
    ).sum()

    df_yearly = yearly_totals.reset_index()
    df_yearly.columns = ["Building", "Yearly_Energy_kWh"]

    yearly_output = os.path.join(
        OUTPUT_DIR,
        f"Building_Wise_Total_Load_{YEAR}.csv"
    )
    df_yearly.to_csv(yearly_output, index=False)

    print("\n====================================")
    print("🏢 BUILDING-WISE YEARLY TOTAL CREATED")
    print("📁 Saved:", yearly_output)
    print("====================================")

    return OUTPUT_DIR
import os
import pandas as pd


def total_demand( locator):
    EAEL_DIR = locator.get_ea_el_output_dir()
    DHW_DIR = locator.get_hotwater_output_dir()
    AUX_DIR = locator.get_aux_output_dir()
    COOL_DIR = locator.get_cooling_output_dir()

    OUT_DIR = locator.get_output_folder("Total_Demand_Load_Buinding_wise_yearly")
    os.makedirs(OUT_DIR, exist_ok=True)
    # ============================================================
    # 🔥 COOLING FILES
    # ============================================================
    cool_files = [
        f for f in os.listdir(COOL_DIR)
        if f.endswith(".csv")
    ]

    print(f"\nBuildings found: {len(cool_files)}")

    # ============================================================
    # LOOP BUILDINGS
    # ============================================================
    for f in cool_files:

        # --------------------------------------------------------
        # FIX 1: SAFE BUILDING NAME EXTRACTION
        # --------------------------------------------------------
        if "_DHW_YEAR" in f:
            continue

        name = f.replace(".csv", "").replace("HVAC_hourly_YEAR_", "")
        name = name.replace("cooling_hourly_", "").replace("HVAC_", "")

        print(f"\n🔹 Processing {name}")

        # ========================================================
        # COOLING
        # ========================================================
        cool_path = os.path.join(COOL_DIR, f)
        df_cool = pd.read_csv(cool_path)

        df_cool = df_cool.rename(columns={
            "timestamps": "timestamp",
            "HVAC_required_kW": "cooling_kW"
        })

        if "timestamp" not in df_cool.columns:
            df_cool["timestamp"] = df_cool.index

        df_cool = df_cool[["timestamp", "cooling_kW"]]

        timestamps = df_cool["timestamp"]

        # ========================================================
        # AUX
        # ========================================================
        aux_file = next(
            (x for x in os.listdir(AUX_DIR) if x.startswith(f"aux_{name}")),
            None
        )

        if not aux_file:
            print(f"❌ AUX file missing for {name}")
            continue

        df_aux = pd.read_csv(os.path.join(AUX_DIR, aux_file))

        df_aux = df_aux.rename(columns={
            "Eaux_total_kW": "aux_kW"
        })

        df_aux["timestamp"] = timestamps.values
        df_aux = df_aux[["timestamp", "aux_kW"]]

        # ========================================================
        # DHW (HOT WATER FIXED)
        # ========================================================
        dhw_file = os.path.join(DHW_DIR, f"{name}_DHW_YEAR.csv")

        if not os.path.exists(dhw_file):
            print(f"❌ DHW file missing for {name}")
            continue

        df_dhw = pd.read_csv(dhw_file)

        df_dhw = df_dhw.rename(columns={
            "DHW_el_kWh": "dhw_kW",
            "timestamps": "timestamp"
        })

        if "timestamp" not in df_dhw.columns:
            df_dhw["timestamp"] = timestamps.values

        df_dhw = df_dhw[["timestamp", "dhw_kW"]]

        # ========================================================
        # EA / EL
        # ========================================================
        eael_file = os.path.join(EAEL_DIR, f"Ea_El_FULL_YEAR_{name}.csv")

        if not os.path.exists(eael_file):
            print(f"❌ EA/EL file missing for {name}")
            continue

        df_eael = pd.read_csv(eael_file)

        df_eael = df_eael.rename(columns={
            "Ea_kW": "ea_kW",
            "El_kW": "el_kW"
        })

        df_eael["timestamp"] = timestamps.values
        df_eael = df_eael[["timestamp", "ea_kW", "el_kW"]]

        # ========================================================
        # MERGE (SAFE JOIN)
        # ========================================================
        df_total = df_cool.merge(df_aux, on="timestamp", how="left") \
                         .merge(df_dhw, on="timestamp", how="left") \
                         .merge(df_eael, on="timestamp", how="left") \
                         .fillna(0)

        # ========================================================
        # TOTAL LOAD
        # ========================================================
        df_total["TOTAL_LOAD_kW"] = (
            df_total["cooling_kW"]
            + df_total["aux_kW"]
            + df_total["dhw_kW"]
            + df_total["ea_kW"]
            + df_total["el_kW"]
        )

        # ========================================================
        # SAVE OUTPUT
        # ========================================================
        out_csv = os.path.join(
            OUT_DIR,
            f"TOTAL_LOAD_REQUIRED_{name}_FULL_YEAR.csv"
        )

        df_total.to_csv(out_csv, index=False)

        print(f"✔ Saved {out_csv}")

    print("\n🎉 ALL BUILDINGS FULL YEAR TOTAL LOAD CREATED")

    return OUT_DIR
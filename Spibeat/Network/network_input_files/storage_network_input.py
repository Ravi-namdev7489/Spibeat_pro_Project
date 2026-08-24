
def generate_storage_generators(OUTPUT_DIR,BASE_DIR):
    import os
    import pandas as pd

    # -------------------------------------------------
    # PATHS
    # -------------------------------------------------

    IN_CSV = os.path.join(BASE_DIR, "Input_1.csv")
    OUT_CSV = os.path.join(OUTPUT_DIR, "generators.csv")

    # -------------------------------------------------
    # READ INPUT
    # -------------------------------------------------
    df = pd.read_csv(IN_CSV)
    df.columns = df.columns.str.strip()

    # -------------------------------------------------
    # CLEAN NUMERIC
    # -------------------------------------------------
    df["Inst_Gen"] = pd.to_numeric(df["Inst_Gen"], errors="coerce").fillna(0.0)
    df["Efficiency"] = pd.to_numeric(df["Efficiency"], errors="coerce").fillna(1.0)

    # -------------------------------------------------
    # COST DATABASE
    # -------------------------------------------------
    cost_data = {
    "coal": {
        "marginal_cost": 5000,
        "capital_cost": 15000000
    },

    "nuclear": {
        "marginal_cost": 2800,
        "capital_cost": 100000000
    },

    "wind": {
        "marginal_cost": 500,
        "capital_cost": 60000000
    },

    "solar": {
        "marginal_cost": 0,
        "capital_cost": 500000
    }
}

    # -------------------------------------------------
    # CREATE GENERATORS
    # -------------------------------------------------
    generators = []
    gen_id = 1

    for _, r in df.iterrows():

        if r["Inst_Gen"] <= 0:
            continue

        raw_type = str(r["type"]).lower().replace("\n", " ").strip()

        if "substation" not in raw_type:
            continue

        name = str(r["Name"]).strip()
        pv = float(r["Pri_Voltag"])
        bus_name = f"{name}_{int(pv)}"

        carrier = str(r["car_Gen"]).strip().lower()

        generators.append({
            "name": f"G{gen_id}",
            "bus": bus_name,
            "p_nom": float(r["Inst_Gen"]),
            "carrier": carrier,
            "efficiency": float(r["Efficiency"]),
            "marginal_cost": cost_data.get(carrier, {}).get("marginal_cost", 0),
            "capital_cost": cost_data.get(carrier, {}).get("capital_cost", 0),
            "p_nom_extendable": True
        })

        gen_id += 1

    # -------------------------------------------------
    # ADD SOLAR GENERATORS
    # -------------------------------------------------
    solar_config = {
        "DT6_415": 0.0004,
        "DT8_415": 0.0004
    }

    for i, (bus, pnom) in enumerate(solar_config.items(), start=1):
        generators.append({
            "name": f"Solar_DT{i}",
            "bus": bus,
            "p_nom": pnom,
            "carrier": "solar",
            "efficiency": 0.8,
            "marginal_cost": 0,
            "capital_cost": 500000,
            "p_nom_extendable": True
        })

    # -------------------------------------------------
    # DATAFRAME
    # -------------------------------------------------
    gen_df = pd.DataFrame(generators)
    print("p not ",gen_df["p_nom"])

    # -------------------------------------------------
    # SAVE CSV
    # -------------------------------------------------
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    if gen_df.empty:
        print("⚠ No generators created — check Inst_Gen column")

    gen_df.to_csv(OUT_CSV, index=False)

    # -------------------------------------------------
    # RETURN FOR FRONTEND ✅
    # -------------------------------------------------
    return {
        "status": "success" if not gen_df.empty else "empty",
        "file_path": OUT_CSV,
        "count": len(gen_df),
        "columns": list(gen_df.columns),
        "data": gen_df.to_dict(orient="records")
    }
import pandas as pd
import os  
def generate_storage_units_data(OUTPUT_DIR):
    # -------------------------------------------------
    # PATHS
    # -------------------------------------------------
    GEN_CSV = os.path.join(OUTPUT_DIR, "generators.csv")
    OUT_CSV = os.path.join(OUTPUT_DIR, "storage_units.csv")

    # -------------------------------------------------
    # READ GENERATORS
    # -------------------------------------------------
    gen_df = pd.read_csv(GEN_CSV)
    gen_df.columns = gen_df.columns.str.strip()

    # -------------------------------------------------
    # CLEAN CARRIER COLUMN
    # -------------------------------------------------
    gen_df["carrier"] = (
        gen_df["carrier"]
        .astype(str)
        .str.strip()
        .str.lower()
    )

    # -------------------------------------------------
    # FILTER SOLAR BUSES
    # -------------------------------------------------
    solar_df = gen_df[gen_df["carrier"] == "solar"].copy()

    if solar_df.empty:
        return {
            "status": "error",
            "message": "No solar generators found",
            "data": []
        }

    solar_buses = solar_df["bus"].unique().tolist()

    # -------------------------------------------------
    # STORAGE CONFIGURATION
    # -------------------------------------------------
    storage_config = {
        "DT8_415": "Battery1",
        "DT6_415": "Battery2"
    }

    # -------------------------------------------------
    # STORAGE PARAMETERS
    # -------------------------------------------------
    storage_costs = {

        "Battery1": {
            "p_nom": 0.0003,
            "marginal_cost": 100,
            "capital_cost": 8125000,
            "efficiency_store": 0.8,
            "efficiency_dispatch": 0.8,
            "max_hours": 4
        },

        "Battery2": {
            "p_nom": 0.0003,
            "marginal_cost": 100,
            "capital_cost": 100000000,
            "efficiency_store": 0.8,
            "efficiency_dispatch": 0.8,
            "max_hours": 4
        }
    }

    # -------------------------------------------------
    # CREATE STORAGE UNITS
    # -------------------------------------------------
    storage_units = []

    for bus, storage_type in storage_config.items():

        if bus not in solar_buses:
            print(f"⚠ {bus} not found among solar buses")
            continue

        params = storage_costs[storage_type]

        storage_units.append({
            "name": f"{storage_type.replace(' ', '_')}_{bus}",
            "bus": bus,
            "type": storage_type,
            "control": "PQ",

            "p_nom": params["p_nom"],
            "p_nom_extendable": True,
            "p_min_pu": -1,
            "p_max_pu": 1,

            "max_hours": params["max_hours"],

            "marginal_cost": params["marginal_cost"],
            "capital_cost": params["capital_cost"],

            "state_of_charge_initial": params["p_nom"] * 0.01,

            "cyclic_state_of_charge": False,
            "cyclic_state_of_charge_per_period": False,

            "efficiency_store": params["efficiency_store"],
            "efficiency_dispatch": params["efficiency_dispatch"],

            "standing_loss": 0.001,
            "inflow": 0
        })

    # -------------------------------------------------
    # DATAFRAME
    # -------------------------------------------------
    storage_df = pd.DataFrame(storage_units)

    # -------------------------------------------------
    # SAVE CSV
    # -------------------------------------------------
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    storage_df.to_csv(OUT_CSV, index=False)

    # -------------------------------------------------
    # RETURN FOR FRONTEND ✅
    # -------------------------------------------------
    return {
        "status": "success" if not storage_df.empty else "empty",
        "file_path": OUT_CSV,
        "count": len(storage_df),
        "columns": list(storage_df.columns),
        "data": storage_df.to_dict(orient="records")
    }
def generate_storage_carriers(OUTPUT_DIR):
       

    # -------------------------------------------------
    # PATHS
    # -------------------------------------------------
    GEN_CSV = os.path.join(OUTPUT_DIR, "generators.csv")
    OUT_CSV = os.path.join(OUTPUT_DIR, "carriers.csv")

    # -------------------------------------------------
    # READ GENERATORS
    # -------------------------------------------------
    gen_df = pd.read_csv(GEN_CSV)
    gen_df.columns = gen_df.columns.str.strip()

    # -------------------------------------------------
    # CLEAN carrier COLUMN
    # -------------------------------------------------
    gen_df["carrier"] = (
        gen_df["carrier"]
        .astype(str)
        .str.strip()
    )

    # -------------------------------------------------
    # GET UNIQUE CARRIERS
    # -------------------------------------------------
    present_carriers = gen_df["carrier"].unique()

    # -------------------------------------------------
    # CO2 EMISSION DATABASE
    # -------------------------------------------------
    co2_data = {
        "gas": 0.25,
        "coal": 0.9,
        "nuclear": 0,
        "wind": 0,
        "solar": 0,
        "biomass": 0.03
    }

    # -------------------------------------------------
    # CREATE carriers DATA
    # -------------------------------------------------
    carrier_rows = []

    for carrier in present_carriers:
        carrier_rows.append({
            "name": carrier,
            "co2_emissions": co2_data.get(str(carrier).lower(), 0)
        })

    # -------------------------------------------------
    # DATAFRAME
    # -------------------------------------------------
    carrier_df = pd.DataFrame(carrier_rows)

    # -------------------------------------------------
    # SAVE CSV
    # -------------------------------------------------
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    carrier_df.to_csv(OUT_CSV, index=False)

    # -------------------------------------------------
    # RETURN FOR FRONTEND ✅
    # -------------------------------------------------
    return {
        "status": "success" if not carrier_df.empty else "empty",
        "file_path": OUT_CSV,
        "count": len(carrier_df),
        "columns": list(carrier_df.columns),
        "data": carrier_df.to_dict(orient="records")
    }
def generate_storage_loads( OUTPUT_DIR):
    import pandas as pd
    import os
    # -------------------------------------------------
    # PATHS
    # -------------------------------------------------
    BUSES_CSV = os.path.join(OUTPUT_DIR, "buses.csv")
    OUT_CSV = os.path.join(OUTPUT_DIR, "Loads.csv")
    # -------------------------------------------------
    # READ BUS FILE
    # -------------------------------------------------
    buses_df = pd.read_csv(BUSES_CSV)
    buses_df.columns = buses_df.columns.str.strip()

    # -------------------------------------------------
    # CREATE LOADS
    # -------------------------------------------------
    loads = []
    load_id = 1

    for _, r in buses_df.iterrows():

        bus_name = str(r["name"]).strip()

        # ONLY LV BUSES (_415)
        if not bus_name.endswith("_415"):
            continue

        loads.append({
            "name": f"Load{load_id}",
            "bus": bus_name,
            "carrier": "AC",
            "p_set": 0.05   # default load
        })

        load_id += 1

    # -------------------------------------------------
    # DATAFRAME
    # -------------------------------------------------
    loads_df = pd.DataFrame(loads)

    # -------------------------------------------------
    # SAVE CSV
    # -------------------------------------------------
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    if loads_df.empty:
        print("⚠ No loads created — check buses.csv")

    loads_df.to_csv(OUT_CSV, index=False)

    # -------------------------------------------------
    # RETURN FOR FRONTEND ✅
    # -------------------------------------------------
    return {
        "status": "success" if not loads_df.empty else "empty",
        "file_path": OUT_CSV,
        "count": len(loads_df),
        "columns": list(loads_df.columns),
        "data": loads_df.to_dict(orient="records")
    }
import pandas as pd
import numpy as np
import os

# --------------------------------------------------
# FUNCTION: CREATE P_MAX_PU
# --------------------------------------------------

def generate_storage_pmax_pu(OUTPUT_DIR,BASE_DIR):
    
    ts_csv   = os.path.join(BASE_DIR, "timeseries_input.csv")
    gen_csv  = os.path.join(OUTPUT_DIR, "generators.csv")
    out_pmax = os.path.join(OUTPUT_DIR, "generators-p_max_pu.csv")
    # -------------------------------
    # LOAD TIME SERIES
    # -------------------------------
    ts_df = pd.read_csv(ts_csv)
    ts_df.columns = ts_df.columns.str.strip()
    time_col = ts_df.columns[0]
    snapshots = pd.to_datetime(ts_df[time_col], errors="raise")

    print(f"✔ Loaded {len(snapshots)} snapshots")

    # -------------------------------
    # LOAD GENERATORS
    # -------------------------------
    gen_df = pd.read_csv(gen_csv)
    gen_df.columns = gen_df.columns.str.strip()

    active_gens = gen_df.loc[
        gen_df["p_nom"].notna() & (gen_df["p_nom"] > 0),
        "name"
    ].tolist()

    if not active_gens:
        raise ValueError("❌ No active generators found")

    print("✔ Active generators:", active_gens)

    # -------------------------------
    # SOLAR PROFILE
    # -------------------------------
    solar_profile_24h = [
        0,0,0,0,0,0,0,
        0.007,0.203,0.432,0.594,0.696,
        0.745,0.745,0.68,0.59,0.448,
        0.23,0.018,0,0,0,0,0
    ]

    n_snapshots = len(snapshots)
    solar_series = np.tile(
        solar_profile_24h,
        int(np.ceil(n_snapshots / 24))
    )[:n_snapshots]

    # -------------------------------
    # OPTIONAL EXTRA SOLAR
    # -------------------------------
    extra_solar_gens = ["Solar_DT1"]

    all_gens = list(set(active_gens + extra_solar_gens))

    # -------------------------------
    # BUILD P_MAX_PU
    # -------------------------------
    pmax_df = pd.DataFrame({"snapshot": snapshots})

    for g in all_gens:
        if "Solar" in g:
            pmax_df[g] = solar_series
        else:
            pmax_df[g] = 1.0

    pmax_df.to_csv(out_pmax, index=False)
    return {
            "status": "success" if not pmax_df.empty else "empty",
            "count": len(pmax_df),
            "columns": list(pmax_df.columns),
            "data": pmax_df.to_dict(orient="records")
        }
# --------------------------------------------------
# CALL FUNCTION
# --------------------------------------------------



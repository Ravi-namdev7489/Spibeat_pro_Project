import pandas as pd
import os

def generate_buses_data(Input_Dir,Output_Dir):
    # -------------------------------------------------
    # FIXED PATHS (same as your script)
    # -------------------------------------------------
    IN_CSV = os.path.join(Input_Dir, "Input_1.csv")
    OUT_CSV = os.path.join(Output_Dir, "buses.csv")
    # -------------------------------------------------
    # READ INPUT
    # -------------------------------------------------
    df = pd.read_csv(IN_CSV)
    df.columns = df.columns.str.strip()

    rows = []

    # -------------------------------------------------
    # LOOP
    # -------------------------------------------------
    for _, r in df.iterrows():

        name = str(r["Name"]).strip()
        y, x = r["y"], r["x"]
        carrier = r["carrier"]

        pv = float(r["Pri_Voltag"])
        sv = float(r["Sec_Voltag"])

        raw_type = str(r["type"]).lower()
        raw_type = raw_type.replace("\r", " ").replace("\n", " ").strip()

        # ---------------- SUBSTATION ----------------
        if "substation" in raw_type:

            rows.append({
                "name": f"{name}_{int(pv)}",
                "y": y,
                "x": x,
                "v_nom": pv,
                "type": "Substation",
                "carrier": carrier,
                "osm_name": f"{name}_{int(pv)}",
                "control": None
            })

            rows.append({
                "name": f"{name}_{int(sv)}",
                "y": y,
                "x": x,
                "v_nom": sv,
                "type": "Substation",
                "carrier": carrier,
                "osm_name": f"{name}_{int(sv)}",
                "control": "PV"
            })

        # ---------------- FEEDER ----------------
        elif "feeder" in raw_type:

            rows.append({
                "name": f"{name}_11",
                "y": y,
                "x": x,
                "v_nom": pv,
                "type": name,
                "carrier": carrier,
                "osm_name": name,
                "control": "PV"
            })

            rows.append({
                "name": f"{name}_415",
                "y": y,
                "x": x,
                "v_nom": sv,
                "type": name,
                "carrier": carrier,
                "osm_name": name,
                "control": "PQ"
            })

    # -------------------------------------------------
    # DATAFRAME
    # -------------------------------------------------
    out_df = pd.DataFrame(rows)

    if out_df.empty:
        raise ValueError("No buses created — check input file")

    # -------------------------------------------------
    # SLACK LOGIC
    # -------------------------------------------------
    substations = out_df[out_df["type"] == "Substation"]
    slack_idx = substations["v_nom"].idxmax()

    out_df.loc[slack_idx, "control"] = "Slack"

    out_df.loc[
        (out_df.index != slack_idx) &
        (out_df["v_nom"] > 1) &
        (out_df["control"].isna()),
        "control"
    ] = "PV"

    # -------------------------------------------------
    # FINAL ORDER
    # -------------------------------------------------
    out_df = out_df[
        ["name", "y", "x", "v_nom", "type", "carrier", "osm_name", "control"]
    ]

    # -------------------------------------------------
    # SAVE CSV (same path)
    # -------------------------------------------------
    os.makedirs(Output_Dir, exist_ok=True)
    out_df.to_csv(OUT_CSV, index=False)

    # -------------------------------------------------
    # RETURN JSON
    # -------------------------------------------------
    return {
        "status": "success",
        "file_path": OUT_CSV,
        "columns": out_df.columns.tolist(),
        "data": out_df.to_dict(orient="records")
    }
def generate_generators_data(Input_Dir,Output_Dir):
    # -------------------------------------------------
    # FIXED PATHS (same as your script)
    # -------------------------------------------------
   
    IN_CSV = os.path.join(Input_Dir, "Input_1.csv")

    
    OUT_CSV = os.path.join(Output_Dir, "generators.csv")

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
    # CREATE GENERATORS
    # -------------------------------------------------
    generators = []
    gen_id = 1

    for _, r in df.iterrows():

        # skip if no generation
        if r["Inst_Gen"] <= 0:
            continue

        name = str(r["Name"]).strip()
        pv = float(r["Pri_Voltag"])

        raw_type = str(r["type"]).lower()
        raw_type = raw_type.replace("\r", " ").replace("\n", " ").strip()

        # only substations
        if "substation" not in raw_type:
            continue

        bus_name = f"{name}_{int(pv)}"

        generators.append({
            "name": f"G{gen_id}",
            "bus": bus_name,
            "p_nom": float(r["Inst_Gen"]),
            "carrier": str(r["car_Gen"]).strip(),
            "efficiency": float(r["Efficiency"]),
            "p_nom_extendable": False
        })

        gen_id += 1

    # -------------------------------------------------
    # DATAFRAME
    # -------------------------------------------------
    gen_df = pd.DataFrame(generators)

    # -------------------------------------------------
    # SAVE CSV
    # -------------------------------------------------
    os.makedirs(Output_Dir, exist_ok=True)

    if gen_df.empty:
        print("⚠ No generators created — check Inst_Gen column")
        gen_df.to_csv(OUT_CSV, index=False)  # still create empty file
    else:
        gen_df.to_csv(OUT_CSV, index=False)

    # -------------------------------------------------
    # RETURN JSON
    # -------------------------------------------------
    return {
        "status": "success",
        "file_path": OUT_CSV,
        "columns": list(gen_df.columns),
        "data": gen_df.to_dict(orient="records")
    }
import pandas as pd
import os


def generate_loads_data(Input_Dir,Output_Dir):
    # -------------------------------------------------
    # FIXED PATHS (same as your script)
    # -------------------------------------------------

    IN_CSV = os.path.join(Input_Dir, "Input_1.csv")
    GEN_CSV = os.path.join(Output_Dir, "generators.csv")
    BUSES_CSV = os.path.join(Output_Dir, "buses.csv")
    OUT_CSV = os.path.join(Output_Dir, "Loads.csv")

    # -------------------------------------------------
    # READ FILES
    # -------------------------------------------------
    inp_df = pd.read_csv(IN_CSV)
    buses_df = pd.read_csv(BUSES_CSV)
    gens_df = pd.read_csv(GEN_CSV)

    # Clean column names
    inp_df.columns = inp_df.columns.str.strip()
    buses_df.columns = buses_df.columns.str.strip()
    gens_df.columns = gens_df.columns.str.strip()

    # -------------------------------------------------
    # CLEAN TYPE COLUMN
    # -------------------------------------------------
    inp_df["type_clean"] = (
        inp_df["type"]
        .astype(str)
        .str.lower()
        .str.replace("\r", " ", regex=False)
        .str.replace("\n", " ", regex=False)
        .str.strip()
    )

    # -------------------------------------------------
    # IDENTIFY LOAD NODES (Feeders / DTs)
    # -------------------------------------------------
    load_nodes = inp_df.loc[
        inp_df["type_clean"].str.contains("feeder"),
        "Name"
    ].astype(str).str.strip()

    load_nodes = set(load_nodes)

    # -------------------------------------------------
    # IDENTIFY GENERATOR BUSES
    # -------------------------------------------------
    generator_buses = set(gens_df["bus"])

    # -------------------------------------------------
    # CREATE LOADS
    # -------------------------------------------------
    loads = []
    load_id = 1

    for _, r in buses_df.iterrows():

        bus_name = r["name"]

        # Skip generator buses
        if bus_name in generator_buses:
            continue

        # Only LV buses (_415)
        if not str(bus_name).endswith("_415"):
            continue

        # Parent feeder/DT name
        parent_name = bus_name.rsplit("_", 1)[0]

        if parent_name not in load_nodes:
            continue

        loads.append({
            "name": f"Load{load_id}",
            "bus": bus_name,
            "carrier": "AC"
        })

        load_id += 1

    loads_df = pd.DataFrame(loads)

    # -------------------------------------------------
    # SAVE CSV
    # -------------------------------------------------
    os.makedirs(Output_Dir, exist_ok=True)
    loads_df.to_csv(OUT_CSV, index=False)

    # -------------------------------------------------
    # RETURN JSON
    # -------------------------------------------------
    return {
        "status": "success",
        "file_path": OUT_CSV,
        "columns":loads_df.columns.tolist(),
        "data": loads_df.to_dict(orient="records")
    }
import pandas as pd
import os

import pandas as pd
import os


def generate_transformers(Input_Dir,Output_Dir):
    # -------------------------------------------------
    # PATHS (UNCHANGED)
    # -------------------------------------------------
    
    IN_CSV = os.path.join(Input_Dir, "Input_1.csv")
    OUT_TRANSFORMERS = os.path.join(Output_Dir, "transformers.csv")
    # -------------------------------------------------
    # READ INPUT
    # -------------------------------------------------
    df = pd.read_csv(IN_CSV)
    df.columns = df.columns.str.strip()

    df["type_clean"] = (
        df["type"]
        .astype(str)
        .str.lower()
        .str.replace("\r", " ", regex=False)
        .str.replace("\n", " ", regex=False)
        .str.strip()
    )

    PARAM_MAP = {
        (220, 33):  {"x_pu": 0.011, "r_pu": 0.005},
        (33, 11):   {"x_pu": 0.011, "r_pu": 0.008},
        (11, 0.415):{"x_pu": 0.010, "r_pu": 0.010},
    }

    transformers = []

    for _, r in df.iterrows():

        name = str(r["Name"]).strip()
        pv = float(r["Pri_Voltag"])
        sv = float(r["Sec_Voltag"])

        key = (pv, sv)
        if key not in PARAM_MAP:
            continue

        params = PARAM_MAP[key]

        if "substation" in r["type_clean"]:
            tf_name = f"{name}_TF1"
            bus0 = f"{name}_{int(pv)}"
            bus1 = f"{name}_{int(sv)}"

        elif "feeder" in r["type_clean"]:
            tf_name = name
            bus0 = f"{name}_11"
            bus1 = f"{name}_415"

        else:
            continue

        transformers.append({
            "name": tf_name,
            "bus0": bus0,
            "bus1": bus1,
            "s_nom": float(r["Inst_Cap"]),
            "x_pu": params["x_pu"],
            "r_pu": params["r_pu"],
            "Voltage_level": f"{pv}/{sv}",
            "type": f'{r["Inst_Cap"]} MVA {pv}/{sv} kV',
            "s_nom_extendable": False
        })

    transformers_df = pd.DataFrame(transformers)

    os.makedirs(Output_Dir, exist_ok=True)
    transformers_df.to_csv(OUT_TRANSFORMERS, index=False)

    return {
        "status": "success",
        "file": OUT_TRANSFORMERS,
        "columns": list(transformers_df.columns),
        "data": transformers_df.to_dict(orient="records")
    }
import pandas as pd
import os


def generate_transformer_types(Input_Dir,Output_Dir):
    # -------------------------------------------------
    # PATHS (UNCHANGED)
    # -------------------------------------------------
    TRANSFORMER_FILE = os.path.join(Output_Dir, "transformers.csv")
    OUT_TYPES = os.path.join(Output_Dir, "transformer_types.csv")

    # -------------------------------------------------
    # READ TRANSFORMERS (DEPENDENCY)
    # -------------------------------------------------
    transformers_df = pd.read_csv(TRANSFORMER_FILE)

    TYPE_PARAMS = {
        (220, 33):  dict(v_nom_0=220, v_nom_1=33, vsc=11.8, vscr=0.27, pfe=41, i0=0.1),
        (33, 11):   dict(v_nom_0=33,  v_nom_1=11, vsc=6.0,  vscr=0.5,  pfe=10.5, i0=0.4),
        (11, 0.415):dict(v_nom_0=11,  v_nom_1=0.415, vsc=4.0, vscr=1.3, pfe=5, i0=0.9),
    }

    type_rows = []

    if not transformers_df.empty:
        for (level, s_nom), _ in transformers_df.groupby(["Voltage_level", "s_nom"]):

            pv, sv = map(float, level.split("/"))
            p = TYPE_PARAMS[(pv, sv)]

            type_rows.append({
                "name": f"{s_nom} MVA {pv}/{sv} kV",
                "s_nom": s_nom,
                "v_nom_0": p["v_nom_0"],
                "v_nom_1": p["v_nom_1"],
                "vsc": p["vsc"],
                "vscr": p["vscr"],
                "pfe": p["pfe"],
                "i0": p["i0"],
                "phase_shift": 0,
                "tap_side": 0,
                "tap_neutral": 0,
                "tap_min": -5,
                "tap_max": 5,
                "tap_step_percent": 1.5,
                "tap_step_degree": 0,
                "tap_phase_shifter": False
            })

    types_df = pd.DataFrame(type_rows)

    os.makedirs(Output_Dir, exist_ok=True)
    types_df.to_csv(OUT_TYPES, index=False)

    return {
        "status": "success",
        "file": OUT_TYPES,
        "columns": list(types_df.columns),
        "data": types_df.to_dict(orient="records")
    }

def generate_lines_data(Input_Dir,Output_Dir):
    # -------------------------------------------------
    # FIXED PATHS
    # -------------------------------------------------
    
    IN_CSV = os.path.join(Input_Dir, "Input_2.csv")
    OUT_CSV = os.path.join(Output_Dir, "lines.csv")

    # -------------------------------------------------
    # READ INPUT
    # -------------------------------------------------
    df = pd.read_csv(IN_CSV)

    # Normalize column names
    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(" ", "_")
    )

    # -------------------------------------------------
    # CLEAN NUMERIC DATA
    # -------------------------------------------------
    def clean_float(val):
        val = str(val).strip()

        # Fix multiple dots like ".0.024"
        if val.count('.') > 1:
            val = val.replace('.', '', val.count('.') - 1)

        try:
            return float(val)
        except:
            return np.nan

    num_cols = ["length", "resistance", "reactance", "rated_i", "voltage_kv"]

    for col in num_cols:
        if col in df.columns:
            df[col] = df[col].apply(clean_float)

    # Drop invalid rows
    df = df.dropna(subset=num_cols)

    # -------------------------------------------------
    # HELPERS
    # -------------------------------------------------
    def format_bus(bus, voltage_kv):
        return f"{bus}_{int(voltage_kv)}"

    # -------------------------------------------------
    # PROCESS
    # -------------------------------------------------
    rows = []

    for i, r in df.iterrows():
        try:
            start = str(r["start_p"]).strip()
            end = str(r["end_p"]).strip()
            voltage_kv = r["voltage_kv"]
            rated_I = r["rated_i"]

            # Apparent power (MVA)
            s_nom = round(np.sqrt(3) * voltage_kv * rated_I / 1000, 3)

            rows.append({
                "name": r["section"],
                "bus0": format_bus(start, voltage_kv),
                "bus1": format_bus(end, voltage_kv),
                "s_nom": s_nom,
                "r": r["resistance"],
                "x": r["reactance"],
                "length": r["length"],
                "s_nom_extendable": True,
                "carrier": "AC"
            })

        except Exception as e:
            print(f"❌ Error processing row {i}: {e}")

    lines_df = pd.DataFrame(rows)

    # -------------------------------------------------
    # SAVE CSV
    # -------------------------------------------------
    os.makedirs(Output_Dir, exist_ok=True)
    lines_df.to_csv(OUT_CSV, index=False)

    # -------------------------------------------------
    # RETURN JSON
    # -------------------------------------------------
    return {
        "status": "success",
        "file_path": OUT_CSV,
        "columns": list(lines_df.columns),
        "data": lines_df.to_dict(orient="records"),
        "total_rows": len(lines_df)
    }
import pandas as pd
import numpy as np
import os
import re

def generate_load_pset_qset(Input_Dir,Output_Dir):
    
    try:
        # ---------------- PATHS ----------------
        #Loads_DIR = r"C:\RaviNamdev\FinalSpibeat\ShapeFile_to_pypsa_Input\Input_1_to_11_pypsa_input_files\Pypsa_csv_formate_output\baseline_scenario"
       # Load_Time_Stamp = r"C:\RaviNamdev\FinalSpibeat\ShapeFile_to_pypsa_Input\shape_to_pypsa_formate_output"
        
        TS_FILE = os.path.join(Input_Dir, "timeseries_input.csv")
        LOAD_FILE = os.path.join(Output_Dir, "Loads.csv")

        OUT_P = os.path.join(Output_Dir, "loads-p_set.csv")
        OUT_Q = os.path.join(Output_Dir, "loads-q_set.csv")

        POWER_FACTOR = 0.9

        # ---------------- READ FILES ----------------
        ts_df = pd.read_csv(TS_FILE)
        loads_df = pd.read_csv(LOAD_FILE)

        ts_df.columns = ts_df.columns.str.strip()
        loads_df.columns = loads_df.columns.str.strip()

        # ---------------- TIME ----------------
        ts_df.iloc[:, 0] = pd.to_datetime(ts_df.iloc[:, 0])
        ts_df = ts_df.rename(columns={ts_df.columns[0]: "time"})

        # ---------------- MAPPING ----------------
        dt_to_load = {}

        for _, row in loads_df.iterrows():
            dt_match = re.match(r"(DT\d+)_", row["bus"])
            if dt_match:
                dt_to_load[dt_match.group(1)] = row["name"]

        if not dt_to_load:
            return {
                "status": "error",
                "message": "DT to Load mapping failed"
            }

        # ---------------- RENAME ----------------
        df = ts_df.copy()

        for col in df.columns:
            if col in dt_to_load:
                df = df.rename(columns={col: dt_to_load[col]})

        load_cols = ["time"] + list(dt_to_load.values())
        p_df = df[load_cols]

        # ---------------- SAVE P ----------------
        p_df.to_csv(OUT_P, index=False)

        # ---------------- Q CALCULATION ----------------
        phi = np.arccos(POWER_FACTOR)
        tan_phi = np.tan(phi)

        q_df = p_df.copy()

        for col in q_df.columns:
            if col != "time":
                q_df[col] = q_df[col] * tan_phi

        # ---------------- SAVE Q ----------------
        q_df.to_csv(OUT_Q, index=False)

        # ---------------- RESPONSE ----------------
        return {
            "status": "success",
            "message": "p_set and q_set generated successfully",

            "p_set": {
                "columns": list(p_df.columns),
                "data": p_df.to_dict(orient="records"),
                "total_rows": len(p_df),
                "file_path": OUT_P
            },

            "q_set": {
                "columns": list(q_df.columns),
                "data": q_df.to_dict(orient="records"),
                "total_rows": len(q_df),
                "file_path": OUT_Q
            }
        }

    except Exception as e:
        return {
            "status": "error",
            "code": "LOAD_PQ_FAILED",
            "message": str(e)
        }
def generate_snapshots(Input_Dir,Output_Dir):
    # --------------------------------------------------
    # PATHS (UNCHANGED)

    TS_CSV = os.path.join(Input_Dir, "timeseries_input.csv")
    OUT_SNAP = os.path.join(Output_Dir, "snapshots.csv")

    # --------------------------------------------------
    # READ TIME SERIES
    # --------------------------------------------------
    ts_df = pd.read_csv(TS_CSV)
    ts_df.columns = ts_df.columns.str.strip()

    time_col = ts_df.columns[0]
    snapshots = pd.to_datetime(ts_df[time_col], errors="raise")

    # --------------------------------------------------
    # BUILD SNAPSHOT FILE
    # --------------------------------------------------
    snap_df = pd.DataFrame({
        "name": snapshots,
        "weightings": 1
    })

    os.makedirs(Output_Dir, exist_ok=True)
    snap_df.to_csv(OUT_SNAP, index=False)

    # --------------------------------------------------
    # RETURN JSON
    # --------------------------------------------------
    return {
        "status": "success",
        "file": OUT_SNAP,
        "total_snapshots": len(snap_df),
        'columns':snap_df.columns.tolist(),
        "data": snap_df.to_dict(orient="records")
    }

import pandas as pd
import os


def generate_generator_pmax(Input_Dir,Output_Dir):
    # --------------------------------------------------
    # PATHS (UNCHANGED)
    # --------------------------------------------------
    # Loads_DIR = r"C:\RaviNamdev\FinalSpibeat\ShapeFile_to_pypsa_Input\Input_1_to_11_pypsa_input_files\Pypsa_csv_formate_output\baseline_scenario"
    # Load_Time_Stamp = r"C:\RaviNamdev\FinalSpibeat\ShapeFile_to_pypsa_Input\shape_to_pypsa_formate_output"
    TS_CSV = os.path.join(Input_Dir, "timeseries_input.csv")
    GEN_CSV = os.path.join(Output_Dir, "generators.csv")
    OUT_PMAX = os.path.join(Output_Dir, "generators-p_max_pu.csv")

    # --------------------------------------------------
    # READ TIME SERIES
    # --------------------------------------------------
    ts_df = pd.read_csv(TS_CSV)
    ts_df.columns = ts_df.columns.str.strip()

    time_col = ts_df.columns[0]
    snapshots = pd.to_datetime(ts_df[time_col], errors="raise")

    # --------------------------------------------------
    # READ GENERATORS
    # --------------------------------------------------
    gen_df = pd.read_csv(GEN_CSV)
    gen_df.columns = gen_df.columns.str.strip()

    active_gens = gen_df.loc[
        gen_df["p_nom"].notna() & (gen_df["p_nom"] > 0),
        "name"
    ].tolist()

    if not active_gens:
        raise ValueError("❌ No active generators found")

    # --------------------------------------------------
    # BUILD PMAX FILE
    # --------------------------------------------------
    pmax_df = pd.DataFrame({"snapshot": snapshots})

    for g in active_gens:
        pmax_df[g] = 1.0

    os.makedirs(Output_Dir, exist_ok=True)
    pmax_df.to_csv(OUT_PMAX, index=False)

    # --------------------------------------------------
    # RETURN JSON
    # --------------------------------------------------
    return {
        "status": "success",
        "file": OUT_PMAX,
        "generators": active_gens,
        "total_snapshots": len(pmax_df),
        "columns":pmax_df.columns.to_list(),
        "data": pmax_df.to_dict(orient="records")
    }

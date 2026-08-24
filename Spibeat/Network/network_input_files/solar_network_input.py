
import pandas as pd
import numpy as np
import os
import pandas as pd
import numpy as np
import os
from ..p_nom_data import get_generator_data
def generate_solar_generators_data(Input_Dir,Output_Dir):
    import os
    import pandas as pd

    # -------------------------------------------------
    # PATHS
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
    # LOAD GENERATOR JSON ONCE ✅
    # -------------------------------------------------
    data = get_generator_data()

    # safe p_nom extraction
    if len(data) > 0:
        p_nom_value = data[0].get("p_nom", 0.03)
    else:
        p_nom_value = 0.03

    print("Using p_nom:", p_nom_value)

    # -------------------------------------------------
    # CREATE GENERATORS
    # -------------------------------------------------
    generators = []
    gen_id = 1

    for _, r in df.iterrows():

        if r["Inst_Gen"] <= 0:
            continue

        name = str(r["Name"]).strip()
        pv = float(r["Pri_Voltag"])

        raw_type = str(r["type"]).lower()
        raw_type = raw_type.replace("\r", " ").replace("\n", " ").strip()

        if "substation" not in raw_type:
            continue

        bus_name = f"{name}_{int(pv)}"

        # Main generator
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
    # ADD SOLAR GENERATOR (ONLY ONCE) ✅
    # -------------------------------------------------
    generators.append({
        "name": "Solar_DT1",
        "bus": "DT8_415",
        "p_nom": p_nom_value,
        "carrier": "solar",
        "efficiency": 0.26,
        "p_nom_extendable": True
    })

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
def generate_solar_generator_pmax_pu(Input_Dir,Output_Dir):
    try:
        # --------------------------------------------------
        # PATHS
        # --------------------------------------------------
        TS_CSV   = os.path.join(Input_Dir, "timeseries_input.csv")
        GEN_CSV  = os.path.join(Output_Dir, "generators.csv")
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
            return {"status": "error", "message": "❌ No active generators found"}

        # --------------------------------------------------
        # SOLAR PROFILE
        # --------------------------------------------------
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

        # --------------------------------------------------
        # EXTRA SOLAR GENERATORS
        # --------------------------------------------------
        extra_solar_gens = ["Solar_DT1"]

        all_gens = list(set(active_gens + extra_solar_gens))

        # --------------------------------------------------
        # BUILD PMAX
        # --------------------------------------------------
        pmax_df = pd.DataFrame({"snapshot": snapshots})

        for g in all_gens:
            if "Solar" in g:
                pmax_df[g] = solar_series
            else:
                pmax_df[g] = 1.0

        pmax_df.to_csv(OUT_PMAX, index=False)

        # --------------------------------------------------
        # RETURN JSON
        # --------------------------------------------------
        return {
            "status": "success",
            "file": OUT_PMAX,
            "generators": all_gens,
            "total_snapshots": len(pmax_df),
            "columns": pmax_df.columns.tolist(),
            "data": pmax_df.to_dict(orient="records")
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}
def generate_solar_generator_p_set(Input_Dir,Output_Dir):
    # --------------------------------------------------
    # PATHS (UNCHANGED)
    TS_CSV   = os.path.join(Input_Dir, "timeseries_input.csv")
    GEN_CSV  = os.path.join(Output_Dir, "generators.csv")
    OUT_PMAX = os.path.join(Output_Dir, "generators-p_max_pu.csv")
    OUT_PSET = os.path.join(Output_Dir, "generators-p_set.csv")
    OUT_SNAP = os.path.join(Output_Dir, "snapshots.csv")

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

    active_gen_df = gen_df.loc[
        gen_df["p_nom"].notna() & (gen_df["p_nom"] > 0)
    ].copy()

    if active_gen_df.empty:
        return {"status": "error", "message": "❌ No active generators found"}

    active_gens = active_gen_df["name"].tolist()

    # Map p_nom
    p_nom_map = active_gen_df.set_index("name")["p_nom"].to_dict()

    # Solar generators
    solar_gens = active_gen_df.loc[
        active_gen_df["carrier"].str.lower() == "solar", "name"
    ].tolist()

    # --------------------------------------------------
    # SOLAR PROFILE
    # --------------------------------------------------
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

    # --------------------------------------------------
    # BUILD p_max
    # --------------------------------------------------
    pmax_df = pd.DataFrame({"snapshot": snapshots})

    for g in active_gens:
        pmax_df[g] = solar_series if g in solar_gens else 1.0

    pmax_df.to_csv(OUT_PMAX, index=False)

    # --------------------------------------------------
    # BUILD p_set
    # --------------------------------------------------
    pset_df = pd.DataFrame({"snapshot": snapshots})

    for g in active_gens:
        if g in solar_gens:
            pset_df[g] = solar_series * p_nom_map[g]
        else:
            pset_df[g] = 0.0

    pset_df.to_csv(OUT_PSET, index=False)

    # --------------------------------------------------
    # BUILD snapshots
    # --------------------------------------------------
    snap_df = pd.DataFrame({
        "name": snapshots,
        "weightings": 1
    })

    snap_df.to_csv(OUT_SNAP, index=False)

    # --------------------------------------------------
    # RETURN JSON (FRONTEND READY 🚀)
    # --------------------------------------------------
    return {
        "status": "success",
        "message": "✅ All generator files created",
        "columns":  pset_df.columns.tolist(),
        # 🔥 preview data (limit for performance)
        "data":  pset_df.to_dict(orient="records")
    }
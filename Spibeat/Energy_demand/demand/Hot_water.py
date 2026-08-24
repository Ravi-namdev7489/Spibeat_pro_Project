import os
import numpy as np
import pandas as pd
from pvlib.iotools import read_epw
import traceback

from .constants import (
    CP_WATER,
    T_SOIL,
    COP_DHW,
    PIPE_LENGTH_M,
    PIPE_U_VALUE,
    RECOVERABLE_FRACTION,
    SAFETY_FACTOR,
    SIMULATION_YEAR,
    J_TO_KWH,
    TANK_SURFACE_COEFF,
    TANK_SURFACE_EXP,
    TANK_U_SMALL,
    TANK_U_MEDIUM,
    TANK_U_LARGE,
    KGH_TO_M3S,
    KW_CONVERSION
)

# ============================================================
# WEATHER
# ============================================================
def load_weather(epw_path):
    weather, meta = read_epw(epw_path)
    weather.index = weather.index.map(lambda t: t.replace(year=SIMULATION_YEAR))
    return weather["temp_air"].values, weather.index


# ============================================================
# SCHEDULE (🔥 FIXED WITH STRICT ZERO LOGIC)
# ============================================================
def load_schedule_8760(schedule_csv, monthly_csv, use_type, timestamps):

    sched = pd.read_csv(schedule_csv, index_col=0)

    mm = pd.read_csv(monthly_csv, index_col="use_type")
    mm.index = mm.index.str.upper().str.strip()

    use_type = use_type.upper().strip()

    if use_type not in mm.index:
        raise ValueError(f"❌ Use type '{use_type}' not found in monthly multiplier")

    mf = mm.loc[use_type].values.astype(float)

    if len(mf) != 12:
        raise ValueError("❌ Monthly multiplier must have 12 values")

    weekday = sched.loc[[f"Weekday_{h:02d}" for h in range(24)], "hot_water"].astype(float).values
    saturday = sched.loc[[f"Saturday_{h:02d}" for h in range(24)], "hot_water"].astype(float).values
    sunday = sched.loc[[f"Sunday_{h:02d}" for h in range(24)], "hot_water"].astype(float).values

    schedule = np.zeros(len(timestamps))

    for i, ts in enumerate(timestamps):

        if ts.weekday() < 5:
            prof = weekday
        elif ts.weekday() == 5:
            prof = saturday
        else:
            prof = sunday

        factor = mf[ts.month - 1]

        # 🔥 STRICT RULE
        if factor == 0:
            schedule[i] = 0
        else:
            schedule[i] = prof[ts.hour] * factor

    # 🔒 EXTRA SAFETY (force zero entire month)
    months = np.array([ts.month for ts in timestamps])
    for m in range(1, 13):
        if mf[m - 1] == 0:
            schedule[months == m] = 0

    return pd.Series(schedule, index=timestamps)


# ============================================================
# PIPE SELECTION
# ============================================================
def select_pipe(pipe_csv, peak_kg_h):
    df = pd.read_csv(pipe_csv)

    vdot = peak_kg_h * KGH_TO_M3S

    valid = df[
        (df["Vdot_min_m3s"] <= vdot) &
        (df["Vdot_max_m3s"] >= vdot)
    ]

    if not valid.empty:
        selected = valid.sort_values(by="D_int_m").iloc[0]
    else:
        df["diff"] = abs(df["Vdot_max_m3s"] - vdot)
        selected = df.sort_values(by="diff").iloc[0]

    return selected["D_ext_m"]


# ============================================================
# LOSSES
# ============================================================
def tank_loss(V, Th, Tc):
    A = TANK_SURFACE_COEFF * V ** TANK_SURFACE_EXP

    if V < 0.5:
        U = TANK_U_SMALL
    elif V < 2:
        U = TANK_U_MEDIUM
    else:
        U = TANK_U_LARGE

    return U * A * (Th - Tc) / KW_CONVERSION


def pipe_loss(D, L, Ts, Tr, U):
    A = np.pi * D * L
    Q = U * A * (Ts - Tr) / KW_CONVERSION
    return RECOVERABLE_FRACTION * Q, (1 - RECOVERABLE_FRACTION) * Q


# ============================================================
# MAIN FUNCTION
# ============================================================
def run_dhw(locator, buildings):

    try:
        print("🔥 Starting DHW calculation")

        epw = locator.get_epw()
        use_db_path = locator.get_use_types()
        monthly_mult = locator.get_monthly_multiplier("HW")
        schedule_dir = locator.get_schedule_library()
        pipe_db = locator.get_thermal_grid()
        out_dir = locator.get_output_folder("HW")

        os.makedirs(out_dir, exist_ok=True)

        combined = []

        for _, b in buildings.items():

            use_db = pd.read_csv(use_db_path).set_index("use_type")
            use_db.index = use_db.index.str.upper().str.strip()

            use_type = b.get("use_type").upper()

            if use_type not in use_db.index:
                raise ValueError(f"❌ Use type '{use_type}' not found")

            use_row = use_db.loc[use_type]
            if isinstance(use_row, pd.DataFrame):
                use_row = use_row.iloc[0]

            Occ_m2p = float(use_row["Occ_m2p"])
            Vw_ldp = float(use_row["Vw_ldp"])
            Vww_ldp = float(use_row["Vww_ldp"])
            Tin_set = float(use_row.get("Tin_set_C", 24.0))

            # WEATHER
            Tout, timestamps = load_weather(epw)

            # SCHEDULE
            schedule = load_schedule_8760(
                os.path.join(schedule_dir, f"{use_type}.csv"),
                monthly_mult,
                use_type,
                timestamps
            )

            schedule_array = schedule.values.astype(float)

            name = b.get("name")
            gfa = float(b.get("floor_area", 0))
            hotwater_type = b.get("hotwater_temp")

            if not name or gfa == 0:
                continue

            # HOT WATER TEMP
            tem_df = pd.read_csv(locator.get_hvac_hotwater())
            row = tem_df[tem_df['class_dhw'] == hotwater_type]

            if row.empty:
                raise ValueError(f"❌ Hot water type '{hotwater_type}' not found")

            HOT_WATER_TEMP = float(row.iloc[0]['Tsww0_C'])

            # DEMAND
            people = gfa / Occ_m2p
            daily_liters = float(people * Vw_ldp + gfa * Vww_ldp)

            mass_kg_h = daily_liters * schedule_array

            # ENERGY
            Tc = 0.6 * Tout + T_SOIL
            dT = np.maximum(HOT_WATER_TEMP - Tc, 0)
            active = Tout < Tin_set

            Q_useful = np.where(
                active,
                (mass_kg_h * CP_WATER * dT) * J_TO_KWH,
                0
            )

            # LOSSES
            peak = mass_kg_h.max()
            Dext = select_pipe(pipe_db, peak)
            Vtank = peak * SAFETY_FACTOR / 1000

            Qr = np.zeros(len(Tout))
            Qnr = np.zeros(len(Tout))
            Qtank = np.zeros(len(Tout))

            for i in range(len(Tout)):
                if active[i]:
                    qr, qnr = pipe_loss(
                        Dext,
                        PIPE_LENGTH_M,
                        HOT_WATER_TEMP,
                        Tc[i],
                        PIPE_U_VALUE
                    )
                    Qr[i] = qr
                    Qnr[i] = qnr
                    Qtank[i] = tank_loss(Vtank, HOT_WATER_TEMP, Tc[i])

            Qsys = Q_useful + Qr + Qnr + Qtank
            DHW_el = Qsys / COP_DHW

            # 🔥 FINAL SAFETY: IF SCHEDULE ZERO → FORCE ALL ZERO
            zero_mask = schedule_array == 0
            Q_useful[zero_mask] = 0
            Qr[zero_mask] = 0
            Qnr[zero_mask] = 0
            Qtank[zero_mask] = 0
            Qsys[zero_mask] = 0
            DHW_el[zero_mask] = 0

            df = pd.DataFrame({
                "timestamp": timestamps,
                "name": name,
                "Q_useful_kWh": Q_useful,
                "Q_tank_loss_kWh": Qtank,
                "Q_dist_rec_kWh": Qr,
                "Q_dist_nonrec_kWh": Qnr,
                "Qsys_kWh": Qsys,
                "DHW_el_kWh": DHW_el,
                "COP_DHW": np.where(active, COP_DHW, 0)
            })

            out_csv = os.path.join(out_dir, f"{name}_DHW_YEAR.csv")
            df.to_csv(out_csv, index=False)

            print(f"✔ Saved: {out_csv}")

            combined.append(df)

        combined_df = pd.concat(combined, ignore_index=True)
        combined_df.to_csv(os.path.join(out_dir, "ALL_BUILDINGS_DHW_YEAR.csv"), index=False)

        print("✅ DHW completed")
        return out_dir

    except Exception as e:
        print("❌ ERROR in run_dhw:")
        traceback.print_exc()
        raise e
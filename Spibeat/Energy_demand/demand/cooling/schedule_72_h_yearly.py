import os
import numpy as np
import pandas as pd
schedule_map = {
    "OFF": 0.0,
    "SETPOINT": 1.0,
    "SETBACK": 0.0
    }
# ------------------------------------------------------------
# 3️⃣ Function: Expand 72h → 8760
# ------------------------------------------------------------  

def expand_schedule_to_8760(schedule_df, timestamps, column_name):
    
    values_8760 = []

    for ts in timestamps:

        hour = ts.hour

        # Determine day type
        if ts.weekday() < 5:
            day_type = "Weekday"
        elif ts.weekday() == 5:
            day_type = "Saturday"
        else:
            day_type = "Sunday"

        row_label = f"{day_type}_{hour:02d}"

        row = schedule_df.loc[schedule_df["hour"] == row_label]

        if row.empty:
            values_8760.append(0.0)
        else:
            raw_value = row.iloc[0][column_name]

            # If string (OFF/SETPOINT/SETBACK)
            if isinstance(raw_value, str):
                values_8760.append(
                    schedule_map.get(raw_value.strip().upper(), 0.0)
                )
            else:
                values_8760.append(float(raw_value))

    return np.array(values_8760)
def expand_monthly_multiplier(mult_file, timestamps, use_type):
    
    df = pd.read_csv(mult_file)

    # ✅ Clean column names
    df.columns = df.columns.str.strip()

    # ✅ Clean use_type column
    df["use_type"] = df["use_type"].astype(str).str.strip()
    use_type = use_type.strip()

    # ✅ Check existence
    if use_type not in df["use_type"].values:
        raise ValueError(f"❌ {use_type} not found in multiplier file")

    # ✅ Pick correct row
    row = df[df["use_type"] == use_type].iloc[0]

    # ✅ Pick exact month columns (NO iloc mistake)
    months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]

    monthly_values = np.array([
        float(str(row[m]).strip()) for m in months
    ])

    # ✅ DEBUG (VERY IMPORTANT)
    print(f"📅 {use_type} monthly:", monthly_values)

    # Map month → value
    month_map = dict(zip(range(1, 13), monthly_values))

    # Expand to 8760
    mult_8760 = np.array([month_map[ts.month] for ts in timestamps])

    return mult_8760
# ------------------------------------------------------------
# MAIN FUNCTION (ONLY CACHE ADDED)
# ------------------------------------------------------------
def schedule_72h_yearly(timestamps, schedule_dir, monthly_multiplayer, building_geoms):
    
    schedule_cache = {}
    schedule_df_cache = {}
    multiplier_cache = {}

    # ✅ final output per building
    results = {}

    for b_id, geom in building_geoms.items():

        USE_TYPE = str(geom["use_type"]).strip()

        print(f"\n🏢 Processing Building: {b_id} | Type: {USE_TYPE}")

        # ----------------------------------------------------
        # ✅ CACHE HIT
        # ----------------------------------------------------
        if USE_TYPE in schedule_cache:
            print(f"⚡ Reusing schedule for {USE_TYPE}")

            cooling_schedule, lighting_schedule, ac_usage_schedule, appliance_schedule, people_schedule = schedule_cache[USE_TYPE]
            monthly_multiplier_8760 = multiplier_cache[USE_TYPE]

        else:
            # ----------------------------------------------------
            # Load CSV
            # ----------------------------------------------------
            schedule_file = os.path.join(schedule_dir, f"{USE_TYPE}.csv")

            if not os.path.exists(schedule_file):
                raise FileNotFoundError(f"❌ Schedule file not found: {schedule_file}")

            if USE_TYPE in schedule_df_cache:
                schedule_df = schedule_df_cache[USE_TYPE]
            else:
                schedule_df = pd.read_csv(schedule_file)

                if "hour" not in schedule_df.columns:
                    raise ValueError("❌ Schedule file must contain 'hour' column")

                schedule_df_cache[USE_TYPE] = schedule_df

            print(f"✔ Loaded schedule for {USE_TYPE}")

            # ----------------------------------------------------
            # Compute schedules
            # ----------------------------------------------------
            cooling_schedule = expand_schedule_to_8760(schedule_df, timestamps, "cooling")
            lighting_schedule = expand_schedule_to_8760(schedule_df, timestamps, "lighting")
            appliance_schedule = expand_schedule_to_8760(schedule_df, timestamps, "appliances")
            people_schedule = expand_schedule_to_8760(schedule_df, timestamps, "occupancy")
            ac_usage_schedule = expand_schedule_to_8760(schedule_df, timestamps, "AC_Usage")

            # ----------------------------------------------------
            # Multiplier
            # ----------------------------------------------------
            if USE_TYPE in multiplier_cache:
                monthly_multiplier_8760 = multiplier_cache[USE_TYPE]
            else:
                monthly_multiplier_8760 = expand_monthly_multiplier(
                    monthly_multiplayer,
                    timestamps,
                    USE_TYPE
                )
                multiplier_cache[USE_TYPE] = monthly_multiplier_8760

            # cache store
            schedule_cache[USE_TYPE] = (
                cooling_schedule,
                lighting_schedule,
                ac_usage_schedule,
                appliance_schedule,
                people_schedule
            )

        # ----------------------------------------------------
        # ✅ STORE PER BUILDING (MAIN FIX)
        # ----------------------------------------------------
        results[b_id] = {
            "use_type": USE_TYPE,
            "cooling": cooling_schedule,
            "lighting": lighting_schedule,
            "ac": ac_usage_schedule,
            "appliances": appliance_schedule,
            "people": people_schedule,
            "multiplier": monthly_multiplier_8760
        }

    return results
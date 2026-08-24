import os
import zipfile
import json
import pandas as pd
from django.conf import settings
from .demand.inputLocator import InputLocator

# ==========================================
# 📦 BASE DIRECTORY
# ==========================================
def get_upload_dir():
    base = os.path.join(settings.MEDIA_ROOT, "uploads")
    os.makedirs(base, exist_ok=True)
    return base


# ==========================================
# 👤 USER FOLDER
# ==========================================
def get_user_folder(user):
    base = get_upload_dir()
    folder = os.path.join(base, f"user_{user.id}")
    os.makedirs(folder, exist_ok=True)
    return folder


# ==========================================
# 📦 HELPERS
# ==========================================


def find_shp(folder):
    for root, _, files in os.walk(folder):
        for f in files:
            if f.endswith(".shp"):
                return os.path.join(root, f)
    return None


def find_epw(folder):
    for root, _, files in os.walk(folder):
        for f in files:
            if f.endswith(".epw"):
                return os.path.join(root, f)
    return None


def validate_shapefile(folder):
    required = [".shp", ".dbf", ".shx"]
    found = set()

    for root, _, files in os.walk(folder):
        for f in files:
            ext = os.path.splitext(f)[1]
            if ext in required:
                found.add(ext)

    missing = [ext for ext in required if ext not in found]
    return missing


# ==========================================
# 📦 LOCATOR (USER BASED)
# ==========================================
def get_locator_from_user(user):

    user_folder = get_user_folder(user)

    building_dir = os.path.join(user_folder, "building")
    weather_dir = os.path.join(user_folder, "weather")

    shp = find_shp(building_dir)
    epw = find_epw(weather_dir)
    if not shp:
        raise Exception("❌ Shapefile not found")
    if not epw:
        raise Exception("❌ EPW not found")
    data = get_use_type(user)
    use_type = data.get('use_type')
    return InputLocator(epw, shp,use_type)
# ==========================================
# 📦 USE TYPE (JSON)
# ==========================================
def save_use_type(user, use_type, per_commercial=0, per_residential=0):

    folder = get_user_folder(user)

    data = {
        "use_type": use_type,
        "per_commercial": per_commercial,
        "per_residential": per_residential
    }

    path = os.path.join(folder, "use_type.json")

    with open(path, "w") as f:
        json.dump(data, f, indent=4)

    return data


def get_use_type(user):
    folder = get_user_folder(user)
    path = os.path.join(folder, "use_type.json")

    # ✅ If file does NOT exist → default
    if not os.path.exists(path):
        return {"use_type": "RESIDENTIAL"}

    try:
        with open(path, "r") as f:
            data = json.load(f)

        # ✅ If JSON empty or missing key
        if not data or not data.get("use_type"):
            return {"use_type": "RESIDENTIAL"}

        return data

    except Exception as e:
        # ✅ If JSON corrupted / invalid
        print("❌ JSON error:", str(e))
        return {"use_type": "RESIDENTIAL"}


# ==========================================
# 📦 PARAMETERS JSON
# ==========================================
def get_param_file(user):
    return os.path.join(get_user_folder(user), "parameter.json")


def save_locator_json(user, selected, params):
    path = get_param_file(user)

    data = {
        "selected_buildings": selected,
        "parameters": params
    }

    with open(path, "w") as f:
        json.dump(data, f, indent=4)

    return data


def get_locator_json(user):
    path = get_param_file(user)

    if not os.path.exists(path):
        return {
            "selected_buildings": [],
            "parameters": {}
        }

    with open(path, "r") as f:
        return json.load(f)


def reset_locator_json(user):
    path = get_param_file(user)

    data = {
        "selected_buildings": [],
        "parameters": {}
    }

    with open(path, "w") as f:
        json.dump(data, f, indent=4)

    return data


# ==========================================
# 📊 USE TYPE ROW (CSV)
# ==========================================
def save_use_type_row(locator, use, row_data):
    try:
        path = locator.get_use_types()

        df = pd.read_csv(path)
        df.columns = df.columns.str.strip()

        idx = df[df["use_type"].str.upper() == use.upper()].index

        if len(idx) == 0:
            return False

        row_index = idx[0]

        for key, value in row_data.items():
            if key in df.columns:
                df.at[row_index, key] = value

        df.to_csv(path, index=False)
        return True

    except Exception as e:
        print("❌ Error:", e)
        return False


def get_use_type_row(locator, use):
    try:
        path = locator.get_use_types()

        df = pd.read_csv(path)
        df.columns = df.columns.str.strip()

        row = df[df["use_type"].str.upper() == use.upper()]

        if row.empty:
            return None

        return row.iloc[0].to_dict()

    except Exception as e:
        print("❌ Error:", e)
        return None


# ==========================================
# 📊 MULTIPLIER
# ==========================================
def update_multiplier(locator, use, type_name, values):
    try:
        path = locator.get_monthly_multiplier(type_name)

        if not os.path.exists(path):
            return

        df = pd.read_csv(path)
        df.columns = df.columns.str.strip()

        idx = df[df["use_type"] == use].index

        if len(idx) == 0:
            return

        row_index = idx[0]

        for key, value in values.items():
            if key in df.columns:
                df.at[row_index, key] = value

        df.to_csv(path, index=False)

    except Exception as e:
        print("❌ Multiplier error:", e)


# ==========================================
# 📊 SCHEDULE
# ==========================================
def save_schedule(locator, use, schedule_rows):

    path = os.path.join(
        locator.get_schedule_library(),
        f"{use}.csv"
    )

    df = pd.DataFrame(schedule_rows)
    df.to_csv(path, index=False)


def get_schedule(locator, use):

    path = os.path.join(
        locator.get_schedule_library(),
        f"{use}.csv"
    )

    if not os.path.exists(path):
        return pd.DataFrame()

    return pd.read_csv(path)
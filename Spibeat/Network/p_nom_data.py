import os
import json
from django.conf import settings

GENERATOR_FILE = os.path.join(settings.MEDIA_ROOT, "generators.json")

# ✅ SAVE / UPDATE GENERATOR
def set_generator_data(name, p_nom):
    data = []

    # load existing data
    if os.path.exists(GENERATOR_FILE):
        with open(GENERATOR_FILE, "r") as f:
            try:
                data = json.load(f)
            except:
                data = []

    # check if generator already exists → update
    updated = False
    for item in data:
        if item["name"] == name:
            item["p_nom"] = p_nom
            updated = True
            break

    # if not found → add new
    if not updated:
        data.append({
            "name": name,
            "p_nom": p_nom
        })

    # save back
    with open(GENERATOR_FILE, "w") as f:
        json.dump(data, f, indent=4)

    return {"name": name, "p_nom": p_nom}


# ✅ GET GENERATOR
def get_generator_data():
    if not os.path.exists(GENERATOR_FILE):
        return []

    with open(GENERATOR_FILE, "r") as f:
        try:
            data = json.load(f)
            return data
        except:
           return []
    
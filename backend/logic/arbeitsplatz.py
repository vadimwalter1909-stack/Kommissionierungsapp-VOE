import json
import os

def load_arbeitsplatz_artikel():
    path = "backend/data/arbeitsplatz_artikel.json"
    if not os.path.exists(path):
        return {"artikel": []}

    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"artikel": []}

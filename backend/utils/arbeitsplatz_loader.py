import json
import os

DATA_PATH = "backend/data/arbeitsplatz_artikel.json"


def load_arbeitsplatz_artikel():
    """Lädt die Arbeitsplatz-Artikel-Liste. Erstellt Datei, falls sie fehlt."""
    if not os.path.exists(DATA_PATH):
        data = {"artikel": []}
        with open(DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        return data

    with open(DATA_PATH, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            # Datei defekt → neu anlegen
            data = {"artikel": []}
            with open(DATA_PATH, "w", encoding="utf-8") as fw:
                json.dump(data, fw, indent=4, ensure_ascii=False)
            return data

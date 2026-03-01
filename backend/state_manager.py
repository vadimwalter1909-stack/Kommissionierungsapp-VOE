import json
from pathlib import Path

STATE_PATH = Path(__file__).resolve().parent / "current_state.json"


def load_state():
    if STATE_PATH.exists():
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}   # leerer State


def save_state(state: dict):
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def merge_excel_into_state(excel_rows: list[dict], old_state: dict) -> dict:
    """
    Narrensichere Merge-Funktion:
    - Stammdaten aus Excel aktualisieren
    - Fortschritt IMMER erhalten
    - neue Zeilen hinzufügen
    - alte Zeilen NICHT löschen
    """

    new_state = {}

    # 1. Excel-Zeilen in Dictionary umwandeln
    excel_dict = {row["merge_key"]: row for row in excel_rows}

    # 2. Alle Keys durchgehen, die in Excel vorkommen
    for key, excel_row in excel_dict.items():

        if key in old_state:
            old_row = old_state[key]

            merged = excel_row.copy()

            # Fortschritt aus altem State übernehmen
            merged["fertig"] = old_row.get("fertig", False)
            merged["ausgeliefert"] = old_row.get("ausgeliefert", False)
            merged["zielort"] = old_row.get("zielort")
            merged["bundles"] = old_row.get("bundles", [])
            merged["timestamp"] = old_row.get("timestamp")

            # Falls du weitere Fortschrittsfelder hast → hier ergänzen

            new_state[key] = merged

        else:
            # Neue Zeile → Fortschritt initialisieren
            new_row = excel_row.copy()
            new_row["fertig"] = False
            new_row["ausgeliefert"] = False
            new_row["zielort"] = None
            new_row["bundles"] = []
            new_row["timestamp"] = None

            new_state[key] = new_row

    # 3. Alte Keys behalten, die NICHT mehr in Excel vorkommen
    for key, old_row in old_state.items():
        if key not in new_state:
            # Alte Zeile unverändert übernehmen
            new_state[key] = old_row

    return new_state


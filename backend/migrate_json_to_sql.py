import json
from backend.database import SessionLocal
from backend.models import Item
from backend.state_manager import STATE_PATH

def migrate_json_to_sql():
    if not STATE_PATH.exists():
        print("Keine current_state.json gefunden – Migration übersprungen.")
        return

    with open(STATE_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    db = SessionLocal()

    for key, row in data.items():
        item = Item(
            merge_key=key,
            kuerzel=row.get("Kuerzel_clean"),
            beschaffung=row.get("Beschaffung"),
            referenz=row.get("Referenz"),
            fertig=row.get("fertig", False),
            ausgeliefert=row.get("ausgeliefert", False),
            zielort=row.get("zielort"),
            bedarfs_menge_pos=row.get("Bedarfs_Menge_pos"),
            prodid_clean=row.get("ProdID_clean"),
            artikel_clean=row.get("ArtikelNr_clean"),
            durchmesser=row.get("Durchm."),
            laenge=row.get("Länge"),
            timestamp=row.get("timestamp")
        )
        db.add(item)

    db.commit()
    db.close()

    print("Migration abgeschlossen.")

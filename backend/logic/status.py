from backend.database_base import SessionLocal
from backend.database import Item

def is_done(kuerzel: str, start_bft: str) -> bool:
    db = SessionLocal()

    # Alle Items dieses Kürzels + Start-BFT laden
    items = db.query(Item).filter(
        Item.kuerzel == kuerzel,
        Item.start_bft == start_bft
    ).all()

    db.close()

    if not items:
        return False

    # Nur Logistik-Items sind relevant
    log_items = [
        i for i in items
        if not (i.beschaffung == "Produktion" and i.referenz == "Produktion")
    ]

    # Wenn es keine Logistik-Items gibt, ist der Prozess nicht relevant
    if not log_items:
        return False

    # NEU: Prozess ist fertig, sobald ALLE Logistik-Items ausgeliefert sind
    return all(i.ausgeliefert for i in log_items)

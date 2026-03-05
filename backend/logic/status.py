from backend.database_base import SessionLocal
from backend.database import Item

def is_done(kuerzel: str, prod_id: str, start_bft: str) -> bool:
    db = SessionLocal()

    # Alle Items dieses EINEN Auftrags laden
    items = db.query(Item).filter(
        Item.kuerzel == kuerzel,
        Item.prod_id == prod_id,
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

    if not log_items:
        return False

    # Auftrag ist fertig, wenn ALLE Logistik-Items ausgeliefert sind
    return all(i.ausgeliefert for i in log_items)

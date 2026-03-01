from backend.database_base import SessionLocal
from backend.database import Item

def is_done(kuerzel: str, start_bft: str) -> bool:
    db = SessionLocal()

    # Nur Items dieses Kürzels UND dieses Start-BFT laden
    items = db.query(Item).filter(
        Item.kuerzel == kuerzel,
        Item.start_bft == start_bft
    ).all()

    db.close()

    if not items:
        return False

    # PRODUKTION: nur Produktion/Produktion
    prod_items = [
        i for i in items
        if i.beschaffung == "Produktion" and i.referenz == "Produktion"
    ]

    # LOGISTIK: alles andere
    log_items = [
        i for i in items
        if not (i.beschaffung == "Produktion" and i.referenz == "Produktion")
    ]

    # Produktion fertig, wenn alle Prod-Items fertig sind (oder keine existieren)
    prod_fertig = all(i.fertig for i in prod_items) if prod_items else True

    # Logistik fertig, wenn alle Logistik-Items ausgeliefert sind
    log_ausgeliefert = all(i.ausgeliefert for i in log_items) if log_items else True

    return prod_fertig and log_ausgeliefert

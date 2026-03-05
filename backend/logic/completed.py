from backend.database_base import SessionLocal
from backend.database import CompletedToday, Item
from datetime import datetime

def mark_as_completed(kuerzel: str, prod_id: str, start_bft: str):
    db = SessionLocal()

    # Prüfen, ob dieser Auftrag (Kürzel + ProdID + Start-BFT) bereits eingetragen ist
    exists = db.query(CompletedToday).filter(
        CompletedToday.kuerzel == kuerzel,
        CompletedToday.prod_id == prod_id,
        CompletedToday.start_bft == start_bft
    ).first()

    if exists:
        db.close()
        return

    # Nur Items dieses EINEN Auftrags laden
    items = db.query(Item).filter(
        Item.kuerzel == kuerzel,
        Item.prod_id == prod_id,
        Item.start_bft == start_bft
    ).all()

    # Menge bestimmen
    menge = sum(abs(i.bedarfs_menge_pos) for i in items)

    # Zielort bestimmen
    zielort = ""
    for i in items:
        if i.ziel_lagerort:
            zielort = i.ziel_lagerort
            break

    # Typ bestimmen
    has_prod = any(i.beschaffung == "Produktion" for i in items)
    has_log = any(i.beschaffung != "Produktion" for i in items)

    if has_prod and has_log:
        typ = "beides"
    elif has_prod:
        typ = "produktion"
    else:
        typ = "logistik"

    entry = CompletedToday(
        kuerzel=kuerzel,
        prod_id=prod_id,
        timestamp=datetime.now(),
        typ=typ,
        menge=menge,
        zielort=zielort,
        start_bft=start_bft
    )

    db.add(entry)
    db.commit()
    db.close()

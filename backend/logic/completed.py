from backend.database_base import SessionLocal
from backend.database import CompletedToday, Item
from datetime import datetime

def mark_as_completed(kuerzel: str, start_bft: str):
    db = SessionLocal()

    # Prüfen, ob bereits eingetragen (tagesscharf!)
    exists = db.query(CompletedToday).filter(
        CompletedToday.kuerzel == kuerzel,
        CompletedToday.start_bft == start_bft
    ).first()

    if exists:
        db.close()
        return

    items = db.query(Item).filter(Item.kuerzel == kuerzel).all()

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
        timestamp=datetime.now(),
        typ=typ,
        menge=menge,
        zielort=zielort,
        start_bft=start_bft
    )

    db.add(entry)
    db.commit()
    db.close()

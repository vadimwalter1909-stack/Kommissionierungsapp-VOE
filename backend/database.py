from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime
from backend.database_base import Base
from datetime import datetime

class Item(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)

    merge_key = Column(String, index=True)
    kuerzel = Column(String, index=True)
    prod_id = Column(String)
    artikel_nr = Column(String)

    artikel_clean = Column(String)
    durchmesser = Column(Float)
    laenge = Column(Float)
    biegung = Column(String)

    bedarfs_menge_pos = Column(Float)
    menge = Column(Float)

    beschaffung = Column(String)
    referenz = Column(String)

    start_bft = Column(String)
    start_bew = Column(String)

    fertig = Column(Boolean, default=False)
    ausgeliefert = Column(Boolean, default=False)

    # ⭐ NEU: Kommissioniert-Status für die Logistik
    kommissioniert = Column(Boolean, default=False)

    # ⭐ NEU: Ziel-Lagerort (wird beim Ausliefern gesetzt)
    ziel_lagerort = Column(String, default="")

    # ⭐ NEU: Fehlteil-Ausbuchung
    ausgebucht = Column(Boolean, default=False)
    ausgebucht_am = Column(String, default="")


# ⭐ TAGESÜBERSICHT FÜR ABGESCHLOSSENE KÜRZEL
class CompletedToday(Base):
    __tablename__ = "completed_today"

    id = Column(Integer, primary_key=True, index=True)

    # Kürzel, das abgeschlossen wurde
    kuerzel = Column(String, index=True)

    # Wann wurde es abgeschlossen?
    timestamp = Column(DateTime, default=datetime.now)

    # Typ: "produktion", "logistik", "beides"
    typ = Column(String)

    # Gesamtmenge des Ladungsträgers
    menge = Column(Integer)

    # Ziel-Lagerort (falls vorhanden)
    zielort = Column(String)

    # ⭐ NEU: Start-BFT für tagesscharfe Aufträge
    start_bft = Column(String, index=True)

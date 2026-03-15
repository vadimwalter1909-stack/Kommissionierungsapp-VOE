from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime
from backend.database_base import Base
from datetime import datetime

# ---------------------------------------------------------
# ITEM – EINZELNE POSITION AUS DEM EXCEL / IMPORT
# ---------------------------------------------------------
class Item(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)

    # Gruppierungsschlüssel
    merge_key = Column(String, index=True)

    # Auftragsschlüssel
    kuerzel = Column(String, index=True)
    prod_id = Column(String, index=True)   # ProdID gehört zum Auftrag
    artikel_nr = Column(String)

    # Artikelmerkmale
    artikel_clean = Column(String)
    durchmesser = Column(Float)
    laenge = Column(Float)
    biegung = Column(String)

    # Mengen
    bedarfs_menge_pos = Column(Float)
    menge = Column(Float)

    # Herkunft / Referenz
    beschaffung = Column(String)
    referenz = Column(String)

    # Startdaten
    start_bft = Column(String, index=True)
    start_bew = Column(String)

    # Statusflags
    fertig = Column(Boolean, default=False)
    ausgeliefert = Column(Boolean, default=False)
    kommissioniert = Column(Boolean, default=False)

    # Logistik
    ziel_lagerort = Column(String, default="")

    # Fehlteil-Ausbuchung
    ausgebucht = Column(Boolean, default=False)
    ausgebucht_am = Column(String, default="")

    # ---------------------------------------------------------
    # PARKZONE – VERSCHOBENE AUFTRÄGE
    # ---------------------------------------------------------
    verschoben = Column(Boolean, default=False)
    reaktiviert = Column(Boolean, default=False)



# ---------------------------------------------------------
# COMPLETED TODAY – TAGESSCHARFE ABSCHLÜSSE
# ---------------------------------------------------------
class CompletedToday(Base):
    __tablename__ = "completed_today"

    id = Column(Integer, primary_key=True, index=True)

    # Auftragsschlüssel (vollständig!)
    kuerzel = Column(String, index=True)
    prod_id = Column(String, index=True)     # ⭐ NEU: ProdID ergänzt
    start_bft = Column(String, index=True)

    # Abschlusszeitpunkt
    timestamp = Column(DateTime, default=datetime.now)

    # Typ: "produktion", "logistik", "beides"
    typ = Column(String)

    # Gesamtmenge des Auftrags
    menge = Column(Integer)

    # Ziel-Lagerort (falls vorhanden)
    zielort = Column(String)

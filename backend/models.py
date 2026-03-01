from sqlalchemy import Column, Integer, String, Boolean, Float
from backend.database import Base

# ---------------------------------------------------------
# Aktive Items (Haupttabelle)
# ---------------------------------------------------------
class Item(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)
    merge_key = Column(String, unique=True, index=True)

    kuerzel = Column(String, index=True)
    beschaffung = Column(String)
    referenz = Column(String)

    fertig = Column(Boolean, default=False)
    ausgeliefert = Column(Boolean, default=False)
    zielort = Column(String, nullable=True)

    bedarfs_menge_pos = Column(Float)
    prodid_clean = Column(String)
    artikel_clean = Column(String)
    durchmesser = Column(Float)
    laenge = Column(Float)

    timestamp = Column(String, nullable=True)


# ---------------------------------------------------------
# Archivierte Items (Archiv-Tabelle)
# ---------------------------------------------------------
class ArchiveItem(Base):
    __tablename__ = "archive"

    id = Column(Integer, primary_key=True, index=True)
    merge_key = Column(String, unique=True, index=True)

    kuerzel = Column(String, index=True)
    beschaffung = Column(String)
    referenz = Column(String)

    fertig = Column(Boolean, default=False)
    ausgeliefert = Column(Boolean, default=False)
    zielort = Column(String, nullable=True)

    bedarfs_menge_pos = Column(Float)
    prodid_clean = Column(String)
    artikel_clean = Column(String)
    durchmesser = Column(Float)
    laenge = Column(Float)

    timestamp = Column(String, nullable=True)

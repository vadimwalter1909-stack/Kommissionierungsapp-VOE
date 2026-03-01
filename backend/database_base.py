from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import sqlite3
import os

SQLALCHEMY_DATABASE_URL = "sqlite:///./app.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


# ---------------------------------------------------------
# MINI-MIGRATIONSENGINE
# ---------------------------------------------------------

DB_PATH = "app.db"

# ⭐ Erwartete Spalten für Tabelle "items"
EXPECTED_COLUMNS_ITEMS = {
    "merge_key": "TEXT",
    "kuerzel": "TEXT",
    "prod_id": "TEXT",
    "artikel_nr": "TEXT",
    "artikel_clean": "TEXT",
    "durchmesser": "FLOAT",
    "laenge": "FLOAT",
    "biegung": "TEXT",
    "bedarfs_menge_pos": "FLOAT",
    "menge": "FLOAT",
    "beschaffung": "TEXT",
    "referenz": "TEXT",
    "start_bft": "TEXT",
    "start_bew": "TEXT",
    "fertig": "BOOLEAN DEFAULT 0",
    "ausgeliefert": "BOOLEAN DEFAULT 0",
    "kommissioniert": "BOOLEAN DEFAULT 0",
    "ziel_lagerort": "TEXT",
    "ausgebucht": "BOOLEAN DEFAULT 0",
    "ausgebucht_am": "TEXT DEFAULT ''"
}

# ⭐ Erwartete Spalten für Tabelle "completed_today"
EXPECTED_COLUMNS_COMPLETED = {
    "kuerzel": "TEXT",
    "timestamp": "DATETIME",
    "typ": "TEXT",
    "menge": "INTEGER",
    "zielort": "TEXT",
    "start_bft": "TEXT"   # ← NEU
}

print("DB PATH:", os.path.abspath("app.db"))


def ensure_columns_exist():
    """Prüft alle erwarteten Spalten und fügt fehlende hinzu."""
    if not os.path.exists(DB_PATH):
        return  # DB existiert noch nicht → wird später erstellt

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # ---------------------------------------------------------
    # Tabelle ITEMS prüfen
    # ---------------------------------------------------------
    cursor.execute("PRAGMA table_info(items);")
    existing_items = [row[1] for row in cursor.fetchall()]

    for column, definition in EXPECTED_COLUMNS_ITEMS.items():
        if column not in existing_items:
            print(f"[Migration] Füge Spalte zu 'items' hinzu: {column} ({definition})")
            cursor.execute(f"ALTER TABLE items ADD COLUMN {column} {definition};")
            conn.commit()

    # ---------------------------------------------------------
    # Tabelle COMPLETED_TODAY prüfen
    # ---------------------------------------------------------
    cursor.execute("PRAGMA table_info(completed_today);")
    existing_completed = [row[1] for row in cursor.fetchall()]

    for column, definition in EXPECTED_COLUMNS_COMPLETED.items():
        if column not in existing_completed:
            print(f"[Migration] Füge Spalte zu 'completed_today' hinzu: {column} ({definition})")
            cursor.execute(f"ALTER TABLE completed_today ADD COLUMN {column} {definition};")
            conn.commit()

    conn.close()


# ---------------------------------------------------------
# AUTOMATISCH BEIM START AUSFÜHREN
# ---------------------------------------------------------
ensure_columns_exist()

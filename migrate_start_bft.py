from backend.database_base import engine

with engine.connect() as conn:
    # Spalte prod_id hinzufügen, falls sie noch nicht existiert
    try:
        conn.execute("ALTER TABLE completed_today ADD COLUMN prod_id TEXT;")
        print("Spalte 'prod_id' erfolgreich hinzugefügt.")
    except Exception as e:
        print("Spalte 'prod_id' existiert bereits oder Fehler:", e)

    # Optional: start_bft hinzufügen, falls noch nicht vorhanden
    try:
        conn.execute("ALTER TABLE completed_today ADD COLUMN start_bft TEXT;")
        print("Spalte 'start_bft' erfolgreich hinzugefügt.")
    except Exception as e:
        print("Spalte 'start_bft' existiert bereits oder Fehler:", e)

print("Migration abgeschlossen.")

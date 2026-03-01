from backend.database_base import engine

with engine.connect() as conn:
    conn.execute("ALTER TABLE completed_today ADD COLUMN start_bft TEXT;")
    print("Migration erfolgreich ausgeführt!")

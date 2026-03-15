import sqlite3
import os

DB_PATH = "app.db"
MIGRATION_FILE = "backend/migrations/add_reaktiviert_column.sql"

with open(MIGRATION_FILE, "r", encoding="utf-8") as f:
    sql = f.read()

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.executescript(sql)
conn.commit()
conn.close()

print("Migration erfolgreich ausgeführt:", MIGRATION_FILE)

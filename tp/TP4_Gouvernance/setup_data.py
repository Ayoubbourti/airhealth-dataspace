"""Étape 0 - Création des deux bases SQLite indépendantes (données fictives)."""
from contextlib import closing
from pathlib import Path
import sqlite3

DOSSIER = Path(__file__).resolve().parent
DB_AIR = DOSSIER / "environnement.db"
DB_HOPITAL = DOSSIER / "hopital.db"

donnees_air = [
    ("2026-10-01", "Tanger", 12.0),
    ("2026-10-02", "Tanger", 35.5),
    ("2026-10-03", "Tanger", 42.1),
    ("2026-10-04", "Tanger", 15.2),
    ("2026-10-05", "Tanger", 38.0),
    ("2026-10-06", "Tanger", 45.0),
    ("2026-10-07", "Tanger", 22.1),
    ("2026-10-08", "Tanger", 18.0),
    ("2026-10-09", "Tanger", 31.0),
    ("2026-10-10", "Tanger", 11.5),
]

donnees_hopital = [
    ("2026-10-01", "Tanger", 8),
    ("2026-10-02", "Tanger", 14),
    ("2026-10-03", "Tanger", 18),
    ("2026-10-04", "Tanger", 9),
    ("2026-10-05", "Tanger", 16),
    ("2026-10-06", "Tanger", 20),
    ("2026-10-07", "Tanger", 10),
    ("2026-10-08", "Tanger", 7),
    ("2026-10-09", "Tanger", 13),
    ("2026-10-10", "Tanger", 5),
]

# closing() ferme réellement la connexion ; "with conn" seul ne fait que valider la transaction.
with closing(sqlite3.connect(DB_AIR)) as conn:
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS qualite_air (
                date TEXT PRIMARY KEY,
                ville TEXT NOT NULL,
                pm25 REAL NOT NULL CHECK(pm25 >= 0)
            )
        """)
        conn.execute("DELETE FROM qualite_air")
        conn.executemany(
            "INSERT INTO qualite_air (date, ville, pm25) VALUES (?, ?, ?)",
            donnees_air,
        )

with closing(sqlite3.connect(DB_HOPITAL)) as conn:
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS admissions (
                date TEXT PRIMARY KEY,
                ville TEXT NOT NULL,
                nombre INTEGER NOT NULL CHECK(nombre >= 0)
            )
        """)
        conn.execute("DELETE FROM admissions")
        conn.executemany(
            "INSERT INTO admissions (date, ville, nombre) VALUES (?, ?, ?)",
            donnees_hopital,
        )

print("Bases créées et données réinitialisées.")
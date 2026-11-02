import sqlite3

# Organisation A : environnement
db_air = sqlite3.connect("environnement.db")
db_air.execute("""
CREATE TABLE IF NOT EXISTS qualite_air (
    date TEXT PRIMARY KEY,
    ville TEXT,
    pm25 REAL
)
""")
db_air.execute("DELETE FROM qualite_air")
donnees_air = [
    ("2026-10-01", "Tanger", 12),
    ("2026-10-02", "Tanger", 35),
    ("2026-10-03", "Tanger", 42),
    ("2026-10-04", "Tanger", 15),
    ("2026-10-05", "Tanger", 38),
]
db_air.executemany("INSERT INTO qualite_air VALUES (?, ?, ?)", donnees_air)
db_air.commit()
db_air.close()

# Organisation B : hôpital
db_hopital = sqlite3.connect("hopital.db")
db_hopital.execute("""
CREATE TABLE IF NOT EXISTS admissions (
    date TEXT PRIMARY KEY,
    ville TEXT,
    nombre INTEGER
)
""")
db_hopital.execute("DELETE FROM admissions")
donnees_hopital = [
    ("2026-10-01", "Tanger", 8),
    ("2026-10-02", "Tanger", 14),
    ("2026-10-03", "Tanger", 18),
    ("2026-10-04", "Tanger", 9),
    ("2026-10-05", "Tanger", 16),
]
db_hopital.executemany("INSERT INTO admissions VALUES (?, ?, ?)", donnees_hopital)
db_hopital.commit()
db_hopital.close()

print("Deux bases locales ont été créées.")
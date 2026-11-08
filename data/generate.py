"""Génère 365 jours de données synthétiques pour les nœuds A et B."""
import math
import random
import sqlite3
from contextlib import closing
from datetime import date, timedelta
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
DB_AIR = RACINE / "nodes" / "node_a" / "environnement.db"
DB_HOPITAL = RACINE / "nodes" / "node_b" / "hopital.db"

SEED = 42
N_JOURS = 365
VILLE = "Tanger"
rng = random.Random(SEED)


def poisson(lam):
    """Échantillonneur de Poisson (Knuth), suffisant pour lam < 30."""
    seuil, k, p = math.exp(-lam), 0, 1.0
    while True:
        p *= rng.random()
        if p <= seuil:
            return k
        k += 1


jours = [date(2026, 1, 1) + timedelta(days=i) for i in range(N_JOURS)]
air, hopital = [], []
pm_veille, bruit_pm = 20.0, 0.0

for i, d in enumerate(jours):
    saison = math.cos(2 * math.pi * (i - 15) / 365)        # 1 = hiver
    temperature = 17 - 7 * saison + rng.gauss(0, 2)         # °C, variable confondante
    bruit_pm = 0.7 * bruit_pm + rng.gauss(0, 6)             # autocorrélation
    pic = rng.uniform(15, 35) if rng.random() < 0.06 else 0 # épisodes de pollution
    pm25 = max(2.0, 18 + 6 * saison + bruit_pm + pic)

    # Admissions : effet retardé (J-1) de la pollution + effet du froid.
    lam = 6 + 0.10 * pm_veille + 0.15 * max(0, 12 - temperature)
    admissions = min(30, poisson(lam))

    air.append((d.isoformat(), VILLE, round(pm25, 1)))
    hopital.append((d.isoformat(), VILLE, admissions))
    pm_veille = pm25

with closing(sqlite3.connect(DB_AIR)) as conn, conn:
    conn.execute("""CREATE TABLE IF NOT EXISTS qualite_air (
        date TEXT PRIMARY KEY, ville TEXT NOT NULL,
        pm25 REAL NOT NULL CHECK(pm25 >= 0))""")
    conn.execute("DELETE FROM qualite_air")
    conn.executemany("INSERT INTO qualite_air VALUES (?, ?, ?)", air)

with closing(sqlite3.connect(DB_HOPITAL)) as conn, conn:
    conn.execute("""CREATE TABLE IF NOT EXISTS admissions (
        date TEXT PRIMARY KEY, ville TEXT NOT NULL,
        nombre INTEGER NOT NULL CHECK(nombre >= 0))""")
    conn.execute("DELETE FROM admissions")
    conn.executemany("INSERT INTO admissions VALUES (?, ?, ?)", hopital)

hautes = [h[2] for a, h in zip(air, hopital) if a[2] > 30]
basses = [h[2] for a, h in zip(air, hopital) if a[2] <= 30]
print(f"{N_JOURS} jours générés (seed={SEED}).")
print(f"Jours PM2.5 > 30 : {len(hautes)} | moyenne admissions : {sum(hautes)/len(hautes):.2f}")
print(f"Jours PM2.5 <= 30 : {len(basses)} | moyenne admissions : {sum(basses)/len(basses):.2f}")
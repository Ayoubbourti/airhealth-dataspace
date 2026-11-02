import sqlite3
from fastapi import FastAPI

app = FastAPI(title="API Environnement")


@app.get("/")
def accueil():
    return {"organisation": "Direction de l'environnement"}


@app.get("/mesures")
def obtenir_mesures():
    db = sqlite3.connect("environnement.db")
    db.row_factory = sqlite3.Row
    lignes = db.execute("""
        SELECT date, ville, pm25
        FROM qualite_air ORDER BY date
    """).fetchall()
    db.close()
    return [dict(ligne) for ligne in lignes]


@app.get("/statistiques")
def statistiques():
    db = sqlite3.connect("environnement.db")
    resultat = db.execute("""
        SELECT COUNT(*), AVG(pm25) FROM qualite_air
    """).fetchone()
    db.close()
    return {
        "nombre_jours": resultat[0],
        "moyenne_pm25": round(resultat[1], 2),
    }
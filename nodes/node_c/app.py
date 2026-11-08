"""Nœud C - Laboratoire : orchestrateur + dashboard. Les clés restent côté serveur."""
from contextlib import closing
from pathlib import Path
import sqlite3

import requests
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse

app = FastAPI(title="Nœud C - Laboratoire")

DOSSIER = Path(__file__).resolve().parent
NODES = DOSSIER.parent
URL_A, URL_B = "http://127.0.0.1:8001", "http://127.0.0.1:8002"
HA = {"X-API-Key": "secret-air-key-demo"}
HB = {"X-API-Key": "secret-hospital-key-demo"}
CONSUMER, DATASET = "laboratoire-iasd", "dataset-air-tanger"
state = {"paquet": None}


def appel(methode, url, **kw):
    try:
        return requests.request(methode, url, timeout=10, **kw)
    except requests.ConnectionError:
        raise HTTPException(503, f"Service injoignable : {url}")


def rendre(r):
    return JSONResponse(status_code=r.status_code, content=r.json())


def nouveau_paquet(purpose="research"):
    r = appel("post", f"{URL_A}/contracts/negotiate", headers=HA,
              json={"dataset_id": DATASET, "consumer_id": CONSUMER, "purpose": purpose})
    if r.status_code != 200:
        return None, r
    cid = r.json()["contract_id"]
    r = appel("get", f"{URL_A}/classifications", headers=HA,
              params={"contract_id": cid, "consumer_id": CONSUMER})
    return (r.json() if r.status_code == 200 else None), r


@app.get("/")
def accueil():
    return FileResponse(DOSSIER / "static" / "index.html")


@app.get("/api/status")
def status():
    def vivant(url, **kw):
        try:
            return requests.get(url, timeout=2, **kw).status_code < 500
        except requests.ConnectionError:
            return False
    return {"A": vivant(f"{URL_A}/catalog"), "B": vivant(f"{URL_B}/budget", headers=HB, params={"consumer_id": CONSUMER})}


@app.get("/api/catalog")
def catalogue():
    return rendre(appel("get", f"{URL_A}/catalog"))


@app.post("/api/contract")
def contrat():
    paquet, r = nouveau_paquet()
    if paquet is None:
        return rendre(r)
    state["paquet"] = paquet
    return {"contract_id": paquet["contract_id"], "jours": len(paquet["classifications"]),
            "signature": paquet["signature"][:16] + "…"}


@app.post("/api/compute")
def calcul():
    if not state["paquet"]:
        raise HTTPException(400, "Négociez d'abord un contrat")
    return rendre(appel("post", f"{URL_B}/compute", headers=HB, json=state["paquet"]))


@app.get("/api/budget")
def budget():
    return rendre(appel("get", f"{URL_B}/budget", headers=HB, params={"consumer_id": CONSUMER}))


@app.get("/api/audit")
def audit():
    r = appel("get", f"{URL_B}/audit", headers=HB)
    return rendre(r)


@app.get("/api/truth")
def verite():
    """DÉMO UNIQUEMENT : le labo n'a normalement aucun accès aux bases."""
    with closing(sqlite3.connect(NODES / "node_a" / "environnement.db")) as a, \
         closing(sqlite3.connect(NODES / "node_b" / "hopital.db")) as b:
        pm = dict(a.execute("SELECT date, pm25 FROM qualite_air").fetchall())
        adm = dict(b.execute("SELECT date, nombre FROM admissions").fetchall())
    h = [adm[d] for d in pm if pm[d] > 30 and d in adm]
    l = [adm[d] for d in pm if pm[d] <= 30 and d in adm]
    return {"haute": round(sum(h) / len(h), 2), "basse": round(sum(l) / len(l), 2)}


@app.post("/api/attack")
def attaque(epuiser: bool = False):
    p = state["paquet"] or nouveau_paquet()[0]
    state["paquet"] = p
    log = []

    def test(nom, attendu, r):
        log.append({"test": nom, "attendu": attendu, "recu": r.status_code, "bloque": r.status_code == attendu})

    test("Sous-ensemble de dates (attaque TP3)", 403,
         appel("post", f"{URL_B}/compute", headers=HB, json={**p, "classifications": p["classifications"][:4]}))
    test("Signature falsifiée", 403,
         appel("post", f"{URL_B}/compute", headers=HB, json={**p, "signature": "0" * 64}))
    test("Clé API incorrecte", 401,
         appel("post", f"{URL_B}/compute", headers={"X-API-Key": "abc"}, json=p))
    test("Finalité commerciale", 403,
         appel("post", f"{URL_A}/contracts/negotiate", headers=HA,
               json={"dataset_id": DATASET, "consumer_id": CONSUMER, "purpose": "commercial"}))
    if epuiser:
        for _ in range(5):
            if appel("post", f"{URL_B}/compute", headers=HB, json=p).status_code == 429:
                break
        p2, _ = nouveau_paquet()
        test("Nouveau contrat pour réinitialiser ε", 429, appel("post", f"{URL_B}/compute", headers=HB, json=p2))
    return log
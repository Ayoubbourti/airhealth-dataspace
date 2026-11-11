"""Nœud C - Laboratoire : orchestrateur + dashboard. Les clés restent côté serveur."""
from contextlib import closing
from pathlib import Path
import math
import random
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

# ---------------------------------------------------------------------------
# ML fédéré : l'hôpital publie des taux bruités par tranche de PM2.5 (veille),
# le laboratoire ajuste log(taux) = b0 + b1 * tranche.
# ---------------------------------------------------------------------------
BORNES = (15.0, 25.0, 35.0)
LABELS = ["< 15", "15 à 25", "25 à 35", "≥ 35"]


def ajuster(points):
    """Régression log(taux) = b0 + b1*tranche, pondérée par n*taux (approx. Poisson)."""
    pts = [(k, math.log(t), n * t) for k, n, t in points if t is not None]
    if len(pts) < 2:
        return None
    sw = sum(w for _, _, w in pts)
    mx = sum(w * x for x, _, w in pts) / sw
    my = sum(w * y for _, y, w in pts) / sw
    sxx = sum(w * (x - mx) ** 2 for x, _, w in pts)
    b1 = sum(w * (x - mx) * (y - my) for x, y, w in pts) / sxx
    return my - b1 * mx, b1


def tranches_verite():
    """DÉMO UNIQUEMENT : lit les deux bases pour comparer au résultat bruité."""
    with closing(sqlite3.connect(NODES / "node_a" / "environnement.db")) as a, \
         closing(sqlite3.connect(NODES / "node_b" / "hopital.db")) as b:
        pm = a.execute("SELECT date, pm25 FROM qualite_air ORDER BY date").fetchall()
        adm = dict(b.execute("SELECT date, nombre FROM admissions").fetchall())
    g = {k: [] for k in range(4)}
    for i in range(1, len(pm)):
        g[sum(1 for x in BORNES if pm[i - 1][1] >= x)].append(adm[pm[i][0]])
    return [(k, len(v), sum(v) / len(v)) for k, v in g.items() if len(v) >= 3]


@app.post("/api/ml/train")
def ml_train():
    r = appel("post", f"{URL_A}/contracts/negotiate", headers=HA,
              json={"dataset_id": DATASET, "consumer_id": CONSUMER, "purpose": "research"})
    if r.status_code != 200:
        return rendre(r)
    cid = r.json()["contract_id"]
    r = appel("get", f"{URL_A}/features", headers=HA,
              params={"contract_id": cid, "consumer_id": CONSUMER})
    if r.status_code != 200:
        return rendre(r)
    r = appel("post", f"{URL_B}/train", headers=HB, json=r.json())
    if r.status_code != 200:
        return rendre(r)
    res = r.json()
    fit = ajuster([(t["tranche"], t["n"], t["taux"]) for t in res["tranches"]])
    if fit is None:
        raise HTTPException(400, "Pas assez de tranches publiées")
    verite = tranches_verite()
    fit_v = ajuster(verite)
    return {
        "labels": LABELS,
        "tranches": res["tranches"],
        "beta1": round(fit[1], 4),
        "effet_pct": round((math.exp(fit[1]) - 1) * 100, 1),
        "vrai_beta1": round(fit_v[1], 4),
        "vrais_taux": [round(t, 3) for _, _, t in verite],
        "epsilon_restant": res["epsilon_restant"],
    }


@app.get("/api/ml/curve")
def ml_curve(reps: int = 300):
    """DÉMO : simule le mécanisme pour plusieurs ε (aucun budget consommé)."""
    verite = tranches_verite()
    vrai = ajuster(verite)[1]
    rng = random.Random(7)
    sortie = []
    for eps in (0.1, 0.25, 0.5, 1, 2, 5):
        erreurs = []
        for _ in range(reps):
            pts = []
            for k, n, t in verite:
                echelle = (30.0 / n) / eps
                bruit = rng.expovariate(1 / echelle) - rng.expovariate(1 / echelle)
                pts.append((k, n, min(max(t + bruit, 0.1), 30.0)))
            erreurs.append(abs(ajuster(pts)[1] - vrai))
        erreurs.sort()
        sortie.append({"epsilon": eps, "erreur_mediane": round(erreurs[len(erreurs) // 2], 4)})
    return {"vrai_beta1": round(vrai, 4), "points": sortie}


# ---------------------------------------------------------------------------
# Interopérabilité sémantique : catalogues DCAT, politique ODRL, SPARQL.
# ---------------------------------------------------------------------------
@app.get("/api/semantic/catalogs")
def catalogues_ld():
    """Catalogues DCAT (JSON-LD) des nœuds A et B, et politique ODRL de A."""
    return {
        "A": appel("get", f"{URL_A}/catalog.jsonld").json(),
        "B": appel("get", f"{URL_B}/catalog.jsonld").json(),
        "politique_A": appel("get", f"{URL_A}/policy").json(),
    }


@app.get("/api/semantic/sparql")
def sparql_proxy(query: str):
    return rendre(appel("get", f"{URL_A}/sparql", params={"query": query}))

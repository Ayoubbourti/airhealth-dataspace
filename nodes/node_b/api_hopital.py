"""Nœud B v2 - Hôpital : bruit imposé, budget persistant par (consommateur, dataset), audit chaîné."""
from contextlib import closing
from pathlib import Path
import hashlib
import hmac
import json
import math
import os
import random
import sqlite3
import time

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Nœud B v2 - Hôpital")

DOSSIER = Path(__file__).resolve().parent
DB_HOPITAL = DOSSIER / "hopital.db"
DB_GOUV = DOSSIER / "gouvernance_b.db"

# Valeurs de démonstration : à ne JAMAIS utiliser en production.
CLE_API_B = os.getenv("CLE_HOPITAL", "secret-hospital-key-demo")
SECRET_FEDERATION = os.getenv("SECRET_FEDERATION", "secret-federation-demo").encode()

DATASET_ID = "dataset-air-tanger"
CATEGORIES_VALIDES = {"au_dessus_seuil", "sous_seuil"}
SEUIL_MIN_JOURS = 3            # seuil minimal de publication (PAS du k-anonymat)
BORNE_MAX = 30.0               # borne pédagogique d'admissions par jour
EPSILON_PAR_REQUETE = 1.0      # fixé par l'hôpital, pas par le client
BUDGET_EPSILON = 3.0           # budget total par (consommateur, dataset)
RNG = random.SystemRandom()


class Classification(BaseModel):
    date: str
    categorie: str


class RequeteCalcul(BaseModel):
    # apply_dp et epsilon envoyés par un client sont ignorés (champs inconnus).
    contract_id: str
    consumer_id: str
    classifications: list[Classification]
    signature: str


# ---------- Base de gouvernance (budget + audit) ----------

def ouvrir():
    conn = sqlite3.connect(DB_GOUV, timeout=10)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS budget (
            consumer_id TEXT NOT NULL,
            dataset_id TEXT NOT NULL,
            epsilon_utilise REAL NOT NULL,
            PRIMARY KEY (consumer_id, dataset_id)
        );
        CREATE TABLE IF NOT EXISTS audit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL,
            consumer_id TEXT,
            contract_id TEXT,
            evenement TEXT NOT NULL,
            code INTEGER NOT NULL,
            epsilon REAL,
            prev_hash TEXT NOT NULL,
            hash TEXT NOT NULL
        );
    """)
    return conn


def calculer_hash(ts, consumer_id, contract_id, evenement, code, epsilon, prev):
    contenu = json.dumps([ts, consumer_id, contract_id, evenement, code, epsilon, prev])
    return hashlib.sha256(contenu.encode("utf-8")).hexdigest()


def journaliser(consumer_id, contract_id, evenement, code, epsilon=None):
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with closing(ouvrir()) as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT hash FROM audit ORDER BY id DESC LIMIT 1").fetchone()
        prev = row[0] if row else "0" * 64
        h = calculer_hash(ts, consumer_id, contract_id, evenement, code, epsilon, prev)
        conn.execute(
            "INSERT INTO audit (ts, consumer_id, contract_id, evenement, code, epsilon, prev_hash, hash) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (ts, consumer_id, contract_id, evenement, code, epsilon, prev, h),
        )
        conn.commit()


def verifier_chaine():
    with closing(ouvrir()) as conn:
        lignes = conn.execute(
            "SELECT id, ts, consumer_id, contract_id, evenement, code, epsilon, prev_hash, hash "
            "FROM audit ORDER BY id"
        ).fetchall()
    prev = "0" * 64
    for (id_, ts, cons, contrat, evt, code, eps, prev_hash, h) in lignes:
        if prev_hash != prev or calculer_hash(ts, cons, contrat, evt, code, eps, prev) != h:
            return False, id_
        prev = h
    return True, None


def consommer_budget(consumer_id, epsilon):
    """Consomme epsilon de façon atomique. Retourne (ok, epsilon_utilisé_après)."""
    with closing(ouvrir()) as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            "SELECT epsilon_utilise FROM budget WHERE consumer_id = ? AND dataset_id = ?",
            (consumer_id, DATASET_ID),
        ).fetchone()
        utilise = row[0] if row else 0.0
        if utilise + epsilon > BUDGET_EPSILON + 1e-9:
            conn.rollback()
            return False, utilise
        conn.execute(
            "INSERT INTO budget (consumer_id, dataset_id, epsilon_utilise) VALUES (?, ?, ?) "
            "ON CONFLICT(consumer_id, dataset_id) DO UPDATE SET epsilon_utilise = excluded.epsilon_utilise",
            (consumer_id, DATASET_ID, utilise + epsilon),
        )
        conn.commit()
        return True, utilise + epsilon


# ---------- Calcul ----------

def verifier_cle(x_api_key):
    if x_api_key is None or not hmac.compare_digest(x_api_key, CLE_API_B):
        raise HTTPException(status_code=401, detail="Clé API invalide")


def signature_attendue(req):
    message = json.dumps(
        {
            "contract_id": req.contract_id,
            "consumer_id": req.consumer_id,
            "classifications": [c.model_dump() for c in req.classifications],
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hmac.new(SECRET_FEDERATION, message, hashlib.sha256).hexdigest()


def bruit_laplace(echelle):
    u = RNG.random() - 0.5
    while u == -0.5:
        u = RNG.random() - 0.5
    return -echelle * math.copysign(1.0, u) * math.log(1 - 2 * abs(u))


def resumer(valeurs, epsilon):
    n = len(valeurs)
    if n < SEUIL_MIN_JOURS:
        return {"n": n, "moyenne": None, "statut": "SUPPRIME_GROUPE_TROP_PETIT"}
    moyenne = sum(valeurs) / n
    moyenne += bruit_laplace((BORNE_MAX / n) / epsilon)   # bruit TOUJOURS appliqué
    moyenne = min(max(moyenne, 0.0), BORNE_MAX)
    return {"n": n, "moyenne": round(moyenne, 2), "statut": "OK"}


def traiter(req, x_api_key):
    verifier_cle(x_api_key)
    if not hmac.compare_digest(req.signature, signature_attendue(req)):
        raise HTTPException(status_code=403, detail="Signature invalide : classification non émise par le nœud A")
    if not req.classifications:
        raise HTTPException(status_code=400, detail="Liste de classifications vide")

    dates = [c.date for c in req.classifications]
    if len(dates) != len(set(dates)):
        raise HTTPException(status_code=400, detail="Date dupliquée")
    for c in req.classifications:
        if c.categorie not in CATEGORIES_VALIDES:
            raise HTTPException(status_code=400, detail=f"Catégorie inconnue : {c.categorie}")

    with closing(sqlite3.connect(DB_HOPITAL)) as conn:
        admissions = dict(conn.execute("SELECT date, nombre FROM admissions").fetchall())
    inconnues = [d for d in dates if d not in admissions]
    if inconnues:
        raise HTTPException(status_code=400, detail=f"Dates absentes de la base hospitalière : {inconnues}")

    ok, utilise = consommer_budget(req.consumer_id, EPSILON_PAR_REQUETE)
    if not ok:
        raise HTTPException(status_code=429, detail="Budget de confidentialité épuisé pour ce consommateur et ce jeu de données")

    groupes = {cat: [] for cat in CATEGORIES_VALIDES}
    for c in req.classifications:
        groupes[c.categorie].append(admissions[c.date])

    return {
        "au_dessus_seuil": resumer(groupes["au_dessus_seuil"], EPSILON_PAR_REQUETE),
        "sous_seuil": resumer(groupes["sous_seuil"], EPSILON_PAR_REQUETE),
        "bruit_applique": True,
        "epsilon": EPSILON_PAR_REQUETE,
        "epsilon_restant": round(BUDGET_EPSILON - utilise, 2),
    }


@app.post("/compute")
def calculer(req: RequeteCalcul, x_api_key: str | None = Header(default=None)):
    try:
        resultat = traiter(req, x_api_key)
    except HTTPException as e:
        journaliser(req.consumer_id, req.contract_id, f"REFUSE: {e.detail}", e.status_code)
        raise
    journaliser(req.consumer_id, req.contract_id, "CALCUL_OK", 200, EPSILON_PAR_REQUETE)
    return resultat


@app.get("/audit")
def lire_audit(x_api_key: str | None = Header(default=None)):
    verifier_cle(x_api_key)
    valide, id_faux = verifier_chaine()
    with closing(ouvrir()) as conn:
        lignes = conn.execute(
            "SELECT id, ts, consumer_id, contract_id, evenement, code, epsilon "
            "FROM audit ORDER BY id DESC LIMIT 20"
        ).fetchall()
    return {"chaine_valide": valide, "premiere_ligne_alteree": id_faux, "dernieres_entrees": lignes}
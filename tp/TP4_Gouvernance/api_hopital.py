"""Étape 2 - Nœud B (Hôpital) : calcul local d'agrégats, seuil minimal, bruit de Laplace."""
from contextlib import closing
from pathlib import Path
import hashlib
import hmac
import json
import math
import os
import random
import sqlite3

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="Nœud B - Hôpital")

DOSSIER = Path(__file__).resolve().parent
DB_HOPITAL = DOSSIER / "hopital.db"

CLE_API_B = os.getenv("CLE_HOPITAL", "secret-hospital-key-demo")
SECRET_FEDERATION = os.getenv("SECRET_FEDERATION", "secret-federation-demo").encode()

CATEGORIES_VALIDES = {"au_dessus_seuil", "sous_seuil"}
SEUIL_MIN_JOURS = 3      # seuil minimal de publication (PAS du k-anonymat)
BORNE_MAX = 30.0         # borne pédagogique d'admissions par jour
BUDGET_EPSILON = 3.0     # budget cumulé par contrat (simulation)
RNG = random.SystemRandom()  # source d'aléa non prévisible

budget_utilise = {}      # contract_id -> epsilon consommé


class Classification(BaseModel):
    date: str
    categorie: str


class RequeteCalcul(BaseModel):
    contract_id: str
    consumer_id: str
    classifications: list[Classification]
    signature: str
    apply_dp: bool = False
    epsilon: float = Field(default=1.0, gt=0)


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
    while u == -0.5:  # évite log(0)
        u = RNG.random() - 0.5
    return -echelle * math.copysign(1.0, u) * math.log(1 - 2 * abs(u))


def resumer(valeurs, apply_dp, epsilon):
    n = len(valeurs)
    if n < SEUIL_MIN_JOURS:
        return {"n": n, "moyenne": None, "statut": "SUPPRIME_GROUPE_TROP_PETIT"}
    moyenne = sum(valeurs) / n
    if apply_dp:
        sensibilite = BORNE_MAX / n  # moyenne d'un groupe de taille n fixée
        moyenne += bruit_laplace(sensibilite / epsilon)
        moyenne = min(max(moyenne, 0.0), BORNE_MAX)  # post-traitement
    return {"n": n, "moyenne": round(moyenne, 2), "statut": "OK"}


@app.post("/compute")
def calculer(
    req: RequeteCalcul,
    x_api_key: str | None = Header(default=None),
):
    verifier_cle(x_api_key)

    # Seules les classifications émises par A pour un contrat valide sont acceptées.
    if not hmac.compare_digest(req.signature, signature_attendue(req)):
        raise HTTPException(
            status_code=403,
            detail="Signature invalide : classification non émise par le nœud A",
        )
    if not req.classifications:
        raise HTTPException(status_code=400, detail="Liste de classifications vide")

    dates = [c.date for c in req.classifications]
    if len(dates) != len(set(dates)):
        raise HTTPException(status_code=400, detail="Date dupliquée")
    for c in req.classifications:
        if c.categorie not in CATEGORIES_VALIDES:
            raise HTTPException(
                status_code=400, detail=f"Catégorie inconnue : {c.categorie}"
            )

    with closing(sqlite3.connect(DB_HOPITAL)) as conn:
        admissions = dict(conn.execute("SELECT date, nombre FROM admissions").fetchall())

    inconnues = [d for d in dates if d not in admissions]
    if inconnues:
        raise HTTPException(
            status_code=400,
            detail=f"Dates absentes de la base hospitalière : {inconnues}",
        )

    if req.apply_dp:
        utilise = budget_utilise.get(req.contract_id, 0.0)
        if utilise + req.epsilon > BUDGET_EPSILON:
            raise HTTPException(
                status_code=429,
                detail="Budget de confidentialité épuisé pour ce contrat",
            )
        budget_utilise[req.contract_id] = utilise + req.epsilon

    groupes = {cat: [] for cat in CATEGORIES_VALIDES}
    for c in req.classifications:
        groupes[c.categorie].append(admissions[c.date])

    return {
        "au_dessus_seuil": resumer(groupes["au_dessus_seuil"], req.apply_dp, req.epsilon),
        "sous_seuil": resumer(groupes["sous_seuil"], req.apply_dp, req.epsilon),
        "bruit_applique": req.apply_dp,
        "epsilon": req.epsilon if req.apply_dp else None,
    }
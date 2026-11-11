"""Étape 1 - Nœud A (Environnement) : catalogue, contrat, classification signée."""
from contextlib import closing
from pathlib import Path
import hashlib
import hmac
import json
import os
import sqlite3
import sys
import uuid

from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI(title="Nœud A - Environnement")

DOSSIER = Path(__file__).resolve().parent
DB_AIR = DOSSIER / "environnement.db"

# Couche sémantique partagée (DCAT, ODRL, SPARQL) : dossier semantic/ à la racine du dépôt.
sys.path.insert(0, str(DOSSIER.parent.parent / "semantic"))
import airhealth_semantic as sem  # noqa: E402

CATALOGUE_LD = sem.charger("catalog_air.jsonld")
POLITIQUE = sem.charger("policy_air.jsonld")
GRAPHE = sem.construire_graphe(CATALOGUE_LD, POLITIQUE)

# Valeurs de démonstration : à ne JAMAIS utiliser en production.
CLE_API_A = os.getenv("CLE_AIR", "secret-air-key-demo")
SECRET_FEDERATION = os.getenv("SECRET_FEDERATION", "secret-federation-demo").encode()

DATASET_ID = "dataset-air-tanger"
FINALITE_AUTORISEE = "research"
CONSOMMATEURS_AUTORISES = {"laboratoire-iasd"}
SEUIL_PM25 = 30.0  # seuil pédagogique (µg/m³), pas une référence réglementaire

# Catalogue simplifié inspiré de DCAT (non conforme au standard).
CATALOGUE = [
    {
        "dataset_id": DATASET_ID,
        "title": "Qualité de l'air - PM2.5 à Tanger",
        "description": "Concentrations journalières de PM2.5 (données fictives).",
        "publisher": "Organisation Environnement",
        "temporal_coverage": "2026-01-01/2026-12-31",
        "unit": "µg/m³",
        "access_endpoint": "/contracts/negotiate",
        "allowed_purpose": FINALITE_AUTORISEE,  # règle inspirée d'ODRL
    }
]

# Contrats en mémoire : perdus au redémarrage du serveur.
contrats = {}


class DemandeContrat(BaseModel):
    dataset_id: str
    consumer_id: str
    purpose: str


def verifier_cle(x_api_key):
    if x_api_key is None or not hmac.compare_digest(x_api_key, CLE_API_A):
        raise HTTPException(status_code=401, detail="Clé API invalide")


def signer(contract_id, consumer_id, classifications):
    """Signature HMAC partagée avec le nœud B."""
    message = json.dumps(
        {
            "contract_id": contract_id,
            "consumer_id": consumer_id,
            "classifications": classifications,
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hmac.new(SECRET_FEDERATION, message, hashlib.sha256).hexdigest()


@app.get("/catalog")
def lire_catalogue():
    return CATALOGUE


@app.get("/catalog.jsonld")
def catalogue_dcat():
    """Catalogue DCAT en JSON-LD (standard W3C), avec référence à la politique ODRL."""
    return JSONResponse(CATALOGUE_LD, media_type="application/ld+json")


@app.get("/policy")
def politique_odrl():
    """Politique d'usage ODRL en JSON-LD."""
    return JSONResponse(POLITIQUE, media_type="application/ld+json")


@app.get("/sparql")
def sparql(query: str = Query(..., max_length=2000)):
    """Requêtes SPARQL en lecture seule sur le catalogue et la politique."""
    try:
        return sem.sparql_lecture_seule(GRAPHE, query)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/contracts/negotiate")
def negocier_contrat(
    demande: DemandeContrat,
    x_api_key: str | None = Header(default=None),
):
    verifier_cle(x_api_key)
    if demande.dataset_id != DATASET_ID:
        raise HTTPException(status_code=404, detail="Jeu de données inexistant")
    # La décision vient de la politique ODRL (semantic/policy_air.jsonld), pas d'un test codé en dur.
    autorise, raison = sem.evaluer(
        POLITIQUE, action="use", purpose=demande.purpose, recipient=demande.consumer_id
    )
    if not autorise:
        raise HTTPException(status_code=403, detail=raison)

    contract_id = f"contract-air-{uuid.uuid4().hex[:8]}"
    contrats[contract_id] = {
        "status": "AGREED",
        "dataset_id": demande.dataset_id,
        "consumer_id": demande.consumer_id,
        "purpose": demande.purpose,
    }
    return {"contract_id": contract_id, "status": "AGREED"}


@app.get("/classifications")
def lire_classifications(
    contract_id: str,
    consumer_id: str,
    x_api_key: str | None = Header(default=None),
):
    verifier_cle(x_api_key)
    contrat = contrats.get(contract_id)
    if contrat is None:
        raise HTTPException(status_code=403, detail="Contrat inconnu")
    if contrat["status"] != "AGREED" or contrat["dataset_id"] != DATASET_ID:
        raise HTTPException(status_code=403, detail="Contrat non applicable")
    if (contrat["purpose"] != FINALITE_AUTORISEE
            or contrat["consumer_id"] != consumer_id):
        raise HTTPException(
            status_code=403, detail="Consommateur ou finalité non autorisé"
        )

    with closing(sqlite3.connect(DB_AIR)) as conn:
        lignes = conn.execute(
            "SELECT date, pm25 FROM qualite_air ORDER BY date"
        ).fetchall()

    classifications = [
        {
            "date": date,
            "categorie": "au_dessus_seuil" if pm25 > SEUIL_PM25 else "sous_seuil",
        }
        for date, pm25 in lignes
    ]
    return {
        "contract_id": contract_id,
        "consumer_id": consumer_id,
        "classifications": classifications,
        "signature": signer(contract_id, consumer_id, classifications),
    }

BORNES_TRANCHES = (15.0, 25.0, 35.0)  # tranches 0 : <15, 1 : 15-25, 2 : 25-35, 3 : >=35


def tranche(pm25):
    return sum(1 for b in BORNES_TRANCHES if pm25 >= b)


def signer_features(contract_id, consumer_id, features):
    message = json.dumps(
        {"type": "features", "contract_id": contract_id,
         "consumer_id": consumer_id, "features": features},
        sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")
    return hmac.new(SECRET_FEDERATION, message, hashlib.sha256).hexdigest()


@app.get("/features")
def lire_features(
    contract_id: str,
    consumer_id: str,
    x_api_key: str | None = Header(default=None),
):
    verifier_cle(x_api_key)
    contrat = contrats.get(contract_id)
    if contrat is None:
        raise HTTPException(status_code=403, detail="Contrat inconnu")
    if (contrat["status"] != "AGREED" or contrat["dataset_id"] != DATASET_ID
            or contrat["purpose"] != FINALITE_AUTORISEE
            or contrat["consumer_id"] != consumer_id):
        raise HTTPException(status_code=403, detail="Contrat non applicable")

    with closing(sqlite3.connect(DB_AIR)) as conn:
        lignes = conn.execute(
            "SELECT date, pm25 FROM qualite_air ORDER BY date"
        ).fetchall()

    # PM2.5 de la veille, en tranches : l'effet est retardé d'un jour.
    features = [
        {"date": lignes[i][0], "tranche": tranche(lignes[i - 1][1])}
        for i in range(1, len(lignes))
    ]
    return {
        "contract_id": contract_id,
        "consumer_id": consumer_id,
        "features": features,
        "signature": signer_features(contract_id, consumer_id, features),
    }
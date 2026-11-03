"""Étape 1 - Nœud A (Environnement) : catalogue, contrat, classification signée."""
from contextlib import closing
from pathlib import Path
import hashlib
import hmac
import json
import os
import sqlite3
import uuid

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Nœud A - Environnement")

DOSSIER = Path(__file__).resolve().parent
DB_AIR = DOSSIER / "environnement.db"

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
        "temporal_coverage": "2026-10-01/2026-10-10",
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


@app.post("/contracts/negotiate")
def negocier_contrat(
    demande: DemandeContrat,
    x_api_key: str | None = Header(default=None),
):
    verifier_cle(x_api_key)
    if demande.dataset_id != DATASET_ID:
        raise HTTPException(status_code=404, detail="Jeu de données inexistant")
    if demande.purpose != FINALITE_AUTORISEE:
        raise HTTPException(status_code=403, detail="Finalité non autorisée")
    if demande.consumer_id not in CONSOMMATEURS_AUTORISES:
        raise HTTPException(status_code=403, detail="Consommateur non autorisé")

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
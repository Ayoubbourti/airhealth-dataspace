"""Attaque n°2 rejouée contre le nœud B v2 : doit échouer."""
import requests

URL_AIR = "http://127.0.0.1:8001"
URL_HOPITAL = "http://127.0.0.1:8002"
CLE_A = "secret-air-key-demo"
CLE_B = "secret-hospital-key-demo"
CONSUMER_ID = "laboratoire-iasd"
DATASET_ID = "dataset-air-tanger"
TIMEOUT = 10
session = requests.Session()


def nouveau_paquet():
    r = session.post(
        f"{URL_AIR}/contracts/negotiate",
        json={"dataset_id": DATASET_ID, "consumer_id": CONSUMER_ID, "purpose": "research"},
        headers={"X-API-Key": CLE_A}, timeout=TIMEOUT,
    )
    r.raise_for_status()
    cid = r.json()["contract_id"]
    r = session.get(
        f"{URL_AIR}/classifications",
        params={"contract_id": cid, "consumer_id": CONSUMER_ID},
        headers={"X-API-Key": CLE_A}, timeout=TIMEOUT,
    )
    r.raise_for_status()
    return r.json()


def calcul(paquet, **extra):
    return session.post(
        f"{URL_HOPITAL}/compute", json={**paquet, **extra},
        headers={"X-API-Key": CLE_B}, timeout=TIMEOUT,
    )


print("=== Étape 1 : le client essaie de désactiver le bruit (apply_dp=false) ===")
paquet = nouveau_paquet()
r = calcul(paquet, apply_dp=False)
print("Code :", r.status_code, "| bruit_applique :", r.json()["bruit_applique"],
      "| moyenne haute :", r.json()["au_dessus_seuil"]["moyenne"], "(réel 16.2)")

print("\n=== Étape 2 : épuisement du budget sur ce contrat ===")
codes = [200] + [calcul(paquet).status_code for _ in range(3)]
print("Codes :", codes, "(attendu 200,200,200,429)")

print("\n=== Étape 3 : nouveau contrat pour remettre le budget à zéro ===")
r = calcul(nouveau_paquet())
print("Code :", r.status_code, "(attendu 429 : l'attaque est bloquée)")

print("\n=== Étape 4 : 40 contrats supplémentaires ===")
succes = sum(1 for _ in range(40) if calcul(nouveau_paquet()).status_code == 200)
print("Réponses obtenues :", succes, "(attendu 0)")

print("\n=== Étape 5 : intégrité du journal d'audit ===")
r = session.get(f"{URL_HOPITAL}/audit", headers={"X-API-Key": CLE_B}, timeout=TIMEOUT)
print("Chaîne valide :", r.json()["chaine_valide"])
"""Attaque n°2 : contourner le budget epsilon en négociant plusieurs contrats."""
import statistics
import sys

import requests

URL_AIR = "http://127.0.0.1:8001"
URL_HOPITAL = "http://127.0.0.1:8002"
CLE_A = "secret-air-key-demo"
CLE_B = "secret-hospital-key-demo"
CONSUMER_ID = "laboratoire-iasd"
DATASET_ID = "dataset-air-tanger"
TIMEOUT = 10

N_CONTRATS = int(sys.argv[1]) if len(sys.argv) > 1 else 40
EPSILON = 1.0

session = requests.Session()


def nouveau_paquet():
    """Négocie un contrat neuf et récupère les classifications signées."""
    r = session.post(
        f"{URL_AIR}/contracts/negotiate",
        json={"dataset_id": DATASET_ID, "consumer_id": CONSUMER_ID, "purpose": "research"},
        headers={"X-API-Key": CLE_A},
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    contract_id = r.json()["contract_id"]
    r = session.get(
        f"{URL_AIR}/classifications",
        params={"contract_id": contract_id, "consumer_id": CONSUMER_ID},
        headers={"X-API-Key": CLE_A},
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    return r.json()


def calcul(paquet, bruit=True):
    return session.post(
        f"{URL_HOPITAL}/compute",
        json={**paquet, "apply_dp": bruit, "epsilon": EPSILON},
        headers={"X-API-Key": CLE_B},
        timeout=TIMEOUT,
    )


print("=== Étape 1 : le budget est bien limité par contrat ===")
paquet = nouveau_paquet()
codes = [calcul(paquet).status_code for _ in range(4)]
print("Codes des 4 appels bruités sur UN contrat :", codes, "(attendu 200,200,200,429)")

print("\n=== Étape 2 : un nouveau contrat remet le budget à zéro ===")
paquet = nouveau_paquet()
print("Appel bruité sur un contrat neuf :", calcul(paquet).status_code, "(attendu 200)")

print(f"\n=== Étape 3 : moyenne de {N_CONTRATS} contrats x 3 appels bruités ===")
hautes, basses = [], []
for _ in range(N_CONTRATS):
    paquet = nouveau_paquet()
    for _ in range(3):  # 3 x epsilon=1 = budget max du contrat
        r = calcul(paquet)
        r.raise_for_status()
        res = r.json()
        hautes.append(res["au_dessus_seuil"]["moyenne"])
        basses.append(res["sous_seuil"]["moyenne"])

m_haut = statistics.mean(hautes)
m_bas = statistics.mean(basses)
print(f"Nombre de réponses bruitées utilisées : {len(hautes)}")
print(f"Estimation au-dessus du seuil : {m_haut:.2f}   (valeur réelle 16.2)")
print(f"Estimation sous le seuil      : {m_bas:.2f}   (valeur réelle 7.8)")
print(f"Différence estimée            : {m_haut - m_bas:.2f}   (valeur réelle 8.4)")

print("\n=== Étape 4 : sans bruit du tout (apply_dp absent) ===")
r = calcul(nouveau_paquet(), bruit=False)
print("Réponse exacte obtenue directement :", r.json()["au_dessus_seuil"], r.json()["sous_seuil"])
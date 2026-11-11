"""Nœud A : catalogue, contrat, contrôles d'accès, signature."""
from conftest import CLE_A, CONSUMER, DATASET


def demande(**modif):
    corps = {"dataset_id": DATASET, "consumer_id": CONSUMER, "purpose": "research"}
    corps.update(modif)
    return corps


def test_catalogue_accessible(client_a):
    r = client_a.get("/catalog")
    assert r.status_code == 200
    assert r.json()[0]["dataset_id"] == DATASET


def test_contrat_autorise(client_a):
    r = client_a.post("/contracts/negotiate", headers=CLE_A, json=demande())
    assert r.status_code == 200
    assert r.json()["status"] == "AGREED"


def test_finalite_commerciale_refusee(client_a):
    r = client_a.post("/contracts/negotiate", headers=CLE_A, json=demande(purpose="commercial"))
    assert r.status_code == 403


def test_cle_incorrecte_refusee(client_a):
    r = client_a.post("/contracts/negotiate", headers={"X-API-Key": "abc"}, json=demande())
    assert r.status_code == 401


def test_dataset_inexistant(client_a):
    r = client_a.post("/contracts/negotiate", headers=CLE_A, json=demande(dataset_id="inconnu"))
    assert r.status_code == 404


def test_consommateur_non_autorise(client_a):
    r = client_a.post("/contracts/negotiate", headers=CLE_A, json=demande(consumer_id="pirate"))
    assert r.status_code == 403


def test_classifications_sans_contrat(client_a):
    r = client_a.get("/classifications", headers=CLE_A,
                     params={"contract_id": "contract-air-inexistant", "consumer_id": CONSUMER})
    assert r.status_code == 403


def test_classifications_signees_et_correctes(nouveau_paquet):
    paquet = nouveau_paquet()
    assert len(paquet["classifications"]) == 10
    assert len(paquet["signature"]) == 64
    categories = {c["date"]: c["categorie"] for c in paquet["classifications"]}
    assert categories["2026-10-02"] == "au_dessus_seuil"   # 35.5 > 30
    assert categories["2026-10-07"] == "sous_seuil"        # 22.1
    assert categories["2026-10-09"] == "au_dessus_seuil"   # 31.0 > 30

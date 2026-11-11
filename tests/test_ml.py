"""ML fédéré : features signées, taux bruités par tranche."""
from conftest import CLE_A, CLE_B, CONSUMER, DATASET


def features(client_a):
    r = client_a.post("/contracts/negotiate", headers=CLE_A, json={
        "dataset_id": DATASET, "consumer_id": CONSUMER, "purpose": "research"})
    cid = r.json()["contract_id"]
    return client_a.get("/features", headers=CLE_A,
                        params={"contract_id": cid, "consumer_id": CONSUMER})


def test_features_veille_en_tranches(client_a):
    r = features(client_a)
    assert r.status_code == 200
    feats = {f["date"]: f["tranche"] for f in r.json()["features"]}
    assert len(feats) == 9                      # le premier jour n'a pas de veille
    assert feats["2026-10-03"] == 3             # veille = 35.5 -> tranche >= 35
    assert feats["2026-10-02"] == 0             # veille = 12.0 -> tranche < 15


def test_train_publie_des_taux_bruites(client_a, client_b):
    res = client_b.post("/train", headers=CLE_B, json=features(client_a).json())
    assert res.status_code == 200
    assert len(res.json()["tranches"]) == 4


def test_train_refuse_features_modifiees(client_a, client_b):
    paquet = features(client_a).json()
    paquet["features"][0]["tranche"] = 3
    assert client_b.post("/train", headers=CLE_B, json=paquet).status_code == 403


def test_signature_classification_inutilisable_pour_train(client_a, client_b, nouveau_paquet):
    """Le champ "type" dans la signature empêche de réutiliser une signature."""
    paquet = features(client_a).json()
    paquet["signature"] = nouveau_paquet()["signature"]
    assert client_b.post("/train", headers=CLE_B, json=paquet).status_code == 403

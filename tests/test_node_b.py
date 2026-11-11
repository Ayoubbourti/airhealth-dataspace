"""Nœud B v2 : une preuve par correction (bruit imposé, budget, signature, audit)."""
import sqlite3
from contextlib import closing

from conftest import CLE_B, CONSUMER, DATES


def test_signature_valide_donne_un_resultat(client_b, nouveau_paquet):
    r = client_b.post("/compute", headers=CLE_B, json=nouveau_paquet())
    assert r.status_code == 200
    res = r.json()
    assert res["au_dessus_seuil"]["n"] == 5
    assert res["sous_seuil"]["n"] == 5


# --- Correction 1 : le client ne peut plus désactiver le bruit ---------------

def test_bruit_impose_meme_si_client_demande_sans(client_b, nouveau_paquet):
    r = client_b.post("/compute", headers=CLE_B, json={**nouveau_paquet(), "apply_dp": False})
    assert r.status_code == 200
    res = r.json()
    assert res["bruit_applique"] is True
    assert res["au_dessus_seuil"]["moyenne"] != 16.2   # valeur exacte jamais renvoyée


def test_epsilon_choisi_par_le_client_ignore(client_b, nouveau_paquet):
    r = client_b.post("/compute", headers=CLE_B, json={**nouveau_paquet(), "epsilon": 1000})
    assert r.json()["epsilon"] == 1.0


# --- Correction 2 : budget par (consommateur, dataset), persistant -----------

def test_budget_epuise_apres_3_requetes(client_b, nouveau_paquet):
    paquet = nouveau_paquet()
    codes = [client_b.post("/compute", headers=CLE_B, json=paquet).status_code for _ in range(4)]
    assert codes == [200, 200, 200, 429]


def test_nouveau_contrat_ne_remet_pas_le_budget_a_zero(client_b, nouveau_paquet):
    """C'est l'attaque n°2 : elle réussissait sur le TP4 de base."""
    paquet = nouveau_paquet()
    for _ in range(3):
        client_b.post("/compute", headers=CLE_B, json=paquet)
    r = client_b.post("/compute", headers=CLE_B, json=nouveau_paquet())
    assert r.status_code == 429


def test_quarante_contrats_ne_donnent_aucune_reponse_de_plus(client_b, nouveau_paquet):
    for _ in range(3):
        assert client_b.post("/compute", headers=CLE_B, json=nouveau_paquet()).status_code == 200
    succes = sum(client_b.post("/compute", headers=CLE_B, json=nouveau_paquet()).status_code == 200
                 for _ in range(40))
    assert succes == 0


def test_budget_persistant_en_base(client_b, nouveau_paquet, gouv_db):
    client_b.post("/compute", headers=CLE_B, json=nouveau_paquet())
    with closing(sqlite3.connect(gouv_db)) as conn:
        (utilise,) = conn.execute(
            "SELECT epsilon_utilise FROM budget WHERE consumer_id = ?", (CONSUMER,)).fetchone()
    assert utilise == 1.0


# --- Signature : l'attaque par différence du TP3 est bloquée -----------------

def test_sous_ensemble_de_dates_refuse(client_b, nouveau_paquet):
    paquet = nouveau_paquet()
    paquet["classifications"] = paquet["classifications"][:1]
    assert client_b.post("/compute", headers=CLE_B, json=paquet).status_code == 403


def test_signature_falsifiee_refusee(client_b, nouveau_paquet):
    r = client_b.post("/compute", headers=CLE_B, json={**nouveau_paquet(), "signature": "0" * 64})
    assert r.status_code == 403


def test_categorie_modifiee_refusee(client_b, nouveau_paquet):
    paquet = nouveau_paquet()
    paquet["classifications"][0]["categorie"] = "au_dessus_seuil"
    assert client_b.post("/compute", headers=CLE_B, json=paquet).status_code == 403


def test_consommateur_modifie_refuse(client_b, nouveau_paquet):
    """consumer_id est dans la signature : changer de consommateur ne contourne pas le budget."""
    r = client_b.post("/compute", headers=CLE_B, json={**nouveau_paquet(), "consumer_id": "autre-labo"})
    assert r.status_code == 403


def test_refus_ne_consomme_pas_de_budget(client_b, nouveau_paquet):
    paquet = nouveau_paquet()
    for _ in range(5):
        client_b.post("/compute", headers=CLE_B, json={**paquet, "signature": "0" * 64})
    codes = [client_b.post("/compute", headers=CLE_B, json=paquet).status_code for _ in range(3)]
    assert codes == [200, 200, 200]


def test_cle_hopital_incorrecte(client_b, nouveau_paquet):
    r = client_b.post("/compute", headers={"X-API-Key": "abc"}, json=nouveau_paquet())
    assert r.status_code == 401


# --- Seuil minimal ------------------------------------------------------------

def test_groupe_trop_petit_supprime(client_b, mod_a):
    """Paquet signé avec le secret de démo, avec seulement 2 jours au-dessus du seuil."""
    classifs = [{"date": d, "categorie": "au_dessus_seuil" if i < 2 else "sous_seuil"}
                for i, d in enumerate(DATES)]
    paquet = {"contract_id": "contract-air-test", "consumer_id": CONSUMER,
              "classifications": classifs,
              "signature": mod_a.signer("contract-air-test", CONSUMER, classifs)}
    res = client_b.post("/compute", headers=CLE_B, json=paquet).json()
    assert res["au_dessus_seuil"]["statut"] == "SUPPRIME_GROUPE_TROP_PETIT"
    assert res["au_dessus_seuil"]["moyenne"] is None
    assert res["sous_seuil"]["statut"] == "OK"


# --- Audit chaîné --------------------------------------------------------------

def test_audit_chaine_valide(client_b, nouveau_paquet):
    paquet = nouveau_paquet()
    client_b.post("/compute", headers=CLE_B, json=paquet)
    client_b.post("/compute", headers=CLE_B, json={**paquet, "signature": "0" * 64})
    r = client_b.get("/audit", headers=CLE_B)
    assert r.status_code == 200
    assert r.json()["chaine_valide"] is True
    assert len(r.json()["dernieres_entrees"]) == 2


def test_audit_detecte_une_modification(client_b, nouveau_paquet, gouv_db):
    paquet = nouveau_paquet()
    for _ in range(3):
        client_b.post("/compute", headers=CLE_B, json=paquet)
    with closing(sqlite3.connect(gouv_db)) as conn, conn:
        conn.execute("UPDATE audit SET code = 500 WHERE id = 2")
    r = client_b.get("/audit", headers=CLE_B).json()
    assert r["chaine_valide"] is False
    assert r["premiere_ligne_alteree"] == 2

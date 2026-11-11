"""Fixtures : nœuds A et B chargés sur des bases temporaires (10 jours, données du TP4)."""
import importlib.util
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

RACINE = Path(__file__).resolve().parent.parent

CLE_A = {"X-API-Key": "secret-air-key-demo"}
CLE_B = {"X-API-Key": "secret-hospital-key-demo"}
CONSUMER = "laboratoire-iasd"
DATASET = "dataset-air-tanger"

PM25 = [12.0, 35.5, 42.1, 15.2, 38.0, 45.0, 22.1, 18.0, 31.0, 11.5]
ADMISSIONS = [8, 14, 18, 9, 16, 20, 10, 7, 13, 5]
DATES = [f"2026-10-{i:02d}" for i in range(1, 11)]


def charger(nom, chemin):
    spec = importlib.util.spec_from_file_location(nom, chemin)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def mod_a():
    return charger("noeud_a", RACINE / "nodes" / "node_a" / "api_air.py")


@pytest.fixture(scope="session")
def mod_b():
    return charger("noeud_b", RACINE / "nodes" / "node_b" / "api_hopital.py")


@pytest.fixture
def client_a(mod_a, tmp_path, monkeypatch):
    db = tmp_path / "environnement.db"
    with closing(sqlite3.connect(db)) as conn, conn:
        conn.execute("CREATE TABLE qualite_air (date TEXT PRIMARY KEY, ville TEXT, pm25 REAL)")
        conn.executemany("INSERT INTO qualite_air VALUES (?, 'Tanger', ?)", zip(DATES, PM25))
    monkeypatch.setattr(mod_a, "DB_AIR", db)
    mod_a.contrats.clear()
    return TestClient(mod_a.app)


@pytest.fixture
def client_b(mod_b, tmp_path, monkeypatch):
    db = tmp_path / "hopital.db"
    with closing(sqlite3.connect(db)) as conn, conn:
        conn.execute("CREATE TABLE admissions (date TEXT PRIMARY KEY, ville TEXT, nombre INTEGER)")
        conn.executemany("INSERT INTO admissions VALUES (?, 'Tanger', ?)", zip(DATES, ADMISSIONS))
    monkeypatch.setattr(mod_b, "DB_HOPITAL", db)
    monkeypatch.setattr(mod_b, "DB_GOUV", tmp_path / "gouvernance_b.db")
    return TestClient(mod_b.app)


@pytest.fixture
def gouv_db(client_b, mod_b):
    """Chemin de la base de gouvernance temporaire (budget + audit)."""
    return mod_b.DB_GOUV


@pytest.fixture
def nouveau_paquet(client_a):
    """Fonction : négocie un contrat neuf et retourne les classifications signées."""
    def _faire():
        r = client_a.post("/contracts/negotiate", headers=CLE_A, json={
            "dataset_id": DATASET, "consumer_id": CONSUMER, "purpose": "research"})
        assert r.status_code == 200
        cid = r.json()["contract_id"]
        r = client_a.get("/classifications", headers=CLE_A,
                         params={"contract_id": cid, "consumer_id": CONSUMER})
        assert r.status_code == 200
        return r.json()
    return _faire

"""Couche sémantique : DCAT/ODRL en JSON-LD, politique appliquée, SPARQL sécurisé."""
import json
import sys
from pathlib import Path

import pytest
from rdflib import Graph, URIRef
from rdflib.namespace import DCAT, DCTERMS, RDF

from conftest import CLE_A, CONSUMER, DATASET

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "semantic"))
import airhealth_semantic as sem  # noqa: E402

PREFIXES = """PREFIX dcat: <http://www.w3.org/ns/dcat#>
PREFIX dct: <http://purl.org/dc/terms/>
PREFIX odrl: <http://www.w3.org/ns/odrl/2/>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX qudt: <http://qudt.org/schema/qudt/>
"""


# --- DCAT -----------------------------------------------------------------------

def test_catalogue_air_est_du_rdf_dcat_valide(client_a):
    r = client_a.get("/catalog.jsonld")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/ld+json")
    g = Graph().parse(data=json.dumps(r.json()), format="json-ld")
    assert (None, RDF.type, DCAT.Dataset) in g
    assert (None, RDF.type, DCAT.Catalog) in g
    titres = [str(t) for t in g.objects(None, DCTERMS.title)]
    assert any("PM2.5" in t for t in titres)


def test_unite_ucum_et_politique_referencee(client_a):
    g = Graph().parse(data=json.dumps(client_a.get("/catalog.jsonld").json()), format="json-ld")
    q = PREFIXES + "SELECT ?u WHERE { ?s qudt:ucumCode ?u }"
    assert [str(x[0]) for x in g.query(q)] == ["ug/m3"]
    assert g.query(PREFIXES + "ASK { ?d odrl:hasPolicy ?p }").askAnswer


def test_catalogue_hopital_cim10(mod_b, client_b):
    r = client_b.get("/catalog.jsonld")
    assert r.status_code == 200
    g = Graph().parse(data=json.dumps(r.json()), format="json-ld")
    q = PREFIXES + "SELECT ?n WHERE { ?c skos:notation ?n }"
    assert [str(x[0]) for x in g.query(q)] == ["J00-J99"]


def test_ancien_catalogue_json_toujours_disponible(client_a):
    assert client_a.get("/catalog").json()[0]["dataset_id"] == DATASET


# --- ODRL : la politique pilote réellement la décision ----------------------------

def test_politique_odrl_publiee(client_a):
    pol = client_a.get("/policy").json()
    assert pol["@type"] == "odrl:Offer"
    assert pol["odrl:permission"] and pol["odrl:prohibition"]


@pytest.mark.parametrize("purpose,recipient,attendu", [
    ("research", CONSUMER, True),
    ("commercial", CONSUMER, False),
    ("marketing", CONSUMER, False),
    ("research", "pirate", False),
])
def test_evaluation_politique(purpose, recipient, attendu):
    pol = sem.charger("policy_air.jsonld")
    ok, _ = sem.evaluer(pol, "use", purpose, recipient)
    assert ok is attendu


def test_interdiction_l_emporte_sur_la_permission():
    pol = sem.charger("policy_air.jsonld")
    pol["odrl:permission"][0]["odrl:constraint"] = []          # permission sans condition
    ok, raison = sem.evaluer(pol, "use", "commercial", CONSUMER)
    assert ok is False and "Interdit" in raison


def test_operande_inconnu_refuse():
    pol = sem.charger("policy_air.jsonld")
    pol["odrl:permission"][0]["odrl:constraint"].append({
        "odrl:leftOperand": {"@id": "odrl:spatial"}, "odrl:operator": {"@id": "odrl:eq"},
        "odrl:rightOperand": "Maroc"})
    assert sem.evaluer(pol, "use", "research", CONSUMER)[0] is False


def test_negociation_suit_la_politique(mod_a, client_a, monkeypatch):
    """Si on change la politique, la décision du nœud A change (pas de règle codée en dur)."""
    corps = {"dataset_id": DATASET, "consumer_id": "labo-partenaire", "purpose": "research"}
    assert client_a.post("/contracts/negotiate", headers=CLE_A, json=corps).status_code == 403
    pol = sem.charger("policy_air.jsonld")
    pol["odrl:permission"][0]["odrl:constraint"][1]["odrl:rightOperand"].append("labo-partenaire")
    monkeypatch.setattr(mod_a, "POLITIQUE", pol)
    assert client_a.post("/contracts/negotiate", headers=CLE_A, json=corps).status_code == 200


# --- SPARQL en lecture seule ---------------------------------------------------------

def sparql(client, q):
    return client.get("/sparql", params={"query": q})


def test_sparql_select(client_a):
    r = sparql(client_a, PREFIXES + "SELECT ?t WHERE { ?d a dcat:Dataset ; dct:title ?t }")
    assert r.status_code == 200
    assert "PM2.5" in r.json()["lignes"][0]["t"]


def test_sparql_ask(client_a):
    r = sparql(client_a, PREFIXES + "ASK { ?d a dcat:Dataset }")
    assert r.json() == {"type": "ASK", "resultat": True}


@pytest.mark.parametrize("requete", [
    "SELECT * WHERE { SERVICE <http://exemple.org/sparql> { ?a ?b ?c } }",
    "INSERT DATA { <http://a> <http://b> <http://c> }",
    "DROP ALL",
    "CLEAR GRAPH <http://a>",
    "ceci n'est pas du sparql",
])
def test_sparql_requetes_dangereuses_refusees(client_a, requete):
    assert sparql(client_a, requete).status_code == 400


def test_sparql_ne_modifie_pas_le_graphe(mod_a, client_a):
    avant = len(mod_a.GRAPHE)
    sparql(client_a, "INSERT DATA { <http://a> <http://b> <http://c> }")
    assert len(mod_a.GRAPHE) == avant

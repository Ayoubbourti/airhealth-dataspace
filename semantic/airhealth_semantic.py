"""Couche sémantique : chargement JSON-LD (DCAT, ODRL), évaluation de politique, SPARQL en lecture seule."""
import json
import re
from pathlib import Path

from rdflib import Graph

DOSSIER = Path(__file__).resolve().parent
MAX_LIGNES_SPARQL = 100


def charger(nom_fichier):
    """Charge un document JSON-LD du dossier semantic/ (dict)."""
    return json.loads((DOSSIER / nom_fichier).read_text(encoding="utf-8"))


def construire_graphe(*documents):
    """Fusionne des documents JSON-LD dans un graphe RDF."""
    g = Graph()
    for doc in documents:
        g.parse(data=json.dumps(doc), format="json-ld")
    return g


def _liste(x):
    if x is None:
        return []
    return x if isinstance(x, list) else [x]


def _nom(terme):
    """'odrl:purpose' ou {'@id': 'odrl:purpose'} -> 'purpose'."""
    if isinstance(terme, dict):
        terme = terme.get("@id", "")
    return str(terme).rsplit(":", 1)[-1].rsplit("/", 1)[-1]


def _contrainte_ok(contrainte, contexte):
    gauche = _nom(contrainte.get("odrl:leftOperand"))
    operateur = _nom(contrainte.get("odrl:operator"))
    valeurs = _liste(contrainte.get("odrl:rightOperand"))
    if gauche not in contexte:
        return False            # opérande inconnu : on refuse (principe du moindre privilège)
    valeur = contexte[gauche]
    if operateur == "eq":
        return valeur == valeurs[0]
    if operateur == "isAnyOf":
        return valeur in valeurs
    return False                # opérateur non géré : refus


def _regle_applicable(regle, action, contexte):
    if _nom(regle.get("odrl:action")) != action:
        return False
    return all(_contrainte_ok(c, contexte) for c in _liste(regle.get("odrl:constraint")))


def evaluer(politique, action, purpose, recipient):
    """Évalue une demande face à une politique ODRL. Retourne (autorisé, raison).

    Règles : une interdiction applicable l'emporte ; sinon il faut une permission applicable.
    """
    contexte = {"purpose": purpose, "recipient": recipient}
    for p in _liste(politique.get("odrl:prohibition")):
        if _regle_applicable(p, action, contexte):
            return False, "Interdit par la politique ODRL (finalité interdite)"
    permissions = _liste(politique.get("odrl:permission"))
    for p in permissions:
        if _regle_applicable(p, action, contexte):
            return True, "Autorisé par la politique ODRL"
    # Raison précise pour l'utilisateur
    for p in permissions:
        if _nom(p.get("odrl:action")) == action:
            for c in _liste(p.get("odrl:constraint")):
                if not _contrainte_ok(c, contexte):
                    gauche = _nom(c.get("odrl:leftOperand"))
                    return False, ("Finalité non autorisée" if gauche == "purpose"
                                   else "Consommateur non autorisé")
    return False, "Aucune permission applicable"


def sparql_lecture_seule(graphe, requete):
    """Exécute un SELECT/ASK. Lève ValueError pour tout ce qui n'est pas autorisé."""
    nettoyee = re.sub(r"#[^\n]*", "", requete)           # retire les commentaires
    if re.search(r"\bSERVICE\b", nettoyee, re.IGNORECASE):
        raise ValueError("SERVICE interdit (requêtes fédérées vers l'extérieur bloquées)")
    if re.search(r"\b(INSERT|DELETE|LOAD|CLEAR|DROP|CREATE|COPY|MOVE|ADD)\b", nettoyee, re.IGNORECASE):
        raise ValueError("Seules les requêtes de lecture sont autorisées")
    if not re.search(r"\b(SELECT|ASK)\b", nettoyee, re.IGNORECASE):
        raise ValueError("Seuls SELECT et ASK sont autorisés")
    try:
        resultat = graphe.query(requete)
    except Exception as e:                               # syntaxe invalide, etc.
        raise ValueError(f"Requête SPARQL invalide : {type(e).__name__}")
    if resultat.type == "ASK":
        return {"type": "ASK", "resultat": bool(resultat.askAnswer)}
    variables = [str(v) for v in resultat.vars]
    lignes = []
    for i, ligne in enumerate(resultat):
        if i >= MAX_LIGNES_SPARQL:
            break
        lignes.append({v: (str(ligne[v]) if ligne[v] is not None else None) for v in variables})
    return {"type": "SELECT", "variables": variables, "lignes": lignes}

# AirHealth Data Space

Mini-espace de données fédéré pour étudier l'association entre la **pollution atmosphérique (PM2.5)** et les **admissions hospitalières respiratoires**, sans jamais centraliser les données.

Projet du Master IASD : *Data Spaces & Data Integration & Semantic Interoperability*.

> Toutes les données sont **fictives**. Les clés et secrets sont des valeurs de démonstration. Ce prototype ne doit pas être exposé sur Internet ni utilisé avec des données réelles.

## Le problème

Trois organisations participent :

| Nœud | Organisation | Rôle | Port |
|---|---|---|---|
| A | Direction de l'environnement | Détient les mesures de PM2.5, publie le catalogue, négocie les contrats, signe les classifications | 8001 |
| B | Hôpital régional | Détient les admissions, calcule localement, impose le bruit et le budget de confidentialité | 8002 |
| C | Laboratoire universitaire | Orchestre l'analyse, dashboard web, ne voit jamais les bases | 8000 |

Question : comment analyser ensemble des données détenues par des organisations différentes, **sans les centraliser**, en **contrôlant leur usage** et en **limitant ce qui est révélé** ?

## Architecture

```
Navigateur ──► Nœud C (laboratoire, :8000) ──► Nœud A (environnement, :8001) ── environnement.db
                                           └─► Nœud B (hôpital, :8002) ─────── hopital.db
                                                                              └ gouvernance_b.db (budget ε + audit)
```

Les clés API restent **côté serveur** (nœud C) et ne sont jamais envoyées au navigateur.

Flux d'une analyse :

1. C lit le catalogue de A (`GET /catalog`).
2. C négocie un contrat avec A (`POST /contracts/negotiate`, finalité `research`).
3. A renvoie des classifications **signées** (HMAC) pour ce contrat et ce consommateur.
4. C transmet le paquet signé à B (`POST /compute`).
5. B vérifie la signature, calcule localement, ajoute du bruit de Laplace, consomme du budget ε, journalise, et ne renvoie que des **agrégats**.

## Structure du dépôt

```
airhealth-dataspace/
├── tp/
│   ├── TP1/ ... TP3/            # TP d'origine (stockage, API, calcul local)
│   ├── TP4_Gouvernance/         # TP4 d'origine (contrat, signature, seuil, bruit)
│   └── TP4_attaques/            # attaques sur le TP4 de base et rejeu sur la version corrigée
├── nodes/
│   ├── node_a/                  # API Environnement (catalogue, contrats, signatures, /features)
│   ├── node_b/                  # API Hôpital v2 (bruit imposé, budget persistant, audit, /train)
│   └── node_c/                  # Laboratoire : orchestration + dashboard (static/index.html)
├── data/generate.py             # générateur de données synthétiques (365 jours)
├── docs/                        # réponses aux questions, captures, notes
└── requirements.txt
```

## Installation (Windows, CMD)

```bat
git clone https://github.com/Ayoubbourti/airhealth-dataspace.git
cd airhealth-dataspace
python -m venv .venv
.venv\Scripts\activate.bat
python -m pip install -r requirements.txt
```

Python 3.10 ou plus est requis.

## Lancer le projet

Générer les données (serveurs arrêtés) et repartir d'un budget neuf :

```bat
python data\generate.py
del nodes\node_b\gouvernance_b.db
```

Puis trois fenêtres CMD, chacune avec le venv activé :

```bat
:: Fenêtre 1 : nœud A
cd nodes\node_a
python -m uvicorn api_air:app --port 8001

:: Fenêtre 2 : nœud B
cd nodes\node_b
python -m uvicorn api_hopital:app --port 8002

:: Fenêtre 3 : laboratoire + dashboard
cd nodes\node_c
python -m uvicorn app:app --port 8000
```

Ouvrez **http://127.0.0.1:8000**. N'utilisez pas `--reload` : il efface la mémoire des contrats à chaque modification.

## Interopérabilité sémantique

| Élément | Où | Rôle |
|---|---|---|
| Catalogues DCAT (JSON-LD) | `semantic/catalog_air.jsonld`, `semantic/catalog_hopital.jsonld`, `GET /catalog.jsonld` | Découverte standard W3C |
| Politique ODRL | `semantic/policy_air.jsonld`, `GET /policy` | Le nœud A **décide des contrats à partir de ce document** (permission : usage `research` par `laboratoire-iasd` ; interdiction : usage `commercial`) |
| Unité UCUM / QUDT | catalogue A | `ug/m3` |
| CIM-10 J00-J99 | catalogue B | Affections respiratoires |
| SPARQL | `GET /sparql?query=...` (nœud A) | Requêtes SELECT/ASK ; `SERVICE` et modifications refusés |

Exemple :

```sparql
PREFIX dcat: <http://www.w3.org/ns/dcat#>
PREFIX dct: <http://purl.org/dc/terms/>
SELECT ?titre WHERE { ?d a dcat:Dataset ; dct:title ?titre }
```

## Tests

```bat
python -m pytest -v
```

Les tests utilisent des bases temporaires : pas besoin de lancer les serveurs, et les vraies bases ne sont pas modifiées.

## Scénario de démo

1. **Lire le catalogue**, **négocier un contrat**, **lancer l'analyse** : deux moyennes bruitées proches de la vérité terrain.
2. **Lancer les attaques** : sous-ensemble de dates, signature falsifiée, clé incorrecte et finalité commerciale sont toutes bloquées (403, 403, 401, 403).
3. **Épuiser le budget** : un nouveau contrat ne remet pas ε à zéro (429).
4. **ML fédéré** : l'hôpital publie des taux d'admissions bruités par tranche de PM2.5 de la veille, et le laboratoire ajuste le modèle.
5. **Courbe précision vs ε** : plus ε est grand, plus le modèle est précis et moins il protège.

## Failles du TP4 de base et corrections

| Faille | Preuve | Correction (nœud B v2) |
|---|---|---|
| Le bruit (`apply_dp`) est choisi par le client | `tp/TP4_attaques/attaque_budget.py`, étape 4 | Bruit toujours appliqué, champ ignoré |
| Budget lié au `contract_id` : un nouveau contrat le remet à zéro | Étape 2 | Budget lié à (consommateur, jeu de données) |
| Moyenne de réponses bruitées = vraie valeur | 120 réponses donnent 16,25 / 8,32 (réel 16,2 / 7,8) | Budget total limité à 3 requêtes |
| Budget perdu au redémarrage | Mémoire volatile | Budget persistant (SQLite) |
| Aucune trace des accès | n/a | Journal d'audit chaîné par hachage SHA-256 |

Rejeu de l'attaque contre la version corrigée : `tp/TP4_attaques/attaque_budget_v2.py` (3 réponses puis 429, 0 réponse sur 40 contrats supplémentaires).

## Données synthétiques

`data/generate.py` produit 365 jours (seed 42) : saisonnalité, autocorrélation de la pollution, épisodes de pic, température (variable confondante), admissions suivant une loi de Poisson avec **effet retardé d'un jour** de la pollution. Plus il y a de données, moins le bruit de Laplace dégrade la précision (échelle `30 / n / ε`).

## Limites connues

- Prototype pédagogique : **pas une confidentialité différentielle formelle** (borne de 30 admissions/jour pédagogique, effectifs non bruités, ajustement du modèle côté laboratoire sur des statistiques bruitées).
- Le seuil minimal de 3 jours n'est **pas du k-anonymat**.
- Signature HMAC **symétrique** : A et B partagent le secret, B pourrait forger des signatures (Ed25519 prévu).
- Pas d'expiration, de révocation ni de nonce sur les contrats (rejeu possible), contrats stockés en mémoire.
- Budget total non renouvelable ; le journal détecte la modification d'une ligne mais pas l'effacement complet de la base.
- Clés API codées en dur, HTTP sans chiffrement, pas d'identité organisationnelle.
- `/api/truth`, `/api/ml/curve` et la « vérité terrain » du dashboard lisent directement les bases : **réservés à la démonstration**.
- Le JSON-LD DCAT/ODRL utilise un contexte inline (pas de validation SHACL ni de profil DCAT-AP) ; l'ancien `/catalog` JSON simple est conservé. La politique ODRL n'est appliquée que par le nœud A (celle du nœud B est déclarée, pas évaluée).

## Roadmap

- [x] TP1 à TP4 et réponses aux questions
- [x] Attaque sur le budget ε et correction (nœud B v2)
- [x] Données synthétiques, dashboard, ML fédéré
- [x] Tests automatiques `pytest` (48 tests, une preuve par correction)
- [ ] Signatures Ed25519, contrats avec expiration, révocation et nonce
- [x] Catalogue DCAT en JSON-LD, politique ODRL appliquée, SPARQL en lecture seule, UCUM et CIM-10 (`semantic/`)
- [x] CI GitHub Actions (`.github/workflows/tests.yml`)
- [ ] Docker Compose
- [ ] Comparaison avec IDSA, Eclipse EDC, Gaia-X, Catena-X

## Notions clés

- **Stockage fédéré** : les données restent chez leurs propriétaires.
- **Traitement fédéré** : le calcul se fait là où sont les données.
- **Analyse fédérée** : calcul coordonné avec gouvernance (contrat, finalité, signature) et protection de ce qui est révélé (seuil, bruit, budget).

## Auteur

Ayoub Bourti, Master IASD.

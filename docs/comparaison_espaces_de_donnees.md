# Comparaison avec les écosystèmes d'espaces de données existants

AirHealth est un **prototype pédagogique** : il reprend les idées des grands cadres d'espaces de données dans une version minimale, sans en implémenter les protocoles. Ce document situe le projet par rapport à quatre références. Il se limite aux grandes lignes ; pour les détails normatifs, se référer aux spécifications officielles de chaque initiative.

| Sujet | IDSA (Dataspace Protocol / IDS) | Eclipse EDC | Gaia-X | Catena-X | AirHealth (ce projet) |
|---|---|---|---|---|---|
| Nature | Association qui définit une architecture de référence et un protocole d'échange | Implémentation open source de connecteurs | Cadre de confiance et de conformité (labels, fédération de services) | Écosystème sectoriel (automobile) bâti sur ces briques | Prototype de TP, 3 nœuds FastAPI |
| Découverte | Catalogue (DCAT) | Catalogue via le connecteur | Catalogues fédérés, descriptions de services | Catalogues par participant | Catalogue DCAT JSON-LD (`/catalog.jsonld`), SPARQL en lecture seule |
| Politiques d'usage | ODRL | Politiques ODRL évaluées par le connecteur | Politiques de conformité et de labels | Politiques d'usage sectorielles | Politique ODRL réellement évaluée par le nœud A (finalité, destinataire) |
| Contrat | Négociation de contrat standardisée | Négociation et transfert automatisés | Hors périmètre direct | Via les connecteurs | Négociation simplifiée (`/contracts/negotiate`), contrat en mémoire, sans expiration |
| Identité et confiance | Identités vérifiables, autorités de confiance | Intégration d'identités décentralisées | Au cœur du modèle (Trust Framework) | Portail d'onboarding, identités des participants | Clés API codées en dur, pas d'identité organisationnelle |
| Transfert de données | Le connecteur déplace ou expose les données | Plan de données séparé du plan de contrôle | Selon le service | Selon le cas d'usage | Aucune donnée brute ne circule : calcul local, agrégats bruités uniquement |
| Protection de ce qui est révélé | Hors périmètre du protocole | Hors périmètre du cœur | Hors périmètre | Selon le cas d'usage | Seuil minimal, bruit de Laplace, budget ε persistant, audit chaîné |

## Ce qu'AirHealth reprend

- La **séparation découverte / politique / contrat / accès** : catalogue, politique ODRL, négociation, contrôle à l'appel.
- Les **vocabulaires standards** (DCAT, ODRL, UCUM, CIM-10) pour l'interopérabilité sémantique.
- Le principe d'un **connecteur par organisation** : chaque nœud garde ses données et applique ses règles.

## Ce qu'AirHealth ne fait pas

- Pas de protocole standard entre connecteurs : les API sont propres au projet.
- Pas d'identités vérifiables ni d'autorité de confiance, et pas de HTTPS.
- Pas de contrats avec expiration, révocation ou nonce.
- Signature HMAC symétrique au lieu de signatures asymétriques.

## Ce qu'AirHealth ajoute par rapport au cœur de ces cadres

Les cadres ci-dessus gouvernent surtout **qui peut accéder à quoi, et pour quel usage**. Ils ne limitent pas, en général, **ce que révèle un calcul** une fois l'accès accordé. AirHealth illustre cette seconde couche : l'attaque par différence du TP 3, le bruit imposé par l'hôpital, le budget de confidentialité par (consommateur, jeu de données) et le journal d'audit. Ce n'est pas une confidentialité différentielle formelle (voir les limites du README), mais cela montre pourquoi la gouvernance d'accès ne suffit pas à elle seule.

## Pistes pour aller vers un vrai connecteur

1. Remplacer la négociation maison par le Dataspace Protocol (catalogue, négociation, transfert).
2. Exposer les nœuds A et B via des connecteurs EDC et déclarer les politiques ODRL dans ces connecteurs.
3. Remplacer les clés API et le HMAC par des identités vérifiables et des signatures asymétriques (Ed25519).
4. Garder le calcul local avec bruit et budget comme service de traitement associé au contrat.

# Réponses aux questions du TP 4

## 1. Quelles informations permettent au laboratoire de découvrir et de comprendre le jeu de données ?
Le catalogue du nœud A (`GET /catalog`) : identifiant (`dataset-air-tanger`), titre, description, éditeur, couverture temporelle, unité (µg/m³), point d'accès (`/contracts/negotiate`) et finalité autorisée (`research`).

## 2. Qu'est-ce que DCAT et pourquoi le catalogue est-il une simplification inspirée de DCAT ?
DCAT (Data Catalog Vocabulary) est un vocabulaire du W3C, exprimé en RDF, pour décrire des catalogues, des jeux de données et leurs distributions de façon interopérable. Notre catalogue est un simple JSON dont quelques champs s'inspirent de DCAT : il n'y a ni RDF, ni URI de vocabulaires, ni distributions, ni licence. Il n'est donc pas conforme au standard.

## 3. Pourquoi contrôler la finalité avant d'autoriser l'accès ? Différence entre catalogue, politique d'usage et contrôle d'accès
Une même donnée peut être légitime pour la recherche et inacceptable pour un usage commercial : l'accès doit dépendre de l'usage prévu.
- **Catalogue** : décrit ce qui existe (découverte).
- **Politique d'usage** (règle inspirée d'ODRL) : dit ce qui est permis, pour quelle finalité et pour qui.
- **Contrôle d'accès** : applique techniquement la règle (clé API, vérification du jeu de données, de la finalité, du consommateur, contrat).

## 4. Quelles informations circulent entre les trois nœuds ? Que reste-t-il dans la base hospitalière ? Pourquoi la conservation locale ne suffit-elle pas ?
- **C → A** : la demande de contrat (jeu de données, consommateur, finalité).
- **A → C** : le catalogue, le contrat, puis les classifications signées (date + catégorie).
- **C → B** : le paquet signé reçu de A.
- **B → C** : des agrégats uniquement (effectif et moyenne par groupe, éventuellement bruités).
- **Reste dans `hopital.db`** : toutes les admissions journalières individuelles.

La conservation locale ne suffit pas, car les classifications et les agrégats sont eux-mêmes des informations. Un agrégat sur un groupe trop petit ou choisi librement révèle une valeur individuelle (attaque du TP 3). Il faut aussi contrôler ce que l'on calcule et ce que l'on publie.

## 5. Pourquoi ne pas publier une statistique sur un groupe trop petit ? Pourquoi un seuil de trois jours n'est-il pas une preuve de k-anonymat ? Comment la signature limite-t-elle l'attaque du TP 3 ?
- Une moyenne sur 1 ou 2 jours révèle presque directement les valeurs individuelles (1 jour : la moyenne vaut la valeur, d'où le 8,0 du TP 3).
- Le seuil de 3 jours est une règle simple de non-publication. Le k-anonymat est une propriété formelle d'un jeu de données (chaque individu est indistinguable d'au moins k−1 autres sur ses quasi-identifiants), que ce seuil ne démontre pas ; de plus, plusieurs requêtes peuvent se recouper.
- La signature HMAC prouve que la liste de classifications a été émise par A pour ce contrat et ce consommateur. Le laboratoire ne peut plus choisir un groupe d'un seul jour : toute modification de la liste donne 403 (capture `TP4_B_signature_403.png`).

## 6. Comparaison avec et sans bruit, compromis précision / protection, et pourquoi ce n'est pas une confidentialité différentielle complète
- **Sans bruit** : 16,2 et 7,8 (valeurs exactes).
- **Avec bruit** : les moyennes changent à chaque exécution et peuvent s'éloigner fortement de la vérité. Pour n = 5 et ε = 1, l'échelle du bruit vaut (30 / 5) / 1 = 6, soit un écart-type d'environ 8,5, comparable à la différence observée (8,4).
- **Compromis** : plus ε est petit, plus la protection est forte et plus le résultat est imprécis. Plus ε est grand, plus le résultat est précis et moins il protège.
- **Pourquoi pas une DP complète** : sensibilité simplifiée (borne pédagogique de 30 admissions/jour, groupes de taille fixée), effectifs `n` publiés sans bruit, budget suivi par simple somme, partition des jours dépendant des données de A, aléa non audité, pas d'analyse formelle de la composition des requêtes.

Dans la version corrigée du nœud B (`nodes/node_b`), le bruit est imposé par l'hôpital et le budget est lié à (consommateur, jeu de données) et persistant, ce qui corrige les failles montrées par `tp/TP4_attaques/attaque_budget.py`.

## 7. La différence observée permet-elle de conclure que la pollution provoque les admissions ? Quelles variables considérer ?
Non : c'est une association observée sur 10 jours fictifs, pas une causalité. Il faudrait considérer : la météo (température, humidité, vent), la saison, les épidémies virales et la grippe, les jours de la semaine et jours fériés, la population exposée, les autres polluants (NO2, O3, PM10), le délai entre exposition et admission, la tendance temporelle et la capacité de l'hôpital. Il faudrait aussi un modèle adapté (séries temporelles, régression de Poisson avec décalages) sur une longue période. Les données synthétiques de `data/generate.py` intègrent justement la température comme variable confondante et un effet retardé d'un jour.

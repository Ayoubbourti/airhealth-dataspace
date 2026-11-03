# Réponses aux questions du TP 3

## 1. Quelles données le laboratoire reçoit-il dans le TP 2 ? Et dans le TP 3 ?

- TP 2 : les données brutes complètes, soit les valeurs exactes de PM2.5 et le nombre exact d'admissions pour chaque jour.
- TP 3 : de l'organisation A, seulement des catégories par date (`elevee` / `non_elevee`), sans les concentrations exactes ; de l'hôpital, seulement des statistiques agrégées (nombre de jours et moyenne par catégorie). Il ne voit plus les admissions jour par jour.

## 2. Pourquoi l'hôpital effectue-t-il les calculs dans son propre environnement ?

Pour que les données brutes ne quittent jamais l'hôpital. On envoie le calcul vers la donnée, et non la donnée vers le calcul. Cela réduit l'exposition de données sensibles (santé), facilite le respect de la souveraineté et de la réglementation, et limite ce qui sort à un résultat agrégé.

## 3. Quelles informations sont encore transmises à l'hôpital ?

L'hôpital reçoit la liste des dates avec leur catégorie de pollution. Il apprend donc quels jours étaient pollués. Ce sont des informations dérivées des mesures de A, mais ce sont bien des informations échangées. Le calcul est local, mais l'ensemble n'est pas une solution de confidentialité formelle.

## 4. Une statistique agrégée garantit-elle toujours la confidentialité ?

Non. L'attaque par différence (section 8) le montre : le laboratoire choisit lui-même le groupe et envoie un seul jour (2026-10-01). Le groupe contient un seul élément, donc la « moyenne » renvoyée (8.0) est exactement le nombre d'admissions de ce jour. Un agrégat calculé sur un groupe trop petit, ou sur un groupe choisi librement par le demandeur, peut révéler une valeur individuelle. En comparant deux requêtes qui diffèrent d'un seul jour, on retrouve aussi la valeur de ce jour.

## 5. Une clé API suffit-elle pour garantir la souveraineté des données ?

Non. Une clé API authentifie seulement l'appelant : elle ne dit rien de la finalité de l'usage, ne limite pas ce qui est demandé, ne laisse pas de traçabilité et peut être volée, partagée ou codée en dur. La souveraineté exige aussi des contrats d'usage, des politiques, des identités organisationnelles, un contrôle de ce qui est calculé, des journaux d'audit et un cadre de gouvernance.

## 6. Comment limiter les demandes d'analyse aux opérations autorisées ?

- Ne permettre que des analyses prédéfinies (liste blanche d'opérations) ;
- imposer un seuil minimal de taille de groupe ;
- faire signer par A les classifications pour que le labo ne puisse pas choisir ses groupes (TP 4) ;
- lier chaque demande à un contrat (finalité, consommateur) ;
- limiter le nombre de requêtes et ajouter du bruit avec un budget de confidentialité ;
- journaliser les accès.

## 7. Quels composants supplémentaires faut-il pour un véritable espace de données ?

- Un catalogue pour découvrir les jeux de données (DCAT) ;
- des politiques d'usage et des contrats (ODRL) ;
- des identités organisationnelles et des connecteurs de confiance ;
- des signatures et un chiffrement (HTTPS) ;
- des journaux d'audit et de traçabilité ;
- une gouvernance et une analyse des risques de divulgation ;
- des vocabulaires communs pour l'interopérabilité sémantique.
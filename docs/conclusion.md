# Conclusion

## Stockage fédéré, traitement fédéré, analyse fédérée
- **Stockage fédéré (TP 1)** : les données restent chez leurs propriétaires, dans deux bases indépendantes (`environnement.db`, `hopital.db`). Rien n'est centralisé, mais rien ne permet encore de communiquer.
- **Traitement fédéré (TP 3)** : le calcul est effectué là où se trouve la donnée (chez l'hôpital) et seules des statistiques sont renvoyées. Mais le laboratoire choisit librement ses groupes de dates, et l'attaque par différence révèle une valeur individuelle (8,0 admissions le 1er octobre).
- **Analyse fédérée (TP 4)** : plusieurs organisations contribuent à une même analyse sous gouvernance : catalogue pour la découverte, contrat et vérification de la finalité, classifications signées, calcul local, seuil minimal, bruit et budget de confidentialité.

## Ce que le TP 4 corrige par rapport au TP 3
1. **L'attaque par différence est bloquée** : la signature HMAC empêche le laboratoire de choisir ses groupes (403) ; les groupes de moins de 3 jours ne sont pas publiés ; le bruit limite l'exactitude des valeurs publiées.
2. **L'accès repose sur un contrat** lié à une finalité (`research`) et à un consommateur identifié, et non plus sur une simple clé API.
3. **Le laboratoire dispose d'un catalogue** pour découvrir les jeux de données.

## Ce que l'extension apporte (nœud B v2)
Le TP 4 de base a lui-même des failles : bruit choisi par le client, budget remis à zéro par un nouveau contrat, budget perdu au redémarrage, aucune trace des accès. Le nœud B v2 les corrige (bruit imposé, budget persistant par consommateur et jeu de données, journal d'audit chaîné). Voir `docs/attaque_budget.md` et `tp/TP4_attaques/`.

## Limites restantes
Les classifications et les agrégats circulent toujours. Le bruit n'est pas une garantie formelle de confidentialité différentielle. La signature HMAC est symétrique. Les clés et secrets sont des valeurs de démonstration. Il n'y a ni HTTPS, ni identités organisationnelles. Le prototype ne doit pas être exposé sur Internet ni utilisé avec des données réelles.

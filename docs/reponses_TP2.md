# Réponses aux questions du TP 2

## 1. Quel est le rôle de FastAPI ?

FastAPI est un framework Python qui permet de créer des API REST. Dans notre TP, il sert à définir les différentes routes, comme `/mesures` et `/admissions`, et à associer chacune d'elles à une fonction qui traite la demande.

Il permet également de retourner les résultats sous forme de JSON, de vérifier les données reçues et de générer automatiquement une documentation interactive accessible depuis `/docs`.

En résumé, FastAPI permet de construire l'API et de définir les services qu'elle met à disposition des utilisateurs.

## 2. Quel est le rôle d'Uvicorn ?

Uvicorn est le serveur qui permet de lancer notre application FastAPI et de la rendre accessible. Il écoute les requêtes envoyées par les clients sur une adresse et un port précis, puis les transmet à FastAPI pour qu'elles soient traitées.

Par exemple, lorsqu'un client demande des données à l'API, Uvicorn reçoit la requête et transmet le résultat au client.

On peut donc dire que FastAPI s'occupe de la logique de l'API, tandis qu'Uvicorn permet de la faire fonctionner et de communiquer avec elle.

## 3. Pourquoi utilise-t-on deux ports différents ?

Dans ce TP, nous avons deux organisations indépendantes : l'organisation A, qui représente le service Environnement, et l'organisation B, qui représente l'Hôpital.

Chaque organisation possède son propre serveur. Nous utilisons donc le port 8001 pour l'environnement et le port 8002 pour l'hôpital.

Cela permet de lancer les deux services en même temps sur la même machine, car un même port ne peut pas être utilisé simultanément par deux serveurs différents.

Cette organisation permet aussi de simuler un système fédéré dans lequel chaque organisme conserve son propre service et ses propres données, tout en permettant au laboratoire de communiquer avec les deux API.

## 4. Le laboratoire reçoit-il les données brutes dans cette version ?

Oui, dans cette version du TP, le laboratoire reçoit directement les données brutes des deux organisations.

Concrètement, il récupère les mesures quotidiennes de PM2.5 depuis l'API Environnement et le nombre d'admissions hospitalières depuis l'API Hôpital.

Il peut ensuite associer les données à partir des dates et effectuer lui-même les calculs nécessaires.

Même si les données restent initialement stockées chez leurs propriétaires, elles sont donc transmises au laboratoire sous leur forme exacte. Cela pose un problème de confidentialité, car le laboratoire a accès aux informations détaillées.

C'est justement ce point qui sera amélioré dans le TP 3 : chaque organisation effectue ses propres calculs et transmet uniquement les résultats nécessaires, sans partager toutes les données originales.

## 5. Une API REST garantit-elle automatiquement la confidentialité ?

Non, le fait d'utiliser une API REST ne signifie pas que les données sont automatiquement protégées.

Une API REST permet simplement à différentes applications de communiquer entre elles à travers HTTP. La confidentialité dépend des mécanismes de sécurité mis en place autour de cette communication.

Dans notre TP, il n'y a pas encore de système d'authentification ni de contrôle d'accès. De plus, les données sont transmises directement et la communication utilise HTTP sans chiffrement.

Pour améliorer la sécurité, on peut ajouter une authentification, utiliser HTTPS pour protéger les échanges, limiter l'accès aux données et éviter de transmettre des informations trop détaillées.

L'idée est donc de ne partager que les informations réellement nécessaires, tout en protégeant les données sensibles des différentes organisations.
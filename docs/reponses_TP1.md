# Réponses aux questions du TP 1

## 1. Où sont stockées les mesures de qualité de l'air ?
Dans `environnement.db` (table `qualite_air`), une base SQLite locale qui appartient à l'organisation A (Direction de l'environnement).

## 2. Où sont stockées les admissions hospitalières ?
Dans `hopital.db` (table `admissions`), une base SQLite locale qui appartient à l'organisation B (Hôpital régional).

## 3. Les deux jeux de données sont-ils dans une même base ?
Non. Ce sont deux fichiers distincts, avec deux schémas et deux propriétaires. Il n'existe aucune base centrale : c'est le principe du stockage fédéré.

## 4. Comment le laboratoire pourrait-il découvrir les données disponibles sans centraliser les fichiers ?
Grâce à un **catalogue de métadonnées** publié par chaque organisation (titre, description, éditeur, couverture temporelle, unité, finalité autorisée). Le laboratoire lit la description du jeu de données, pas les données elles-mêmes. C'est le rôle de `GET /catalog` du nœud A au TP 4.

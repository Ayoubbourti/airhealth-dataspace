import sqlite3

requetes = [
    ("environnement.db", "SELECT * FROM qualite_air ORDER BY date"),
    ("hopital.db", "SELECT * FROM admissions ORDER BY date"),
]

for fichier, requete in requetes:
    print("\nBase :", fichier)
    db = sqlite3.connect(fichier)
    for ligne in db.execute(requete):
        print(ligne)
    db.close()
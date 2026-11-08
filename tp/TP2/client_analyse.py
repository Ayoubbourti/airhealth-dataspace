import requests

URL_AIR = "http://127.0.0.1:8001"
URL_HOPITAL = "http://127.0.0.1:8002"

r_air = requests.get(f"{URL_AIR}/mesures", timeout=5)
r_air.raise_for_status()
mesures_air = r_air.json()

r_hopital = requests.get(f"{URL_HOPITAL}/admissions", timeout=5)
r_hopital.raise_for_status()
admissions = r_hopital.json()

air_par_date = {x["date"]: x["pm25"] for x in mesures_air}
hopital_par_date = {x["date"]: x["nombre"] for x in admissions}

elevees = []
non_elevees = []

print("Date | PM2.5 | Admissions")
for date in sorted(air_par_date.keys() & hopital_par_date.keys()):
    pm25 = air_par_date[date]
    nombre = hopital_par_date[date]
    print(date, "|", pm25, "|", nombre)
    if pm25 > 30:
        elevees.append(nombre)
    else:
        non_elevees.append(nombre)

print("Moyenne admissions, pollution élevée :",
      round(sum(elevees) / len(elevees), 2))
print("Moyenne admissions, autres jours :",
      round(sum(non_elevees) / len(non_elevees), 2))
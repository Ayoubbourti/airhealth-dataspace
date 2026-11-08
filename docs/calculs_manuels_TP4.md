# Calculs manuels du TP 4

Seuil pédagogique : une journée est `au_dessus_seuil` si PM2.5 > 30 µg/m³, sinon `sous_seuil`.

| Date | PM2.5 (µg/m³) | Admissions | Catégorie |
|---|---|---|---|
| 01/10 | 12,0 | 8 | sous_seuil |
| 02/10 | 35,5 | 14 | au_dessus_seuil |
| 03/10 | 42,1 | 18 | au_dessus_seuil |
| 04/10 | 15,2 | 9 | sous_seuil |
| 05/10 | 38,0 | 16 | au_dessus_seuil |
| 06/10 | 45,0 | 20 | au_dessus_seuil |
| 07/10 | 22,1 | 10 | sous_seuil |
| 08/10 | 18,0 | 7 | sous_seuil |
| 09/10 | 31,0 | 13 | au_dessus_seuil |
| 10/10 | 11,5 | 5 | sous_seuil |

- Au-dessus du seuil (5 jours) : (14 + 18 + 16 + 20 + 13) / 5 = 81 / 5 = **16,2**
- Sous le seuil (5 jours) : (8 + 9 + 10 + 7 + 5) / 5 = 39 / 5 = **7,8**
- Différence : 16,2 − 7,8 = **8,4 admissions par jour**

Le client sans bruit (`tp/TP4_Gouvernance/client_laboratoire.py`) retrouve exactement ces valeurs (capture `TP4_client_sans_bruit.png`).

Remarque : le 09/10 (31,0 µg/m³) est classé `au_dessus_seuil` car 31,0 > 30, même s'il est très proche du seuil.

## Tests négatifs réalisés

| Test | Attendu | Capture |
|---|---|---|
| Finalité `commercial` | 403 | `TP4_A_finalite_403.png` |
| Clé API incorrecte (nœud A) | 401 | `TP4_A_cle_401.png` |
| Clé API incorrecte (nœud B) | 401 | `TP4_B_cle_401.png` |
| Signature falsifiée (sous-ensemble de dates) | 403 | `TP4_B_signature_403.png` |
| 4ᵉ appel / contournement du budget ε | 429 | `ATTAQUE_budget.png` |

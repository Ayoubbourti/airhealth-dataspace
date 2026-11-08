# Attaque n°2 : contournement du budget epsilon

Faille : le budget est lié au contract_id, et apply_dp est choisi par le client.
Résultat : avec 40 contrats x 3 appels (120 réponses bruitées), le laboratoire estime
16.25 / 8.32 (réel 16.2 / 7.8). Avec apply_dp absent, il obtient les valeurs exactes.
Correction prévue : bruit imposé côté hôpital + budget par (consommateur, dataset), persistant.
# Corrections testées : volume local (Rohmer 2008) et DQS anti-gonflement (Kim & Han 2014)

Scripts : `engine/validation/skinning/correction_volume.py`, `correction_bulge.py`, `experience_volume.py`,
`experience_bulge.py`. Tests : `test_metriques_synthetiques.py`, tests K1a à K1c.
Données : `masculin.json`, `feminin.json`, `maria.json`, `bulge_*.json` (même dossier).

## Résultats (flex120 et combo, même poses et mesures que comparer_v2)

| Personnage | Variante | max | >1,25 | >1,5 | retournements | vol. total | vol. zone |
|---|---|---:|---:|---:|---:|---:|---:|
| masculin | LBS | 2,471 | 211 | 86 | 4 | −4,49 % | −29,9 % |
| masculin | LBS + C3 | 2,449 | 215 | 93 | 7 | 0,00 % | −23,4 % |
| masculin | DQS | 3,288 | 213 | 130 | 1 | +1,27 % | +17,4 % |
| masculin | DQS + C3 | 3,303 | 211 | 129 | 1 | 0,00 % | +14,3 % |
| masculin | DQS + anti-gonflement | 6,448 | 204 | 121 | 1 | −1,10 % | +4,7 % |
| féminin | LBS | 2,525 | 195 | 92 | 6 | −5,44 % | −31,3 % |
| féminin | LBS + C3 | 2,500 | 208 | 96 | 6 | 0,00 % | −21,6 % |
| féminin | DQS | 3,324 | 186 | 116 | 0 | +1,49 % | +18,5 % |
| féminin | DQS + anti-gonflement | 5,280 | 180 | 111 | 0 | −0,80 % | +4,2 % |
| Maria | LBS | 8,300 | 101 | 70 | 18 | −0,87 % | +22,1 % |
| Maria | LBS + C3 | 8,300 | 101 | 70 | 18 | −0,57 % | +21,9 % |
| Maria | DQS | 10,003 | 110 | 83 | 26 | +0,02 % | +30,2 % |
| Maria | DQS + anti-gonflement | 10,003 | 106 | 81 | 26 | −0,78 % | +22,9 % |

Abduction (abd30) : DQS 1,96 → anti-gonflement 5,23 (masculin) ; DQS 1,87 → 4,62 (féminin).

Coût CPU par pose : correction Rohmer 1 étape 0,02 s, 3 étapes 0,045 s ; anti-gonflement 0,002 s.

## Lecture
- La correction de volume est exacte sur le volume total (1e-14) mais n'améliore aucun maximum d'étirement et augmente
  les retournements (entrée 164).
- L'anti-gonflement réduit le gonflement de zone mais multiplie le maximum d'étirement par 1,6 à 1,9 (entrée 165). Il est
  refusé en l'état ; l'approximation des segments d'os est la cause suspectée, non testée.
- Aucune des deux variantes ne satisfait les critères sur les trois morphologies. La phase 4 reste ouverte.

# Étape 3b : blend rigide articulaire (candidat C1), interpolation et généralisation

## Candidat
x'(v) = (1 − s) x_LBS(v) + s x_rig(v), s(v) = clamp(1 − d(v, centre)/(α L_os), 0, 1).
- centre = tête réelle de l'os articulé (étape 1), L_os = longueur réelle de cet os, x_rig = transformation rigide
  de la chaîne (rotation autour de l'axe X réel de l'os).
- Aucune cible sculptée, aucune cible HR (voir étape 3a : les HR sont identiques au LBS).

## Générateur de poses (validé)
- Reproduit les matrices réelles des poses L_flex90, L_flex120 et L_genou90 à 1,5e-7 près (chaîne complète).
- Permet des angles intermédiaires (75°, 105°) qui n'existent pas dans les données.
- Signes mesurés sur les poses réelles : masculin et féminin hanche −1, genou +1 ; Maria hanche +1, genou −1.

## Protocole (fixé avant calcul)
- Calibration : hanche gauche 60° et 90°, masculin uniquement. Critère : p99 ≤ LBS et retournements ≤ LBS, sur chaque pose.
- Test (jamais utilisé pour α) : hanche gauche 75°, 105°, 120° ; hanche droite 75°, 120° ; genou gauche 60°, 90°, 105°.

## Résultats
- Calibration : aucun α accepté. α = 0,25 échoue de 0,005 sur le p99 (1,159 contre 1,154 en LBS) : à ce niveau le blend ne
  change presque rien. Les α plus grands échouent davantage.
- Interpolation (PSD), erreur |δ(75) − (δ(60)+δ(90))/2| sur la correction δ = méthode − LBS :
  DQS 1,73 mm ; C1 : α 0,25 → 0,19 mm ; 0,5 → 1,13 mm ; 0,75 → 2,16 mm ; 1,0 → 3,16 mm.
  (Mesurer la position brute donnait la même valeur pour toutes les méthodes : la courbure des trajectoires rigides
  domine. Métrique corrigée, voir entrée 178.)

Résultats de test (8 poses par morphologie, informatifs seulement, α non choisi) :

| Morphologie | Méthode | Étirement max pire | p99 moyen | Retournements | |Volume| max |
|---|---|---:|---:|---:|---:|
| masculin | LBS | 2,485 | 1,106 | 31 | 0,045 |
| masculin | DQS | 3,288 | 1,128 | 15 | 0,014 |
| masculin | C1 α 0,5 | 2,637 | 1,127 | 5 | 0,049 |
| masculin | C1 α 1,0 | 2,393 | 1,493 | 9 | 0,114 |
| féminin | LBS | 2,525 | 1,086 | 39 | 0,055 |
| féminin | DQS | 3,324 | 1,099 | 23 | 0,016 |
| féminin | C1 α 0,5 | 2,657 | 1,148 | 12 | 0,062 |
| féminin | C1 α 1,0 | 2,470 | 1,555 | 12 | 0,138 |
| Maria | LBS | 8,300 | 1,000 | 126 | 0,036 |
| Maria | DQS | 10,003 | 1,013 | 150 | 0,036 |
| Maria | C1 α 0,5 | 5,221 | 1,130 | 68 | 0,047 |
| Maria | C1 α 1,0 | 2,875 | 1,630 | 216 | 0,084 |

## Lecture
- Sur Maria, C1 réduit le maximum d'étirement de 8,3 à 2,9 (α = 1,0), mais le p99 passe de 1,00 à 1,63 et le volume
  s'écarte davantage. Gain sur une métrique, dégradation sur les autres : rejeté.
- Sur masculin et féminin, C1 ne réduit pas le maximum de manière significative (2,49 → 2,39 au mieux) et dégrade le p99.
- Aucun candidat ne passe le critère de calibration ; la généralisation n'est donc pas testable comme prévu.

## Décision
C1 n'est pas intégré. Référence inchangée (LBS, DQS, Bone Heat).

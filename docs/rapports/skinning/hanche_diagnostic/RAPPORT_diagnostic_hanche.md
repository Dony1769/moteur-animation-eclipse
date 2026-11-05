# Diagnostic de la hanche et expériences contrôlées sur les poids (phase 4, étapes A et B)

Outils : `engine/validation/skinning/diagnostic_hanche.py` et `experience_poids_controlee.py`. Pose de référence : L_flex120.
Zone D : sommets dont l'étirement LBS dépasse 1,25. Zone Z : sommets à moins de 0,20 m de la tête de LeftUpLeg.

## A. Diagnostic (sans modification)

### HBM masculin

- Sommets D : 211 ; sommets Z : 235. Os dominant dans D : {'Hips': 23, 'Spine': 40, 'Spine1': 45, 'LeftUpLeg': 74, 'RightUpLeg': 29}.
- Poids moyens dans Z (LeftUpLeg / Hips / Spine) : 0.534 / 0.155 / 0.169.
- Transition max par arête dans D (Hips / Spine / Spine1 / LeftUpLeg / RightUpLeg) : 0.19 / 0.20 / 0.23 / 0.23 / 0.21.
- Transition max par arête hors D (même ordre) : 0.19 / 0.25 / 0.29 / 0.38 / 0.37.
- Volume dans Z : LBS -29.9 % ; DQS +17.4 %.
- Étirement max dans Z : LBS 2.47 ; DQS 3.29.
- |LBS − DQS| sur D : moyenne 33.6 mm, max 70.9 mm. Sommets D plus étirés en DQS qu'en LBS : 125.

### HBM féminin

- Sommets D : 195 ; sommets Z : 323. Os dominant dans D : {'Hips': 21, 'Spine': 47, 'Spine1': 27, 'LeftUpLeg': 72, 'RightUpLeg': 28}.
- Poids moyens dans Z (LeftUpLeg / Hips / Spine) : 0.398 / 0.138 / 0.132.
- Transition max par arête dans D (Hips / Spine / Spine1 / LeftUpLeg / RightUpLeg) : 0.28 / 0.26 / 0.24 / 0.30 / 0.27.
- Transition max par arête hors D (même ordre) : 0.26 / 0.29 / 0.30 / 0.82 / 0.81.
- Volume dans Z : LBS -31.3 % ; DQS +18.5 %.
- Étirement max dans Z : LBS 2.53 ; DQS 3.32.
- |LBS − DQS| sur D : moyenne 30.8 mm, max 74.3 mm. Sommets D plus étirés en DQS qu'en LBS : 114.

### Maria

- Sommets D : 101 ; sommets Z : 479. Os dominant dans D : {'Hips': 52, 'LeftUpLeg': 43, 'RightUpLeg': 6}.
- Poids moyens dans Z (LeftUpLeg / Hips / Spine) : 0.256 / 0.679 / 0.015.
- Transition max par arête dans D (Hips / Spine / Spine1 / LeftUpLeg / RightUpLeg) : 0.65 / 0.01 / 0.00 / 0.73 / 0.52.
- Transition max par arête hors D (même ordre) : 0.50 / 0.38 / 0.37 / 0.41 / 0.48.
- Volume dans Z : LBS +22.1 % ; DQS +30.2 %.
- Étirement max dans Z : LBS 8.30 ; DQS 10.00.
- |LBS − DQS| sur D : moyenne 18.7 mm, max 57.8 mm. Sommets D plus étirés en DQS qu'en LBS : 80.

Figures : `masculin/poids_par_os_zone_hanche.png` (poids par os), `masculin/carte_thermique_deformations.png` (étirement LBS, DQS, |LBS−DQS|), et les mêmes pour `feminin/` et `maria/`.

Constats : les transitions dans D ne sont pas plus raides que hors D sur le masculin et le féminin ; sur Maria, elles le sont (0,65–0,73 contre 0,41–0,50 hors D). Le volume dans la zone est faux dans les deux sens (LBS perd environ 30 %, DQS gagne environ 17 % sur les deux premiers) : aucune méthode ne conserve le volume local.

## B. Expériences contrôlées (poids modifiés dans Z seulement, même pose, même méthode)

E0 reproduit le système actuel à 1e-15 m (contrôle). Variantes : E1 nette (un os par sommet), E2 lissée (5 itérations), E3 sans cuisse, E4 sans bassin, E5 gradient limité automatiquement (seuil = percentile 95 des gradients hors zone, fixé avant mesure).

### HBM masculin

| variante | max | p99 | >1,1 | >1,25 | >1,5 | vol. zone | vol. total | retournements | max DQS |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| E0_reference | 2.471 | 1.185 | 285 | 211 | 86 | -29.9 % | -4.5 % | 4 | 3.288 |
| E5_gradient_limite | 2.458 | 1.184 | 279 | 211 | 93 | -31.0 % | -4.7 % | 1 | 2.611 |
| E1_nette | 17.065 | 1.004 | 165 | 125 | 71 | +3.5 % | -1.2 % | 20 | 17.065 |
| E2_lissee | 2.513 | 1.177 | 285 | 198 | 88 | -33.8 % | -4.9 % | 2 | 3.349 |
| E3_sans_cuisse | 11.604 | 1.002 | 149 | 108 | 58 | -0.1 % | -1.5 % | 16 | 11.613 |
| E4_sans_bassin | 6.189 | 1.184 | 261 | 211 | 160 | -30.7 % | -4.4 % | 13 | 7.048 |

Repli (sommets sans poids après retrait, reçoivent Hips) : {'E3_sans_cuisse': 14, 'E4_sans_bassin': 0}. Contrôle E0 : 1.3e-15 m.

### HBM féminin

| variante | max | p99 | >1,1 | >1,25 | >1,5 | vol. zone | vol. total | retournements | max DQS |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| E0_reference | 2.525 | 1.156 | 264 | 195 | 92 | -31.3 % | -5.4 % | 6 | 3.324 |
| E5_gradient_limite | 2.652 | 1.169 | 271 | 191 | 101 | -33.3 % | -5.7 % | 3 | 2.908 |
| E1_nette | 13.746 | 1.000 | 130 | 105 | 64 | -1.2 % | -1.7 % | 14 | 13.746 |
| E2_lissee | 2.353 | 1.161 | 267 | 189 | 83 | -35.8 % | -6.0 % | 0 | 3.011 |
| E3_sans_cuisse | 13.896 | 1.000 | 113 | 88 | 47 | -10.1 % | -2.2 % | 10 | 13.896 |
| E4_sans_bassin | 3.529 | 1.194 | 245 | 207 | 158 | -32.9 % | -5.8 % | 14 | 3.915 |

Repli (sommets sans poids après retrait, reçoivent Hips) : {'E3_sans_cuisse': 42, 'E4_sans_bassin': 0}. Contrôle E0 : 1.3e-15 m.

### Maria

| variante | max | p99 | >1,1 | >1,25 | >1,5 | vol. zone | vol. total | retournements | max DQS |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| E0_reference | 8.300 | 1.000 | 146 | 101 | 70 | +22.1 % | -0.9 % | 18 | 10.003 |
| E5_gradient_limite | 2.895 | 1.034 | 155 | 109 | 73 | +21.6 % | -0.9 % | 17 | 3.157 |
| E1_nette | 14.440 | 1.000 | 38 | 36 | 34 | +26.0 % | -0.4 % | 18 | 14.440 |
| E2_lissee | 3.007 | 1.021 | 132 | 62 | 32 | -2.9 % | -3.6 % | 9 | 3.649 |
| E3_sans_cuisse | 20.544 | 1.000 | 80 | 78 | 76 | +2.9 % | -1.3 % | 35 | 20.544 |
| E4_sans_bassin | 14.068 | 1.000 | 92 | 88 | 84 | +29.1 % | -0.1 % | 33 | 14.068 |

Repli (sommets sans poids après retrait, reçoivent Hips) : {'E3_sans_cuisse': 63, 'E4_sans_bassin': 243}. Contrôle E0 : 6.7e-16 m.

## Lecture (chaque point vaut pour les trois morphologies sauf mention)

- **Transition nette (E1)** : maximum multiplié par 5 à 6 (14 à 17). Les transitions raides sont donc nuisibles partout.
- **Retrait de la cuisse (E3) ou du bassin (E4)** : pire partout (3,5 à 20). Les deux apports sont nécessaires.
- **Lissage (E2)** : réduit les retournements et les comptages sur les trois, mais la perte de volume de la zone s'aggrave sur le masculin et le féminin, et le maximum du masculin augmente un peu (2,47 → 2,51). Ce n'est pas une amélioration nette : refusée comme correction.
- **Gradient limité (E5)** : Maria passe de 8,30 à 2,90 au maximum, mais ses comptages au-delà de 1,25 augmentent (101 → 109). Sur le masculin et le féminin, le maximum ne baisse pas et les comptages au-delà de 1,5 augmentent. Refusée comme correction validée.
- **Conclusion sur les poids** : leur responsabilité est démontrée sur Maria seulement (les transitions raides dans D). Pour le masculin et le féminin, la cause n'est pas établie par les poids. Aucune variante de poids ne passe tous les critères sur les trois morphologies.

## Non fait dans cette étape
- Corrective Blend Shapes et PSD : elles exigent des formes cibles (sculptées ou simulées). Aucune n'est disponible ici ; une cible tirée du modèle lui-même serait circulaire. Décision à prendre (voir le rapport d'étape).
- DQS avec correction de volume : pas implémentée dans cette étape. Le volume de zone reste le critère bloquant (−30 % en LBS, +17 % en DQS).
- Étape C complète (intersections réelles, continuité, temps CPU, qualité visuelle par variante) : non faite pour les variantes de poids, car aucune ne passe le premier critère.
- Étape D (généralisation) : pas de méthode retenue, donc rien à généraliser. La règle de seuil E5 est automatique, mais elle n'est pas validée.
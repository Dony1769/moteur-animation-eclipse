# Comparatif v2 : LBS, DQS, hybrides sur trois morphologies (phase 4, priorité 3)

Généré par `engine/validation/skinning/comparer_v2.py` à partir des JSON de ce dossier. Mêmes poses, mêmes matrices,
même maillage de base, mêmes mesures pour chaque personnage. Chaque personnage est présenté séparément.

Colonnes : retournements (comptage), p99 et **maximum** de l'étirement, nombre d'arêtes/sommets > 1,25 et > 1,5,
écart maximal au mouvement rigide de l'os dominant (mm), variation de volume (%), étirement maximal dans la zone
hanche et dans la zone genou (sphères de 20 cm autour de la tête de l'os).

## HBM masculin (10 582 sommets)

| pose | méthode | retourn. | p99 | max | n>1,25 | n>1,5 | résidu os max (mm) | vol. (%) | hanche max | genou max |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| L_flex120 | LBS | 4 | 1.185 | 2.471 | 211 | 86 | 161.8 | -4.49 | 2.471 | 1.184 |
| L_flex120 | DQS | 1 | 1.250 | 3.288 | 213 | 130 | 183.3 | +1.27 | 3.288 | 1.050 |
| L_flex120 | HYBRIDE_global | 1 | 1.223 | 2.876 | 203 | 107 | 170.2 | -1.89 | 2.876 | 1.114 |
| L_flex120 | HYBRIDE_angle | 1 | 1.250 | 3.288 | 213 | 130 | 183.3 | +1.27 | 3.288 | 1.050 |
| L_combo_flex120_genou90 | LBS | 12 | 1.185 | 2.471 | 211 | 86 | 161.8 | -5.62 | 2.471 | 1.196 |
| L_combo_flex120_genou90 | DQS | 5 | 1.253 | 3.288 | 218 | 130 | 183.3 | +0.44 | 3.288 | 1.277 |
| L_combo_flex120_genou90 | HYBRIDE_global | 8 | 1.223 | 2.876 | 203 | 107 | 170.2 | -2.88 | 2.876 | 1.195 |
| L_combo_flex120_genou90 | HYBRIDE_angle | 5 | 1.253 | 3.288 | 218 | 130 | 183.3 | +0.44 | 3.288 | 1.277 |
| L_genou90 | LBS | 8 | 1.020 | 1.196 | 0 | 0 | 65.9 | -1.13 | 1.000 | 1.196 |
| L_genou90 | DQS | 4 | 1.010 | 1.277 | 5 | 0 | 71.3 | -0.83 | 1.000 | 1.277 |
| L_genou90 | HYBRIDE_global | 7 | 1.014 | 1.195 | 0 | 0 | 67.3 | -0.99 | 1.000 | 1.195 |
| L_genou90 | HYBRIDE_angle | 4 | 1.010 | 1.277 | 5 | 0 | 71.3 | -0.83 | 1.000 | 1.277 |
| L_abd30 | LBS | 0 | 1.043 | 1.910 | 25 | 9 | 50.2 | +0.99 | 1.910 | 1.062 |
| L_abd30 | DQS | 0 | 1.043 | 1.959 | 23 | 11 | 50.6 | +1.15 | 1.959 | 1.051 |
| L_abd30 | HYBRIDE_global | 0 | 1.042 | 1.935 | 24 | 9 | 50.3 | +1.07 | 1.935 | 1.056 |
| L_abd30 | HYBRIDE_angle | 0 | 1.043 | 1.943 | 23 | 9 | 50.4 | +1.10 | 1.943 | 1.054 |

Contrôle LBS vs Blender : erreur max 5.9e-07 m sur 28 poses.

## HBM féminin, poids Bone Heat (10 582 sommets)

| pose | méthode | retourn. | p99 | max | n>1,25 | n>1,5 | résidu os max (mm) | vol. (%) | hanche max | genou max |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| L_flex120 | LBS | 6 | 1.156 | 2.525 | 195 | 92 | 139.0 | -5.44 | 2.525 | 1.064 |
| L_flex120 | DQS | 0 | 1.196 | 3.324 | 186 | 116 | 160.0 | +1.49 | 3.324 | 1.011 |
| L_flex120 | HYBRIDE_global | 0 | 1.183 | 2.921 | 192 | 95 | 145.8 | -2.31 | 2.921 | 1.037 |
| L_flex120 | HYBRIDE_angle | 0 | 1.196 | 3.324 | 186 | 116 | 160.0 | +1.49 | 3.324 | 1.011 |
| L_combo_flex120_genou90 | LBS | 16 | 1.163 | 2.525 | 201 | 96 | 139.0 | -6.76 | 2.525 | 1.613 |
| L_combo_flex120_genou90 | DQS | 8 | 1.201 | 3.324 | 192 | 120 | 160.0 | +0.14 | 3.324 | 1.736 |
| L_combo_flex120_genou90 | HYBRIDE_global | 8 | 1.187 | 2.921 | 198 | 99 | 145.8 | -3.66 | 2.921 | 1.675 |
| L_combo_flex120_genou90 | HYBRIDE_angle | 8 | 1.201 | 3.324 | 192 | 120 | 160.0 | +0.14 | 3.324 | 1.736 |
| L_genou90 | LBS | 10 | 1.000 | 1.613 | 6 | 4 | 48.4 | -1.33 | 1.000 | 1.613 |
| L_genou90 | DQS | 8 | 1.000 | 1.736 | 6 | 4 | 52.1 | -1.35 | 1.000 | 1.736 |
| L_genou90 | HYBRIDE_global | 8 | 1.000 | 1.675 | 6 | 4 | 48.7 | -1.35 | 1.000 | 1.675 |
| L_genou90 | HYBRIDE_angle | 8 | 1.000 | 1.736 | 6 | 4 | 52.1 | -1.35 | 1.000 | 1.736 |
| L_abd30 | LBS | 0 | 1.040 | 1.820 | 23 | 11 | 48.8 | +1.04 | 1.820 | 1.017 |
| L_abd30 | DQS | 0 | 1.036 | 1.867 | 24 | 11 | 49.2 | +1.26 | 1.867 | 1.012 |
| L_abd30 | HYBRIDE_global | 0 | 1.039 | 1.844 | 23 | 11 | 48.9 | +1.15 | 1.844 | 1.014 |
| L_abd30 | HYBRIDE_angle | 0 | 1.038 | 1.852 | 23 | 11 | 49.0 | +1.19 | 1.852 | 1.014 |

Contrôle LBS vs Blender : erreur max 5.9e-07 m sur 28 poses.

## Maria, FBX (8 094 sommets)

| pose | méthode | retourn. | p99 | max | n>1,25 | n>1,5 | résidu os max (mm) | vol. (%) | hanche max | genou max |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| L_flex120 | LBS | 18 | 1.000 | 8.300 | 101 | 70 | 99.5 | -0.87 | 8.300 | 1.000 |
| L_flex120 | DQS | 26 | 1.030 | 10.003 | 110 | 83 | 114.9 | +0.02 | 10.003 | 1.000 |
| L_flex120 | HYBRIDE_global | 21 | 1.004 | 9.137 | 101 | 76 | 103.5 | -0.49 | 9.137 | 1.000 |
| L_flex120 | HYBRIDE_angle | 26 | 1.030 | 10.003 | 110 | 83 | 114.9 | +0.02 | 10.003 | 1.000 |
| L_combo_flex120_genou90 | LBS | 36 | 1.057 | 8.300 | 120 | 79 | 99.5 | +0.22 | 8.300 | 1.927 |
| L_combo_flex120_genou90 | DQS | 41 | 1.098 | 10.003 | 132 | 98 | 114.9 | +1.28 | 10.003 | 1.900 |
| L_combo_flex120_genou90 | HYBRIDE_global | 37 | 1.066 | 9.137 | 121 | 88 | 103.5 | +0.68 | 9.137 | 1.793 |
| L_combo_flex120_genou90 | HYBRIDE_angle | 41 | 1.098 | 10.003 | 132 | 98 | 114.9 | +1.28 | 10.003 | 1.900 |
| L_genou90 | LBS | 18 | 1.000 | 1.927 | 19 | 9 | 42.5 | +4.33 | 1.000 | 1.927 |
| L_genou90 | DQS | 15 | 1.000 | 1.900 | 22 | 15 | 45.7 | +4.54 | 1.000 | 1.900 |
| L_genou90 | HYBRIDE_global | 16 | 1.000 | 1.793 | 20 | 12 | 43.0 | +4.43 | 1.000 | 1.793 |
| L_genou90 | HYBRIDE_angle | 15 | 1.000 | 1.900 | 22 | 15 | 45.7 | +4.54 | 1.000 | 1.900 |
| L_abd30 | LBS | 0 | 1.000 | 4.180 | 46 | 34 | 23.4 | +0.69 | 4.180 | 1.000 |
| L_abd30 | DQS | 0 | 1.000 | 4.224 | 48 | 31 | 23.6 | +0.74 | 4.224 | 1.000 |
| L_abd30 | HYBRIDE_global | 0 | 1.000 | 4.201 | 47 | 31 | 23.4 | +0.72 | 4.201 | 1.000 |
| L_abd30 | HYBRIDE_angle | 0 | 1.000 | 4.208 | 47 | 31 | 23.5 | +0.73 | 4.208 | 1.000 |

Contrôle LBS vs Blender : erreur max 2.6e-07 m sur 28 poses.

## Lecture

- **p99 ≈ 1,00 à 1,25 sur tous les personnages, y compris là où le maximum atteint 8,3 (Maria, hanche).** Le p99 ne suffit pas, c'est pourquoi les maxima et les comptages sont obligatoires.
- **DQS réduit les retournements et l'écart de volume (masculin flex120 : −4,49 % en LBS, +1,27 % en DQS) mais augmente le maximum d'étirement à la hanche (2,47 → 3,29 masculin ; 8,30 → 10,00 Maria).** Ce n'est pas une amélioration globale.
- **Les défauts sont localisés devant le bassin et le bas-ventre (hanche), pas seulement à l'aine.** Capture : `captures_masculin.png`, zone rouge à y ≈ −0,1 à 0,1, z ≈ 0,75 à 1,15.
- **Genou (genou90) : maximum 1,20 à 1,28 (masculin), 1,61 à 1,74 (féminin), 1,79 à 1,93 (Maria).** Le genou est donc le plus sensible chez Maria. Peu de sommets au-delà de 1,25, mais le maximum est trop élevé pour une validation.
- **Le résidu os dominant est grand à flex120 (16 cm) parce que les sommets du bassin mélangent des os qui se déplacent beaucoup ; c'est le mélange lui-même, pas une erreur de calcul.**
- **Abduction (abd30) : maximum 1,8 à 4,2 selon le personnage ; Maria est la plus défavorable (4,2 pour toutes les méthodes).**
- Phase 4 **non terminée** : hanche et genou ne sont pas satisfaisants (voir limites dans le rapport).

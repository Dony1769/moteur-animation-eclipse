# Optimisation des poids de skinning (expérimentale, non adoptée)

Date : 4 novembre 2026. Corps : `GEO-body_male_realistic` (HBM), pipeline de référence `corps_final.blend`, sans clés correctives, LBS standard.

## Méthode
Inspirée d'ARAP-LBS (Thiery et al., Telecom Paris, https://perso.telecom-paris.fr/jthiery/papers/araplbs/araplbs.pdf) : les poids sont optimisés pour que les arêtes se déforment le moins possible sur des poses d'exemple, au lieu de corriger la forme après coup par des clés.
- Énergie : Σ_arêtes (|x'_i − x'_j| / L_ij − 1)² + λ‖W − W0‖², λ = 1e-3.
- Contraintes : poids ≥ 0, somme 1 par sommet, mêmes os qu'au départ.
- Descente de gradient projetée sur le simplexe, 300 itérations, pas adaptatif.
- Évaluation : le LBS est reconstruit en numpy (`engine/skinning/lbs_numpy.py`) et confronté à la mesure Blender du projet (`controle_gonflement.py`, variante sans clés). Témoin : à 0°, étirement = 1.

## Témoin de validation
| Bras à 120° | numpy | Blender |
|---|---|---|
| étirement max (origine) | 3,3584 | 3,3584 |
| compression min (origine) | 0,1139 | 0,1139 |

Le harnais numpy reproduit exactement la mesure Blender.

## Résultats (test sur 120° jamais vu à l'entraînement, sauf mention)
| Variante | Bras max / min | Avant-bras max / min | Jambe max / min | Statut |
|---|---|---|---|---|
| Origine | 3,36 / 0,11 | 1,78 / 0,22 | 1,27 / 0,26 | référence |
| Bras seul, entraîné 60/90/105 | **1,65 / 0,55** (Blender confirmé) | 1,55 / 0,16 | 1,27 / 0,26 (inchangé) | meilleur bras, validé |
| Trois chaînes conjointes (60/90/105) | 1,74 / 0,47 | 1,45 / 0,38 | **1,40 / 0,35 (régression)** | rejeté |
| Masque par os dominant | **5,39** / 0,17 | 1,51 / 0,21 | 1,40 / 0,35 | rejeté (frontière) |
| Exposant 4 sur les arêtes extrêmes | 1,62 / 0,53 | 1,58 / 0,42 | **1,70 / 0,41 (régression)** | rejeté |
| Séquence bras puis jambe (60/90/105) | 1,65 / 0,55 | 1,55 / 0,16 | **1,40 / 0,35 (régression)** | rejeté |
| Séquence 60/90/120, test 105 | **5,43** / 0,26 | 1,34 / 0,65 | 1,16 / 0,36 | rejeté (arête courte au coude) |

Témoin à 0° : étirement 1,000 dans tous les cas.

## Constats
1. Le bras seul, entraîné sur des poses intermédiaires (60/90/105), réduit de moitié l'étirement maximal à 120°, sans augmenter le mouvement (déplacement moyen de la zone du bras 0,914 m → 0,914 m).
2. L'optimisation ne généralise pas hors de la plage d'entraînement : la jambe s'améliore à 60/90/105 et se dégrade à 120°.
3. Les chaînes conjointes se font concurrence sur les sommets partagés (bassin, hanche).
4. Masquer par os dominant crée une frontière brutale (étirement 5,39).
5. La métrique de ratio sur arêtes est très sensible aux arêtes courtes (1 cm au coude) : un petit déplacement de poids y crée un grand ratio. Il faut une pondération par longueur de repos, ou une garde de rejet.

## Ce qui reste à faire avant toute adoption
- Pondérer la perte par la longueur de repos (les arêtes courtes ne doivent pas dominer).
- Garde de rejet : refuser toute configuration dont l'étirement max augmente sur un angle d'entraînement.
- Valider chaque chaîne sur un angle de test non utilisé, et un témoin à 0°.
- Mesurer la déformation visuelle (carte d'étirement) avant d'adopter.

## Outils
- `engine/skinning/exporter_poids.py` : exporte géométrie, poids et matrices de pose (3 chaînes × 5 angles).
- `engine/skinning/lbs_numpy.py` : LBS et étirements en numpy.
- `engine/skinning/optimiser_poids.py` : optimisation (puissance 2 ou 4, lambda, poids initiaux).
- `engine/skinning/appliquer_poids.py` : réécrit des poids dans une copie du .blend pour la mesure Blender.
- Le pipeline de référence `construit_final.py` n'a pas été modifié.

## Plis (faces repliées) : résultat et calibration
- Métrique : `engine/skinning/plis_numpy.py`, calibrée sur Blender (`mesure_lbs.faces_repliees`) à ±4 faces (erreur 51).
- Poids du haut du corps (entraînement 60/90/120, test 75) : étirement du bras à 120° 3,36 → 1,56, mais plis du bras 15 → 32 (origine numpy → Blender). Avant-bras : 6 → 6 à 120°. Jambe inchangée.
- Conclusion : non adoptable. La garde de rejet doit désormais inclure le nombre de plis (non encore implémenté).

## Validation Blender des correctifs ARAP (formes-clés)
- LBS Blender = LBS numpy (2e-6). Clés de référence désactivées pour la mesure.
- Étirement max après correction : 1,08 à 1,23 sur tous les angles testés (origine : 3,36 à 120° pour le bras).
- Plis hors entraînement : bras 75° 0, bras 105° 4 (origine 12) ; avant-bras 75° 0, 105° 4 (origine 2, 5) ; jambe 75° 0, 105° 3 (origine 1, 7).
- Plis résiduels à 120° : bras 12, avant-bras 4, jambe 8 (origine 15, 6, 10).
- Non retenus : amortissement des plis (erreur 56), pondération cotangente (erreur 57, gain mixte).

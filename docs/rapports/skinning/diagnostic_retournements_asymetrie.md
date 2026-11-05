# Diagnostic des différences de retournements gauche/droite (phase 4, priorité 1)

Outil : `engine/validation/skinning/diff_retournements.py` (appariement polygone à polygone par les sommets miroir).

## Résultats polygone par polygone
| Modèle | Mouvement | Retournements G / D | Polygones différents | Cosinus (G / D) |
|---|---|---|---|---|
| masculin | flex120 | 4 / 5 | 1 (repos x −2,15 ; z 0,92) | +0,10 / −0,65 |
| masculin | combo_flex120_genou90 | 12 / 13 | même polygone | +0,10 / −0,65 |
| féminin | genou60 | 3 / 2 | 1 (x −2,14 ; z 0,47) | −0,18 / +0,30 |
| féminin | combo_flex90_abd30_ext30 | 1 / 2 | 3 | −0,16 à +0,22 |
| féminin | combo_flex60_abd20_int20_genou60 | 3 / 2 | 1 | −0,18 / +0,30 |

Les autres mouvements (masculin genou60, combo_flex90, combo_flex60 ; féminin flex90) : 0 différence.

## Causes testées
1. **Pose** (mouvement des os gauche/droite) : symétrique à < 0,2 mm et < 0,001 rad sur les os de jambe. Écarté.
2. **Repos non symétrique** : symétriser le repos seul ne change pas les compteurs (4/5 et 12/13). Écarté comme cause suffisante.
3. **Poids** : les poids automatiques de Bone Heat diffèrent de 0,01 à 0,03 entre sommets miroir (ex. 0,682 contre 0,658 ;
   0,571 contre 0,555). Symétriser les poids seuls donne 5 = 5 et 13 = 13. **Cause retenue** pour les compteurs.
4. **Sensibilité du pli** : au pli de l'entrejambe, un écart de 1 à 3 mm entre sommets posés fait basculer la normale
   d'environ 40°. Le cosinus n'est donc pas un seuil fiable.

## Conclusion
Le critère « comptages de retournements égaux » mesure, sur ces polygones, l'asymétrie des poids automatiques
de Blender (2 à 4 %), amplifiée par le pli. Ce n'est pas une asymétrie de déformation anatomique.
Le critère n'est pas modifié (règle phase 4). Les échecs sont conservés et expliqués ici.

## Limite à déclarer
Les poids symétrisés ne sont pas une vérité : on ne sait pas lequel des deux côtés est « juste ». Il faut une référence
externe (poids à la main ou transfert symétrique) pour trancher.

# Critère Maria (fixé avant mesure)
Voir `criteres_asymetrie_maria.md`. Résultat : OK sur les 14 mouvements pour les trois morphologies (écart p99 de
l'étirement < 0,8 %).
**Mise en garde** : ce critère est un percentile 99 ; il ne mesure pas les étirements locaux maximaux, qui restent
élevés au genou et à l'entrejambe (2,4 à 8 selon le corps). Un passage à ce critère ne valide pas la qualité
anatomique. La phase 4 reste ouverte.

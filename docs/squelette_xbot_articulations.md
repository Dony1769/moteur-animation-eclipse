# Squelette de référence X-Bot : articulations, axes et jonctions (phase 4)

Source : fichier `X-Bot` fourni par l'utilisateur (FBX binaire 7700, 65 os, deux maillages :
`Beta_Surface` et `Beta_Joints`, 10 514 sommets de marqueurs d'articulation). Lecture par Blender 4.5.15 en mode headless.

## Points de jonction (centres, mètres, repère X-Bot : Z vers le haut, bras en T le long de X)

| Articulation | Os parent → enfant | Centre (tête de l'os enfant) | Type |
|---|---|---|---|
| Hanche | Hips → LeftUpLeg | (0,082 ; 0,000 ; 0,975) | rotule (3 DDL) |
| Genou | LeftUpLeg → LeftLeg | (0,082 ; −0,003 ; 0,532) | charnière |
| Cheville | LeftLeg → LeftFoot | (0,082 ; 0,027 ; 0,087) | charnière |
| Épaule | Spine2 → LeftShoulder → LeftArm | (0,152 ; 0,056 ; 1,441) | rotule (3 DDL) |
| Coude | LeftArm → LeftForeArm | (0,430 ; 0,056 ; 1,441) | charnière |
| Poignet | LeftForeArm → LeftHand | (0,713 ; 0,056 ; 1,441) | condylienne (2 DDL) |

## Axes de flexion (axe local X de chaque os, exprimé en monde)
- Genou, cheville : axe monde X (flexion dans le plan sagittal).
- Coude : axe monde Y quand le bras est en T (le bras est horizontal chez X-Bot). Dans le modèle HBM, le bras pend : l'axe devient X, ce qui est l'hypothèse actuelle de la chaîne.
- Hanche : os enfant tourne autour de l'axe X au point de jonction, avec 3 DDL réels.

## Sens de pliage (règle anatomique à implémenter)
Chaque jonction n'autorise qu'un ensemble de mouvements. Une pose hors de cet ensemble est impossible :
- coude et genou : flexion seule, extension limitée à quelques degrés (hyperextension mesurée 3,9° et 1,9° en moyenne) ;
- cheville : flexion dorsale 15°, flexion plantaire 56° ;
- hanche : flexion 130°, extension 20° ;
- épaule : flexion 170°, extension limitée.

## Constat sur le modèle HBM actuel (`engine/skinning/limites_articulations.py`, `penetration.py`)
Pénétrations nouvelles par angle, méthode des chaînes actuelle (bande B), mesurées dans le repère HBM :

| Articulation | Angles normaux testés | Pénétrations nouvelles |
|---|---|---|
| Genou | 30 / 60 / 90 / 120 / 140 | 11 / 3 / 0 / 8 / 40 |
| Coude | −10 (hyperextension) / 30 / 60 / 90 / 120 / 145 | 5 / 36 / 17 / 5 / 0 / 0 |
| Cheville | −55 / −30 / +15 | 71 / 57 / 1 |
| Hanche | 30 / 60 / 90 / 120 / 130 | 9 / 13 / 14 / 26 / 31 |
| Épaule | 20 / 60 / 90 / 120 / 170 | 1 / 9 / 32 / 30 / 43 |
| Poignet | −10 / 30 / 50 / 80 | 0 / 0 / 0 / 0 |

Conclusion : la méthode actuelle pénètre dans toutes les articulations sauf le poignet (que nous ne savons pas mesurer,
faute de valeur officielle). Le coude en hyperextension (−10°) pénètre : c'est le défaut que vous avez vu.

## Ce qui est dans ce commit et ce qui ne l'est pas
- Fait : bornes anatomiques (source CDC), mesure de pénétration par articulation, constat ci-dessus.
- Non fait : calotte rigide au point de jonction (génération géométrique), validation Blender, rig 47 os
  avec nœuds de jonction, bornes d'abduction de hanche et d'épaule, poignet.

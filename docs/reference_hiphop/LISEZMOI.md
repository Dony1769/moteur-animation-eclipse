# Référence de mouvement : Hip Hop Dancing (X-Bot, Mixamo)

Fichiers fournis par l'utilisateur :
- `Hip_Hop_Dancing__1_.fbx` (avec peau : 3 maillages, 2 skins, 53 clusters) → `angles_articulations_avec_peau.json`
- `Hip_Hop_Dancing.fbx` (sans peau : squelette et courbes seulement) → `angles_articulations_sans_peau.json`

Squelette : 65 os, préfixe `mixamorig1:`. Cadre 1 à 250. Échelle FBX 0,01 appliquée à l'objet (cm → m).

## Plages réelles de la danse (250 images, angles de flexion, 0 = membre tendu)
| Articulation | Min | Max |
|---|---|---|
| Coude gauche | 3,0° | 82,8° |
| Coude droit | 0,6° | 100,3° |
| Genou gauche | 8,9° | 150,0° |
| Genou droit | 4,7° | 146,4° |

## Angles depuis la verticale (cône, non séparé flexion / abduction)
| Segment | Min | Max |
|---|---|---|
| Cuisse gauche | 2,2° | 90,0° |
| Bras gauche | 1,6° | 86,1° |
| Bras droit | 4,3° | 92,4° |

## Poids de peau au coude : profil brut, non fiable
`profil_poids_coude_brut.json` : échantillonnage de peu de sommets près du coude, pose de référence du maillage incertaine. Ne pas s'en servir pour fixer la largeur de la zone de fusion avant une mesure plus dense (voir erreur 97).

## Ce que ces données valident et ce qu'elles ne valident pas
- Valident (plage d'entraînement de la danse) : coude jusqu'à 100°, genou jusqu'à 150°, cuisse et bras jusqu'à 90° du vertical.
- Ne valident pas les limites humaines complètes : coude 145°, hanche 120°, épaule 180°. Ces limites restent celles du CDC/NCHS.

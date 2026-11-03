# Étape 3 : auto-skinning du corps HBM (test B)

## Statut
Fait et testé pour le **corps masculin HBM** (sans skinning). Le contrôle qualité déclare le personnage
`READY FOR ANIMATION`, score 100. Défaut visuel connu signalé plus bas.

## Source
- Bundle : `assets/hbm/human-base-meshes-bundle-v1.4.1/human_base_meshes_bundle.blend` (Human Base Meshes, Blender Studio, CC0).
- Extraction : `engine/skinning/extraire_hbm.py` copie `GEO-body_male_realistic` et ses deux yeux, sans armature ni poids.
- Le fichier source n'est jamais modifié. Les `.blend` produits ne sont pas committés (reproductibles).

## Méthode (déterministe, CPU)
1. **Mesure** : hauteur 1,69 m (bbox Z), ligne médiane en X (−2,264) et Y.
2. **Tronc et jambes** : articulations placées à des fractions anatomiques de la hauteur (hanches 0,52 H, genoux 0,285 H, chevilles 0,04 H, épaules 0,80 H, cou 0,84 H), écart des hanches mesuré.
3. **Bras** : centres de masse des sections horizontales, hors du tronc, de chaque côté (épaule à 0,80 H, coude à 0,64 H, poignet à 0,47 H). Les positions des bras ne sont pas figées : elles sont calculées sur la géométrie.
4. **Poids** : Blender `ARMATURE_AUTO` (diffusion de chaleur). Repli `ARMATURE_ENVELOPE` prévu, non déclenché.
5. **Post-traitement** (Python explicite) : lissage par voisinage (2 passes, facteur 0,5), limite à 4 influences, normalisation à 1.
6. **Pièces rigides** : les yeux sont attachés en rigide à l'os `mixamorig:Head` (transformation monde conservée).

Squelette : 19 os, nommage Mixamo (`mixamorig:*`), une racine (`Hips`).

## Tests
Script : `engine/skinning/auto_skin.py`. Rapport : `docs/rapports/hbm_skinning_tests.json`.

| Test | Résultat |
|---|---|
| Pose de repos inchangée (écart max) | 0,0005 mm |
| Épaule, coude, hanche, genou (gauche et droite) | passent |
| Colonne et cou | passent |
| Fuite vers les sommets non rattachés | 0 à 0,7 % (tolérance 1 %) |
| Aucun NaN, déplacement max < 0,5 H | passent |

Critère de fuite : un os ne doit déplacer de plus de 2 cm que les sommets qui lui sont liés (groupe dominant = cet os ou un descendant). Le bras est donc légitimement mobile quand la colonne se plie.

Contrôle qualité : `docs/rapports/hbm_corps_skinne.json` (diagnostic réel sur le fichier skinné) → `READY FOR ANIMATION`, 100.

Pour la mise à jour de l'outil de diagnostic : `engine/importer/diagnostic.py` expose désormais `parent_type` et `parent_os` (lecture seule). `engine/validation/controle.py` accepte une pièce rigide attachée à un os comme « skinning » valide pour un objet qui ne se déforme pas.

Non-régression : `tests/test_skinning.py` (4 tests sur les rapports committés).

## Défauts connus
- **Pincement visible** au coude et au poignet à 60° de flexion (contrôle visuel à gros plan, `Workbench`). Le test numérique le couvre mal : il vérifie l'absence de fuite, pas la qualité du pli. À corriger par poids correctifs (étape de correction, non faite).
- **Épaule** : déplacement maximal de 0,67 m à 60°, à vérifier en animation réelle.
- **Squelette estimé** : les articulations sont des mesures de sections, sans référence anatomique par corps réel. Il n'a été testé que sur ce corps.
- **Rendu visuel** : contrôle à l'œil sur deux images, pas sur une animation.
- Pas de test sur un second personnage non skinné : test B n'est couvert que par ce corps.

## Correction des pliages (étape 3, suite)

Défaut mesuré : la déformation linéaire (LBS) fait se replier la surface au coude, à l'épaule et au genou. Mesure correcte : `engine/skinning/mesure_lbs.py` (faces repliées par rapport à la normale de repos tournée par l'os dominant ; témoin à 0° = 0 ; LBS explicite égal au modificateur Blender à 0,0005 mm).

Méthode retenue : clé de forme corrective par articulation (`engine/skinning/correction_pose.py`), calibrée à 90°, décalage vers l'intérieur de la surface, valeur de la clé = clamp(angle / 90, 0, 1). Le calcul complet est `engine/skinning/construit_correctives.py`, qui reprend le pipeline (squelette, skinning, attache des yeux, clés). Rapport : `docs/rapports/hbm_corrections.json`.

| Articulation | Replis à 90° avant | Après | Replis à 120° après |
|---|---|---|---|
| Bras gauche | 24 | 3 | 18 |
| Bras droit | 8 | 3 | 7 |
| Avant-bras gauche | 4 | 0 | 6 |
| Avant-bras droit | 0 | 0 | 2 |
| Jambe gauche | 5 | 0 | 10 |
| Jambe droite | 6 | 0 | 8 |

Amplitude au repos : 0,0 mm (la clé vaut 0 au repos).

Comparaison écartée : élargir seulement la zone de transition des poids (–17 % de replis à 90°). Insuffisant, mais reste dans le pipeline sous forme de lissage global.

Limites connues, à ne pas masquer :
- À 120°, il reste des replis (bras gauche 18). Une forme calibrée à 120° fait pire à 90° (13 replis). Il faudra un os de torsion ou une seconde forme pilotée.
- Les clés ont été calibrées chaque articulation seule. Leur combinaison (plusieurs articulations pliées à la fois) n'est pas encore testée : la chaîne épaule-coude doit être posée hiérarchiquement pour cela.
- La valeur `angle / 90` est une règle de test ; le pilotage automatique par les os (drivers) reste à écrire à l'étape rig.
- Les mesures portent sur le maillage de base ; le détail Multires n'est pas mesuré.

## Combinaisons d'articulations (mesurées)

Test : `engine/skinning/test_combinaisons.py`. Les chaînes sont posées hiérarchiquement (`engine/skinning/pose_chaine.py` : l'avant-bras suit le bras). Témoins : un os seul en chaîne retrouve les résultats du test à un os (6 et 5 replis).

| Scénario | Sans correction | Avec correction |
|---|---|---|
| Bras gauche 90° + avant-bras 90° | 28 | 3 |
| Bras gauche 60° + avant-bras 60° | 6 | 1 |
| Deux bras à 90° | 32 | 6 |
| Deux jambes à 90° | 11 | 0 |
| Corps entier à 60° | 7 | 1 |

Bilan : les corrections à 90° se combinent sans créer de replis nouveaux dans ces cas. Un scénario plus extrême (bras et avant-bras à 90° chacun) reste à 3 replis.

## Seconde pose (120°) et DQS : résultats mesurés

- Seconde clé, calibrée à 120° par-dessus la première, valeur `clamp((angle − 90) / 30)` (`engine/skinning/construit_seconde_pose.py`, rapport `docs/rapports/hbm_seconde_pose.json`) : avant-bras 6 → 0 et 2 → 0 à 120° ; jambes 10 → 3 et 8 → 5 ; bras gauche 22 → 20 (plafond de 40 mm atteint). Le bras reste le point faible.
- DQS (Preserve Volume), testé avec les clés (`engine/skinning/test_dqs_cles.py`, rapport `docs/rapports/hbm_dqs_cles.json`) : bras gauche 105° : 18 → 8 ; jambes 105° : 3 → 0 ; 120° : 20 → 17. Le gonflement du DQS n'est pas encore mesuré : le DQS n'est pas adopté.

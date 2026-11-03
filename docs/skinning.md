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

## Pipeline final : os d'aide + clés (mesuré)

Script : `engine/skinning/construit_final.py`. Rapport : `docs/rapports/hbm_final_epaule_cles.json`. 21 os, 0 sommet sans poids, 4 influences au plus.

Replis LBS, bras gauche : 60° : 0 ; 90° : 2 ; 105° : 6 ; 120° : 13. Combinaison des deux méthodes plus efficace que chacune seule (clés seules : 3 / 18 / 20 ; os d'aide seul : 12 / 17 / 19).

Limite : le champ `deplacement_max_120_mm` du rapport ne mesure pas le gonflement (voir erreur 21). Un contrôle de gonflement n'est pas encore implémenté.


## Contrôle de gonflement (mesuré)

Mesure : volume signé du maillage évalué / volume de repos, et étirement des arêtes (module `engine/skinning/controle_gonflement.py`). Témoin à 0° vérifié (`tests/test_gonflement.py`, tolérance 1,5e-3 justifiée par le plancher de précision mesuré).

| Variante | Bras 90° : volume / étirement max | Bras 120° : volume / étirement max | Replis bras 60/90/105/120 |
|---|---|---|---|
| LBS sans clés | 0,966 / 2,63 | 0,963 / 3,36 | — |
| LBS avec clés (pipeline de référence) | 0,964 / 3,59 | 0,961 / 5,90 | 0 / 2 / 6 / 13 |
| DQS avec clés | 0,955 / 4,08 | 0,940 / 6,81 | — |
| LBS avec clés, lissage 1, 200 it. | 0,962 / 2,63 | 0,948 / 3,34 | 3 / 9 / 15 / 18 |

Lecture :
- DQS n'améliore pas le volume ; il ne doit pas être adopté pour le bras.
- Les clés correctives réduisent les replis mais créent des arêtes étirées (frontière brutale du décalage).
- Le lissage supprime l'étirement mais dégrade les replis : aucun des deux n'est adopté. Le pipeline de référence reste sans lissage.
- Défaut connu ouvert : étirement de 5,9 à 120° pour le bras. À traiter avant toute animation.

Rapports : `docs/rapports/gonflement_avec_cles.json`, `gonflement_sans_cles.json`, `gonflement_lissage1_200it.json`, `final_lissage1_200it.json`, `final_lissage1_80it.json`.

Contrainte de gradient (kappa) sur le décalage : bras à 120° étirement 3,36 contre 5,90, mais replis 19 contre 13. Même compromis que le lissage ; option désactivée par défaut. Voir docs/erreurs_apprises.md, entrée 25. Rapports : docs/rapports/final_kappa015.json, final_kappa030.json, gonflement_kappa015.json, gonflement_kappa030.json.

Direction « vers l'os » (mode `vers_os`) testée : replis bras 11 à 90° et étirement 7,2 : pire que la référence. Non adoptée (entrée 26). Rapports : docs/rapports/final_vers_os.json, gonflement_vers_os.json.

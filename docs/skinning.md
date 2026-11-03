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

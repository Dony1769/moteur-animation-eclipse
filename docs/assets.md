# Sources et licences (style « The Chase », étape A)

Référence de style uniquement. Aucun asset, personnage ou plan de la vidéo originale n'est copié.

| Asset | Source | Licence | Usage |
|---|---|---|---|
| namaqualand_cliff_01 (LOD1) | polyhaven.com/a/namaqualand_cliff_01 | CC0 | Parois |
| rock_face_01 | polyhaven.com/a/rock_face_01 | CC0 | Parois |
| rock_face_02 | polyhaven.com/a/rock_face_02 | CC0 | Parois (non utilisé dans l'étape A) |
| sand_rocks_small_01 (LOD3) | polyhaven.com/a/sand_rocks_small_01 | CC0 | Sol, débris |
| Cartes diffuse, normal OpenGL, rugosité (1k) | Poly Haven, mêmes pages | CC0 | Matériaux PBR |
| belfast_sunset_puresky (1k EXR) | polyhaven.com/a/belfast_sunset_puresky | CC0 | Environnement |

Non utilisé : Human Base Meshes (Blender Studio) pour l'instant. blender.org et studio.blender.org sont
accessibles. mocap.cs.cmu.edu répond en HTTP (200) mais le tunnel HTTPS échoue au proxy : les clips CMU déjà
téléchargés (dépôt Shriinivas/cmubvh, README : « CMU places no restrictions ») restent disponibles
localement, mais l'étape B est arrêtée par cette limite réseau.

## Fichiers de travail hors dépôt
Les maillages et textures Poly Haven sont dans assets/ph/ (ignoré par git).

## Ajouts des étapes 6 à 8 (3 novembre 2026)
- Human Base Meshes Bundle v1.4.1 (Blender Studio, CC0) : corps stylisé « GEO-body_male_stylized » et rig Rigify. Fichier dans assets/hbm/ (ignoré par git), non redistribué.
- Mixamo : Personnage_Maria.fbx (placeholder, avec peau), Idle.fbx, Running.fbx, Sword_Slash.fbx, Hit_Reaction.fbx (sans peau). Fichiers dans assets/mixamo/ (ignoré par git), non redistribués, téléchargés depuis le compte de l'auteur.
- Clips CMU BVH (run/09_01, jump/13_11, sword/02_09) déjà présents localement, non utilisés pour l'instant (retargeting non fait).

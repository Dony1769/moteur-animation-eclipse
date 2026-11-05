# Plan d'étude : apprentissage des technologies de création humaine 3D

Source : pièce jointe 23e7bf47 (5 novembre 2026). Objectif : comprendre les architectures et les méthodes, puis améliorer
notre propre moteur. Aucune fonctionnalité ne doit dépendre d'un abonnement, de crédits ou d'une API payante.

## Statut de ce document

- Ce plan liste les projets, leur rôle dans notre moteur et l'ordre d'étude.
- Les licences de UniRig et Puppeteer sont vérifiées (section « Résultats » ci-dessous). Les autres projets ne le sont pas.
- Aucune intégration n'est déclarée fonctionnelle. Le test d'inférence local n'a pas été exécuté (voir « Limitations »).

## Résultats : UniRig (VAST-AI Research)

Sources lues : dépôt officiel `https://github.com/VAST-AI-Research/UniRig` (clone superficiel, commit 6793c66, 2026-06-04),
fiche Hugging Face `https://huggingface.co/VAST-AI/UniRig` (API, tag `license:mit`).

| Élément | Licence vérifiée | Source |
|---|---|---|
| Code racine | MIT (© 2025 VAST-AI-Research) | fichier LICENSE du dépôt |
| Poids (skeleton, skin) | MIT | tag `license:mit` de la fiche HF |
| Dataset Articulation-XL2.0 | CC-BY-4.0 | tag de la fiche HF `Seed3D/Articulation-XL2.0` |
| Code Michelangelo (`src/model/michelangelo/`) | **GPL-3.0** (fichier LICENSE local et en-tête) | licence locale, pas la licence MIT racine |
| Code Pointcept (`src/model/pointcept/`) | MIT (© 2024 Pointcept) | LICENSE local |
| Modèle OPT-350m (cité) | `license:other` | fiche HF `facebook/opt-350m` ; UniRig ne charge que la configuration (`from_config`, poids aléatoires) |

Limites de licence à retenir :
- Le code Michelangelo est GPL-3.0 dans un dépôt MIT. Le réutiliser ou le redistribuer impose la GPL-3.0 à ce code.
  Nous ne le copierons pas : on ne réimplémente que l'idée.
- Le dataset (CC-BY-4.0) contient des modèles issus d'Objaverse, dont la licence dépend de chaque objet. Les poids entraînés
  sur ces données ne sont pas « libres de tout risque » pour un usage commercial : à traiter avant toute utilisation commerciale.

Architecture lue (`src/model/unirig_skin.py`, 595 lignes, prédiction des poids) :
1. Encodeur d'os : positions des articulations, parents, latents du maillage.
2. Encodeur de maillage : PTv3 (Point Transformer v3) sur les sommets, normales et grille.
3. Attention croisée des sommets vers les os (une tête par canal) ; softmax sur les os.
4. Prior de voxels : le poids d'un enfant est propagé à son parent le long de la chaîne (`skin_mask`), puis multiplié par le
   masque en fin de prédiction.
5. Tête de poids : MLP sur les caractéristiques par paire sommet-os, softmax, puis normalisation.

Ce qui est réutilisable comme idée : le prior de voxels à propagation parent (point 4) et la lecture par paire
sommet-os. Ce qui ne l'est pas tel quel : le modèle ne fait aucune validation de pli ni d'étirement ; il prédit des poids
appris, sans garantie d'injectivité.

Dépendances matérielles (lues dans le code et `requirements.txt`) :
- `flash_attn` importé au niveau du module (`unirig_skin.py`, ligne 10) : paquet compilé pour CUDA.
- `torch.autocast(device_type='cuda')` codé en dur (lignes 370, 429 ; `src/system/ar.py` ligne 135).
- `bpy==4.2` (Blender en module Python) : roue prévue pour Python 3.11.
- Checkpoint skin : 4,4 Go (`skin/articulation-xl/model.ckpt`). Modèle d'articulations AR de 350 M de paramètres.

## Résultats : Puppeteer (ByteDance Seed)

Sources lues : dépôt officiel `https://github.com/ByteDance-Seed/Puppeteer` (clone superficiel, commit 1c9d948, 2025-09-09),
fiche Hugging Face `https://huggingface.co/Seed3D/Puppeteer` (tag `license:apache-2.0`).

| Élément | Licence vérifiée | Source |
|---|---|---|
| Code racine | Apache-2.0 | fichier LICENSE du dépôt |
| Poids (skeleton, skinning) | Apache-2.0 | tag de la fiche HF |
| Dataset Articulation-XL2.0 | CC-BY-4.0 | fiche HF |
| PartField (`skinning/third_partys/`) | **Licence NVIDIA, usage non commercial** (§ 3.3 : « non-commercially means for non-commercial research and educational purposes only ») | LICENSE du dépôt ChaoyueSong/PartField (sous-module non cloné ici) |
| Michelangelo (`skeleton/third_partys/`) | **GPL-3.0** | LICENSE du dépôt ChaoyueSong/Michelangelo |
| ptlflow, Video_Depth_Anything (`animation/third_partys/`) | Apache-2.0 | LICENSE des dépôts |
| co-tracker (`animation/third_partys/`) | **CC-BY-NC-4.0** (usage non commercial) | LICENSE du dépôt amont `facebookresearch/co-tracker` ; le dépôt ChaoyueSong renvoie 404 |

Limites de licence à retenir :
- La partie skinning dépend de PartField (licence NVIDIA non commerciale) : elle ne peut pas servir à un produit commercial.
- La partie animation dépend de co-tracker (CC-BY-NC) : même limite.
- Les poids Puppeteer sont Apache-2.0, mais leur chemin d'inférence complet passe par ces composants.

Architecture lue (`skinning/skinning_models/models.py`) :
- Bloc « SkinningBlock » : attention croisée joint-joint (avec un biais de distance dans le graphe d'articulations, appelé
  TAJA), joint-point, point-shape, point-joint.
- Tête de poids : similarité cosinus point-joint normalisée, mise à l'échelle, puis softmax sur les articulations.

Ce qui est réutilisable comme idée : le biais de distance dans le graphe d'articulations (TAJA). Il donne aux articulations
voisines plus d'influence, sans codifier la géométrie. Ce qui ne l'est pas : la tête est apprise, sans contrainte d'injectivité.

## Résultats : MPFB2 (makehumancommunity)

Sources lues : dépôt officiel `https://github.com/makehumancommunity/mpfb2` (clone superficiel, commit 6ff1eb3, 2026-10-24),
fichiers `LICENSE.md`, `LICENSE.CODE.md`, `LICENSE.ASSETS.md` à la racine du dépôt.

| Élément | Licence vérifiée | Source |
|---|---|---|
| Code source (`src/mpfb/`) | GPL-3.0 | `LICENSE.CODE.md` et `LICENSE.md` § B |
| Assets (morphes, vêtements, matériaux) | CC0 1.0 | `LICENSE.ASSETS.md` ; champs `license` par défaut à CC0 dans les propriétés de création |

Limites :
- Code GPL-3.0 : on n'en copie aucune ligne. On étudie la méthode et on réimplémente.
- Assets CC0 : utilisables, à condition de conserver la mention d'origine (CREDITS.md du dépôt).

Architecture lue (partielle) :
- `services/rigservice.py` : rig MakeHuman sur Blender, poids au format « MHW » (dictionnaire de poids par os), refit d'un
  squelette existant. Dépend de `bpy` : pas exécutable hors Blender.
- Le format MHW (poids par sommet, par os) est une référence utile pour notre format de poids.
- Pas de test local : MPFB2 est un addon Blender. Il faut Blender 4.x, non installé dans cette session.

Ce qui reste à lire dans MPFB2 : la génération de morphologie (`services/humanservice.py`, `targetservice.py`) et
la création de visage ; à relier à notre `engine/human_generator/`.

## Limitations (à lire avant toute reprise)

- **Test d'inférence local non exécuté.** Raisons mesurées : checkpoints de 1,7 à 4,4 Go ; 7 Go de RAM et 2 CPU ; 12 Go
  de disque libre ; code CUDA à patcher (flash_attn, autocast) ; bpy 4.2 requiert Python 3.11 (présent : `/usr/bin/python3.11`).
  Un test CPU exige donc un environnement dédié et des patchs dans une copie de travail, pas dans le dépôt.
- Aucun de ces modèles n'est intégré au moteur. Pour le moteur, la piste retenue reste la géométrie et les tests de déformation
  (corrections de poses), qui ne dépendent pas d'un entraînement.

## Projets et rôle dans le moteur

| Domaine | Projet | Rôle pour nous | Lien avec l'existant |
|---|---|---|---|
| Génération humaine | MPFB2 (MakeHuman pour Blender) | Référence de génération paramétrique, peaux, yeux, vêtements | `engine/human_generator/` (cibles CC0 MakeHuman déjà utilisées) |
| Génération humaine | MakeHuman Community | Cibles de morphologie, bases anatomiques | idem |
| Génération humaine | MB-Lab | Morphologie avancée, expressions ; **étudier ses limites** | — |
| Génération humaine | ManuelBastioniLAB | Historique ; ne pas en faire une dépendance | — |
| IA image vers 3D | TRELLIS.2 | Architecture O-Voxel, poids et dépendances | `docs/audits/audit_phase1_generateur_humain.md` : 24 Go de VRAM, hors de portée |
| IA image vers 3D | Hunyuan3D 2.1 | Pipeline forme et texture ; licence communautaire restrictive | étudié, idées retenues (entrée 137) |
| IA image vers 3D | TripoSR | Reconstruction rapide, licence MIT du code | à étudier (poids à vérifier) |
| IA image vers 3D | Stable Fast 3D | Textures, UV, matériaux | accès et licence des poids à vérifier |
| Modélisation | Blender | Référence d'architecture 3D, API Python | outil de référence, `bpy` non installé dans cette session |
| Traitement de maillage | Open3D | Nuages de points, géométrie, reconstruction | candidat pour la phase 4 (skinning) |
| Traitement de maillage | MeshLab | Nettoyage, réparation, normales | outil d'inspection |
| Traitement de maillage | Instant Meshes | Retopologie, edge loops | utile pour la phase 2 (topologie) |
| Rigging automatique | UniRig | Squelette et poids par vertex ; **vérifier les checkpoints réels** | phase 3 |
| Rigging automatique | ByteDance Puppeteer | Squelette, poids, prédiction ; **vérifier poids et licence** | phase 3 |
| Rigging | Rigify | Métarigs humanoïdes, IK/FK, visage | phase 5 |
| Rigging | Blender Animation Nodes | Animation procédurale | phase 6 (à évaluer) |
| Visage | MMD Tools | Expressions, shape keys, import/export | phase 5 (visage) |
| Visage | MediaPipe | Landmarks du visage (suivi) | outil d'analyse, pas de rig |
| Visage | OpenSeeFace | Suivi de visage temps réel | outil d'analyse |
| Visage | Rhubarb Lip Sync | Phonèmes et formes de bouche | déjà utilisé dans le studio animation |
| Cheveux | Blender Curves / Geometry Nodes / Hair Curves | Cheveux en courbes | phase 5 (cheveux) |
| Vêtements | OpenSew 2 | Patrons, mesures sur le corps, drapage | phase 5 (vêtements) |
| Vêtements | Blender Cloth | Simulation textile, collisions | phase 7 (mouvement secondaire) |
| Animation | MMD Tools | Systèmes d'animation de personnages | phase 6 |
| Ressources | Quaternius | Assets CC0 : humanoïdes, animations | **ressource, pas un moteur** |

## Ordre d'étude proposé

1. **Skinning et rigging (phases 3 et 4 du moteur)** : UniRig, Puppeteer, Instant Meshes, Open3D. C'est là que le blocage
   de la hanche se joue : relire comment ces projets choisissent les centres d'articulation et les poids.
2. **Génération humaine (phase 2)** : MPFB2 et MakeHuman (cibles et morphologie), puis MB-Lab pour ses limites.
3. **Visage et expressions (phase 3 et phase 5)** : MMD Tools, MediaPipe, OpenSeeFace, Rhubarb.
4. **Cheveux et vêtements (phase 5)** : Blender Curves, OpenSew 2, Blender Cloth.
5. **IA image vers 3D (phase 4 de la mission humaine)** : TripoSR, TRELLIS.2, Hunyuan3D, Stable Fast 3D. Priorité aux
   licences et aux besoins matériels (CPU, 8 Go de RAM) avant toute lecture de code.

## Méthode pour chaque projet

1. Licence du code, puis des poids, des datasets et des assets : source officielle, puis une seconde source.
2. Architecture : lire le code d'entrée et la documentation, noter les étapes du pipeline.
3. Apprendre la méthode, la reformuler, puis la réimplémenter sans copier de code ni de poids.
4. Tester avec un critère mesurable sur nos personnages (Maria, HBM).
5. Consigner dans `docs/recherches_humain.md` (journal) et `docs/erreurs_apprises.md` si un défaut apparaît.

## Ce qui n'est pas encore fait

- UniRig et Puppeteer : code et licences lus ; test local non exécuté (voir Limitations).
- MPFB2 : licence vérifiée (code GPL-3.0, assets CC0), lecture partielle du rig ; test non exécuté (Blender absent).
- Les autres projets (MB-Lab, TripoSR, Stable Fast 3D, Open3D, Instant Meshes, etc.) ne sont pas lus. Leurs licences
  ne sont pas vérifiées.
- Anomalie texturage A1 (67 faces) ouverte dans `docs/todo.md`, non bloquante.

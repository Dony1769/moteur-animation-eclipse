# Plan d'étude : apprentissage des technologies de création humaine 3D

Source : pièce jointe 23e7bf47 (5 novembre 2026). Objectif : comprendre les architectures et les méthodes, puis améliorer
notre propre moteur. Aucune fonctionnalité ne doit dépendre d'un abonnement, de crédits ou d'une API payante.

## Statut de ce document

- Ce plan liste les projets, leur rôle dans notre moteur et l'ordre d'étude.
- **Aucune licence n'est vérifiée ici.** Chaque projet doit d'abord avoir sa licence du code, des poids, des datasets
  et des assets relue sur sa source officielle, puis une seconde source avant d'être utilisé (règle de la mission).
- Aucun résultat de test n'est ajouté par ce document.

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

- Aucun projet de cette liste n'a été lu dans cette session.
- Les licences de UniRig, Puppeteer, TripoSR et Stable Fast 3D (poids) ne sont pas vérifiées.
- Le test de classification extérieure (texturage) reste en attente d'une décision de l'utilisateur.

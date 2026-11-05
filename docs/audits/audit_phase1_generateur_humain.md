# Audit phase 1 : moteur existant, contraintes matérielles, licences, plan (5 novembre 2026)

Aucun code moteur modifié. Ce document est le diagnostic demandé avant toute intégration.

## 1. État du moteur existant
- 153 fichiers Python. Modules présents : engine/skinning (95), engine/validation (14), engine/importer (4),
  engine/rigging (3), engine/generation (2, dont ara_adapter.py), tests/ (4 fichiers).
- Modules demandés par la mission et absents : human_generator, body_generator, face_generator, hair_generator,
  clothing_generator, ai_generation, image_reconstruction, material_system, facial_animation, character_export.
- Réutilisable : moteur de skinning (DQS, chaîne de nœuds coaxiaux, mesures de plis et d'étirement), importeur FBX
  (Maria, X-Bot), validation de Maria (engine/validation/test_maria.py).
- Bloquant : phase 4 (skinning de la hanche) non validée. Toute articulation dépendant du skinning reste non prouvée.

## 2. Contraintes matérielles (machine de session)
- 2 CPU, 7 Go de RAM, 12 Go d'espace libre, aucun GPU NVIDIA (nvidia-smi absent).
- Blender 4.5.15 disponible en mode headless (tools/blender-4.5.15-linux-x64).
- Conséquence : tout modèle de génération IA lourd ne peut pas tourner ici.

## 3. Licences et exigences des références demandées
| Référence | Licence (source) | Matériel | Verdict |
|---|---|---|---|
| Microsoft TRELLIS.2 | MIT, code et poids (page GitHub officielle, lue via WebFetch) | GPU NVIDIA ≥ 24 Go VRAM, CUDA 12.4 ; testé sur A100/H100 | Non exécutable ici. Nécessite un serveur GPU distant. |
| Tencent Hunyuan3D 2.1 | « Tencent Hunyuan 3D 2.1 Community License » (copie LICENSE d'un miroir, non officiel) | GPU requis | Pas une licence open source au sens OSI. Exclue dans l'UE, au Royaume-Uni et en Corée du Sud. Accord obligatoire au-delà de 1 million d'utilisateurs mensuels. Interdit d'utiliser ses sorties pour entraîner d'autres IA. |
| MakeHuman | Logiciel AGPL ; MPFB GPL ; assets de base CC0 (site officiel, static.makehumancommunity.org) | CPU | Assets de base utilisables sans attribution. Les autres packs d'assets tiers doivent être vérifiés un par un. |
| Blender / Rigify | GPL (Blender ; Rigify fait partie de Blender) | CPU | Utilisable comme outil externe ; les scripts du moteur qui l'importent restent sous GPL à vérifier avant distribution. |
| Mixamo (X-Bot, Maria) | Fichiers fournis par l'utilisateur | CPU | Usage de référence et de test uniquement, pas de redistribution. |
| Meshy | Plan gratuit refusé pour la création de tâches (erreur 402) | cloud | Bloqué tant que le plan n'est pas payé. |

Remarque : « open source » ne s'applique qu'à TRELLIS.2 (MIT) et à MakeHuman (AGPL/CC0) dans ce tableau. Hunyuan3D 2.1 ne doit pas être présenté comme open source.

## 4. Plan d'intégration proposé (ordre de la mission, adapté aux contraintes)
- Phase 2 (générateur paramétrique) : partir des assets CC0 de MakeHuman (morph targets, proportions) pour le corps de base,
  à importer et valider dans Blender. Première étape réalisable ici.
- Phase 3 (anatomie et visage) : dépend de la phase 2 ; la géométrie faciale CC0 est à vérifier asset par asset.
- Phase 4 (génération IA image/texte) : TRELLIS.2 seulement sur un GPU distant (≥ 24 Go). Décision de l'utilisateur sur le
  fournisseur et le coût. Hunyuan3D 2.1 : non recommandé pour un moteur autonome (licence non open source, exclusions).
- Phases 5 à 9 (cheveux, vêtements, auto-rigging, animation faciale, export, tests) : auto-rigging et skinning reprennent la
  phase 4 du skinning actuel (hanche non validée) ; le rigging Blender/Rigify peut servir de première voie testable.

## 5. Décisions demandées à l'utilisateur
1. Accepter MakeHuman CC0 comme base du générateur paramétrique ? (recommandé)
2. Pour TRELLIS.2 : un GPU distant est-il disponible, et un coût est-il acceptable ?
3. Hunyuan3D 2.1 : l'écarter, ou l'étudier seulement sans l'intégrer ?
4. Priorité : rester sur le skinning de la hanche, ou démarrer la phase 2 en parallèle ?

## 6. Sources
- TRELLIS.2 : https://github.com/microsoft/TRELLIS.2 (MIT, VRAM 24 Go).
- Hunyuan3D 2.1 licence : copie miroir https://gitserver.onethingai.com/ai-models/Hunyuan3D-2.1/raw/branch/main/LICENSE (non officielle ; à confirmer sur le dépôt Tencent).
- MakeHuman licences : https://static.makehumancommunity.org/about/license.html.

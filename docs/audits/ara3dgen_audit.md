# Audit d'Ara 3D Gen (olatunde85/3d-gen) : lecture statique

Date : 3 novembre 2026. Commit audité : `a4947ff` (clone en lecture seule). Aucun code du dépôt n'a été exécuté : la commande de vérification de types (`tsc`) a été refusée par le contrôle de sécurité, et les tests du dépôt n'ont donc pas été lancés.

## 1. Ce qui est établi (lecture du code)

| Domaine | Ce que fait le code | Fichier principal | Limite |
| --- | --- | --- | --- |
| Génération du corps | Macro-paramètres et sliders MakeHuman interpolés sur un treillis de cibles | `src/core/morph.ts`, `src/core/human.ts` | Données MakeHuman uniquement : pas de génération à partir d'un maillage externe |
| Morphing facial | 34 formes (20 expressions, 14 visèmes), nommage ARKit | `docs/faces.md`, `src/core/face.ts` | Mêmes données ; 9 expressions nommées |
| Squelette | « Game rig » 65 os, « lite » 25, « full » 163 ; nommage Mixamo | `src/core/rig/skeletons.ts`, `src/core/rig/rig.ts` | Squelette construit sur les articulations MakeHuman |
| Skinning | Poids MakeHuman précalculés, transférés aux vêtements et cheveux (référence de sommets ou plus proche voisin) | `src/core/rig/rig.ts` (section « Skin weights ») | Pas de calcul de poids (chaleur ou distance) sur un maillage quelconque |
| Animation | Clips keyframés plus clips retargetés depuis CMU (marche, course, saut, coups, s'asseoir) | `src/core/anim/*`, `scripts/mocap-takes.ts` | Dépend de la topologie MakeHuman |
| Export | GLB (jointures, matrices inverses, JOINTS_0/WEIGHTS_0) ; FBX binaire 7.4 écrit à la main (LimbNodes, Skin/Cluster) ; OBJ ; ZIP | `src/export/glb.ts`, `src/export/fbx.ts` | Écriture seulement |
| Import | **Aucun import FBX.** Les scripts Blender importent les exports pour vérification, sans les lire dans le moteur | `scripts/blender_*.py` | Maria (FBX externe) ne peut pas entrer dans ce moteur |
| Performance | Génération et export dans un worker ; niveaux de détail (≈5k à 120k sommets) | `src/app/worker.ts`, `docs/characters.md` | Pas de mesure CPU publiée dans le dépôt |
| Tests | `npm test` : personnages aléatoires à chaque niveau de détail, intégrité des exports ; contrôles glTF et Blender | `scripts/selftest.ts`, `scripts/gltf-check.ts` | Non exécutés ici |

## 2. Licences

- **Code** : MIT (© 2026 Josh Ola et contributeurs). Réutilisable avec la mention de licence.
- **Données de personnages** (maillage de base, cibles, squelette, poids, cheveux, vêtements) : MakeHuman, CC0 1.0. Réutilisables sans attribution.
- **Mouvements** (marche, course, saut, coups, s'asseoir, etc.) : rétro-ciblés depuis la base CMU Graphics Lab. Les conditions CMU autorisent l'usage commercial, mais **interdisent la revente directe, même sous forme convertie**. Il faut la mention « The data used in this project was obtained from mocap.cs.cmu.edu. The database was created with funding from NSF EIA-0196217. » Tout clip CMU repris dans notre moteur doit être traité avec cette réserve.

## 3. Compatibilité avec notre moteur

| Élément d'Ara | Intérêt pour nous | Incompatibilité |
| --- | --- | --- |
| Écrivain FBX binaire 7.4 (`src/export/fbx.ts`) | Module d'export réutilisable, à tester contre Blender | Une seule maille par fichier ; pas d'import |
| Nommage Mixamo des os et « WeaponR » | Compatibilité Mixamo, déjà visée dans notre étape 3 | Notre squelette est construit sur les articulations du corps HBM, pas sur celles de MakeHuman |
| Morphing facial ARKit (34 formes) | Base pour l'étape faciale (≥ 15 expressions) | Ne se transfère pas à un maillage externe sans topologie MakeHuman |
| Skinning par données précalculées | Rapide, déterministe | Ne répond pas à notre priorité (skinning automatique sur un maillage quelconque) |
| Génération de worker et niveaux de détail | Modèle d'architecture pour le CPU (étape 12) | Dans un contexte navigateur, pas Blender |

## 4. Conclusion de l'audit

Ara 3D Gen est une **référence utile pour l'export et les conventions de nommage**, pas un sous-système réutilisable pour notre moteur tel quel. Sa force (données CC0 de haute qualité, génération de personnages) ne répond pas à notre besoin principal, qui est de rigger et de skinner un maillage externe comme Maria. Son point faible pour nous est précisément ce besoin : aucun import, et un skinning qui dépend des données MakeHuman.

Décision technique proposée : ne pas intégrer le code. Étudier et réimplémenter, avec mention de licence, uniquement l'écrivain FBX et les conventions d'os, après des tests contre Blender sur notre propre HBM.

## 5. Ce qui reste à faire avant toute intégration

1. Exécuter `npm test` et `npm run typecheck` dans un environnement isolé. **Bloqué** : l'exécution a été refusée. Décision à prendre par l'utilisateur.
2. Télécharger les données CC0 (≈420 Mo) seulement si l'étape 1 est autorisée.
3. Valider l'écrivain FBX sur le corps HBM par import Blender et contrôle de déformation.

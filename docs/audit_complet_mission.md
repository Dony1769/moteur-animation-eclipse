# Audit complet du moteur (phase 1 de la mission)

Méthode : chaque ligne a été vérifiée dans le dépôt (fichier présent, test exécuté ou preuve citée). Rien n'est déclaré « fait » sans preuve. Les statuts :
- **Vérifié** : un test automatique ou une mesure reproductible existe et a été exécuté.
- **Partiel** : une partie est vérifiée, le reste ne l'est pas.
- **Lu seulement** : une méthode a été étudiée, rien n'est implémenté.
- **Absent** : rien dans le dépôt.

## 0. Constats sur le dépôt lui-même

- Les assets (FBX Mixamo, HBM, Poly Haven, mocap) ne sont **pas** dans le dépôt (`.gitignore` : `assets/`). Ils vivent dans `/home/claude/moteur3d/assets`. Le dépôt n'est donc pas reproductible seul. Action : un manifeste d'assets avec sommes SHA-256 (le dossier mixamo en contient déjà un : `SHA256SUMS.txt`), à généraliser.
- `run.sh` cité par l'ancien audit : **absent**. Ancien audit corrigé ici.
- `tests/` (3 fichiers, 17 tests) : **passent**, mais ils relisent des rapports JSON déjà produits. Ce sont des tests de non-régression sur rapports, pas sur le code. Action : les remplacer par des tests qui relancent le pipeline.
- `engine/validation/test_*.py` : tests Blender, dépendants des assets externes. Relancés cette session : `test_importer.py` (vert). Les autres ont été exécutés dans les sessions précédentes (commits cités dans APPRENTISSAGE.md) ; à relancer avant toute livraison.
- Deux arborescences coexistent : `engine/` (moteur nouveau) et `scenes/` (scènes écrites à la main, `cinema_combat.py` 425 lignes, `chase_*.py`, `combat_2maria.py`, `guerrier_pose.py`). Les paramètres de scène sont codés en dur.

## 1. Capacités demandées par la mission

### 1.1 Génération de personnages (modèles 3D texturés)
| Élément | Statut | Preuve / module |
|---|---|---|
| Génération par Ara 3D Gen (adaptateur) | Partiel | `engine/generation/ara_adapter.py` ; `engine/validation/test_ara_integration.py` (vert : 69 os sans préfixe, 169 cm, 4 influences max, poids normalisés, 10 matériaux) |
| Textures des modèles générés | Non vérifié | Les matériaux sont comptés ; les images de texture ne sont pas inspectées |
| Génération de personnages sans pipeline externe | Absent | Aucun générateur propre |

### 1.2 Import et diagnostic (phase 2)
| Élément | Statut | Preuve |
|---|---|---|
| Diagnostic à 14 points (géométrie, topologie, dimensions, matériaux, textures, UV, hiérarchie, armatures, os, groupes, poids, animations, erreurs) | Vérifié | `engine/importer/diagnostic.py` v2 ; `test_importer.py` (vert) |
| Détection d'échelle et d'axe vertical (erreur 33 et 45) | Vérifié | Variante sans armature : facteur 0,01 et axe Y proposés |
| Normalisation sur copie, source intacte | Vérifié | `engine/importer/normaliser.py` : dimensions de Maria retrouvées à 0 m ; SHA-256 de la source inchangé |
| Variantes de test (sans armature, poids partiels, sans poids) | Vérifié | `engine/importer/variantes.py` |
| Parties du corps | Partiel | Seulement par noms d'os. Sans armature : rien n'est déduit (volontaire) |
| FBX de proportions variées | Partiel | Maria, HBM, Ara. Pas de quatrième morphologie |

### 1.3 Auto-rigging (phase 3)
| Élément | Statut | Preuve |
|---|---|---|
| Armature humanoïde sur HBM : bassin, colonne, cou, tête, jambes (11 os) | Vérifié | `engine/validation/test_hbm_armature.py` (symétrie 7,8 mm ; points dans le maillage) |
| Bras, avant-bras, mains | Vérifié (HBM) | Squelette complet : `engine/validation/test_hbm_complet.py` (symétrie 0,8 mm ; milieux dans le maillage) ; coude estimé |
| Doigts | Partiel (HBM) | 4 doigts mesurés par côté (lobes distaux, courbure suivie) ; petit doigt et base du pouce estimés ; `test_hbm_doigts.py` |
| Rig Mixamo existant (préservation, contrôleurs manquants) | Partiel | Maria : 65 os, convention reconnue ; contrôleurs absents (`test_maria_controles.py`, item 7 : inventaire seulement) |
| Rigify ou méthode propre | Absent | Non choisi formellement ; à décider après recherche |

### 1.4 Auto-skinning (phase 4, priorité)
| Élément | Statut | Preuve |
|---|---|---|
| Poids LBS, normalisation, limite à 4 influences | Vérifié | `lbs_numpy.py` ; `test_ara_integration.py` ; `test_maria.py` |
| Poids par distance (lissage, symétrie) | Partiel | `engine/skinning/auto_skin.py` existe ; à réverifier |
| Optimisation de poids (arêtes par aire, garde plis + étirement) | Vérifié | `optimiser_poids.py` ; `docs/skinning_optimisation_poids.md` |
| Correctifs de poses (ARAP interpolé, formes-clés) | Vérifié sur le bras, l'avant-bras, la jambe, l'épaule répartie : 105° à 0–4 plis | Erreurs 54–63 ; commits `2b5f81d`, `94fb67e`, `ad4893f` |
| Résidu à 120° | **Ouvert** | 11 à 15 plis selon la pose (`APPRENTISSAGE.md` section 45) |
| Score de confiance par zone | Absent | — |
| Heat-based weighting | Lu seulement | — |

### 1.5 Rig avancé (phase 5)
| Élément | Statut |
|---|---|
| IK/FK, pôles coude et genou | Absent (contrôle 7 de Maria : inventaire seulement) |
| Contrôles de doigts, limites articulaires | Absent |
| Visage : 15 expressions, visèmes | Absent (contrôle 8 : 0 formes-clés, 0 os faciaux sur Maria) ; visèmes DAZ lus, non testés |

### 1.6 Animation (phase 6)
| Élément | Statut | Preuve |
|---|---|---|
| Clips Mixamo (Idle, Running, Jump, Sword_Slash, Hit_Reaction) | Vérifié | `test_maria_anim.py` ; transition Idle → Running 1,02 (seuil 3) |
| Pistes NLA avec fondu | Vérifié | erreur 36 |
| Clips procéduraux (marche, victoire) | Vérifié (mesures) | `engine/clips.py` |
| Retargeting vers un autre squelette | Partiel | Couverture 100 % des os de Maria (`test_maria_export.py`) ; pas testé sur un autre squelette |
| Bibliothèque de mouvements réutilisable | Absent | — |
| Pieds cloués au sol (foot locking), équilibre | Partiel | Pas de cloutage ; contacts mesurés dans `cinema_combat.py` (contacts_pieds, 32 pas) |

### 1.7 Mouvements secondaires et physique (phase 7)
| Élément | Statut |
|---|---|
| Cheveux, cape, accessoires (ressorts, inertie) | Absent (méthodes lues dans les sessions précédentes, rien implémenté) |
| Collisions personnage / décor | Absent |

### 1.8 Rendu anime (phase 8)
| Élément | Statut |
|---|---|
| Rendu Cycles CPU (≈ 6 s par image à 960×405) et débruitage | Vérifié (mesures de `cinema_combat.py`) |
| Rendu GPU (OptiX / CUDA) | Partiel : exécuté seulement sur Colab (T4), `notebooks/colab_render.ipynb` |
| Cel shading, contours, ombres contrôlées, matériaux anime | Absent (méthodes lues ; non implémentées) |

### 1.9 Caméras, cinématographie, décors (phase 9)
| Élément | Statut | Preuve |
|---|---|---|
| Caméras liées à des marqueurs, suivi (Track To) | Vérifié | `cinema_combat.py` (plan_suivi) ; mesures centre |
| Placement automatique de caméra selon le dialogue ou l'action | Absent | — |
| Transitions de plans, cadrage, profondeur de champ | Absent (ou codé en dur dans la scène) | — |
| Décors 3D (Poly Haven) | Partiel | Assets présents (`ph/`), grotte utilisée ; plan large non validé (falaise trop proche à ±7 m) |
| Décors dans lesquels les personnages ne traversent pas | Absent | — |
| Interaction avec le décor et les objets (épée, matériaux) | Absent | Retrait de la main et fourreau : méthode lue, non testée |

### 1.10 Effets visuels (phase 10)
| Élément | Statut |
|---|---|
| Particules, auras, fumée, feu, étincelles, traînées | Absent (méthodes lues, rien implémenté) |
| Déclenchement par événements d'animation | Absent |

### 1.11 Son (cahier des charges « sound design »)
| Élément | Statut | Preuve |
|---|---|---|
| Bruitages synthétisés (pas, sabre, impact, choc, chute) | Vérifié en timing | `engine/son.py` ; `engine/verif_son.py` (60/60 événements à 3,3 ms) |
| Qualité sonore | Non jugée | Aucune écoute |
| Ambiances, musique, mixage | Absent | — |
| Synchronisation labiale | Absent | — |

### 1.12 Profils CPU et production (phases 11 et 12)
| Élément | Statut |
|---|---|
| Profils LOW / MEDIUM / HIGH | Absent |
| Cache, réutilisation des calculs, reprise après interruption | Partiel : rendus reprenables par tranches (`cinema_combat.py`, run.sh absent) |
| Orchestration automatique d'un personnage (14 étapes) | Absent |
| Journal, validation, récupération d'erreurs | Partiel : journaux des tests seulement |
| Registre de personnages | Partiel : `engine/personnages.py` (2 entrées, pas de vérification automatique) |

### 1.13 Épisodes (sérialisation complète)
| Élément | Statut |
|---|---|
| Écriture d'un scénario en plans, dialogues, caméras | Absent (une scène écrite à la main existe) |
| Génération d'un épisode entier sans intervention | Absent |
| Rendu d'un épisode en peu de temps | Partiel : 6 s par image CPU, soit environ 1 h par minute de vidéo à 24 i/s ; à optimiser (profils, GPU optionnel) |

### 1.14 Contrôle qualité (phase 14)
| Élément | Statut |
|---|---|
| Tests automatiques par module | Partiel (voir section 0) |
| Statut « READY FOR ANIMATION » conditionné aux tests | Absent |

## 2. Architecture cible (adaptée à l'existant)

Pas de second moteur : on étend `engine/` et on déplace `scenes/` vers un format de scénario lu par le moteur.

```
engine/
  importer/        diagnostic, normalisation, variantes          (fait)
  generation/      adaptateur Ara, textures                     (partiel)
  rigging/         armature humanoïde à partir de la géométrie  (phase 3, en cours)
  skinning/        poids, correctifs, validation de déformation (phase 4)
  facial/          formes-clés, visèmes                         (phase 5)
  animation/       clips, NLA, retargeting, bibliothèque        (phase 6)
  secondary/       ressorts, cheveux, cape                      (phase 7)
  scene/           décors, collisions, caméras, cadrage         (phase 9)
  vfx/             particules paramétriques                     (phase 10)
  sound/           bruitages, ambiances, mixage, lip-sync       (son.py, verif_son.py à étendre)
  render/          profils CPU/GPU, tranches reprenables        (cinema_combat.py à extraire)
  episode/         scénario -> plans -> rendu -> assemblage     (absent)
  validation/      tests et QA                                   (existant)
  pipeline/        orchestration, journal, reprise              (absent)
```

## 3. Priorités (ordre de travail)

1. **Phase 3** : fait pour le corps HBM (squelette 47 os, doigts partiellement estimés) ; reste à généraliser la construction à partir de la géométrie à d'autres corps.
2. **Phase 4** : résidu de plis à 120°, score de confiance, poids par distance validés.
3. **Assets reproductibles** : manifeste et sommes SHA-256 (section 0).
4. **Tests qui relancent le pipeline** au lieu de relire des JSON.
5. **Phase 5 et 6** : IK/FK, visage, bibliothèque, retargeting.
6. **Épisode** : format de scénario, caméra automatique, rendu par profils.
7. **Son, VFX, décors avec collisions, interaction avec les objets.**
8. **QA « READY FOR ANIMATION »** conditionné aux tests.

## 4. Ce qui reste à vérifier avant de déclarer cet audit complet

- Relancer les tests `engine/validation/` qui dépendent des assets (le reste n'a pas été revérifié cette session).
- Inspecter les textures des modèles Ara (images, pas seulement le nombre de matériaux).
- Mesurer le temps de rendu réel sur une scène d'épisode, et non sur une image de combat.

## 5. Mise à jour (5 novembre 2026)

Relecture de la mission (pièce jointe 435d1225, 15 phases, tests A = Maria et B = FBX sans skinning). Le contenu de la section 3 ci-dessus correspond à cette mission : l'item « liste d'étapes non reçue » du plan est donc levé.

Corrections apportées à cette relecture :
- Le plan est déjà écrit (`docs/plan_mission_autonome.md`, commit 2b5f81d). L'affirmation selon laquelle l'audit et le plan n'existaient pas était fausse ; ils sont là, et cette section les met à jour.
- Environnement de cette session : Blender 4.5.15 LTS est présent (`/home/claude/moteur3d/tools/blender-4.5.15-linux-x64/blender`, démarrage headless vérifié). Il n'est pas dans le PATH, d'où une fausse conclusion d'absence (corrigée le 5 novembre). Les tests « Vérifié » qui en dépendent sont à relancer avec la variable BLENDER.
- Le test de classification extérieure/intérieure (`engine/texturing/test_surface_exterieure.py`, commit f2a4123) est relancé en arrière-plan ; son résultat n'est pas encore connu et n'est pas compté comme validé.

Ordre de travail retenu (inchangé dans le fond, précisé) :
1. Phase 4 : résidu de la jambe au genou ; critère d'acceptation à fixer avant d'élargir les poses.
2. Phase 2 : diagnostic à 14 points sur une copie normalisée, rapport par personnage (Blender requis).
3. Phase 3 : construction d'armature à partir de la géométrie pour d'autres corps que HBM.
4. Phases 5 à 15 : après les étapes précédentes, dans l'ordre du plan.

Rien de ce qui suit n'est déclaré fait par cette mise à jour : elle ne contient aucun nouveau résultat de test.

### Relances réelles (5 novembre 2026, Blender 4.5.15 LTS)
- `engine/validation/test_importer.py` : 21/21 après sélection explicite du corps (entrée 143 ; avant : 19/20, entrée 142).
- `engine/validation/test_hbm_armature.py` : RESULTAT OK (symétrie jambes 7,8 mm ; 11 os ; hiérarchie à la racine Hips ;
  milieux dans le maillage).
- `engine/validation/test_hbm_complet.py` : RESULTAT OK (47 os ; symétrie des bras 0,8 mm ; 5 doigts par côté ; 20 phalanges
  mesurées dans le maillage ; 8 phalanges estimées signalées, non testées).
- `engine/validation/test_maria.py` : RESULTAT OK après correction du test 10 (clip Running, slot affecté, mètres monde relatifs à la hanche ; entrées 144 et 145). Le test précédent était faux : il lisait une action statique de 2 images.
- Non relancés : test_maria_anim.py, test_maria_export.py, test_maria_controles.py, test_ara_integration.py (à faire ensuite).

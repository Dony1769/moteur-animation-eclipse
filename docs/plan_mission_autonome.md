# Plan priorisé : moteur autonome de production d'anime 3D

Source : mission « Autonomous Anime Production Engine » (15 phases, tests A = Maria, B = FBX sans skinning).
Priorité imposée : skinning d'abord (phase 4). État vérifié, pas déclaratif : un point n'est « fait » que s'il a été testé.

## Ordre de travail

| Ordre | Phase | État vérifié | Prochaine action |
|---|---|---|---|
| 1 | 4 Skinning | En cours. LBS + optimisation d'arêtes par aire et garde (plis + étirement). Correctifs ARAP interpolés : validés en numpy hors entraînement (bras 75° : 7 → 0 plis). | Appliquer les correctifs dans Blender et mesurer avec `mesure_lbs`. Tant que ce n'est pas fait, aucun succès n'est déclaré. |
| 2 | 4 Skinning, test B | Non commencé sur le mesh sans skinning (poids automatiques). | Poids par distance + ARAP, puis correctifs. Score de confiance par zone. |
| 3 | 2 Importeur FBX | Partiel : diagnostic avec convention Mixamo, reconnaissance des noms sans préfixe (Ara). | Analyse des 14 points de la mission ; rapport par personnage. |
| 4 | 3 Auto-rigging | Fait pour le corps HBM : squelette complet de 47 os (jambes, tronc, bras, mains, doigts). Test : `test_hbm_complet.py`. Estimé et signalé : coude, base du pouce, auriculaire, bout de main. Maria non traitée (phase 5). | Armature à partir de la géométrie pour d'autres corps (phase 2 à relancer dessus). |
| 5 | 5 Rig avancé | Non fait. Test A contrôles 7 et 8 : inventaire seulement (absents). | IK/FK, pôles, racine ; rig facial avec ≥ 15 expressions à construire. |
| 6 | 6 Animation | Partiel : transitions NLA validées (Idle→Running 1,02 ; seuil 3). | Bibliothèque, retargeting ; second jeu de clips pour valider le seuil. |
| 7 | 7 Mouvement secondaire | Non fait. | Os-ressorts déterministes (cheveux, cape). |
| 8 | 8 Rendu anime | Non fait. | Toon et contours. |
| 9 | 9 Décor et caméra | Non fait. | Génération de décor (Ara en source de personnages seulement). |
| 10 | 10 VFX | Non fait. | Systèmes paramétriques. |
| 11 | 11 Profils CPU | Partiel : usage CPU systématique, aucun profil LOW/MEDIUM/HIGH. | Trois profils de qualité. |
| 12 | 12 Orchestration | Non fait. | Reprise sur étape validée, journal. |
| 13 | 13 Tests A et B | A : items 1–6, 9–12 validés ; 7, 8 absents. B : items 1–5 validés, 6 partiel. | Compléter B (6–15). |
| 14 | 14 Assurance qualité | Partiel (tests par module). | Rapport unique « READY FOR ANIMATION » conditionné aux tests. |
| 15 | 15 Architecture | Partiel. | Ranger en modules indépendants sans second moteur. |

## Règles appliquées
- Un défaut devient une erreur documentée (`docs/erreurs_apprises.md`) et une leçon (`engine/APPRENTISSAGE.md`).
- Recherche officielle d'abord, puis non officielle, en chaînant plusieurs sources ; une source non officielle n'est retenue qu'après test.
- Pas de succès déclaré sans mesure ; une métrique numpy n'est retenue qu'après calibration Blender.
- Commit par étape validée, avec attribution.

## Limites actuelles
- Pourcentage d'avancement : qualitatif. Les phases 4 et 13 sont les plus avancées ; les phases 5 à 12 n'ont pas commencé.
- Liste d'étapes « ultra-autonome » de l'utilisateur : non reçue. À réaligner dès réception.

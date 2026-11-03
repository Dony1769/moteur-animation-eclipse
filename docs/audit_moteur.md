# Audit du moteur (3 novembre 2026)

Méthode : inventaire réel du dépôt (fichiers, lignes, commits, registre), sans supposer qu'une fonction existe. Chaque ligne ci-dessous dit ce qui est testé, ce qui est partiel, ce qui manque.

## 1. Ce qui existe et a été testé

| Capacité | Module | État |
|---|---|---|
| Import FBX Mixamo (Maria, armature `mixamorig:*`) | scenes/cinema_combat.py (charger) | Testé : rendu du combat |
| Nettoyage du FBX (retrait du cube, retrait du déplacement Hips X/Z) | cinema_combat.py (retirer_cubes) | Testé |
| Clips procéduraux (marche, victoire) sur le squelette Mixamo | engine/clips.py | Testé (mesures, images) |
| Pistes NLA (animations Mixamo réutilisées avec décalage) | cinema_combat.py (planifier, ajouter) | Testé |
| Caméras liées à des marqueurs, suivi par Track To | cinema_combat.py (plan_suivi) | Testé (centre mesuré) |
| Mesure dans le monde (sommets évalués, z minimal, projection image) | engine/mesure.py | Testé |
| Sons synthétisés (pas, sabre, impact, chute) calés sur les images | engine/son.py | Testé en timing (60/60 à 3,3 ms) ; qualité sonore non jugée à l'oreille |
| Vérification du son par rapport aux événements | engine/verif_son.py | Testé |
| Pas calés sur le contact réel des pieds | cinema_combat.py (contacts_pieds) | Testé (32 pas, mesurés) |
| Rendu Cycles CPU, débruitage OIDN, motion blur | cinema_combat.py, run.sh | Testé : environ 6 s par image à 960×405 |
| Rendu GPU (OptiX, CUDA) | cinema_combat.py, notebooks/colab_render.ipynb | Prévu ; exécuté seulement sur Colab (T4) |

## 2. Partiel ou non validé

| Capacité | État |
|---|---|
| Registre de personnages | engine/personnages.py : deux entrées (Maria contrôlée, guerrier de test). Pas de vérification automatique. |
| Cadrage de la grotte | Plan large non validé (falaise trop proche de la caméra à ±7 m). |
| Combat réaliste | Animations Mixamo lentes, pas de réaction de coup couplée. |
| Épée | Retrait de la main et fourreau : méthode lue (os « hand hold », socket) non testée. |
| Rig facial | Visèmes DAZ lus, non testés dans Blender. |
| Cheveux, cape, tissu | Méthodes lues (cartes, Cloth Houdini), valeurs Blender non lues ; rien d'implémenté. |
| VFX magiques | Méthodes lues (Niagara, fumée), rien d'implémenté dans Blender. |

## 3. Ce qui n'existe pas (exigé par la mission)

- Importeur universel FBX avec diagnostic par personnage (aucune analyse automatique).
- Auto-rigging (armature générée à partir de la géométrie) : rien.
- Auto-skinning (poids par distance, heat, normalisation, lissage, limite d'influences, validation de déformation) : rien.
- Rig avancé : IK/FK, pôles, limites, contrôles de doigts : rien.
- Bibliothèque de mouvements réutilisable et retargeting sur un squelette différent : rien.
- Mouvements secondaires : rien (ni cheveux, ni ressorts, ni cape).
- Système VFX paramétrique : rien.
- Profils LOW / MEDIUM / HIGH CPU : rien.
- Pipeline d'orchestration, journal, reprise après interruption : rien (les rendus sont reprenables par tranches, mais c'est un script).
- Contrôle qualité automatique (READY FOR ANIMATION) : rien.
- Export d'un personnage et de ses animations : rien au format du moteur.

## 4. Dette technique repérée

- Le seul pipeline complet est une scène de combat écrite à la main (425 lignes). Les paramètres (positions, durées, caméras) sont codés en dur.
- Les modules `engine/` ne sont pas testés automatiquement : les vérifications sont des scripts ponctuels.
- Les fichiers `scenes/chase_*.py` et `combat_2maria.py` sont des versions antérieures non maintenues.
- Le second personnage FBX « sans skinning » demandé par la mission n'est pas dans `assets/`. Le seul candidat présent est un maillage Human Base Meshes (`assets/hbm`) : à confirmer avec toi avant de le tenir pour le test B.

## 5. Plan priorisé (étapes validées une à une)

1. **Importeur FBX et diagnostic** (engine/importer) : analyser un FBX et produire un rapport JSON (géométrie, UV, matériaux, armature, poids, animations). Test : Maria et le maillage HBM.
2. **Registre validé** : un personnage n'entre dans le registre qu'après des tests automatiques (import, hiérarchie, poids normalisés, déformation).
3. **Auto-skinning** (poids par distance et proximité d'os, normalisation, limite à 4 influences, validation par pliage des articulations).
4. **Auto-rigging humanoïde** pour le maillage sans armature (armature à partir de la géométrie, puis IK/FK).
5. **Bibliothèque de mouvements et retargeting** (marche, course, pose ; transfert vers un autre squelette).
6. **Expressions faciales** (formes-clés déduites de la géométrie, 15 expressions, combinaison).
7. **Mouvements secondaires légers** (ressorts sur cheveux, cape, accessoires), profils CPU LOW / MEDIUM / HIGH.
8. **VFX paramétrique** et **scène** (environnement, caméra, lumière), puis **rendu** et **export**.

Chaque étape : code, test automatique, rapport, commit. Une étape non testée n'est pas marquée comme faite.

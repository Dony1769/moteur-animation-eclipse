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
- Le second personnage FBX « sans skinning » demandé par la mission n'est pas dans `assets/`. Le fichier Human Base Meshes (`assets/hbm`) a été diagnostiqué : c'est une bibliothèque de 382 pièces séparées (yeux, pieds, bras, variantes), sans armature et sans personnage complet. Il ne peut donc pas servir de test B tel quel. Il faut un FBX de personnage complet, ou assembler les pièces, ce qui est une étape à part.

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

## 6. Résultats de l'étape 1 (importeur et diagnostic)

- `engine/importer/diagnostic.py` : lit un FBX ou un .blend, produit un rapport JSON, sans modifier la source.
- Maria (`docs/rapports/maria.json`) : type `armature_et_poids`, hauteur 1,75 m, 65 os Mixamo (convention reconnue), 8 094 sommets, 4 influences au maximum par sommet, poids normalisés, 0 anomalie. L'épée est un maillage séparé (`Maria_sword`, 42 sommets, 1 groupe), utile pour le retrait de la main.
- HBM (`assets/hbm`) : type `sans_armature`, 382 pièces, 7 signalements (n-gones sur des pièces de visage et de pied). Pas un personnage complet.
- Limite : le diagnostic lit seulement ; aucune correction n'est faite. Le test sur un FBX de personnage complet sans skinning reste à fournir.

## 7. Test B : source trouvée, libre, sans skinning

- Le bundle HBM contient des corps complets sans armature : `GEO-body_male_realistic` et `GEO-body_female_realistic` (10 582 sommets, presque tout en quads, UV `UVMap`, pas de matériau, pas de groupes de sommets), ainsi que les variantes stylisées (12 502 sommets).
- Il est déjà présent dans `assets/hbm` ; rapport complet dans `docs/rapports/hbm_bundle.json`.
- Plan pour le test B : isoler `GEO-body_male_realistic` (sans les yeux ni les pièces séparées), lui assigner un matériau neutre, puis appliquer les étapes 2 à 8 de la mission (registre, auto-skinning, auto-rig).
- Licence : Human Base Meshes est distribué par Blender Studio ; à vérifier dans le README officiel avant publication. Pour l'apprentissage, aucune limite.

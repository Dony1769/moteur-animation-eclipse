# À faire et bloqué (mis à jour le 2 novembre 2026)

## Réseau
- blender.org : accessible (HTTPS 200).
- mocap.cs.cmu.edu : tunnel HTTPS en échec depuis le proxy, mais les clips utiles sont déjà sur la machine
  (run/09_01, jump/13_11, sword/02_09 et l'archive cmubvh). L'étape 6 n'est donc plus bloquée par le réseau.

## Dépend de l'utilisateur
- Fichiers Mixamo (Default Character FBX avec peau, puis Idle, Running, Jump, Sword Slash, Hit Reaction sans
  peau) : aucun fichier FBX dans /mnt/user-data/uploads/ (seulement deux images de contrôle). Étape 5 non
  faite. À déposer dans la conversation si l'utilisateur veut un placeholder.
- Notebook Kaggle (étape 3) : à lancer par l'utilisateur depuis son compte, avec Internet activé.

## Bloqué par une dépendance ci-dessus
- Étape 5 (placeholder Mixamo) : fichiers absents.
- Étape 6 (guerrier) : pose de course correcte à l'œil à obtenir (images-clés en code).
- Étapes 7 à 9 : dépendent des étapes 5 et 6.

## Notebook Kaggle (étape 3)
- Le téléchargement des assets Poly Haven est maintenant écrit dans le notebook (à vérifier au premier lancement). Précédemment, le notebook n'était pas prêt à tourner : la cellule de téléchargement des textures et maillages
  Poly Haven est une étape à compléter. Sans elle, le rendu échoue dès le premier réglage.
- Le script accepte le GPU (variables DEVICE et BACKEND), mais le profil gpu-kaggle n'est pas mesuré : il
  faut que l'utilisateur lance le notebook avec GPU et Internet activés, puis colle les lignes de résultats.

## Blocage Kaggle (utilisateur)
- Le GPU et l'accès Internet de Kaggle exigent une vérification par téléphone. L'utilisateur ne reçoit pas le
  SMS : ni GPU ni Internet dans le notebook. Sans Internet, le téléchargement de Blender et des assets échoue.
- Le notebook ne plante plus sans GPU : il bascule en CPU. Le profil gpu-kaggle reste non mesuré.
- Solution de repli proposée : Google Colab (GPU T4), à adapter si l'utilisateur accepte.

## Étape 5 (placeholder Mixamo) : état au 2 novembre 2026, 22 h 50
- Fichiers reçus et vérifiés : six FBX binaires (personnage à 65 os, animations Idle, Running, Jump, Sword
  Slash, Hit Reaction à 24 images/s). Empreintes dans assets/mixamo/SHA256SUMS.txt (dossier ignoré par git).
- Animation appliquée au personnage : il faut assigner le « slot » de l'action (Blender 4.5). Corrigé.
- Pose de course : l'animation évolue d'une image à l'autre, mais l'image frame 8 ne se lit pas comme une
  course (bras écartés, jambes presque droites). Non validée.
- MP4 4 s : non fait. À 640×270, le personnage fait passer le rendu à environ 40 s par image, soit plus de 60
  min pour 96 images : au-dessus de la limite de 20 min par test. À réduire avant le MP4.
- Repli Google Colab : notebooks/colab_render.ipynb, écrit, non testé (à lancer par l'utilisateur).

## Étape 5 (placeholder Mixamo) : mise à jour du 2 novembre 2026, 23 h 20
- Corrigé : mode de rotation QUATERNION (l'action Mixamo est en quaternions) ; translation horizontale du bassin
  retirée (course sur place) ; hauteur mesurée en monde (2,24 m avant, 1,75 m après) ; personnage tourné pour
  courir vers +Y. Action assignée par son slot.
- Mesuré : 640×270, 4 échantillons, 4,4 s par image (contre ~40 s à 1280×540 et 16 échantillons).
- MP4 de 4 s produit : 96 images, 24 images/s. Vue de dos uniquement ; profil non validé.
- Notebook Colab (repli) : valide syntaxiquement, mais il lance scenes/chase_a.py (décor seul), pas la scène Mixamo.

## Colab GPU (2 novembre 2026, 23 h 55)
- Kaggle est retiré : seul Colab est utilisé.
- Les scènes choisissent OptiX, puis CUDA, et n'activent que les GPU ; sans GPU, le rendu reste en CPU et le
  notebook affiche le périphérique réellement utilisé (ligne RENDU).
- À faire par l'utilisateur : lancer notebooks/colab_render.ipynb avec Exécution → Modifier le type d'exécution →
  GPU T4, puis coller les lignes de résultats. Le profil gpu-colab sera ajouté à docs/budget.md à partir de ces lignes.
- Non testé sur GPU réel ici : le chemin GPU n'a été exécuté que sans GPU (repli CPU vérifié).

## Étape 6 (guerrier) : état au 3 novembre 2026, 00 h 45 — NON VALIDÉE
- Base : Human Base Meshes v1.4.1 (Blender Studio, CC0), corps masculin stylisé (GEO-body_male_stylized, 1,80 m).
  Téléchargé depuis le miroir officiel ; fichiers dans assets/ (ignoré par git), jamais versionnés.
- Rig Rigify généré (706 os), poids automatiques posés, FK des membres actif (IK_FK = 0).
- Retargeting du clip CMU run/09_01 sur les contrôles FK : ÉCHEC. Les jambes ne tournent que de 9° à l'image 9
  (le clip en demande 30 à 40°), le buste se penche de 22°. Planche de profil refusée.
- Cause probable : le delta de rotation monde n'est pas correctement composé avec le repos des contrôles Rigify.
  À reprendre avec un contrôle image par image (angles par os) avant tout nouveau rendu.
- Pas d'épée, pas de cape, pas de visage rigé à ce stade.

## Étapes 7 à 9 : non commencées (dépendent de l'étape 6 ou du placeholder).

## Étapes 6 à 9 : état du 3 novembre 2026, 01 h 15
- Étape 6 (guerrier, Human Base Meshes, rig Rigify) : pose de course de test (images-clés sur les os de déformation,
  scenes/guerrier_pose.py). Pas validée : artefacts aux genoux et aux coudes, retargeting CMU non fait.
- Étape 7 (combat 6 s) : fait avec le placeholder Maria. Poussière et débris non faits.
- Étape 8 (20 s, trois plans) : fait, 480 images, MP4 20,00 s, placeholder.
- Étape 9 (estimation d'un épisode) : rien ne tient sur CPU ni sur Colab avec les mesures actuelles. À faire par l'utilisateur :
  un rendu de 96 images en un seul processus sur T4, pour une mesure GPU propre.

# À faire et bloqué (mis à jour le 2 novembre 2026)

## Réseau
- blender.org : accessible (HTTPS 200).
- mocap.cs.cmu.edu : HTTP 200, mais le tunnel HTTPS échoue au proxy. Conséquence : étape 6 utilise des
  images-clés en code sur le squelette Rigify, pas de capture CMU, tant que le domaine n'est pas accessible.

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

# Mémoire du moteur : ce qu'il faut toujours faire (combat, chute, victoire, son)

Chaque règle vient d'une lecture ou d'un test. Une règle non testée est marquée « à vérifier ».

## 1. Son calé sur les images
- Image Blender n (1 au début) = instant (n − 1) / 24 s dans le fichier son.
- Erreur courante : prendre n / 24 décale tout de 42 ms. Corrigé dans `engine/son.py` (piste à partir de n − 1).
- Les bruitages sont posés sur l'image exacte de l'impact (`evenements.json`), jamais à l'oreille.
- À vérifier par écoute ou par spectrogramme : le son arrive sur le contact visuel.

## 2. Chute au sol
- Ne jamais faire tomber un personnage en pivotant seulement autour des pieds : le corps s'enfonce dans le sol.
- Méthode : pendant la chute, calculer à chaque image la hauteur la plus basse du maillage (après déformation) et régler la position verticale pour que ce point soit exactement à z = 0.
- Vérifier : la hauteur minimale du maillage pendant la chute reste ≥ 0 (contrôle automatique à faire dans le script).

## 3. Pose de victoire
- Une pose se valide seulement par une image rendue en gros plan, lue à l'œil : bras levé, épée visible, tête droite.
- Test rapide : rendre une seule image à la fin du combat à petite résolution, puis regarder.

## 4. Arrêt sur impact (principe d'animation, article « Animating Sword Combat », sword-cartoon.pages.dev)
- Au contact, ralentir le mouvement puis le réaccélérer à la sortie.
- Une pose tenue 2 à 4 images après un coup fort renforce le choc. À faire par répétition de l'image d'impact dans la piste (à vérifier).
- Réaction immédiate de la cible, avec une intensité adaptée (le coup du gagnant est plus lourd).

## 5. Lisibilité des personnages
- Une teinte multipliée trop sombre rend un personnage invisible sur une roche sombre : garder une teinte claire (valeurs autour de 0,6 à 0,8 par canal).
- Vérifier chaque personnage sur au moins une image où il est seul au centre du cadre.

## 6. Rendu et contrôle
- Tests : tranches de moins de 20 minutes de calcul, images de contrôle regardées une par une.
- Ne jamais écrire « validé » sans avoir regardé l'image ou écouté le son.
- Le rendu complet ne se lance qu'après ces contrôles.

## Sources
- Blender 4.5, documentation de l'API Action (slots et canaux) : https://docs.blender.org/api/4.5/bpy.types.Action.html
- « Animating Sword Combat & Action Sequences with Real Weight and Impact » : https://sword-cartoon.pages.dev/posts/animating-sword-combat-action-sequences
- Blender Audio Sequences (wiki 2015) : https://archive.blender.org/wiki/2015/index.php/Manual/Audio_Sequences

## État au moment de cette mise à jour (à lire avant de reprendre)
- Son : décalage d'une image corrigé dans engine/son.py. Non écouté.
- Victoire : bras de A levé (rotation de 2,4 rad autour de X), vérifié par lecture des quaternions. Lisibilité à l'image non confirmée.
- Chute de B : BUG OUVERT. La hauteur au sol calculée donne −1,73 m, la position finale reste à z = 1,73. Ne pas lancer le rendu avant correction. Piste : vérifier les bornes du maillage évalué (ce qui inclut peut-être l'épée ou un os mal orienté), ou faire la chute par rotation simple sans compensation puis contrôler à l'œil.
- Teinte de B : éclaircie (0,62 ; 0,8 ; 1,0). Non vérifiée à l'image.
- Cadrage : plan de victoire passé en plan large.

## 7. Mesure des positions (quel que soit l'angle de la caméra)
- Sources lues : discussions Blender sur depsgraph et données évaluées (developer.blender.org, blenderartists) et documentation bpy_extras (world_to_camera_view).
- Règle 1 : `obj.bound_box` d'un objet déformé par une armature peut être périmé. Mesurer les sommets évalués : `obj.evaluated_get(depsgraph).to_mesh()`, puis transformer chaque sommet par la matrice monde (module `engine/mesure.py`, fonction `sommets_monde`).
- Règle 2 : la hauteur au sol d'un personnage est le minimum des z de tous ses sommets évalués. Une chute est correcte si ce minimum vaut 0 (à 1 mm près).
- Règle 3 : pour vérifier une position à l'image, projeter le point avec `world_to_camera_view` : x et y entre 0 et 1 = dans le cadre, distance positive = devant la caméra. Ceci marche pour tout angle de caméra.
- Règle 4 : toujours mesurer avant de rendre. Une valeur mesurée se consigne dans le journal de test.

## 8. Plans dédiés : caméra qui vise un point mesuré
- Sources lues : discussions Blender sur la contrainte « Track To » (blenderartists, archive.blender.org).
- Méthode : mesurer le centre du personnage (`mesure.sommets_monde`, moyenne des min et max), créer un point cible (empty) à cet endroit, placer la caméra à distance fixe devant le sujet, et ajouter une contrainte Track To vers la cible (axe −Z, haut Y).
- Contrôle obligatoire : `mesure.position_image` doit donner x et y entre 0,1 et 0,9 pour le centre du sujet. Si le sujet sort du cadre, reculer la caméra ou changer la focale.
- Le plan est lié à un marqueur de timeline (voir plus haut), donc il se déclenche à l'image voulue.

## 9. Vérifier le son sans l'écouter
- Méthode : mixer le WAV, calculer son enveloppe d'énergie par tranches de 10 ms, et repérer les débuts de bruitage (montées nettes).
- Comparer chaque début mesuré à l'instant attendu (image − 1) / 24 s. Tolérance : 15 ms. Un écart au-delà = erreur à corriger.
- Contrôle visuel complémentaire : spectrogramme en image (ffmpeg, filtre showspectrumpic), à regarder avec l'outil de lecture d'images.
- Ce contrôle prouve le calage, pas la qualité du bruit. La qualité reste à juger à l'oreille par l'utilisateur.

## 10. Valider une pose
- Une pose se valide seulement par une image rendue en plan rapproché, avec le sujet centré (règle 8) et le bras ou l'épée visibles.
- Si le sujet n'est pas lisible, ne pas écrire « validé ».

## État vérifié (dernière mise à jour)
- Chute de B : corps couché visible sur le sol, plan dédié à 1245 (contrôle image). Mesure : point le plus bas à 0 m.
- Victoire de A : profil, épée levée au-dessus de la tête, plan dédié à 1290 (contrôle image). Lisibilité confirmée à 640×270.
- Son : 60 événements contrôlés par mesure (engine/verif_son.py) : écart de 3,3 ms au plus, constant (fenêtre de mesure). Calage numériquement validé. La qualité sonore n'est PAS validée : à juger à l'oreille.

## 11. Créer des personnages et des objets (état honnête)

Sources lues :
- Poly Haven (polyhaven.com) : textures PBR photoscannées et modèles, licence CC0 sans restriction, résolution 8k, téléchargement direct sans inscription. Confirmé par la page.
- Documentation Blender Rigify (docs.blender.org, Basic Usage) : la page récupérée ne contenait que la navigation, donc la procédure exacte n'est pas confirmée. À vérifier par test dans Blender.
- Recherches sur la création de personnages dans Blender (shape keys, MakeHuman, Manuel Bastioni Lab, UniHuman) : pistes seulement. MakeHuman et Bastioni Lab ont des licences à vérifier avant usage (MB-Lab est AGPL et reste interdit par la règle du projet).

Ce que le moteur sait faire déjà (testé) :
- Modifier un personnage existant : taille, teinte, texture (Maria : teinte bleue, éclaircie à 0,62 / 0,8 / 1,0).
- Réutiliser le squelette Rigify du corps Human Base Meshes (CC0), avec ses contrôles FK, dans guerrier_rig.blend.
- Produire des clips procéduraux sur le squelette (marche, victoire).
- Exporter un FBX depuis Blender (à faire et tester).

Ce qui n'est PAS encore fait ni testé :
- Créer un personnage entièrement nouveau et réaliste à partir de rien.
- Appliquer Rigify à un maillage qui n'est pas Human Base Meshes (procédure à apprendre par test : métarig, ajustement, génération, poids automatiques, vérification de la déformation sur plusieurs poses).
- Peau et textures réalistes sur un nouveau visage : texture CC0 à choisir et contrôler à l'image.

Règle de travail :
- Pour un épisode, le script demande un personnage par son nom (dans le registre `engine/personnages.py`), avec ses variantes. Un personnage absent du registre n'est pas inventé à la volée : il est créé et contrôlé d'abord, puis ajouté au registre.
- Tout personnage nouveau passe par : mesure (hauteur, z minimal), contrôle d'image sous deux angles, contrôle de la déformation sur trois poses, puis seulement l'usage dans un épisode.

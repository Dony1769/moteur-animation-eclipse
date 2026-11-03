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

# Donner du volume à un dessin 2D (méthode 2.5D)

Un dessin 2D n'a pas de profondeur réelle. Le volume se fabrique avec la lumière, pas avec la 3D.
Le moteur applique les mêmes règles que les dessinateurs de séries.

## 1. Penser en formes, pas en contours

Chaque élément est un volume simple : la tête est une sphère, le bras un cylindre, la cape un tissu qui tombe.
Avant de colorier, on se demande : « quelle forme cette partie a-t-elle, et où est son centre ? ».
Dans le moteur : la couche d'un membre est un volume gonflé à partir de sa silhouette (voir section 4).

## 2. Trois valeurs au minimum

- **Lumière** : la zone frappée directement.
- **Ombre propre** : la zone qui tourne loin de la lumière, avec une ligne nette (le « terminateur »).
- **Ombre portée** : l'ombre qu'un élément jette sur un autre (la cape sur la tunique).

Les séries utilisent souvent deux tons seulement (cel shading) : une couleur claire et une couleur d'ombre, bords nets.
Le moteur fait exactement cela : 1.0 côté lumière, 0.60 côté ombre.

## 3. Une seule lumière, partout

Choisir une direction (ici haut-gauche, légèrement devant) et la garder pour tout le personnage et le décor.
Une ombre qui n'est pas du bon côté casse immédiatement le volume.

## 4. La méthode de gonflement (ce que fait le moteur)

1. On prend la silhouette d'une couche (la tunique, un bras, la tête).
2. On calcule, pour chaque pixel, sa distance au bord. Plus on est loin du bord, plus la forme est « haute ».
3. On lisse cette hauteur, puis on en déduit une direction de surface en chaque point.
4. On compare cette direction à la lumière : face à la lumière = clair, de biais = ombre.
5. On quantifie en deux tons.

Résultat : une silhouette plate devient une forme qui a l'air arrondie, sans rien modeler à la main.
Limite : ça ne sait pas que la cape est devant ou derrière le bras ; c'est l'ombre portée qui le dit.

## 5. Ombre portée

Décaler la silhouette de l'élément qui projette, le flouter légèrement, et l'appliquer sur ce qui est dessous.
Dans le moteur : la cape projette vers le bas-droit ; la surface reçue est assombrie de 30 %.
Attention : une couche qui contient aussi le corps ne doit pas projeter sur lui-même (on retire le corps avant).

## 6. Lumière de bord (contre-jour)

Un liseré clair sur le bord opposé à la lumière détache le personnage du fond.
À ajouter : le moteur ne le fait pas encore.

## 7. Occlusion ambiante

Les zones où deux formes se rejoignent sont plus sombres : aisselle, entre les jambes, sous la ceinture, sous le col.
À ajouter : petites taches sombres aux articulations, qui suivent la chaîne d'os.

## 8. Plis et tensions

Les plis partent des points de tension : épaule, coude, genou, ceinture, hanche.
Un tissu qui tombe fait des plis verticaux ; un tissu qui tire fait des plis en éventail depuis le point de tension.
Le moteur déforme déjà les tissus avec les os : les plis bougent avec la pose.

## 9. Perspective et raccourci

En trois quarts, la jambe proche est plus grande que la lointaine ; la tête est tournée, les yeux se décalent.
C'est pour cela qu'il faut des vues séparées (face, trois quarts, profil) au lieu d'une seule image tournée.

## 10. Ordre de profondeur et chevauchement

Dessiner les éléments dans l'ordre de profondeur : cape arrière, jambes, tunique, bras, tête, col avant.
Chaque couche doit déborder légèrement sur sa voisine pour qu'aucun trou blanc n'apparaisse en mouvement (le moteur dilate chaque couche de 1 px).

## 11. Traits et couleurs

- Trait plus épais côté ombre, plus fin côté lumière et sur les plis.
- Ombres un peu plus froides et saturées, lumière plus chaude.

## 12. Cheveux

Les mèches vont par groupes. Chaque groupe a une bande de reflet et une ombre sous la frange.
À ajouter : découper les cheveux en groupes séparés, qui bougent un peu en retard sur la tête.

## Ce que le moteur fait déjà
- Chaînes d'os : bassin -> cou pour le tronc, épaule -> coude -> poignet -> doigt pour les bras, hanche -> genou -> cheville -> orteil pour les jambes.
- Volume par gonflement et deux tons (sections 2 et 4).
- Ombre portée de la cape sur le corps (section 5).
- Jambes et bottes dans une seule couche : plus de décollement.

## À faire ensuite
1. Lumière de bord (section 6).
2. Occlusion aux articulations (section 7).
3. Cheveux en mèches (section 12).
4. Plis ajoutés comme couches courtes sur la cape et la tunique.

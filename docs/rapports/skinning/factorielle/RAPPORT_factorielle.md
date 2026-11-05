# Isolation des facteurs : géométrie, poids, triangulation (hanche masculine)

Script : `engine/validation/skinning/investigation_morphologie_descriptive.py` (descriptif natif) et
`engine/validation/skinning/investigation_factorielle.py` (plan 2 × 2 × 2 synthétique).
Données : `descriptif_morphologies.json`, `plan_factoriel.json` (ce dossier).
Statut : **diagnostic**. Aucune méthode n'est validée ni intégrée. LBS, DQS et Bone Heat restent la référence.

## 1. Comparaison native des maillages (sans correspondance)

Les deux maillages ont la même connectivité (N = 10 582, 10 570 quads, 20 triangles) mais un ordre de sommets
différent (`b_boucle`). Leur plus proche voisin est une mauvaise correspondance : médiane 2,0 cm (masculin → féminin),
non injective (4 215 cibles uniques pour 10 582 sommets masculins ; 3 960 dans l'autre sens). Aucune correspondance n'est donc utilisée ici.

| Mesure (région R = mixte + anneau) | Masculin | Féminin |
|---|---|---|
| Sommets de R / sommets à deux influences | 317 / 221 | 252 / 171 |
| Arêtes mixtes | 393 | 300 |
| Arête médiane | 3,04 cm | 2,85 cm |
| Courbure médiane (1 − cos, R) | 0,0495 | 0,0382 |
| Histogramme poids G des mixtes (10 classes) | [81,26,11,9,7,8,6,10,15,48] | [67,30,13,10,6,6,6,9,14,10] |
| Centroïde des mixtes (x, y, z) | (−2,265 ; −0,007 ; 0,779) | (−2,264 ; 0,012 ; 0,839) |
| Gradient de poids médian sur arêtes mixtes | 1,15 /m | 1,54 /m |

Lecture : le masculin a plus de sommets mixtes, plus d'arêtes mixtes, une courbure plus forte et une
masse de poids très proches de 1 (48 sommets dans la dernière classe, contre 10 chez le féminin). Son centroïde mixte
est plus bas. Le gradient médian est en revanche plus faible chez l'homme : un gradient plus fort ne peut donc pas
expliquer seul la régression.

## 2. Plan factoriel synthétique

Grille carrée 0,6 m, rotation de 120° de l'os G autour de y, λ = 0,1, moyenne arithmétique (configuration actuelle).
Facteurs :

- **G (géométrie)** : pas de grille 0,0300 m (21 × 21 points) ou 0,0285 m (22 × 22). Attention : ce facteur change
  aussi la densité, il ne sépare donc pas « forme » et « pas ».
- **W (poids)** : histogramme natif masculin ou féminin, appliqué par quantiles sur la bande |x| ≤ 0,10 m, triée selon x.
  Ce n'est pas une reproduction des champs de poids réels.
- **T (triangulation)** : diagonales parallèles (A) ou alternées (B), mêmes sommets.

Mesures sur les arêtes, LBS et SQ (max = étirement maximal, p99, max dans la bande).

Résultats de cellules (extrait) :

| Cellule | LBS max | SQ max | SQ p99 | Retournements |
|---|---|---|---|---|
| GM WM TA | 1,392 | 1,114 | 1,079 | 0 |
| GM WF TA | 2,054 | 1,221 | 1,157 | 0 |
| GF WM TA | 1,637 | 1,129 | 1,085 | 0 |
| GF WF TB | 1,970 | 1,271 | 1,192 | 0 |

Effets principaux (F − M) sur SQ max : géométrie +0,023 ; poids +0,121 ; triangulation +0,014.
Sur SQ − LBS (max) : géométrie −0,058 ; poids −0,376 ; triangulation +0,014 ; interaction géométrie × poids +0,170.

## 3. Réponses aux six questions

1. **La géométrie masculine explique-t-elle la régression ?** Non, pas dans ce plan. L'effet géométrique est faible
   (≤ 0,04 sur l'étirement) et disparaît sur SQ − LBS. Limite : le facteur géométrie n'est qu'une densité.
2. **La distribution des poids explique-t-elle la régression ?** Elle domine les écarts de valeurs absolues, mais
   la direction n'est pas celle observée : SQ améliore toujours LBS dans les huit cellules.
3. **La triangulation influence-t-elle le résultat ?** Peu (effet ≤ 0,02 sur le maximum, 0,005 sur p99).
4. **Y a-t-il des interactions ?** Une interaction géométrie × poids apparaît sur SQ − LBS (+0,17). Elle vient
   surtout de la non-linéarité de LBS (le maximum LBS varie fortement avec les poids), et elle n'est pas interprétée
   causalement ici.
5. **Rôle exact de G** : traité dans une étape séparée (non réalisée dans ce rapport, voir §4).
6. **Propriétés d'une future formulation** : voir §4.

Conclusion critique : **le plan synthétique ne reproduit pas la régression masculine.** Dans toutes les cellules,
SQ réduit l'étirement maximal par rapport à LBS et ne crée aucun retournement. La régression réelle (2 à 15 poses
sur 29 selon λ, voir `intermediaire_hanche_masc`) dépend donc de facteurs que ce plan ne contient pas : chemin de
déformation réel, interface précise des 24 sommets défectueux, topologie locale du bord de l'entrejambe. Aucune cause
n'est établie par ce plan.

## 4. Limites et étapes non réalisées

- Le plan factoriel réel (masculin / féminin sur leur propre maillage) reste **bloqué** : aucune correspondance
  validée (injective, erreur sous une arête) n'existe encore.
- Le terme G (direction, norme, variation, invariance de repère, sensibilité aux transformations) n'a pas été étudié
  numériquement dans cette étape. Il doit l'être avant toute formulation.
- Batterie de propriétés (translation, rotation globale, continuité de transition, stabilité de triangulation,
  étirements) : non exécutée en totalité ici.
- Jeu de poses de validation indépendant : **à déclarer, non exécuté**. Candidats : hanche G 45°, 135°, 150° ;
  hanche D 45° ; genou G 45°, 120°. Ces poses ne doivent servir ni à la calibration ni aux choix de conception.

## 5. Critères

Aucun seuil n'a été modifié. Les conclusions ne sont pas des validations. Le ratio de qualité réel reste
« non validé ».

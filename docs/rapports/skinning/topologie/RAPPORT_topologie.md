# Topologie ouverte, frontières et solveur : Maria

Scripts : `engine/validation/skinning/investigation_topologie.py` (audit des trois maillages et système linéaire),
`investigation_topologie_detail.py` (sommets coïncidents, soudure diagnostique, frontières),
`investigation_topologie_experiences.py` (expériences A à E), `investigation_topologie_flexion.py` (phase 4).
Données : `topologie.json`, `topologie_maria_detail.json`, `experiences_topologie.json`, `flexion_topologie.json`,
`comparaison_HBM_Maria.json`.

Rappel conservé : **32 occurrences (triangle × pose) = 7 triangles distincts** ; les sept sont de catégorie 3. Les
six poses indépendantes ne sont pas utilisées. Aucune correction n'est faite dans le moteur, et les seuils ne sont
pas modifiés.

## 1. Audit topologique (phase 1)

| Mesure | Maria | HBM masculin | HBM féminin |
|---|---:|---:|---:|
| Sommets | 8 094 | 10 582 | 10 582 |
| Faces | 14 566 | 21 160 | 21 160 |
| Arêtes | 22 604 | 21 170 | 21 170 |
| Composantes (graphe d'arêtes) | **73** | 1 | 1 |
| Composantes fermées | 18 | 1 | 1 |
| Arêtes frontière | **1 510** | 0 | 0 |
| Boucles de frontière | 88 | 0 | 0 |
| Arêtes non variétés | 0 | 0 | 0 |
| Sommets non référencés | 0 | 0 | 0 |
| Faces dégénérées ou dupliquées | 0 | 0 | 0 |
| Poids nuls | 0 | 0 | 0 |

Les composantes de Maria ont des tailles très variées : la plus grande compte 907 sommets, puis 373, 373, 359, 326.
Les 73 composantes ne sont pas 73 défauts (comme demandé). Plusieurs sont des pièces fermées bien formées, et
d'autres sont des morceaux ouverts.

**Origine des 1 510 arêtes frontière.** On distingue trois types.

- **Coutures non soudées (198 arêtes).** 125 paires de sommets ont exactement la même position dans deux composantes
  différentes. Si l'on soude ces paires (expérience de diagnostic), les arêtes frontière tombent de 1 510 à 1 312, les
  composantes de 73 à 62, et la surface reste ouverte (30 arêtes non variétés apparaissent). La soudure n'est donc
  pas une correction : elle révèle surtout des coutures.
- **Vraies frontières ouvertes (1 312 arêtes).** Elles n'ont pas de sommet coïncident. La médiane de la distance d'un
  sommet de frontière à la composante la plus proche est d'environ 1 cm. Cette distance est trop grande pour une
  couture et trop petite pour écarter une pièce séparée (vêtement, par exemple). Le maillage ne contient aucune
  métadonnée qui permette de trancher.
- **Composantes symétriques.** 56 composantes ont exactement les mêmes nombres de sommets, d'arêtes et de faces
  qu'une autre composante, deux à deux. Ce ne sont **pas** des doublons : leurs positions diffèrent de 0,05 à 0,26 m
  en moyenne. Ce sont des pièces gauche/droite symétriques.

**Vérification de l'hypothèse « parties volontairement séparées ».** Elle ne peut pas être vérifiée
complètement à partir de la géométrie seule. Les arguments dans les deux sens sont les suivants.
- Contre l'hypothèse de simples coutures : la plupart des frontières ne coïncident pas avec une autre composante.
- Pour une séparation volontaire : les pièces sont symétriques, et plusieurs sont fermées (18 composantes).
- Pour un défaut de construction : 198 arêtes sont des coutures non soudées, et les zones mixtes sont fragmentées
  (voir section 5).

**Composante contenant les sept triangles : la composante 45.** Elle a 155 sommets, 262 faces et 50 arêtes
frontière, réparties en trois boucles. Elle est centrée sur le plan médian (x ≈ 0, z ≈ 0,92 m) : c'est une pièce
ouverte de l'entrejambe. Aucun de ses sommets de frontière ne coïncide avec un sommet d'une autre composante. Ce
n'est donc ni une couture ni un doublon : c'est une pièce à frontière réelle.

**Sommets de frontière près des articulations.** Les sommets de frontière les plus proches sont à 0,37 longueur de
hanche (hanches) et à 0,17 (genoux). Seize sommets de frontière sont à moins de 0,5 longueur de hanche de chaque
hanche ; douze à moins de 0,5 de chaque genou.

## 2. Système linéaire de SQ (phase 2)

M = diag(deg + λ) − Adj, avec un λ uniforme. **Il n'existe aucune condition de frontière explicite** : les sommets
de frontière ont seulement moins de voisins, et ils sont traités comme les autres.

- **Couplage entre composantes : aucun.** Aucune entrée de M ne relie deux composantes (0 entrée hors bloc, pour les
  trois morphologies). M est donc diagonale par blocs.
- **Solutions indépendantes : vérifié.** La solution globale et la solution bloc par bloc diffèrent au plus de
  2,2 × 10⁻¹⁵ (Maria) et 2,7 × 10⁻¹⁵ (HBM).
- **Rang et conditionnement.** Pour Maria, la dimension du noyau sans ancre vaut **73** (une constante par
  composante) ; avec λ = 0,1 le système est inversible. λmin = 0,1, λmax = 20,26, conditionnement 202,6. Pour HBM :
  noyau 1, conditionnement 84,4.
- **Composantes isolées.** Aucune composante n'est sans contrainte : chacune est ancrée à LBS par λ. Une composante
  n'a pas de solution non contrainte, mais elle ne dépend d'aucune autre.

**Ce que cela établit.** Le système de SQ ne peut pas transmettre d'influence entre composantes. La solution des sept
triangles ne dépend que de la composante 45 et de son propre graphe d'arêtes. Les autres composantes (et leurs
frontières) ne peuvent pas influencer les sept triangles.

## 3. Expériences contrôlées (phase 3)

Tout est fixé (poids, os, LBS, Mv, Rsq) ; seul le graphe ou le paramètre de contrainte change. Le solveur utilisé
reproduit `solve_fixe` (écart nul avec λ uniforme). Les résultats sont donnés en nombre de nouveaux retournements
(mesure A) sur les sept triangles, pour trois poses : gauche 105 (`generative_hanche_G_105`), droite flexion 120
(`reelle_R_flex120`), gauche flexion 120 (`reelle_L_flex120`).

**A. Composante native ouverte.** Résoudre la seule composante 45 reproduit le maillage complet exactement (écart
0,0 m). Résultat : 3, 3, 4.

**B. Frontières fermées par éventail.** Les trois boucles de la composante 45 sont fermées (50 faces ajoutées).
- Aire ajoutée : 0,10 m², soit environ quatre fois l'aire de la pièce.
- Déplacement des sept sommets : 6 à 7 mm en moyenne, jusqu'à 10 mm au maximum.
- Retournements : 3, 3, **3** (contre 4 en ouvert pour la pose gauche 120).

La fermeture n'est donc pas neutre géométriquement, et elle ne supprime aucun retournement : elle en supprime un
seul, dans une seule pose.

**C. Contraintes de frontière explicites.** Les sommets de frontière de la composante 45 reçoivent un λ plus fort.

| λ de frontière | 0,1 (identique au cas natif) | 1 | 10 | 1 000 |
|---|---:|---:|---:|---:|
| Gauche 105 | 3 | 3 | 3 | 3 |
| Droite 120 | 3 | 3 | 3 | 3 |
| Gauche 120 | 4 | 3 | 3 | 3 |

Une contrainte forte réduit une fois, de 4 à 3, le nombre dans la pose gauche 120. Elle ne supprime pas les
retournements.

**D. Distance aux frontières (sous-domaines centrés sur les sept triangles).** Le rayon h est en anneaux. La taille du
domaine et la distance à la frontière varient ensemble (confondu, comme indiqué).

| h | 1 | 2 | 3 | 4 | 5 | 6 (complet) |
|---|---:|---:|---:|---:|---:|---:|
| Gauche 105 | 2 | 3 | 3 | 4 | 3 | 3 |
| Droite 120 | 3 | 3 | 3 | 3 | 3 | 3 |
| Gauche 120 | 3 | 4 | 4 | 4 | 4 | 4 |

Le domaine tronqué modifie le compte (2 à 4). Au-delà de trois anneaux, le compte varie peu (3 à 4). Les sommets des sept triangles sont à 0 à 3 anneaux de la
frontière (le sommet 4172 est lui-même sur la frontière), donc la troncature touche directement leur voisinage.

**E. Taille du domaine avec composantes disjointes.** Ajouter une composante disjointe (la plus grande autre, 907
sommets) ne modifie pas la solution de la composante 45 (écart 0,0 m). La composante ajoutée a un écart de 1,3 × 10⁻⁸ m
entre les deux calculs, ce qui relève de l'arrondi d'une factorisation plus grande.

## 4. Interaction topologie et flexion (phase 4)

La topologie est identique pour toutes les poses. Balayage de 0 à 120° par pas de 15°, à gauche et à droite.

| Angle | 0 | 15 | 30 | 45 | 60 | 75 | 90 | 105 | 120 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Gauche (nouveaux retournements) | 0 | 0 | 0 | 1 | 3 | 2 | 2 | 3 | 4 |
| Droite (nouveaux retournements) | 0 | 0 | 0 | 1 | 2 | 3 | 3 | 3 | 3 |

- **Seuil d'apparition : 45°, identique à gauche et à droite.**
- **Évolution** : croissante à gauche jusqu'à 4 à 120°, plateau à 3 à droite.
- **Composante** : sur les 47 poses et sur tout le maillage, les **62 occurrences** sont dans la composante 45. Aucune
  autre composante n'en contient.
- **Distance aux frontières** (distance en anneaux du triangle à la frontière la plus proche) : 58 occurrences à
  deux anneaux, 4 à zéro anneau (le triangle touche la frontière), aucune à un ou à plus de deux anneaux. L'échantillon
  est petit : ce résultat est une observation, pas une loi.
- **Gauche et droite** : le même seuil et une évolution proche. Les miroirs concordent partiellement (rapport
  de la section précédente).

## 5. Comparaison avec les modèles HBM (phase 5)

| Mesure | Maria | HBM masculin | HBM féminin |
|---|---:|---:|---:|
| Composantes | 73 | 1 | 1 |
| Frontières (arêtes) | 1 510 | 0 | 0 |
| Arêtes pelvis–cuisses (directes) | **8** | 46 | 52 |
| Sommets de zone mixte | 3 135 | 7 557 | 9 071 |
| Composantes de la zone mixte | **53** | 3 | 3 |
| Plus grande composante mixte (sommets) | 204 | 6 632 | 6 261 |
| Sommets mixtes isolés | 2 | 0 | 0 |

**Lecture.** La différence la plus nette n'est pas le nombre de frontières, mais **la continuité entre pelvis et
cuisses** : chez Maria, seules 8 arêtes relient directement le pelvis aux cuisses, contre 46 et 52 chez les HBM. La
zone mixte est aussi fragmentée en 53 morceaux, contre 3. Le mélange de poids, qui explique la régression, est donc
discontinu chez Maria. C'est une différence structurelle démontrée. Son effet sur les retournements reste à tester
(section 6).

## 6. Diagnostic final (phase 6)

**Faits démontrés**
- Le solveur de SQ ne couple pas les composantes : la solution des sept triangles ne dépend que de la composante 45.
- Il n'existe aucune condition de frontière explicite ; λ est uniforme.
- Les sept triangles sont dans la composante 45, une pièce ouverte réelle (pas une couture ni un doublon), avec des
  sommets à 0 à 3 anneaux de sa frontière.
- Les 62 occurrences de retournement sont toutes dans la composante 45.
- Le seuil d'apparition est de 45° à gauche comme à droite, sur la même topologie.
- La fermeture des frontières ne supprime pas les retournements (3, 3, 3 au lieu de 3, 3, 4 ; géométrie modifiée de
  0,10 m² et de 6 à 10 mm).
- Une contrainte de frontière plus forte n'en supprime aucun (une seule réduction, de 4 à 3, à partir de λ = 1).
- Maria a une continuité pelvis–cuisses et une zone mixte très différentes de celles des HBM.

**Corrélations**
- Le nombre de retournements dépend de la troncature du domaine (2 à 4 selon le rayon), surtout dans les deux premiers
  anneaux. Cette sensibilité est une corrélation avec la distance à la frontière, non une cause.

**Hypothèses non vérifiées**
- Une fragmentation de la zone mixte (53 morceaux) ou une continuité pelvis–cuisses insuffisante provoquent les
  retournements. Cette hypothèse est plausible mais n'a pas été testée : il faudrait modifier la connectivité des
  poids dans un patch contrôlé.
- Les frontières ouvertes elles-mêmes (1 312 arêtes) sont la cause : non démontré, car la fermeture ne supprime pas
  les retournements.
- Les pièces séparées (vêtement ou autre) sont la source des frontières : non vérifiable à partir de la géométrie.

**Résultats négatifs**
- La topologie ouverte n'explique pas, à elle seule, l'existence des retournements : ils persistent avec la
  fermeture et avec des contraintes fortes.
- Les conditions aux limites du solveur (λ de frontière) n'expliquent pas les retournements.
- Les composantes ne se couplent pas : l'hypothèse d'une influence globale par le solveur est réfutée.
- Les sept triangles ne sont pas dans une composante en double (les composantes symétriques ne sont pas des
  doublons).

**Question posée : une topologie comparable reproduit-elle les retournements dans un patch synthétique ?** Non testé
dans cette étude. Les expériences portent sur le patch réel de Maria, pas sur un patch synthétique. Un test
synthétique requiert un patch ouvert avec une zone mixte fragmentée, à construire explicitement.

## 7. Limites

- Une seule composante (45) contient les sept triangles ; l'échantillon de retournements est petit (sept triangles).
- Les expériences de fermeture et de sous-domaine changent la géométrie : leurs résultats ne sont pas neutres.
- L'origine des frontières ouvertes (pièce séparée ou trou) ne peut pas être tranchée par la géométrie.
- Aucun patch synthétique n'a été construit dans cette étude.

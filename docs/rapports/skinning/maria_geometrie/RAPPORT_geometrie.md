# Origine géométrique des retournements SQ de Maria

Scripts : `engine/validation/skinning/investigation_maria_geometrie.py` (phases 1 à 4),
`investigation_maria_concordance.py` (symétrie pose par pose), `investigation_regionale_v2.py` (phase 5).
Données : `geometrie_retournements.json`, `concordance_miroir.json`, `../regionale/regionale_v2.json`.
Les anciennes mesures régionales sont conservées dans `../regionale/regionale.json`.

Rappel de comptage, conservé : **32 occurrences (triangle × pose) = 7 triangles distincts, 11 poses**. Toutes sont
de catégorie 3. Les six poses indépendantes ne sont pas utilisées. Aucun seuil ni aucun algorithme n'est modifié.
Aucune correction spécifique aux sept triangles n'est faite dans le moteur.

## 0. Trois mesures séparées (phase 4)

| Mesure | Définition | Sur les 77 cas (7 triangles × 11 poses) |
|---|---|---|
| A — référence locale | normale déformée opposée à polaire(Mv moyen)·n_repos | 32 nouvelles inversions introduites par SQ ; 0 pour LBS sur ces cas |
| B — forme LBS | normale SQ opposée à la normale LBS | 18 occurrences : 14 parmi les 32 nouvelles inversions A, 4 hors de A |
| C — forme SQ propre | normale SQ opposée à la partie rigide polaire de sa propre déformation affine | 0 occurrence : ce critère ne se déclenche dans aucun des 77 cas |

Classement par occurrence : 32 « nouvelle inversion introduite par SQ » (mesure A) ; 4 « seulement différence de
forme » (B seulement, sans A) ; 41 « non retourné ». Les 4 dernières ne sont pas des retournements au sens de la
convention de référence de la mesure A.

**Rotations rigides.** Une rotation globale du maillage (repos et os tournés de la même matrice Q) donne zéro
inversion pour A, B et C. Les mesures ne comptent donc pas les rotations rigides.

## 1. Voisinage et témoins (phase 1)

Les sept triangles, tous dans l'entrejambe, ont des valences de 5 à 7 par sommet. Chacun a 3 triangles voisins
par arête (anneau 1), et 18 à 22 triangles à deux anneaux selon le cas. Leurs aires au repos vont de 3,7e-5 à 1,2e-4 m².

**Comparaison aux témoins appariés.** Les témoins sont huit triangles de l'entrejambe qui ne se retournent dans
aucune des 11 poses, choisis au plus proche voisin sur sept caractéristiques de repos (log-aire, angles min et
max, courbure, mélange des poids, longueur moyenne, valence moyenne), normalisées.

- Aire, angles minimal et maximal, courbure, valence et mélange des poids des sept triangles sont **dans la
  plage des témoins**. Exemple : triangles (4145, 4135, 4144) : angle minimal 14,7°, témoins 13,5° à 15,8°.
- Il n'existe donc pas de propriété de repos qui isole les sept triangles.
- Différence dans la pose : dans les exemples examinés, les triangles retournés ont un os dominant tourné de
  120°, alors que leurs témoins ont souvent un angle plus faible dans la même pose. Ce n'est pas systématique
  (voir `dynamique` dans le JSON), et le triangle (4102, 4172, 4170) fait exception (voir plus bas).
- Le triangle (4102, 4172, 4170) a un sommet de bord (4172 ; 1 508 sommets de bord sur 8 094). Sa courbure
  moyenne négative (−1,35) est un artefact de bord, et ce cas doit être lu à part.

## 2. Expériences à un seul facteur (phase 2)

Référence : pose P1 = `generative_hanche_G_105`, nouvelles inversions A : 3 sur les sept triangles, 3 sur tout
le maillage, 16 retournements LBS, 4 SQ.

| Facteur (un seul changé) | Protocole | Résultat sur les sept triangles |
|---|---|---|
| Angle d'articulation (hanche G) | 0 à 120° par pas de 15° | 0, 0, 0, 1, 3, 2, 2, 3, 4 : **apparaît à partir de 45° et augmente** |
| Répartition des poids | affectation progressive (α de 0 à 1) vers l'os dominant, sur les 13 sommets concernés ; contrôle : même opération sur 13 sommets témoins, 5 tirages | concerné : 3, 3, 3, 3, 4 ; contrôle : 3 à chaque α (aucun changement) |
| λ (conditions aux limites) | 0,01 à 3 | P1 : 4, 4, 3, 3, 3, 3 ; P2 (`reelle_R_flex120`) : 3 partout |
| Position normale d'un sommet | ±1 mm, un sommet à la fois (13 sommets) | 2 ou 3 dans tous les cas |
| Position tangentielle d'un sommet | ±5 % de la longueur moyenne d'arête (13 sommets) | 2 ou 3 dans tous les cas |

Lecture :
- **Sensibilité à la pose** : démontrée sur ce maillage (angle d'articulation). Les retournements n'apparaissent
  qu'au-delà de 45° de flexion.
- **Poids** : affecter les poids des sommets concernés à leur os dominant ajoute au plus une occurrence (α = 1).
  Le contrôle ne change pas. L'effet est faible et ne supprime rien. Un effet très faible n'établit pas un
  mécanisme.
- **λ** : sans effet notable.
- **Géométrie locale** : déplacer un sommet de 1 mm (normal) ou de 5 % d'arête (tangentiel) ne supprime ni
  n'ajoute de retournement de façon systématique. Les sept triangles ne sont donc pas sur une frontière fine de
  géométrie : la géométrie locale à cette échelle ne les contrôle pas.
- **Taille des triangles et courbure en tant que facteur isolé** : non testés séparément, car un changement de
  taille exige un remaillage. Le contrôle de courbure et de taille est seulement indirect (témoins, E4 et E5).
- **Conditions aux limites** : seul λ a été balayé ; l'ancrage vers LBS n'a pas été testé autrement.
- **Triangulation** : non testée sur Maria ; le résultat synthétique antérieur (triangulation inverse) est dans
  `docs/rapports/skinning/comparaison_morphologies/retournements.json` et ne peut pas être transféré sans
  précaution (voir erreur 206).

## 3. Symétrie gauche/droite (phase 3)

**Géométrie de repos.** Le plan de symétrie est x = 0 (centres des hanches à ±0,097 m). Pour 95,9 % des sommets, le
symétrique le plus proche est à moins de 0,2 longueur d'arête. La médiane de la distance symétrique vaut 3e-5 fois
la longueur moyenne, mais 1 % des sommets ont un symétrique à plus de 0,44 longueur d'arête. Le maillage est donc
symétrique dans sa majorité, pas partout.

**Les sept triangles ont des miroirs exacts.** Chacun a un triangle miroir dans le maillage. Pour six d'entre eux,
l'aire au repos est identique à environ 10⁻⁵ près en relatif ; le triangle (4102, 4172, 4170) diffère de 2 % de son
miroir. Le miroir de 4145, 4135, 4144 est 4226, 4225, 4216 : ces paires sont
**incluses dans l'ensemble des sept**. Les paires sont donc (4145, 4135, 4144) ↔ (4226, 4225, 4216),
(4161, 4135, 4145) ↔ (4242, 4226, 4216), (4161, 4145, 4103) ↔ (4242, 4184, 4226). Le triangle (4102, 4172, 4170) a
pour miroir (4170, 4172, 4183), qui n'est pas dans l'ensemble.

**Poids.** Entropie moyenne des poids : 0,2277 à gauche et à droite. Mélange moyen : 0,1083 et 0,1084. Somme des
poids par os, écart relatif moyen : 9e-5. Les 29 paires d'os gauche/droite ont donc des poids symétriques.

**Courbure et valence.** Valence moyenne : 5,58 (gauche) et 5,59 (droite). Défaut angulaire moyen : 0,0460 (gauche)
et 0,0412 (droite), soit environ 11 % d'écart. Cette asymétrie de courbure est réelle mais modérée.

**Déformations et retournements gauche/droite (pose par pose).** Les poses réelles gauche et droite ne sont pas
des miroirs exacts (ce sont des captures distinctes). Sur les quatre paires :

| Paire de poses | Nouvelles inversions gauche | Dont miroir retourné à droite | Nouvelles inversions droite | Dont miroir retourné à gauche |
|---|---:|---:|---:|---:|
| flex 120 | 4 | 3 | 3 | 3 |
| flex 60 | 3 | 2 | 2 | 2 |
| flex 120 + genou 90 | 4 | 3 | 3 | 3 |
| flex 60 + abd 20 + int 20 + genou 60 | 3 | 1 | 1 | 1 |

Au total, **9 inversions sur 14 à gauche ont leur miroir inversé à droite**, et réciproquement. La concordance est
donc nette mais pas parfaite.

**Conclusion sur la symétrie.** Le maillage et ses poids sont quasi symétriques sur les sept triangles. Les
retournements apparaissent sur les deux côtés, dans des poses symétriques, avec des miroirs souvent concordants.
Il n'existe pas de défaut géométrique asymétrique qui expliquerait les sept triangles. L'effectif identique
genou gauche/droite de la comparaison précédente n'est pas expliqué par une asymétrie du maillage.
Ce point reste une lecture compatible avec des poses symétriques, pas une preuve.

## 4. Régions : classes d'arêtes et BFS (phase 5)

**Vérification du BFS.** La distance aux zones mixtes calculée en numpy et un BFS indépendant (deque) donnent
exactement la même valeur pour les trois morphologies (écart maximal 0). Les régions elles-mêmes ne sont **pas**
construites par BFS : elles sont définies par coordonnées normalisées autour des articulations (`regions`). Le BFS
ne sert qu'à mesurer la distance de propagation.

**Trois classes d'arêtes**, sur les 29 poses, arêtes ≥ 5 mm, seuils inchangés (régression > 0,05) :

| Morphologie | Classe | Arêtes×poses | % régression | % régression pondérée longueur | % régression pondérée aire | % amélioration | p99 SQ−LBS |
|---|---|---:|---:|---:|---:|---:|---:|
| masculin | mixte | 358 817 | 0,63 % | 1,26 % | 1,88 % | 3,05 % | 0,033 |
| masculin | entre pur et mixte | 10 556 | 0,63 % | 1,27 % | 1,87 % | 3,42 % | 0,036 |
| masculin | pure propagée (1–3 anneaux) | 34 452 | 0,05 % | 0,13 % | 0,23 % | 1,33 % | 0,009 |
| masculin | pure éloignée | 64 264 | 0 % | 0 % | 0 % | 0 % | 0 |
| féminin | mixte | 375 289 | 0,49 % | 1,01 % | 1,67 % | 2,22 % | 0,025 |
| féminin | entre pur et mixte | 9 599 | 1,45 % | 2,37 % | 2,88 % | 9,00 % | 0,062 |
| féminin | pure propagée (1–3 anneaux) | 29 000 | 1,10 % | 2,28 % | 2,76 % | 5,93 % | 0,052 |
| féminin | pure éloignée | 34 626 | 0 % | 0 % | 0 % | 0,69 % | 0,001 |
| Maria | mixte | 206 364 | **1,14 %** | **1,65 %** | **1,95 %** | 1,99 % | 0,060 |
| Maria | entre pur et mixte | 56 086 | 0,90 % | 1,24 % | 1,48 % | 3,06 % | 0,042 |
| Maria | pure propagée (1–3 anneaux) | 111 331 | 0,12 % | 0,12 % | 0,20 % | 0,89 % | 0,008 |
| Maria | pure éloignée | 225 214 | 0 % | 0 % | 0 % | 0 % | 0 |

Vérification du BFS : écart maximal 0 pour les trois morphologies. Chez Maria, 2 238 sommets ne sont pas
atteignables depuis une zone mixte (composantes sans sommet mixte) ; ils sont classés « pure éloignée ».

Lecture : **sur les arêtes mixtes, Maria régresse à 1,14 % (1,65 % pondéré longueur, 1,95 % pondéré aire), contre
0,63 % et 0,49 % (1,26 % et 1,01 % pondérés longueur) pour masculin et féminin**. Le féminin a davantage de
régression sur les arêtes entre pur et mixte (1,45 %) et sur les arêtes propagées (1,10 %) ; Maria est
intermédiaire sur ces classes. C'est une différence
nouvelle, qui n'apparaissait pas dans la comparaison précédente (où les arêtes mixtes étaient regroupées avec les
arêtes à poids purs dans la classe « directe mixte »). Les régressions sont au total très concentrées sur les
arêtes qui touchent une zone mixte (les arêtes éloignées ne régressent jamais).

## 5. Décision scientifique (phase 6)

**Une propriété géométrique commune explique-t-elle les sept triangles ?** Non démontré, et probablement non.
Leurs caractéristiques de repos sont dans la plage des témoins, leurs miroirs sont géométriquement identiques, et
des perturbations de 1 mm ou de 5 % n'y changent rien de systématique.

**Le mécanisme est-il spécifique à Maria ?** Non établi. Masculin et féminin n'ont aucune nouvelle inversion A
sur les 29 poses (0 et 0), alors que Maria en a 32 occurrences. La comparaison est confondue avec la différence de maillage : Maria
a 1 510 arêtes frontières et 73 composantes, contre un maillage fermé et connexe pour les deux autres. Cette
topologie particulière est une cause plausible à tester, non une cause démontrée.

**Les retournements dépendent-ils d'une configuration particulière des os ?** Oui, démontré sur ce maillage. Ils
apparaissent au-delà de 45° de flexion de la hanche gauche et augmentent avec l'angle (expérience E1). Les
inversions à droite apparaissent dans les poses droites.

**Une intervention sur la géométrie synthétique reproduit-elle le phénomène ?** Pas dans cette étude. Les
perturbations locales de Maria (E4, E5) ne le modifient pas. Le résultat synthétique antérieur (31 configurations
avec nouveaux retournements, surtout à l'angle 120/−60) reste soumis à la réserve de dégénérescence de la
référence (erreur 206). Il ne prouve pas la reproduction sur des géométries réelles.

**Une relation causale est-elle démontrée ?**
- Démontré : dépendance à l'angle d'articulation (pose) sur ce maillage ; absence d'effet des perturbations
  géométriques locales testées (±1 mm, ±5 %) et de λ sur les sept triangles ; symétrie quasi parfaite des
  propriétés de repos et des poids entre les côtés.
- Faible effet mesuré, non concluant : répartition des poids (une occurrence au maximum).
- Hypothèse non vérifiée : rôle de la topologie ouverte de Maria, rôle de la courbure réelle, rôle de la
  triangulation, rôle du repère de référence polaire.
- Non testé : taille des triangles et courbure isolées (nécessite un remaillage), conditions aux limites autres
  que λ.

## 6. Limites

- Une seule forme de SQ est testée. Les expériences ne disent rien sur d'autres formulations.
- Les poses L et R réelles ne sont pas des miroirs exacts : la concordance est donc mesurée, pas attendue.
- Les défauts angulaires près du bord ouvert ne sont pas fiables (1 508 sommets de bord).
- Sept triangles seulement : toute généralisation est fragile.
- Les seuils (régression 0,05, amélioration −0,02, arêtes ≥ 5 mm) sont ceux de la comparaison précédente.

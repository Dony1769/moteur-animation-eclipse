# Défaut réel du maillage masculin : identification, confrontation synthétique, deux échecs

Scripts : `engine/validation/skinning/investigation_defaut_reel.py` (phase 1, données
`defaut_reel_masculin.json`) et `engine/validation/skinning/investigation_confrontation.py` (phases 2 et 3,
données `confrontation.json`). Statut : **diagnostic**. Aucune méthode validée ni intégrée. LBS, DQS et Bone Heat
restent la référence. Poses de validation candidates (hanche G 45/135/150, hanche D 45, genou G 45/120) : non utilisées.

## Phase 1 — Défaut réel (maillage masculin original, 11 poses)

Poses : celles où SQ (moyenne arithmétique, λ = 0,1) dépasse LBS sur l'étirement max (`lambda_morphologies.json`) :
hanche G générative 75/105/120, réelles L/R flex120, L/R combo flex120 genou90, L/R combo flex60 abd20 int20 genou60.
Maillage : 10 582 sommets, 21 170 arêtes, 21 160 triangles, 19 os.

Vérification : LBS reconstruit `Σ w_k T_k(r)` avec `T_k = pm_k · inv(B_k)` : erreur 9,9 × 10⁻⁸ m. Identité
`lbs_a − lbs_c = Mv_a d + G` vérifiée sur les arêtes (erreur consignée dans les JSON).

**Arêtes régressées** (arêtes ≥ 5 mm, SQ − LBS > 0,05 sur le rapport de longueurs) :

| Pose | Nb régressées | Part à < 0,30 m du milieu des hanches | Part à < 0,15 m | Max distance (m) |
|---|---|---|---|---|
| G générative 75 | 114 | 0,73 | 0,31 | 0,39 |
| G générative 120 | 174 | 0,67 | 0,25 | 0,39 |
| L réelle flex120 | 174 | 0,67 | 0,25 | 0,39 |
| L combo flex120 genou90 | 188 | 0,53 | 0,23 | 0,48 |
| R combo flex120 genou90 | 198 | 0,53 | 0,24 | 0,48 |
| R réelle flex60 | 86 | 0,79 | 0,36 | 0,39 |

Lecture : la régression est **majoritairement** dans la zone hanche, mais **pas exclusivement** (jusqu'à 0,48 m du
milieu). Elle touche 83 à 198 arêtes par pose, et non seulement les 24 sommets défectueux initiaux.

**100 arêtes les plus régressées** (toutes poses) : 79 sommets distincts ; centroïde au repos (−2,253 ; −0,040 ;
0,753) m, écarts types (0,106 ; 0,055 ; 0,236) m ; SQ − LBS entre 0,20 et 0,35 ; longueur médiane 0,029 m ; gradient
médian de poids 11,7 /m ; |G|/longueur médiane 0,385 ; |Mv·d|/longueur médiane 0,827. Ce sont des arêtes à fort
gradient de poids, où le terme rigide domine.

**100 témoins sans régression** (appariés en longueur, 0,015–0,05 m) : |G|/longueur médiane 0,0 ; gradient médian
1,24 /m. Hypothèse à vérifier : les os impliqués ont la même transformation sur ces arêtes, donc G = 0 malgré un
gradient non nul. Ce point n'est pas encore démontré.

**100 triangles les plus déformés** : principalement dans les poses flex120 (22 + 22 + 18 + 17 + 16 + 4 + 1 selon les
poses). Distorsion SQ max 2,13 contre 1,83 pour LBS sur les mêmes triangles.

**Volume (global seulement)** : variation relative pour la pose combo flex120 genou90 gauche : LBS −0,056, SQ −0,087 ;
SQ réduit plus le volume que LBS dans toutes les poses (−0,018 contre −0,030 pour la générative 75). Une variation
de volume locale n'est pas calculée : elle dépend de l'origine (erreur 196).

**Retournements** : 0 nouveau retournement SQ par triangle dans les 11 poses (mesure par triangle, repère polaire de Mv).
LBS en produit de 0 à 29.

**Métriques corrigées** (phase 4 du cahier) : percentiles 50/90/95/99 des rapports sur arêtes ≥ 5 mm ; classes de
longueur ; déplacements en mètres ; aires par triangle ; nombre de retournements supplémentaires. Les métriques
historiques restent dans les rapports précédents.

## Phase 2 — Confrontation avec un patch synthétique

Zone : arêtes ≥ 5 mm à moins de 0,30 m du milieu des hanches, pose L flex120 (1 178 arêtes réelles).

| Métrique | Réel | V0 apparié (h, largeur, angles, lisse) | V1 largeur 0,30 m | V4 angles 90/0 | V5 arrangement aléatoire |
|---|---|---|---|---|---|
| Pas médian (m) | 0,0287 | 0,0287 | 0,0287 | 0,0287 | 0,0287 |
| Gradient L1 médian (/m) | 3,73 | 2,73 | 4,71 | 2,73 | 26,4 |
| \|G\|/longueur médiane | 0,071 | 0,167 | 0,040 | 0,136 | 1,78 |
| \|Mv·d\|/longueur médiane | 0,997 | 0,895 | 1,00 | 0,931 | 0,910 |
| Part régressée (> 0,05) | 0,089 | 0,260 | 0,194 | 0,165 | 0,053 |
| Excédent p50 | −0,022 | 0,001 | 0,001 | 0,001 | −1,17 |
| Excédent p99 | 0,179 | 0,208 | 0,216 | 0,118 | 0,146 |

Conclusion : **aucune variante ne reproduit quantitativement le défaut réel**. V0 surestime la part régressée d'un
facteur ~3 et |G| d'un facteur ~2,4. V5 a un gradient sept fois trop fort et n'est pas représentatif. Le patch
appariement est imparfait : le gradient obtenu (2,73) n'est pas celui visé (3,73), car la largeur a été déduite d'une
formule à deux paramètres sans recalibrage. Ce résultat est négatif et contredit l'idée qu'un patch plat « simple »
suffit. Le critère d'acceptation (reproduction quantitative des principales mesures) n'est pas satisfait.

Remarque sur le terme G : dans le réel, |G|/longueur est petit (0,07) par rapport au terme rigide (1,0). Dans les
patchs synthétiques, G est plus grand (rapport 1,65 mesuré précédemment). Les patchs surestiment donc G : c'est une
différence de fond qui limite toute conclusion sur le rôle de G tiré des patchs.

## Phase 3A — Poids purs (écart de 0,048 m)

- Sur le réel (pose L flex120) : 2 751 sommets dont le voisinage est pur et sur le même os. Écart SQ − LBS par distance
  au bord pur :
  - distance 0 : max 13,9 mm, médiane 1,2 µm ;
  - distance 1 : max 8,8 mm, médiane 0,33 µm ;
  - distance 2 : max 0,11 mm ;
  - distance 3 : max 2,2 µm ; décroissance d'environ un ordre de grandeur par anneau au-delà de 2.
- La déformation SQ est calculée par un système global `(deg + λ)I − Adj`. L'écart sur un sommet pur est donc
  `M⁻¹ g`, qui se propage depuis les arêtes mixtes voisines et décroît avec la distance. Il ne s'agit pas d'un
  forçage : aucune contrainte n'impose la position LBS.
- Conditions : le maillage est fermé, la surface n'a pas de bord ; l'ancrage λ·p_LBS est le seul terme de rappel.
- Transformation rigide commune : reproduite exactement (1 × 10⁻¹⁵ m) sur le cas témoin.
- Le phénomène existe dans le patch à solution connue : le patch V0 n'a pas de zone pure (largeur de transition égale
  à la moitié du domaine), donc la mesure de décroissance y est impossible. Le cas témoin alterné de la phase
  précédente donnait 0,048 m.

Conclusion : l'écart sur poids purs est une propagation globale, décroissante avec la distance, qui n'est pas
supprimée par une condition aux limites. Il n'est pas démontré qu'il soit à l'origine de la régression réelle.
Le chiffre de 0,048 m provient d'un patch synthétique, non du maillage réel (où le maximum est 13,9 mm, sur des
sommets de bord).

## Phase 3B — Retournements

**Correction importante.** Le rapport précédent annonçait 3 configurations avec retournements supplémentaires. Ce
comptage comparait les totaux (SQ > LBS), pas les triangles nouveaux. Le compte correct, par triangle (SQ retourné et
LBS non retourné), sur les 144 configurations : **31 configurations, 769 triangles au total**. La pire est 54 triangles
(angles 120/−60, arrangement aléatoire, histogramme masculin, géométrie plate, triangulation A).

Analyse des triangles (configuration 120/−60, arrangement lisse, 4 triangles) : poids aux sommets entre 0,35 et 0,65
(tous mixtes, aucun sommet pur), écart de poids d'arête jusqu'à 0,20, aire SQ ≈ 0,55 × aire repos contre aire LBS ≈ 1,2
× aire repos. Les triangles sont fortement comprimés par SQ.

Test de l'hypothèse « moyenne arithmétique des rotations » : remplacer R_ab par la polaire de la moyenne ne supprime
pas les retournements (lisse : 4 → 4 ; alterné 120/−60 : 28 → 33). L'hypothèse est donc réfutée pour cette
configuration. Le mécanisme probable est la compression d'un triangle sous un solveur global, mais il n'est pas
démontré.

Sur le maillage réel : **0 retournement supplémentaire** dans les 11 poses. Les retournements synthétiques ne sont donc
pas observés dans le cas réel à ce stade.

## Phase 4 — Métriques

Les métriques corrigées sont présentes dans `defaut_reel_masculin.json` : percentiles, classes de longueur,
déplacements en mètres, aires par triangle, retournements par triangle. Les mesures du patch sont encore faites pour
partie sur des rapports sans seuil de longueur (phase 2 applique le seuil de 5 mm, mais les patchs ont des arêtes
de 0,029 m, donc sans effet).

## Phase 5 — Poses de validation

Les six poses candidates n'apparaissent dans aucune des analyses ci-dessus. Les poses utilisées (11 réelles ou
génératives de hanche G 75–120, flex60/flex120 et combinaisons) étaient celles du balayage de λ, déjà consignées
comme non indépendantes pour une validation finale.

## Réponse à la question « pourquoi SQ améliore le féminin et Maria, mais aggrave le masculin ? »

**Non établie.** Ce que la mesure démontre :
1. La régression réelle est localisée dans la zone hanche (53 à 79 % des arêtes régressées à moins de 0,30 m), mais
   elle est plus diffuse que les 24 sommets initiaux.
2. Les arêtes les plus régressées ont des gradients de poids élevés (11,7 /m) et un terme rigide dominant.
3. SQ réduit davantage le volume global que LBS dans les mêmes poses.
4. Aucun nouveau retournement par triangle n'apparaît sur le maillage réel.
5. Les patchs synthétiques reproduisent le phénomène qualitativement mais pas quantitativement : aucune variante
   ne satisfait le critère de représentativité.

Ce qui reste à faire pour répondre : comparer le féminin et Maria dans les mêmes métriques (non fait ici), identifier
les triangles réels responsables par arête avec leurs poids et transformations (partiellement fait), et construire un
patch dont les mesures réelles sont reproduites avant de tester un mécanisme.

## Ce qui n'est pas démontré

- Le lien causal entre G, la propagation, la compression et la régression réelle.
- Le rôle de la largeur de transition, de l'angle et de l'arrangement spatial, pris séparément sur le réel.
- Que le mécanisme du patch soit celui du maillage réel.

Aucune nouvelle formulation n'est justifiée par ce rapport.

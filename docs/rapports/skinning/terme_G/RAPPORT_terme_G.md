# Terme G de la décomposition LBS et patchs de jonction (diagnostic)

Script : `engine/validation/skinning/investigation_terme_G.py`
Données : `resultats_terme_G.json` (ce dossier). Statut : **diagnostic, rien n'est validé ni intégré**.
LBS, DQS et Bone Heat restent la référence. Aucun poids n'est transféré entre maillages.

## 1. Définitions, dimensions, repère

- Repère : monde, pose courante. Os k : `T_k(x) = R_k x + t_k`, `R_k ∈ SO(3)` (3×3), `t_k ∈ ℝ³` (m).
  Pour une rotation d'angle θ autour de l'axe passant par c_k : `t_k = c_k − R_k c_k`.
- Poids `w_ik` sans dimension, `Σ_k w_ik = 1`. Sommets `r_i ∈ ℝ³` (repos, m).
- `lbs_i = Σ_k w_ik T_k(r_i)` (m). `Mv_i = Σ_k w_ik R_k` (sans dimension, 3×3).
- Arête (a, c), `d = r_a − r_c` (m), `Δw_k = w_ak − w_ck`.
- **Dérivation** : `lbs_a − lbs_c = Σ_k w_ak R_k (r_a − r_c) + Σ_k (w_ak − w_ck)(R_k r_c + t_k)`
  = `Mv_a d + G`, avec `G = Σ_k Δw_k · T_k(r_c)` (m).
- Hypothèses : aucune. C'est une identité algébrique exacte pour toute valeur de poids (y compris hors de [0,1]) et
  pour toute transformation affine.
- Lecture géométrique : `Mv_a d` est la part rigide locale ; G est la part due à la variation des poids entre les
  deux extrémités, évaluée sur les transformations de l'autre extrémité.

## 2. Vérifications numériques

| Test | Résultat |
|---|---|
| Identité `lbs_a − lbs_c = Mv_a d + G`, 60 configurations aléatoires (20–60 sommets, 2–4 os, graphes aléatoires) | erreur max 1,8 × 10⁻¹⁵ m |
| Approximation de premier ordre `G ≈ Σ_k (∇w_k · d) T_k(r_c)`, poids quadratiques | erreur ∝ h², pente log-log = 2,00 |
| Translation globale c (rest + c, t'_k = t_k + c − R_k c) | G invariant, erreur 9 × 10⁻¹⁶ m |
| Rotation globale Q (R'_k = Q R_k Qᵀ, t'_k = Q t_k) | G ↦ Q G, erreur 3 × 10⁻¹⁵ m |

Le test de premier ordre avec poids affines serait trivialement exact : il n'a pas été retenu (voir erreur 201).

Conséquences démontrées :
- `G = O(|d|·|∇w|)` : G est du premier ordre en les gradients de poids. Sur une arête de poids constants, G = 0 et
  `lbs_a − lbs_c = Mv_a d` exactement.
- G est linéaire en chaque `T_k` (donc en `R_k` et `t_k`) : il dépend de la pose par les seuls os de l'arête.
- G est covariant par rotation globale et invariant par translation globale, comme le lbs lui-même.
- La partie rigide `Mv_a d` dépend de l'extrémité a seulement ; G dépend de `r_c` et de la transformation.

## 3. Batterie de propriétés (cas témoin : patch plat, triangulation A, arrangement alterné, histogramme M, angles 120°/0°)

| Propriété | Résultat | Verdict |
|---|---|---|
| Pose de repos (os identité) | SQ − repos : 1 × 10⁻¹⁵ m | respectée |
| Transformation rigide commune | SQ − LBS : 1 × 10⁻¹⁵ m | respectée |
| Translation globale | 4 × 10⁻¹⁶ m | respectée |
| Rotation globale | 3 × 10⁻¹⁶ m | respectée |
| Poids purs (sommets dont tout le 1-anneau est pur, 105 sommets) | écart SQ − LBS jusqu'à 0,048 m | **non respectée** (propagation depuis l'interface) |
| Continuité (perturbation de poids 10⁻⁴) | variation SQ ≈ 0,061 m par unité de poids | bornée (continue) |
| Stabilité triangulation (A contre B, mêmes sommets) | écart SQ de 0,036 m (≈ 6 % de la taille du patch) | **non négligeable** |
| Retournements | voir §4 | partiellement respectée |
| Étirements / volume | surface ouverte : volume non défini ; étirement max LBS 20,8 (arête très courte, voir erreur 202) | à reprendre sur métrique robuste |

## 4. Plan de patchs de jonction (144 configurations)

Patch : grille 21 × 21 (plate, ou courbée `z = 4 x²`), pelvis (identité) sur y ≥ 0,15, cuisses G et D (rotation autour
de y, centres (±0,1 ; 0,15 ; 0)) pour y ≤ 0 ; transition linéaire pelvis / cuisses pour 0 ≤ y ≤ 0,15.
Poids cuisse : `w_G = (1 − p) s`, `w_D = (1 − p)(1 − s)`. `s` prend les valeurs de l'histogramme natif (10 classes,
masculin ou féminin), arrangées selon : **lisse** (croissant selon x), **aléatoire** (permutation, graine fixe),
**alterné** (zigzag maximal selon x). Même histogramme dans les trois cas : seule la répartition spatiale varie.
Solveur : ARAP.solve_fixe, λ = 0,1, moyenne arithmétique (configuration actuelle). LBS et SQ utilisent les mêmes données.

Régression = arêtes mixtes où `ρ_SQ − ρ_LBS > 0,05` (ρ = longueur déformée / longueur de repos).

Niveaux (moyennes sur les autres facteurs ; données dans le JSON) :

| Facteur | Niveau | Excédent max moyen | Part d'arêtes mixtes régressées |
|---|---|---|---|
| Géométrie | plate / courbe | 0,30 / 0,44 | 0,065 / 0,057 |
| Arêtes | régulières / non uniformes | 0,42 / 0,33 | 0,086 / 0,037 |
| Triangulation | A / B | 0,379 / 0,364 | 0,064 / 0,059 |
| Arrangement (même histogramme) | lisse / aléatoire / alterné | 0,20 / 0,48 / 0,43 | 0,088 / 0,044 / 0,052 |
| Histogramme | masculin / féminin | 0,357 / 0,386 | 0,057 / 0,066 |
| Angles cuisses (90/0 ; 120/0 ; 120/−60) | | 0,31 / 0,41 / 0,40 | 0,066 / 0,088 / 0,029 |

Cas témoin : 757 arêtes mixtes, 54 régressées (7 %), excédent max 0,38.

Résultats démontrés dans ce plan (cellules synthétiques uniquement) :
1. **Le phénomène est reproduit qualitativement** : SQ dépasse LBS sur des arêtes mixtes dans les 144 configurations.
   Ce n'est pas une preuve que c'est le même défaut que sur le maillage masculin (aucune comparaison quantitative faite).
2. **À histogramme identique, la répartition spatiale change fortement le résultat** (excédent max 0,20 à 0,48). La
   question « histogramme ou distribution spatiale » reçoit donc une réponse : la distribution spatiale compte.
3. **L'histogramme seul** (masculin contre féminin) produit un écart faible (0,357 contre 0,386).
4. **La triangulation** a un effet faible sur l'excédent (0,379 contre 0,364).
5. **L'orientation des cuisses** a un effet non monotone : la paire 120/−60 a la plus faible part régressée (0,029)
   mais un excédent comparable (0,40).
6. **Propriété « pas de retournement supplémentaire »** : violée dans 3 configurations sur 144 (jusqu'à +3 retournements
   SQ par rapport à LBS, toutes avec les angles 120/−60 et arrangement lisse). Ce résultat est négatif et doit être
   consigné comme tel.
7. Sur les arêtes mixtes des patchs, la norme médiane de G dépasse celle de `Mv d` (rapport médian 1,65). Cela signifie
   que, dans ces cas, G n'est pas un petit terme correctif.

## 5. Limites (à lire avant toute conclusion)

- **Métrique** : le rapport de longueurs par arête est dominé par les arêtes très courtes (le maillage non uniforme
  en contient). L'excédent max est donc sensible à ces arêtes, et l'effet « arêtes non uniformes » est en partie un
  artefact de métrique. La part régressée est plus stable. À refaire avec une métrique robuste (par exemple médiane
  pondérée par la longueur) avant tout chiffre cité.
- **Identification des triangles réels responsables** : non faite dans cette étape. Elle exige de rejouer le pipeline
  réel sur le maillage masculin, arête par arête. Aucune comparaison quantitative (longueur, courbure, poids, G) avec
  le maillage réel n'est donc établie ici.
- **Causalité** : aucune intervention sur G n'a été testée (ce qui est volontaire, voir la consigne). Les différences
  entre niveaux sont des observations dans un plan, pas des causes démontrées.
- **Propagation** : la violation de la propriété « poids purs » montre que les effets se propagent au-delà de
  l'interface. Ce n'est pas encore quantifié par rapport à la régression.

## 6. Jeu de poses de validation indépendant (non exécuté)

Candidats : hanche G 45°, 135°, 150° ; hanche D 45° ; genou G 45°, 120°.
Vérification : l'ensemble des poses réelles et génératives utilisées pour le balayage de λ
(`docs/rapports/skinning/intermediaire_hanche_masc/lambda_morphologies.json`) contient hanche G 75°, 105°, 120°
(génératives) et les poses réelles listées au même endroit. Aucun des candidats n'y figure. Ces candidats n'ont pas
été utilisés pour la conception de cette étape. Ils restent à conserver inutilisés.

## 7. Ce qui est démontré, ce qui reste hypothétique

Démontré : identité exacte de G ; dépendance du premier ordre aux gradients de poids ; covariance et invariance
globales ; propriétés de repos, rigide, translation et rotation sur le cas témoin ; reproduction qualitative de
SQ > LBS sur des arêtes mixtes dans des patchs synthétiques ; effet de la répartition spatiale à histogramme fixé.

Hypothétique : que ce mécanisme soit exactement celui du défaut masculin réel ; le rôle causal de G ; la magnitude
réelle de la régression comparée au maillage masculin.

Non démontré : une formulation corrigée. Aucune nouvelle méthode n'est validée ni intégrée.

## Correction (voir docs/rapports/skinning/defaut_reel/RAPPORT_defaut_reel.md, phase 3B)

Le compte « 3 configurations sur 144 avec retournements supplémentaires » comparait les totaux de retournements SQ et LBS.
Le compte correct, triangle par triangle (SQ retourné et LBS non retourné), donne 31 configurations sur 144, pour 769
triangles au total. Ce tableau de la section 4, point 6, est donc remplacé par ce compte corrigé.

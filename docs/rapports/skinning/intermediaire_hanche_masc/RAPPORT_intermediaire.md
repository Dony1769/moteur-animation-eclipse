# Reproduction intermédiaire du défaut de l'entrejambe (sur maillage complet) et étude de λ sur trois morphologies

Objet : séparer les mécanismes de SQ sur le modèle réel, tester les interactions poids / rotations, décomposer
l'énergie du solveur, et évaluer λ sur trois morphologies avec des poses réelles indépendantes. Aucun critère modifié,
LBS et les méthodes de référence conservés, **aucune méthode sélectionnée**.

Fichiers : `engine/validation/skinning/investigation_intermediaire.py` (blocs 1 à 4),
`engine/validation/skinning/investigation_lambda_morphos.py` (bloc 5).
Sorties : `resultats_intermediaire.json`, `lambda_morphologies.json`.

Note méthodologique : toutes les mesures portent sur le **maillage complet** (10 582 sommets). Aucun patch isolé
n'est utilisé comme équivalent, parce que SQ est un système global : un patch changerait les conditions aux limites.
Les « zones » ne sont que des sous-ensembles de mesure.

## Réponses

**1. La compression par moyenne arithmétique contribue-t-elle au défaut masculin ?** Pas de façon mesurable sur le
maximum. Entre la moyenne arithmétique (B) et la polaire (C) : maximum global 2,590 contre 2,592 ; p99 zone défauts
2,589 contre 2,589 ; aire minimale des triangles de la zone défauts 0,238 contre 0,251. La compression existe, mais la
supprimer ne change pas le défaut.

**2. La propagation globale contribue-t-elle à son amplification ?** Pas sur les sommets à poids pur dans la
configuration de référence. Le déplacement médian des sommets purs est de 5 × 10⁻⁶ h, et seuls 39 sommets purs sur
9 462 ont un résidu non nul. L'amplification se produit dans les zones à poids mixte (déplacement médian 0,32 h sur les
sommets mixtes, 0,34 h aux interfaces). La propagation vers les sommets purs, mise en évidence sur synthétique, n'est
donc pas le mécanisme actif sur le modèle réel à poids d'origine.

**3. Ces deux phénomènes interagissent-ils ?** Non démontré. Sur les 69 arêtes défectueuses, le terme de rotation
(écart entre la cible et le repère rigide) corrèle à −0,01 avec l'amplification, et le terme de gradient de poids à
−0,26. Une régression exploratoire (R² = 0,08) ne donne pas de structure claire. À géométrie et poids fixes, faire
varier seulement l'angle des cuisses ne produit pas d'effet monotone (écart 0° : +0,004 ; 60° : −0,013 ;
120° : +0,040 en médiane). Les seules classes qui se distinguent sont des partitions observationnelles : les arêtes
« mixte équilibré / mixte équilibré » (n = 42) ont une amplification médiane de +0,063, contre +0,011 pour les arêtes
asymétriques (n = 270). Ce n'est pas une causalité.

**4. Quel facteur explique les différences entre masculin, féminin et Maria ?** Non identifié. Ce qui est exclu :
- le squelette (identique pour masculin et féminin) ;
- la valeur du LBS à l'entrejambe (2,47 masculin, 2,53 féminin) : mêmes niveaux, effets opposés ;
- la magnitude moyenne des gradients de poids (médianes 0,035 et 0,043 sur les arêtes mixtes).
Ce qui est observé : le masculin a plus de sommets à deux cuisses (221 contre 171) et d'arêtes mixtes (393 contre 300).
Maria a un maillage beaucoup plus grossier (arêtes médianes 2 cm contre 0,8 cm) et seulement 19 sommets à deux cuisses :
la comparaison est confondue par la densité. Le LBS de Maria atteint 8,3, donc SQ y corrige un LBS fortement défectueux.
Aucune de ces différences ne suffit à établir un mécanisme.

**5. Quelle propriété mathématique une future correction devrait-elle respecter ?** Voir section 4 (formulation).
Propriétés candidates, à valider avant toute méthode :
- préserver exactement les mouvements rigides (si toutes les cibles sont cohérentes, la solution est le LBS) ;
- rester invariante aux translations et rotations globales de la pose ;
- tenir compte du terme de gradient de poids, sans lequel la cible ne peut pas reproduire le LBS dans les zones mixtes ;
- avoir une réponse bornée aux résidus, donc une portée contrôlée par λ, sur des maillages de densités différentes ;
- être évaluée sur les trois morphologies et sur des poses réelles non utilisées pour le réglage.

## 1. Zones et configurations (bloc 1 et 2)

Zones : 24 défauts ; 1er voisinage (50 sommets) ; 2e voisinage (82) ; voisinage à 6 arêtes (290).
Configurations, pose G 120° / D 0°, λ = 0,1 :

| Configuration | Max global | p99 global | Max défauts | p99 défauts | p99 voisins 2 | p99 à 6 arêtes | Retournements | Variation de volume |
|---|---|---|---|---|---|---|---|---|
| A. LBS | 2,471 | 1,185 | 2,471 | 2,437 | 2,289 | 2,066 | 4 | −0,0449 |
| B. SQ arithmétique | 2,590 | 1,132 | 2,590 | 2,589 | 2,521 | 2,028 | 1 | −0,0687 |
| C. SQ polaire | 2,592 | 1,132 | 2,592 | 2,589 | 2,521 | 2,035 | 1 | −0,0686 |
| D. = C, propagation mesurée séparément | 2,592 | 1,132 | 2,592 | 2,589 | 2,521 | 2,035 | 1 | −0,0686 |

Lecture : SQ dégrade le maximum et le p99 près des défauts et jusqu'à 2 arêtes, mais il réduit le p99 à 6 arêtes.
Le p99 des défauts passe de 2,44 à 2,59 : l'amplification touche une population d'arêtes, pas un seul sommet.
Aire minimale des triangles (SQ) : 0,24–0,25 dans la zone défauts, contre 0,08 pour LBS : SQ réduit la compression
locale par rapport au LBS. Le volume est une variation relative globale : il n'est pas mesuré localement.

Propagation (configuration D, médiane en h) : sommets purs 5 × 10⁻⁶ ; sommets mixtes 0,32 ; interfaces 0,34.

## 2. Interaction poids / rotations (bloc 3)

Géométrie et poids fixes ; seuls les angles des deux cuisses varient (G ∈ {60°, 120°}, D ∈ {0°, +60°, −60°}).

| Angle relatif entre cuisses | Amplification médiane (arith.) | Arêtes |
|---|---|---|
| 0° | +0,004 | 138 |
| 60° | −0,013 | 138 |
| 120° | +0,040 | 138 |

Par classe (partition observationnelle, pas d'intervention) :

| Classe d'arête | Amplification médiane | n |
|---|---|---|
| mixte équilibré / mixte équilibré | +0,063 | 42 |
| mixte asymétrique / mixte asymétrique | +0,011 | 270 |
| mixte asymétrique / mixte équilibré | −0,009 | 102 |

Décomposition exacte d'arête (bloc 4), indépendante de l'origine :
`lbs_a − lbs_c = Mv_a·d + G`, avec `G = Σ_k (w_ak − w_ck)·T_k·r_c` (terme de gradient de poids).
Vérification numérique de l'identité : 1,7 × 10⁻⁷ m.

| Terme (médiane, en longueur d'arête) | Valeur | Corrélation avec l'amplification |
|---|---|---|
| Gradient de poids G | 0,60 | −0,26 |
| Rotation (Mv_a − R_ab)·d | 0,33 | −0,01 |

Conclusion : l'amplification d'une arête n'est pas prédite par la taille locale de son résidu. Ce résultat exclut une
explication locale simple et renforce l'hypothèse d'un effet global du solveur.

## 3. Décomposition de la formulation (bloc 4)

Énergie minimisée par SQ : `E(p) = Σ_arêtes |p_a − p_c − R_ab·d_ac|² + λ·Σ_i |p_i − p_LBS,i|²`.

- **Terme de rotation** : `R_ab·d` (cible d'arête, moyenne de rotations, ici en polaire).
- **Terme d'ancrage** : `λ·|p − p_LBS|²`, seul ancrage du système. Sans lui, le système est singulier.
- **Contribution des voisins** : `M = L + λI`, où L est le Laplacien de graphe. M n'a pas de condition de bord fixe.
- **Résidu** : `g_i = Σ_j r_ij`, somme des résidus d'arêtes incidentes (`r_ij = R_ij·d − (p_LBS,i − p_LBS,j)`).
- **Solution** : `p_SQ − p_LBS = M⁻¹·g`. Vérification : écart 1,4 × 10⁻¹⁴ m.

Propriétés vérifiées :
- somme des lignes de M égale à λ, pas de condition de bord cachée ;
- centre de masse conservé (déplacement moyen 10⁻¹⁵ m, en synthétique) ;
- spectre du Laplacien sur le maillage réel : plus petite valeur 10⁻⁸ (mode constant), puis 2,9 × 10⁻⁴, 3,5 × 10⁻⁴,
  6,2 × 10⁻⁴, 7,0 × 10⁻⁴, 2,6 × 10⁻³ : les modes lisses sont peu amortis, seul λ les ancre.

Réponse à la question « un sommet pur peut-il être déplacé ? » : oui uniquement si `g_i ≠ 0`, c'est-à-dire si une de ses
arêtes incidentes a un résidu. Sur le maillage réel, 9 462 sommets purs ont `g ≈ 10⁻¹⁷` ; 39 ont un résidu, situés
au voisinage des interfaces. La formulation préserve donc les régions pures, sauf à leur contact direct avec une
interface. La continuité aux articulations est assurée par construction (solution continue), mais elle se fait au
prix d'une déviation des régions pures voisines. Le système n'impose donc pas la rigidité des régions pures : c'est une
propriété de la formulation, pas une erreur d'implémentation.

## 4. Étude de λ sur trois morphologies, poses réelles indépendantes (bloc 5)

Poses : 3 génératives (hanche G 75/105/120°) et 26 réelles par morphologie (toutes les poses réelles, sauf les deux
références de signe L_flex90 et R_flex90). Aucun λ n'est choisi. Méthode étudiée : SQ à moyenne arithmétique (configuration
actuelle). Vérification du LBS contre le contrôle réel : 6 × 10⁻⁷ m (masculin, féminin), 3 × 10⁻⁷ m (Maria).

Poses régressées (max SQ > max LBS), sur 29 poses par morphologie :

| Morphologie | λ = 0,01 | λ = 0,1 | λ = 1,0 | Pire régression à λ = 0,1 |
|---|---|---|---|---|
| Masculin | 2 | 11 | 15 | +0,128 (R_flex60) |
| Féminin | 0 | 0 | 0 | aucune (gain de −0,070 au pire) |
| Maria | 0 | 0 | 0 | aucune (gain de −0,083 au pire) |

Genou : aucune pose de genou seul n'est régressée à λ = 0,1 (les quatre régressions du masculin sont des combinaisons
avec flexion de hanche). Aucune pose ne présente de retournement supplémentaire par rapport au LBS.

Exemple de hanche G 120° (poses réelles) :

| Morphologie | LBS max | SQ λ = 0,01 | SQ λ = 0,1 | SQ λ = 1,0 |
|---|---|---|---|---|
| Masculin | 2,471 | 2,402 | 2,590 | 2,615 |
| Féminin | 2,525 | 2,008 | 2,258 | 2,442 |
| Maria | 8,300 | 1,643 | 2,036 | 3,381 |

Points d'attention, sans jugement sur la qualité réelle :
- À λ = 0,1, le volume de Maria passe de −3,0 % (LBS) à +2,1 % (SQ) : le signe change. Le volume de référence n'est pas
  connu, donc cette variation ne peut pas être jugée.
- La réduction du maximum chez Maria est mesurée contre un LBS déjà très défectueux (8,3). Elle ne prouve pas une qualité
  anatomique.

## 5. Ce qui reste ouvert

- Le facteur qui distingue le masculin (aggravé) du féminin (amélioré) n'est pas identifié. Une piste à tester : la
  répartition exacte des sommets à deux cuisses et leur ordre dans le maillage. Elle n'est pas démontrée.
- Patch isolé : non réalisé. Il faudrait démontrer qu'il reproduit le maillage complet avec les mêmes conditions aux limites.
- Géométrie synthétique à poids mixtes et angle réel : non réalisée à ce stade.
- Validation sur morphologie inconnue et pose hors protocole : non réalisée. Aucun candidat n'est proposé.

## 6. Décision

Le défaut masculin n'est pas expliqué par la compression arithmétique (négligeable sur le maximum). La propagation
vers les sommets purs n'est pas le mécanisme actif à poids d'origine. Les deux phénomènes n'ont pas d'interaction
démontrée. L'amplification est un effet global de la formulation, qu'aucune mesure locale ne prédit. Le facteur qui
distingue les morphologies reste à identifier. La prochaine étape consiste à tester une propriété précise (terme de
gradient dans la cible, invariance, portée contrôlée par λ) sur les trois morphologies et des poses réelles non
utilisées pour le réglage, avant toute nouvelle méthode.

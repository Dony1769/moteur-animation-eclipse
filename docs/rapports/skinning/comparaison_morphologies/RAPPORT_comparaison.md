# Comparaison rigoureuse des trois morphologies (masculin, féminin, Maria) — protocole identique

Scripts : `engine/validation/skinning/investigation_comparaison.py` (phases 1 à 3, `comparaison.json`) et
`engine/validation/skinning/investigation_retournements.py` (phase 4, `retournements.json`).
Statut : **diagnostic**. Aucune méthode validée, aucune intégration. LBS, DQS, Bone Heat inchangés.
Poses de validation candidates (hanche G 45/135/150, hanche D 45, genou G 45/120) : non utilisées.

## 0. Protocole

- 29 poses identiques pour les trois morphologies (26 réelles + 3 génératives hanche G 75/105/120), par nom.
  Les génératives utilisent la même convention de signe, calculée sur le squelette de chaque morphologie.
- Pipeline d'origine (`DEC.pipeline`, `ARAP.solve_fixe`, λ = 0,1, moyenne arithmétique). Vérification : le chemin
  dense utilisé pour les interventions reproduit le pipeline à 1 × 10⁻¹⁵ m pour les trois morphologies.
- **Correction de protocole** : les poids féminins ne somment pas à 1 (0,878 à 1,0) ; le pipeline les normalise
  (`methodes._valides`). Le premier passage ne normalisait pas et produisait un écart de 0,28 m (erreur 205).
  Toutes les données ci-dessous sont normalisées.
- Résolutions : masculin et féminin, 10 582 sommets, 21 160 triangles, 19 os. Maria, 8 094 sommets, 14 566 triangles,
  65 os. Métriques normalisées par la distance entre centres de hanche : 0,220 m (HBM) et 0,194 m (Maria).
- Arêtes « ≥ 5 mm » pour les rapports d'étirement ; régression = SQ − LBS > 0,05 sur le rapport de longueurs.

## 1. Phase 1 — Métriques agrégées (moyenne sur les 29 poses)

| Métrique | Masculin | Féminin | Maria |
|---|---|---|---|
| Sommets à poids purs / mixtes | 0,286 / 0,714 | 0,143 / 0,857 | 0,613 / 0,387 |
| Gradient L1 médian, arêtes mixtes (/m) | 2,23 | 2,78 | 6,64 |
| Part d'arêtes régressées (moy. ; max pose) | 0,50 % ; 1,23 % | 0,51 % ; 1,25 % | 0,50 % ; 1,10 % |
| Différence SQ − LBS, p50 / p90 / p99 | 0,000 / 0,0003 / 0,0268 | 0,000 / 0,0003 / 0,0267 | 0,000 / 0,000 / 0,0166 |
| Étirement SQ p99 / LBS p99 | 1,075 / 1,113 | 1,073 / 1,110 | 1,011 / 1,013 |
| Déplacement p99 (m) ; normalisé par hanche | 0,0099 ; 0,045 | 0,0096 ; 0,043 | 0,0126 ; 0,065 |
| Retournements LBS / SQ (total 29 poses) | 131 / 3 | 186 / 0 | 300 / 71 |
| **Retournements nouveaux SQ** (poses concernées) | **0 (0)** | **0 (0)** | **32 (11)** |
| Surface SQ / LBS, p99 | 1,062 / 1,099 | 1,058 / 1,083 | 1,014 / 1,034 |
| Variation relative de volume LBS / SQ | −0,015 / −0,025 | −0,018 / −0,030 | −0,007 / +0,010 |
| Terme rigide / longueur, arêtes mixtes, p50 | 1,00 | 1,00 | 1,00 |
| Propagation vers poids purs, max à 0 / 1 / 2 anneaux (m) | 0,0086 / 0,0056 / 0,0001 | 0,0143 / 0,0105 / 0,0078 | 0,0445 / 0,0234 / 0,0053 |

Lecture (ne pas confondre maximum et qualité globale) :
- Sur le **maximum**, SQ est inférieur à LBS en moyenne pour les trois morphologies. Le masculin a en revanche des poses
  où le maximum SQ dépasse LBS (λ = 0,1 : 11 poses, voir `lambda_morphologies.json`) ; féminin et Maria n'en ont aucune
  avec ce critère.
- Sur la **distribution par arête**, le masculin et le féminin sont presque identiques (p99 de la différence : 0,0268
  contre 0,0267 ; part régressée 0,50 % contre 0,51 %). La différence visible sur le maximum n'apparaît donc pas dans la
  distribution.
- La part régressée moyenne est la même pour les trois (≈ 0,5 %) ; Maria a un p99 de différence plus faible (0,0166), mais la **pire** propagation vers les poids purs (0,045 m à
  l'anneau 0, contre 0,009 masculin et 0,014 féminin) et les seuls retournements nouveaux.
- Le volume diminue davantage avec SQ qu'avec LBS pour le masculin et le féminin (de 0,010 à 0,012 de plus en relatif),
  alors qu'il augmente avec SQ pour Maria.

## 2. Phase 2 — Régions anatomiques (coordonnées normalisées par les centres de hanche)

Régions : entrejambe (|x − x_milieu| < 0,35 d, z entre −0,8 d et +0,1 d sous le milieu des hanches), hanche G/D
(centre à moins de 0,5 d), genou G/D (centre de genou à moins de 0,5 d), bassin (au-dessus de +0,1 d), cuisse G/D
(le reste latéral). d = distance entre centres de hanche. Arête attribuée à la région commune des deux extrémités,
sinon « frontière ». Pools sur les 29 poses.

| Région | Masc. n / améliore / aggrave / aggravées mixtes-pures | Fém. n / améliore / aggrave / mixtes-pures | Maria n / améliore / aggrave / mixtes-pures |
|---|---|---|---|
| Entrejambe | 3 741 / 28 % / **12,4 %** / 463-0 | 4 002 / 30 % / **8,7 %** / 347-0 | 11 745 / 20 % / **10,2 %** / 1 169-25 |
| Hanche G | 2 755 / 33 % / 3,6 % / 100-0 | 2 813 / 32 % / 3,3 % / 93-0 | 1 827 / 17 % / **9,5 %** / 168-6 |
| Hanche D | 2 755 / 31 % / 2,5 % / 70-0 | 2 871 / 29 % / 2,4 % / 69-0 | 1 827 / 16 % / **6,8 %** / 122-3 |
| Genou G | 4 553 / 4 % / 4,2 % / 189-0 | 5 684 / 4 % / 3,9 % / 221-3 | 7 917 / 3 % / 1,9 % / 147-0 |
| Genou D | 4 611 / 4 % / 4,2 % / 194-0 | 5 742 / 4 % / 3,8 % / 218-2 | 7 917 / 3 % / 1,9 % / 147-0 |
| Cuisse G | 105 125 / 1,4 % / 0,1 % / 79-6 | 97 701 / 1,1 % / 0,1 % / **37-87** | 27 521 / 3,2 % / 1,1 % / 236-53 |
| Cuisse D | 105 038 / 1,4 % / 0,0 % / 47-3 | 97 498 / 1,0 % / 0,1 % / **15-46** | 27 521 / 2,4 % / 0,8 % / 183-33 |
| Bassin | 229 187 / 1,6 % / 0,4 % / 911-0 | 219 733 / 1,6 % / 0,4 % / 785-0 | 481 429 / 0 % / 0 % / 20-0 |

Constats par région :
- **Entrejambe** : SQ améliore 20 à 30 % des arêtes et en aggrave 9 à 12 %. Toutes les aggravations masculines et
  féminines sont sur arêtes mixtes ; chez Maria, 25 sont sur arêtes pures.
- **Hanches** : masculin et féminin améliorent 30 à 33 % et aggravent 2 à 4 %. Maria améliore moins (16–17 %) et aggrave
  davantage (7–10 %). Une amélioration « globale » du féminin sur les hanches n'est donc pas une propriété de Maria.
- **Genoux** : aggravation 4 % (HBM, féminin) contre 2 % (Maria), amélioration 3–4 %.
- **Cuisses** : le féminin aggrave surtout des arêtes **pures** (133 contre 52 mixtes) : c'est une propagation. Le
  masculin aggrave des arêtes **mixtes** (126 contre 9). Maria est mixte-dominant sur les cuisses, avec aussi des
  arêtes pures.

Question centrale (mixtes ou propagation) : chez le masculin, les régressions de la zone sont **mixtes** ; chez le
féminin, elles sont **en partie propagées** vers les cuisses pures ; chez Maria, elles sont mixtes dans la zone hanche
et propagées sur les cuisses. Les trois valeurs sont cohérentes avec la phase 1, mais l'attribution causale reste à
établir (phase 3).

## 3. Phase 3 — Hypothèses testées (interventions sur le même maillage ; poses SUB = L flex120, génératives 120, combo flex120 genou90)

| Hypothèse | Test | Résultat (part régressée, masc. / fém. / Maria) | Verdict |
|---|---|---|---|
| H1 Répartition spatiale des poids | permutation aléatoire des poids mixtes (5 graines) ; réarrangement trié | base 0,011 / 0,011 / 0,007 → permuté 0,28 / 0,33 / 0,12 ; trié 0,30 / 0,34 / 0,11 | **Démontré** : la disposition spatiale change fortement la régression, à histogramme constant. Limite : la permutation détruit toute la structure du maillage ; elle ne reproduit pas la disposition réelle. |
| H2 Courbure / géométrie locale | dilatation locale de la zone entrejambe ×0,8 / ×1 / ×1,25 | 0,0098 → 0,0110 (masc.) ; 0,0109 → 0,0111 (fém.) ; 0,0073 → 0,0075 (Maria) | **Faible effet** de la taille locale. Courbure : non testée isolément. |
| H3 Taille et orientation des triangles | même intervention (taille seulement) ; orientation non testée (pas de remaillage) | voir H2 | **Partiellement testée** : effet faible de la taille ; orientation non vérifiée. |
| H4 Position des articulations | pivot de hanche G décalé de ±1 cm (x et z) | ≈ inchangé dans les trois morphologies (0,0106–0,0111) | **Réfutée** comme cause majeure à cette échelle. |
| H5 Conditions aux limites / propagation | λ ∈ {0,01 ; 0,1 ; 1} | λ décroissant : régression ↑ (masc. 0,0138 ; fém. 0,0144 ; Maria 0,0068) ; propagation à l'anneau 0 : masc. 0,028 / 0,014 / 0,003 ; fém. 0,038 / 0,024 / 0,008 ; Maria 0,086 / 0,086 / 0,055 | **Effet démontré** (λ et propagation). **Non retenue comme explication de la différence** : Maria propage le plus et régresse le moins par max. |
| H6 Volume | corrélation entre Δvolume (SQ − LBS) et part régressée, par pose | masc. −0,93 ; fém. −0,87 ; Maria +0,79 | **Corrélation seulement** (29 poses non indépendantes, aucun volume local). Non démontré comme cause. |

Ces tests n'isolent pas, à eux seuls, la cause de la différence entre morphologies. Aucune variable testée ne fait
passer Maria du régime « peu de régressions » à celui du masculin, ni l'inverse.

## 4. Phase 4 — Retournements synthétiques

Comptage : un triangle est « nouveau retournement » si sa normale SQ est opposée à la référence (normale de repos
tournée par la polaire de la moyenne des Mv de ses sommets), et que LBS n'est pas retourné sur le même triangle.
Aucun seuil n'est modifié.

**Correction maintenue** : 31 configurations sur 144 ; 769 triangles au total.

Résultat décisif : **les 31 configurations sont toutes à l'angle de cuisses (120°, −60°)**, soit 180° entre les
rotations des deux cuisses. Sur les 48 cas (120°, 0°) et les 48 cas (90°, 0°), aucun retournement nouveau.

| Facteur changé seul (sur les 31 échecs) | Échecs disparaissant | Total de retournements nouveaux après |
|---|---|---|
| Angles 90°/0° | 31 / 31 | 0 |
| Arrangement lisse | 13 / 31 | 80 |
| Triangulation inverse | 9 / 31 | 585 |
| Géométrie inverse | 1 / 31 | 766 |
| Histogramme inverse | 7 / 31 | 738 |
| λ = 1 | 9 / 31 | 496 |
| λ = 0,01 | 0 / 31 | 1 261 |
| (référence) | — | 769 |

Mécanisme observé : pour les triangles concernés, la moyenne Mv a une valeur singulière minimale **médiane de 0,17**
(contre 0,5 pour l'ensemble des triangles, et 0,03 minimum). Le repère de référence est donc presque dégénéré : deux
rotations opposées se compensent dans le mélange de poids. Dans cette zone, le comptage dépend fortement de la
référence. Le compactage réel est aussi visible (aire SQ ≈ 0,55 × aire repos). **Ce qui est démontré** : les retournements
nouveaux dépendent de l'angle relatif de 180° ; ils disparaissent avec un autre angle, et ne disparaissent ni avec la
triangulation ni avec la géométrie seules. **Ce qui n'est pas démontré** : que ces triangles soient réellement repliés
au sens physique, car la référence y est mal définie.

Contrôles d'orientation (démontrés) :
- Pose rigide commune : 0 retournement (SQ = LBS = pose rigide) ;
- Rotation rigide de 170° de tout le maillage : 0 retournement ;
- Rotation globale aléatoire appliquée à l'ensemble : 28 retournements avant et 28 après (comptage invariant).

**Maria, réel** : 32 retournements nouveaux sur 11 poses, de 1 à 4 par pose (poses flex120 et combo). Leur
référence est bien conditionnée (σ_min ≈ 0,64–0,74, médiane de tous les triangles = 1,0). Ils persistent avec λ = 0,01
et λ = 1, et avec la cible polaire : **ni λ ni la moyenne arithmétique n'expliquent ces retournements** (démontré pour
ces deux facteurs). Leur origine (géométrie locale, poids, triangulation) n'est pas établie : analyse triangle par
triangle non poussée au-delà de l'identification.

Masculin et féminin, réel : **0 retournement nouveau** sur les 29 poses.

## 5. Diagnostic comparatif (phase 5)

Catégories : **D** démontré ; **S** fortement soutenu par les expériences ; **H** hypothèse non vérifiée ;
**R** réfuté.

| Résultat | Par morphologie | Cat. |
|---|---|---|
| Sur le maximum, SQ est meilleur en moyenne pour les trois morphologies | masc., fém., Maria | D |
| Maximum SQ > LBS dans certaines poses | masc. (11 poses) ; fém., Maria : aucune | D (critère du maximum) |
| Distribution par arête identique masculin / féminin | p99 0,0268 / 0,0267 | D |
| Le « gain » féminin/Maria n'est pas une amélioration de la distribution | Maria : aggrave plus les hanches (7–10 %) | D |
| Entrejambe : aggravations mixtes (masc., fém.) | 463 / 347 mixtes | D |
| Cuisses féminines : aggravations majoritairement propagées | 133 pures / 52 mixtes | D |
| Répartition spatiale des poids change fortement la régression | toutes morphologies | D |
| Histogramme seul : effet modéré masc./fém. | 0,357 / 0,386 (patchs synthétiques, antérieur) | S |
| Retournements synthétiques dépendent de l'angle 180° | 31/31 | S |
| Référence de retournement mal conditionnée pour ces cas | σ médiane 0,17 | S |
| λ gouverne la régression et la propagation | toutes | D |
| Propagation plus forte chez Maria, sans régression maximale | Maria | D (effet) / R (explication de la différence) |
| Position des articulations sans effet à ±1 cm | toutes | R (cause majeure) |
| Taille locale : effet faible | toutes | S |
| Volume : SQ perd davantage de volume (masc., fém.) et en gagne chez Maria | toutes | D (mesure globale) |
| Corrélation volume / régression | corrélation seule | H |
| Retournements nouveaux réels chez Maria, indépendants de λ et de la moyenne | Maria | D (indépendance) / H (origine) |
| Retournements réels absents chez masc. et fém. | masc., fém. | D |

**Réponse à la question** « pourquoi SQ améliore certaines régions du féminin et de Maria, mais aggrave certaines
régions du masculin ? » : **non établie**. Ce qui est établi : la différence visible sur le maximum ne se retrouve pas
dans la distribution par arête ; l'entrejambe masculin et féminin ont des aggravations de même ordre, sur arêtes
mixtes ; Maria aggrave davantage les hanches ; le volume est perdu par SQ chez le masculin et le féminin, et gagné
chez Maria. Ces faits décrivent les morphologies sans en fournir la cause.

**Conditions avant toute nouvelle formulation** : (1) expliquer pourquoi Maria a 32 retournements réels sans
dégénérescence de référence ; (2) identifier, pour chaque morphologie, la part de l'aggravation qui est mixte contre
propagée ; (3) remplacer le critère du maximum par la distribution et la proportion par région, pour éviter de valider
une variante sur un maximum seul.

## 6. Ce qui n'est pas fait

- Analyse triangle par triangle de Maria pour expliquer ses retournements réels : seule l'identification est faite.
- Test de la courbure isolée et de l'orientation des triangles (le remaillage n'a pas été fait).
- Corrélation volume-régression locale : impossible proprement sans volume local bien défini (origine).
- Les interventions H1–H5 utilisent des poses de développement (λ) : ce ne sont pas des validations.

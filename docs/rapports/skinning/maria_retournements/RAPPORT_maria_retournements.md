# Retournements SQ nouveaux de Maria : diagnostic, solveur, régions, volume, mécanisme

Scripts : `engine/validation/skinning/investigation_maria_retournements.py` (phases 1 et 2),
`investigation_regionale.py` (phases 3 et 4), `investigation_maria_mecanisme.py` (phase 1 complément et phase 5).
Sorties : `maria_retournements.json`, `mecanisme_retournements.json`, `../regionale/regionale.json`,
`../regionale/tableau_regional.md`. Convention : retournement = normale déformée opposée à la normale de référence
`polaire(moyenne Mv)` appliquée à la normale de repos. Catégorie 3 = retourné avec SQ, non retourné avec LBS.
Les six poses indépendantes ne sont pas utilisées. Aucun seuil n'est modifié et SQ n'est pas changé.

## 1. Ce qui est démontré

**Décompte corrigé.** Les « 32 retournements » sont **32 occurrences (triangle × pose)**. Elles concernent
**7 triangles distincts** répartis sur 11 poses. Ce ne sont pas 32 triangles. Les 7 triangles sont tous dans la
région « entrejambe ». Les 32 occurrences sont toutes de catégorie 3 (`verification_categorie3` : 32/32).

**Effet global de SQ sur les retournements (Maria, 29 poses).** LBS : 300 occurrences ; SQ : 71. SQ supprime
261 retournements LBS, en garde 39 communs aux deux méthodes, et en crée 32 nouveaux (catégorie 3).

**Classement par triangle.** Le produit scalaire normale SQ / normale LBS est négatif pour 14 occurrences. Pour ces
14, le retournement est relatif à la forme LBS. Pour les 18 autres, SQ est retourné seulement par rapport au repère
de référence, alors que sa forme reste orientée comme LBS. Le détail par triangle est dans
`mecanisme_retournements.json`, clé `triangles`.

**Le solveur n'est pas la cause.** Résolution LU, gradient conjugué (rtol 1e-13), LSQR et LU avec raffinement en
précision étendue donnent la même solution à moins de 9e-14 m près (par rapport à la solution d'origine), et les
mêmes compteurs de retournements à chaque pose. Conditionnement de M : λmin = 0,1, λmax = 20,26, cond = 202,6. La
topologie est saine : les arêtes issues des triangles coïncident avec A (22 604 arêtes), sans sommet dégénéré ni
indice hors bornes. Ce contrôle porte sur l'implémentation du système ; il ne couvre pas le choix de formulation.

**Régions (phase 3, extrait du tableau complet).** Voir `../regionale/tableau_regional.md`.
- Régression globale non pondérée : masculin 0,50 %, féminin 0,51 %, Maria 0,50 %. Pondérée par la longueur :
  1,06 %, 1,09 %, 0,76 %. Maria n'est donc pas plus régressé que les autres morphologies sur ce critère global.
- Amélioration : 2,5 % des arêtes pour masculin et féminin, 1,1 % pour Maria. Les améliorations sont donc moins
  fréquentes chez Maria.
- Entrejambe, arêtes régressées : 12,4 % (masculin), 8,7 % (féminin), 10,2 % (Maria). Le taux n'est pas propre à
  Maria.
- Entrejambe, percentile 99 de SQ−LBS : 0,23 (masculin), 0,19 (féminin), **0,39 (Maria)**. C'est la différence la
  plus nette : la queue de distribution est beaucoup plus lourde chez Maria dans cette région.
- Régression propagée (arêtes à poids purs à 1 à 3 anneaux d'une zone mixte) : 16 (masculin), **319 (féminin)**,
  131 (Maria). La propagation est donc plus marquée chez la féminine que chez Maria, contrairement à l'intuition.
- Régression sur arêtes à poids purs éloignées (> 3 anneaux) : 0 pour les trois morphologies.
- Déplacement de l'extrémité (p99 normalisé par la distance entre hanches) : 0,056 (masculin), 0,056 (féminin),
  0,071 (Maria). Chez Maria, le déplacement p99 de l'entrejambe est de 0,236 de la distance entre hanches, contre
  0,112 à 0,129 chez les deux autres.

**Volume (phase 4).**
- Masculin et féminin : surface fermée, orientation cohérente, une seule composante. Le volume signé est donc
  mesurable. Variation moyenne sur les 29 poses : masculin LBS −1,49 %, SQ −2,46 % ; féminin LBS −1,83 %,
  SQ −2,95 %. SQ réduit donc davantage le volume global que LBS. Ce résultat est global. Il ne prouve pas une
  conservation locale et ne dit rien sur les régions.
- Maria : 1 510 arêtes frontières, 73 composantes connexes. Le volume est **non fiable** et n'est pas interprété.
  Les orientations sont cohérentes, mais la surface n'est pas fermée.

**Les 7 triangles.** (4226, 4225, 4216), (4242, 4226, 4216), (4242, 4184, 4226), (4102, 4172, 4170),
(4145, 4135, 4144), (4161, 4145, 4103), (4161, 4135, 4145). Six d'entre eux ont un angle d'os dominant de 120° dans
au moins une pose. **Le triangle (4102, 4172, 4170) se retourne avec un angle dominant nul** (3 occurrences, poses
hanche gauche 120° et flexion 120° gauche) : la corrélation par angle n'explique donc pas tous les cas.

## 2. Corrélations (observations, pas mécanisme)

Comparaison des 32 occurrences aux triangles de l'entrejambe qui ne sont pas retournés par SQ, pendant les mêmes
poses (AUC de Mann-Whitney : 0,5 = aucune séparation, 1 = séparation parfaite).

| Caractéristique | AUC | Médiane retournés | Médiane non retournés |
|---|---:|---:|---:|
| Angle de rotation maximal des os dominants (°) | 0,90 | 105 | 0 |
| Valeur singulière minimale de Mv moyen (contraction) | 0,12 (inversé : 0,88) | 0,72 | 1,00 |
| Ratio d'aire LBS / repos | 0,34 (inversé : 0,66) | 0,64 | 1,00 |
| Mélange moyen des poids (1 − poids max) | 0,77 | 0,25 | 0,15 |
| Ratio d'aire SQ / repos | 0,42 | 0,88 | 1,00 |
| Rapport d'aspect du triangle au repos | 0,59 | 0,48 | 0,37 |
| Angle relatif entre os dominants | 0,46 | 0 | 0 |

Lecture prudente. Les triangles retournés sont ceux qui sont fortement déformés. La plupart des caractéristiques
ci-dessus sont donc des conséquences de la déformation, pas nécessairement des causes. Le contrôle est trop faible
pour séparer cause et effet. La forme du triangle au repos (rapport d'aspect, AUC 0,59) est à peine discriminante.

## 3. Test contrôlé : affectation dure des poids

On remplace, dans une pose donnée, les poids des 13 sommets concernés par leur os dominant (affectation dure). On
recompte les retournements nouveaux sur les mêmes triangles. Un contrôle applique la même opération à 13 sommets de
l'entrejambe choisis hors des triangles concernés.

- Total sur les 11 poses : base 32 ; après affectation dure des sommets concernés **38** ; après affectation dure
  du contrôle 31.
- L'affectation dure ne supprime pas les retournements et en augmente le nombre dans plusieurs poses.

Conclusion : retirer le mélange des poids sur ces sommets **ne suffit pas à faire disparaître** les retournements.
Le test ne démontre pas non plus que les poids en soient la cause, car il modifie aussi la géométrie résultante.
Ce test n'établit donc aucun mécanisme.

## 4. Ce qui reste hypothétique ou non testé

- Origine dans le repère de référence (polaire de Mv moyen) : la contraction (valeur singulière 0,72) est
  compatible avec une référence peu fiable, mais ce n'est pas démontré. Il faudrait un test où la référence est
  remplacée par une référence indépendante.
- Géométrie, courbure, taille des arêtes : non testées dans cette phase.
- Conditions aux limites (ancrage λ vers LBS) : non testées séparément, seul le paramètre λ l'a été en amont.
- Triangulation : faible corrélation seulement (AUC 0,59).
- Propagation : mesurée par classes de régression, sans expérience dédiée.
- Échantillon : 7 triangles distincts seulement. Toute généralisation est fragile.
- Symétrie : les régions genou gauche et droit de Maria ont des effectifs identiques. Cela peut être un artefact de
  l'échantillonnage des poses symétriques ; ce point n'a pas été vérifié.

## 5. Classification

| Affirmation | Statut |
|---|---|
| 32 occurrences = 7 triangles, tous catégorie 3, dans l'entrejambe | Démontré |
| SQ supprime 261 retournements LBS de Maria et en crée 32 | Démontré |
| Le solveur (précision, implémentation) ne cause pas les retournements | Démontré pour ce système |
| Le volume global de SQ diminue davantage que LBS (masculin et féminin) | Démontré (global seulement) |
| Le volume de Maria est mesurable | Réfuté (surface non fermée, 73 composantes) |
| Les retournements sont associés à une forte rotation d'os et à une contraction de Mv | Fortement soutenu (corrélation, confondue avec la déformation) |
| Retirer le mélange des poids supprime les retournements | Non confirmé : l'affectation dure ne les supprime pas (32 → 38) |
| La référence polaire est la cause des retournements | Hypothèse non vérifiée |
| Géométrie, courbure, arêtes, conditions aux limites expliquent le phénomène | Hypothèse non vérifiée (non testé) |
| Maria régresse plus que masculin et féminin sur le critère global | Réfuté (taux comparables ; c'est la queue de distribution et l'amélioration qui diffèrent) |

## 6. Limites

- Une seule formulation de SQ est testée. Les résultats ne disent rien sur d'autres formulations.
- Les seuils (régression 0,05, amélioration −0,02, arête ≥ 5 mm) sont ceux de la comparaison précédente, sans
  ajustement.
- Les six poses indépendantes ne sont pas utilisées ici.

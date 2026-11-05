# Étape 2 : correction procédurale par longueurs réelles (phase 4)

## Hypothèse testée
Des poids générés à partir des longueurs réelles des os (extraites à l'étape 1, aucune valeur par défaut) doivent
réduire les étirements de hanche et de genou, sans réglage par personnage. Un seul coefficient global ALPHA est choisi
dans {0,25 ; 0,5 ; 1,0} et appliqué aux trois morphologies.

Méthodes :
- **A. Remplacement** : w_k(v) = exp(−(d_k(v)/(α L_k))²), os dominants par sommet, 4 influences normalisées.
- **B. Bande articulaire** : W = (1 − β) W_réf + β W_proc, β = max_j exp(−(d(v, tête_j)/(α L_j))²). Loin des
  articulations, la référence Bone Heat est conservée.

Protocole : `comparer_v2.py` inchangé, mêmes poses (28), mêmes matrices, mêmes métriques, mêmes seuils. Code :
`engine/validation/skinning/poids_procedural.py`, `experience_poids_procedural.py` (`remplacement` ou `bande`).
Résultats bruts : `resume_remplacement.json`, `resume_bande.json`.

## Résultats (LBS ; DQS dans les fichiers JSON)

Maximum d'étirement pire cas / p99 moyen / retournements totaux. Référence entre parenthèses.

| Morphologie | Méthode | α | LBS max | LBS p99 | LBS retournements | DQS max | DQS p99 | DQS retournements |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Maria | référence | — | 8,30 | 1,006 | 288 | 10,00 | 1,015 | 314 |
| Maria | remplacement | 0,5 | 10,37 | 1,610 | 8441 | 10,19 | 1,701 | 10799 |
| Maria | bande | 0,25 | 6,55 | 1,167 | 194 | 8,23 | 1,195 | 211 |
| masculin | référence | — | 2,49 | 1,075 | 50 | 3,29 | 1,085 | 22 |
| masculin | remplacement | 0,5 | 8,38 | 1,427 | 438 | 10,05 | 1,482 | 489 |
| masculin | bande | 0,25 | 2,50 | 1,084 | 26 | 3,19 | 1,099 | 0 |
| féminin | référence | — | 2,53 | 1,065 | 77 | 3,32 | 1,071 | 36 |
| féminin | remplacement | 0,5 | 9,88 | 1,652 | 1192 | 12,26 | 1,731 | 1336 |
| féminin | bande | 0,25 | 2,52 | 1,090 | 44 | 3,31 | 1,105 | 0 |

Maximum de la zone hanche gauche (pire pose) : Maria LBS 8,30 → 6,55 (bande, α = 0,25) ; masculin 2,49 → 2,50 ;
féminin 2,53 → 2,52.

## Lecture
- **A (remplacement) : échec net.** Sur les trois morphologies et tous les α, le p99, les retournements et le résidu sont
  dégradés de 2 à 30 fois. Le noyau de distance ignore la topologie du maillage ; les poids Bone Heat la portent.
- **B (bande) : mitigé, non validé.** À α = 0,25 : les retournements baissent (DQS masculin et féminin : 0), le maximum
  de Maria baisse, mais le p99 augmente sur les trois morphologies (+0,01 à +0,04) et le maximum de hanche reste au-dessus de
  1,5 partout. À α ≥ 0,5, la dégradation est nette. Aucun gain sur une seule métrique n'est retenu.
- Conclusion : une correction de poids par distance seule ne suffit pas. La cause doit être cherchée dans la géométrie
  de la transition (étape 3 : formes correctives, étude de la contribution de pose).

## Coût CPU
Calcul des poids pour Maria : 0,1 s (une fois, hors de la boucle de pose). Comparaison v2 complète : environ 9 s par morphologie.

## Limites
- Un seul noyau testé (gaussien, 4 influences). D'autres noyaux (géodésiques sur le maillage, diffusion) ne sont pas testés.
- Les poids sont évalués sur le maillage de base (8094 à 10582 sommets), pas sur le maillage HR.
- Aucune vérification visuelle des captures : aucune affirmation visuelle n'est faite.

## Décision
Aucune variante n'est intégrée. Le système de référence reste inchangé.

# Rapport comparatif : LBS, DQS et hybrides sur la hanche et le genou (phase 4)

Personnage : corps HBM (GEO-body_male_realistic), armature Mixamo à 19 os, maillage de base 10 582 sommets
(10 590 polygones). Mètres monde. Toutes les méthodes reçoivent exactement les mêmes positions de repos, poids, matrices
d'os et topologie. Blender ne déforme que le contrôle.

**Statut : phase 4 NON validée.** Aucune méthode ne résout la hanche ni le genou. Les critères ont été fixés avant la
mesure et n'ont pas été modifiés.

## 1. Méthodes comparées

| Méthode | Principe | Source de la formule |
|---|---|---|
| LBS | somme_k w_k (R_k p + t_k) | Blender ARMATURE ; Puppeteer `animation/model.py` (LBS) |
| DQS | blend de quaternions duaux, hémisphère alignée sur l'os dominant, normalisation du dual | Kavan et al., ACM TOG 2008 (article ; implémentation écrite ici, pas copiée) |
| HYBRIDE_global | (1 − a) LBS + a DQS, a = 0,5 partout | règle fixée avant mesure |
| HYBRIDE_angle | a = min(1, angle relatif maximal entre os du sommet / 45°) | règle fixée avant mesure |

Contrôle : LBS reconstruit en numpy reproduit la déformation évaluée par Blender à **6,6e-7 m** près (28 poses).
Les quatre méthodes partagent la même fonction de mesure et le même repère rigide de référence (voir §5).

## 2. Résultats, maillage de base (mesures corrigées, entrée 147)

Colonnes : étirement max d'arête ; retournements de polygones ; variation de volume signé ; sommets aberrants
(sommet dont une arête dépasse 1,5 fois sa longueur au repos).

| Pose | Méthode | Étirement max | Retournements | Volume | Aberrants |
|---|---|---|---|---|---|
| flexion 60° | LBS | 1,655 | 0 | −1,10 % | 15 |
| | DQS | 1,781 | 0 | +0,68 % | 27 |
| flexion 90° | LBS | 2,105 | 0 | −2,70 % | 53 |
| | DQS | 2,472 | 0 | +0,99 % | 74 |
| flexion 120° | LBS | **2,471** | **4** | **−4,49 %** | 86 |
| | DQS | 3,288 | 1 | +1,27 % | 130 |
| | HYBRIDE_global | 2,876 | 1 | −1,89 % | 107 |
| genou 90° | LBS | 1,196 | 8 | −1,13 % | 0 |
| | DQS | 1,277 | 4 | −0,83 % | 0 |
| combo flex 120° + genou 90° | LBS | 2,471 | 12 | −5,62 % | 86 |
| | DQS | 3,288 | 5 | +0,44 % | 130 |
| combo flex 90° + abd 30° + rot ext 30° | LBS | 2,712 | 0 | −4,29 % | 52 |
| | DQS | 3,124 | 0 | −0,50 % | 92 |

Remarque : HYBRIDE_angle est identique à DQS sur ces poses. Le seuil de 45° est atteint par presque tous les sommets
multi-os (la part de sommets à angle non nul va de 3 % à 18 % selon la pose), donc la règle sature.

## 3. Lecture honnête

- **Volume** : DQS conserve mieux le volume en valeur absolue (à 120° : +1,3 % contre −4,5 % en LBS). Mais il le
  *gonfle* au lieu de le conserver : le signe change. Ce n'est pas une préservation, c'est une autre erreur.
- **Étirement de pointe** : DQS est **pire** que LBS (3,29 contre 2,47 à 120°, et p99 1,250 contre 1,185). Les arêtes
  les plus étirées ne sont pas de petites arêtes : elles font 11 à 27 mm au repos. L'étirement est réel.
- **Retournements** : très faibles avec toutes les méthodes après correction (4 à 12 polygones sur 10 590). DQS en
  retourne légèrement moins. Ce n'est pas une différence décisive.
- **Conclusion par mesure** : DQS n'est pas une amélioration globale. Il améliore le volume en valeur absolue et les
  retournements, et il dégrade l'étirement de pointe et le nombre de sommets aberrants. Je ne le déclare pas meilleur.

## 4. Localisation des défauts (attribution)

Fichier : `attribution_retournements_LBS.txt`, outil : `engine/validation/skinning/attribution_retournements.py`.

- Flexion 120° : les 4 polygones retournés sont à z 0,76–0,95 m (centre de la hanche vers 0,87 m), dominés par
  LeftUpLeg. Le sommet le plus étiré est dans la zone bassin-entrejambe.
- Genou 90° : les 8 polygones retournés sont à z 0,46–0,50 m, au pli sous le genou, dominés par LeftUpLeg et LeftLeg.
- Symétrie gauche-droite (flexion 120°) : étirement max 2,471 (L) contre 2,485 (R), écart 0,6 % ; retournements
  4 contre 5 ; volume −4,49 % contre −4,41 %. Symétrique à quelques pour cent près pour la flexion et le genou.
- **Asymétrie gauche-droite en abduction** : 1,41 (L) contre 1,90 (R) à 30°. Non expliquée, non corrigée.
- Influences dans la bande de hanche (z 0,6–1,15 m, 2 747 sommets) : Hips + Spine + les deux cuisses, ou
  Hips + LeftUpLeg + Spine + Spine1. La fuite entre cuisses gauche et droite est faible : 84 sommets, poids moyen 0,027.

## 5. Expériences de cause (une seule modification à la fois)

**a) Lissage des poids dans la bande de hanche, méthode inchangée** (`experience_poids_lissage.py`,
`experience_poids_lissage.json`). Hypothèse écrite avant mesure : une transition de poids trop brusque cause
l'étirement. **Réfutée** : l'étirement de pointe augmente légèrement (LBS 2,471 → 2,504 ; DQS 3,288 → 3,344), et le
volume se dégrade un peu. Le lissage ne doit pas être retenu.

**b) Repère rigide de référence pour les retournements** : la première mesure comparait la normale posée à la normale
de repos brute. Une rotation rigide de 120° fait changer de signe le produit scalaire sans aucune déformation : 828
« retournements » à 120° étaient des faux positifs (entrée 147). La métrique corrigée compare à la normale de repos
tournée par la rotation locale mélangée du sommet, identique pour toutes les méthodes. Test : `test_skinning.py` (5, 5b).

**c) Haute résolution (MULTIRES niveau 3)** : les poids sont transférés du sommet de base le plus proche. Le contrôle
montre une erreur médiane de 3e-8 m, mais 0,4 % des sommets à 120° ont une erreur supérieure à 1 cm (max 5,5 cm), et
2,6 % sont au-dessus de 1 mm. **Les chiffres haute résolution ne sont donc pas fiables au niveau du pourcent**, et
les retournements haute résolution (853 à 120° en LBS) ne sont pas interprétables. Une interpolation sur les 3 sommets
les plus proches réduit le max à 4,7 cm et ne suffit pas. Il faut transférer les poids depuis l'évaluation Blender
elle-même (Data Transfer sur le maillage appliqué). Non fait ici.

## 6. Ce qui reste (et ce qui n'est pas fait)

- Abduction et rotation (LBS, base) : abduction 30° donne un étirement max de **1,41 à gauche et 1,90 à droite** ;
  rotation externe 30° donne 1,37 (gauche) et 1,44 (droite). L'abduction est donc **asymétrique** : c'est un signal à
  traiter avant toute autre correction, et il n'est pas expliqué ici. Tableau complet dans `comparatif.json`.
- Intersections entre parties du corps : **non mesurées**. Le banc ne fait pas de test de collision.
- Correction locale des poids à la hanche et au genou : **non faite**. La piste la plus prometteuse n'est pas encore
  testée (position du centre de rotation de la hanche par rapport à la géométrie, puis correction par formes de pose).
- Architecture de sélection automatique de méthode par personnage et articulation : **non faite**.
- Autres morphologies : **non testées**. Un seul personnage (HBM) a été mesuré.

## 7. Captures

`captures_profil_hr.png` : vue de profil du maillage haute résolution, coloré par étirement par sommet, pour
LBS, DQS, HYBRIDE_global et HYBRIDE_angle, à 120° de hanche et à 90° de genou. Vérifiée visuellement : l'étirement se
concentre à l'entrejambe et au pli du genou, et les quatre méthodes donnent des images proches. Les captures
haute résolution ont l'erreur de transfert décrite au §5c.

## 8. Licences (vérifiées dans cette session, séparément)

| Ressource | Code | Poids / données / assets |
|---|---|---|
| Puppeteer (ByteDance Seed) | Apache 2.0 (`LICENSE` lu) ; LBS dans `animation/model.py` lu | non vérifiés ici |
| UniRig (VAST-AI-Research) | MIT (`LICENSE` lu) ; `src/model/unirig_skin.py` lu | non vérifiés ici |
| DQS | article Kavan 2008 (publication) ; implémentation écrite ici | sans objet |

Aucun code de Puppeteer ou d'UniRig n'a été copié. Les poids et jeux de données de ces deux projets n'ont pas été
téléchargés (taille) et leurs licences ne sont pas vérifiées ; elles le seront avant toute réutilisation.

## 9. Fichiers et tests

Fichiers (`engine/validation/skinning/`) : `extraire_poses.py` (extraction Blender), `methodes.py`, `mesures.py`,
`comparer.py`, `attribution_retournements.py`, `experience_poids_lissage.py`, `test_skinning.py`.

Données source (non versionnées, 50 Mo) : `poses.npz` produit par
`blender -b --factory-startup --disable-autoexec corps_skin.blend -P engine/validation/skinning/extraire_poses.py -- corps_skin.blend poses.npz`
à partir de `corps_skin.blend` (scratchpad de session).

Tests exécutés : `test_skinning.py poses.npz` → 9 tests OK (log : `tests_skinning.log`). Banc `comparer.py` exécuté sur
28 poses, base et haute résolution. Résultats : `comparatif.json`.

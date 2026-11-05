# Investigation de la dégradation de la hanche masculine (SQ et SQV1)

Phase 4, étape 3c (suite). Objet : identifier la cause géométrique et mathématique de la dégradation du maximum
d'étirement de la hanche masculine par les variantes à rotations du squelette (SQ, SQV1, SQV3).

Résultat principal : **la cause n'est pas identifiée**. Une partie du mécanisme est localisée et mesurée ; plusieurs
hypothèses sont réfutées. Aucun candidat n'est validé. La référence (LBS, DQS, Bone Heat) reste inchangée.

## 1. Données et protocole

- Modèle : HBM masculin (`poses2.npz`, 10 582 sommets), squelette extrait à l'étape 1 (Blender 4.5.15 LTS).
- Poses de test de hanche : G 75°, G 105°, G 120°, D 75°, D 120° (articulations réelles, signe mesuré sur la pose réelle).
- Variante SQ : `solve_fixe(lbs, rest, A, Rsq, λ = 0,1)`, avec Rsq = polaire(Mv), Mv = Σ w_k R_k.
- Métrique : étirement d'un sommet = maximum, sur ses arêtes incidentes, de |p_a − p_b| / |r_a − r_b|.
- Sommet défectueux : étirement SQV1 > 1,5 et dégradation de plus de 0,05 par rapport au LBS.
- Aucun seuil n'a été modifié.

## 2. Faits établis (mesurés)

| Fait | Valeur | Fichier |
|---|---|---|
| Convention LBS vérifiée (somme manuelle des transformations) | erreur 9,9e-8 m | `etape_D_transformations.json` |
| Mv non rigide dans l'entrejambe | déterminant médian 0,36 (0,25–0,64 sur les défauts) | `etape_D_transformations.json` |
| Sommets défectueux (union des cinq poses) | 24, tous dans l'entrejambe | `etape_A_defauts.json` |
| Localisation | z ≈ 0,73–0,76 m, entre les influences cuisse gauche et cuisse droite | `carte_defauts_masculin_hanche_G120.png` |
| LBS déjà défectueux | max 2,47 au sommet 8734 (G 120°) | `etape_B_fiches.json` |
| Amplification SQ sur des arêtes courtes | 8734–9130 : LBS 2,471 → SQ 2,590 ; 3474–9131 : 2,241 → 2,518 | fiches B |
| Arêtes où SQ dépasse LBS de plus de 0,05 (21 170 arêtes) | 174, gradient de poids médian 0,15 (toutes arêtes : 0,00) | `H3_gradient_poids.json` |
| Corrélation |gradient de poids| / |SQ − LBS| | 0,447 | `H3_gradient_poids.json` |
| Corrélation |gradient de poids| / étirement LBS | 0,431 | `H3_gradient_poids.json` |
| 50 arêtes au gradient de poids le plus fort | longueur médiane 2,8 cm ; étirement LBS médian 1,41 ; SQ − LBS médian +0,007 ; SQ > LBS dans 62 % des cas | `H3_gradient_poids.json` |

Lecture : la dégradation SQ est concentrée là où le poids passe vite de « cuisse gauche » à « deux cuisses à parts
égales ». Mais le gradient de poids ne détermine ni le signe ni l'amplitude de l'effet de SQ : sur les arêtes où le
gradient est le plus fort, SQ améliore plus souvent qu'il ne dégrade.

## 3. Hypothèses testées

| Réf. | Hypothèse | Test | Résultat | Statut |
|---|---|---|---|---|
| a | La convention de moyenne des rotations (quaternion ou polaire) cause le défaut | F3 : moyenne alternative | 2,586 contre 2,590 (F0) | **Réfutée** |
| b | La zone d'application de SQ est trop large | F4 : α = 0,5 / 1,0 / 1,5 | Aucun changement sur le maximum ; le défaut est dans la zone | **Réfutée** |
| c | Un désaccord de rotation entre arêtes explique l'amplification | H2 : corrélation angle / variation d'étirement | −0,43 ; 9 arêtes dégradées, angle médian 17° contre 0° globalement | **Réfutée comme cause unique** |
| d | La rotation de l'os dominant est meilleure que le repère moyen | SD / SDV1 | Pire : 3,35–3,49 contre 2,59 | **Réfutée** |
| e | La correction de volume explique la régression masculine | SQ seul, sans volume | SQ seul déjà à 2,59 | **Réfutée** |
| f | Les poids de l'entrejambe peuvent être reportés sur les Hips | F6 : transfert de poids | LBS avec poids modifiés explose (5,50 à G 60°, 2 retournements) | **Non viable** |
| g | Le gradient de poids explique où SQ amplifie | H3 | Localise (174 arêtes, corrélation 0,45) ; n'explique ni le signe ni l'amplitude | **Partielle** |
| h | Une ancre plus forte (λ) suffit à corriger | F5 : λ = 0,01 / 0,1 / 1,0 | λ = 0,01 réduit le maximum à G 60° (1,67) mais dégrade le volume (−0,025) ; λ = 1,0 réduit le volume mais augmente le max | **Non suffisante** |
| i | La correction de volume seule corrige la hanche | F1, F2 | Volume rétabli, étirement local inchangé | **Ne traite pas le défaut** |

Remarque sur F5 : λ n'est pas un paramètre libre. Le choisir après avoir vu les résultats sur la hanche reviendrait à
calibrer sur le test. Aucune valeur de λ n'est retenue.

## 4. Mécanisme retenu (non démontré)

Au niveau de l'entrejambe, deux cuisses tirent des sommets voisins dans des directions presque opposées, avec des
poids proches. Le repère moyenné Mv y est non rigide (déterminant ≈ 0,36) : sa polaire ne correspond à la rotation
d'aucun os. Les arêtes courtes de ce gradient voient leur longueur mal reproduite. Cette explication est cohérente
avec les mesures, mais elle n'est pas prouvée : H3 ne montre qu'une corrélation, et la moitié des arêtes les plus
raides ne sont pas dégradées par SQ.

## 5. Ce qui n'est pas établi

- Le mécanisme exact qui fait passer une arête de « non dégradée » à « dégradée ».
- Une correction qui réduise le maximum sans dégrader le volume, les autres poses ou les autres morphologies.
- Le comportement sur les poses indépendantes (L_abd30, L_add20, L_flex60, L_genou60, combinaisons, etc.) et sur
  les morphologies féminine et Maria : aucun candidat n'a été proposé, donc ces tests n'ont pas été lancés.

## 6. Décision

- Aucun candidat n'est retenu. Les variantes SQ, SQV1, SQV3 restent expérimentales et non intégrées.
- Le système de référence (LBS, DQS, Bone Heat) reste inchangé.
- Prochaine étape proposée : soit une formulation de la rotation locale qui impose l'orthonormalité par arête
  (test de la cause « repère non rigide »), soit l'abandon de SQ pour l'entrejambe au profit d'une correction
  construite par modèle, à valider sur les poses indépendantes avant toute intégration.

## 7. Fichiers

- `etape_A_defauts.json`, `etape_B_fiches.json`, `etape_D_transformations.json`, `carte_defauts_masculin_hanche_G120.png`
- `H2_angle_aretes.json`, `H3_gradient_poids.json`
- `../isolation_hanche_masc/resultats_isolation.json`
- Scripts : `engine/validation/skinning/investigation_hanche_masc.py`, `investigation_hanche_masc_BCD.py`,
  `investigation_isolation.py`, `investigation_aretes_rotation.py`, `investigation_gradient_poids.py`

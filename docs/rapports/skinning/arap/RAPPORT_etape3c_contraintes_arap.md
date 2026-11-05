# Étape 3c : contraintes d'arêtes, ARAP et rotations du squelette (+ volume), sans cible

Aucune cible externe (étape 3a). Protocole identique à l'étape 3b : calibration masculin hanche 60°/90° ; critère
sur chaque pose : p99 ≤ LBS, retournements ≤ LBS, |volume| ≤ LBS (critères fixés avant les calculs, non relâchés).
Test : hanche G 75/105/120, hanche D 75/120, genou G 60/90/105, trois morphologies (poses non utilisées pour choisir).

## Candidats
1. **Contraintes d'arêtes** (position-based dynamics, `experience_contraintes_aretes.py`) : rejetées. Le p99 baisse
   légèrement (1,15 → 1,11) mais retournements 0 → 4 et maximum non réduit. Une contrainte de longueur ignore l'orientation.
2. **ARAP locale-globale** (Sorkine & Alexa 2007, `experience_arap.py`) : rotations locales ajustées sur la géométrie
   déformée. Un retournement de plus en calibration (0 → 1) : rejetée. Test : Maria améliorée (max 8,30 → 1,90), masculin
   et féminin : maximum dégradé (2,49 → 2,99 ; 2,53 → 2,83).
3. **Rotations du squelette (SQ)** : rotations locales = polaire du repère rigide LBS Mv = Σ w_k R_k (déjà utilisé pour
   les retournements), résolution linéaire unique avec ancrage λ. Calibration : p99 et retournements OK ; rejetée
   uniquement sur le volume (0,011 → 0,019 à 60° ; 0,027 → 0,043 à 90°).
4. **SQ + correction de volume, 1 étape (SQV1), λ = 0,1** : passe tous les critères de calibration ; retenue comme
   meilleur candidat, mais non validée (voir ci-dessous).

## Résultats de test (informatifs, α/λ non choisis sur ces poses)

| Morphologie | Méthode | Étirement max | p99 moyen | Retournements | |Volume| max |
|---|---|---:|---:|---:|---:|
| masculin | LBS | 2,485 | 1,106 | 31 | 0,045 |
| masculin | SQV1 λ 0,1 | 2,604 | 1,089 | 3 | 0,002 |
| féminin | LBS | 2,525 | 1,086 | 39 | 0,055 |
| féminin | SQV1 λ 0,1 | 2,268 | 1,094 | 0 | 0,003 |
| Maria | LBS | 8,300 | 1,000 | 126 | 0,036 |
| Maria | SQV1 λ 0,1 | 2,035 | 1,013 | 38 | 0,000 |

Détail par pose (maximum, LBS → SQV1) :
- masculin hanche G 75/105/120° : 1,89 → 1,93 ; 2,30 → 2,37 ; 2,47 → 2,59 (dégradation). Genou G 60/90/105° : 1,14 → 1,06 ;
  1,20 → 1,09 ; 1,23 → 1,11 (amélioration).
- féminin hanche G 120° : 2,53 → 2,20 ; genou G 105° : 1,63 → 1,20.
- Maria hanche G 120° : 8,30 → 2,04 ; genou G 105° : 2,32 → 1,51.
- p99 : Maria +0,014 à +0,018 à chaque pose (critère de test non atteint sur ce point).

## Lecture
- SQ seul est déjà responsable de la dégradation masculine de hanche (2,59 sans correction de volume) ; la correction de
  volume n'en est pas la cause. Hypothèse à tester : sur la zone de transition hanche/bassin, Mv moyenne des rotations de
  deux os ; la polaire de cette moyenne n'est pas la rotation d'un os, et l'ancrage fausse les arêtes voisines.
- SQV1 réduit fortement le maximum sur Maria et le féminin, et conserve le volume (0,000 à 0,003).
- **Non validé** : la hanche masculine se dégrade, et le p99 de Maria augmente. Le critère « tous les critères améliorés
  sur toutes les morphologies » n'est pas rempli.

## Décision
Aucun candidat n'est intégré. Référence : LBS, DQS, Bone Heat, inchangés.
Prochaine investigation : rotation par arête issue du seul os dominant (au lieu d'une moyenne sur la zone de transition).

## Complément : rotation de l'os dominant (hypothèse de l'étape 3c, réfutée)
Hypothèse : la dégradation masculine vient de la moyenne du repère Mv sur la zone de transition.
Test : rotation par sommet de l'os de plus fort poids (polaire de son R_k), résolution linéaire, avec et sans une étape de volume.

| Morphologie | Méthode | Étirement max | p99 moyen | Retournements | |Volume| max |
|---|---|---:|---:|---:|---:|
| masculin | LBS | 2,485 | 1,106 | 31 | 0,045 |
| masculin | SDV1 λ 0,1 (os dominant + volume) | 3,486 | 1,097 | 8 | 0,003 |
| féminin | SDV1 λ 0,1 | 2,678 | 1,102 | 17 | 0,004 |
| Maria | SDV1 λ 0,1 | 2,160 | 1,010 | 53 | 0,000 |

Lecture : pire que le repère moyenné (SQV1 : masculin 2,604, féminin 2,268). L'hypothèse est donc réfutée : la moyenne
n'est pas la cause, et la rotation d'un seul os crée des défauts plus grands. La dégradation masculine reste inexpliquée.
Entrée 185.

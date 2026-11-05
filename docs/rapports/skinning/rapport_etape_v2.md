# Phase 4 : rapport d'étape v2 (métriques fiabilisées, comparatif trois morphologies)

Statut : **phase 4 NON TERMINÉE**. Hanche et genou ne sont pas satisfaisants (voir « Résultats » et « Limites »).

## 1. Erreurs historiques corrigées (détail dans docs/erreurs_apprises.md)
- 146 à 149 : filtre de triangles, normale de Newell rigide, transfert de poids MULTIRES, signe de rotation.
- 150 : signe du côté par coordonnée absolue (asymétrie d'abduction, 1,41 contre 1,90 ; corrigé, 1,910 contre 1,897).
- 151 : étirement sur arêtes sub-millimétriques (seuil de 5 mm choisi après observation, déclaré post hoc).
- 152 : poids non normalisés (LBS rétrécissait les sommets, écart de 0,277 m ; corrigé, 4e-7 m).
- 153 : critère « étirement maximal » sensible à la topologie (Maria).
- 154 : écarts de retournements gauche/droite = poids automatiques (2 à 4 %) amplifiés au pli.
- 155 : classement du « sommet le plus touché » par maximum (égalités) ; corrigé par nombre d'arêtes étirées.
- 156 : résidu rigide global (Kabsch) inadapté à un corps articulé (1 m) ; remplacé par le résidu par os dominant.
- 157 : un attendu de test calculé à la main était faux (1,30 et non 1,118 ni le sommet attendu). Corrigé
  après vérification géométrique, et non ajusté à la sortie du code.

## 2. Métriques validées sur géométries synthétiques (31 tests, 0,3 s)
Fichier : `engine/validation/skinning/test_metriques_synthetiques.py` (log : `tests_metriques_synthetiques.log`).
Chaque métrique a un test positif et un test négatif, attendus calculés à la main.

| Métrique | Tests | Résultat |
|---|---|---|
| Translation rigide | T1a–T1d | aucune déformation ; bosse de 20 mm détectée (19,6 mm) |
| Rotation rigide | R1a–R1e | étirement 1, résidu 2e-16 m, 0 retournement avec repère ; 64 sans repère (régression 147) |
| Échelle uniforme | E1a–E1c | étirement exact 1,2 ; volume s³−1 = 0,728 exact |
| Compression locale | C1a–C1d | détectée (0,70), localisée au centre (0,5 ; 0 ; 0) |
| Étirement très localisé | S1a–S1e | 1,118034 exact ; 4 arêtes ; bon sommet ; localisation à 6 cm près |
| Bordure de compression | C1c | 1,30 exact (0,25 → 0,325 m) |
| Intersection (sommets de B dans A) | I1a–I1d | 26/26 détectés, profondeur 0,400 exacte, localisation (0 ; 0 ; 0) ; séparés : 0 |
| Volume local | V1a–V1b | face translatée de 0,05 : 0,050000 exact |
| Séparation rigide globale | P1 | résidu 1e-15 m |
| Résidu par os dominant | D1a–D1c | rigide : 0 ; mélange 50/50 : 0,5 exact |

**Limites des tests** : l'intersection ne teste que les sommets de B (une interpénétration sans sommet de B à
l'intérieur de A passe inaperçue) ; le test de bordure est une conséquence de la déformation de test, pas une
compression pure.

## 3. Comparatif LBS / DQS / hybrides sur trois morphologies
Tableaux complets : `docs/rapports/skinning/v2/TABLEAUX_v2.md` ; données : `comparatif_masculin.json`,
`comparatif_feminin.json`, `comparatif_maria.json` ; captures : `captures_masculin.png`, `captures_feminin.png`,
`captures_maria.png` (rouge = étirement > 1,25).

Points retenus (détail dans les tableaux) :
- **p99 satisfaisant (1,00 à 1,25) alors que le maximum atteint 8,3 (Maria, hanche, LBS).** Le p99 cache le défaut.
- **DQS** : moins de retournements et de dérive de volume, mais maximum d'étirement plus élevé à la hanche
  (masculin 2,47 → 3,29 ; Maria 8,30 → 10,00). Pas d'amélioration globale.
- **Localisation** : défauts devant le bassin et le bas-ventre (zone hanche), pas seulement à l'aine (capture).
- **Genou (genou90)** : maximum 1,20–1,28 (masculin), 1,61–1,74 (féminin), 1,79–1,93 (Maria).
- **Abduction (abd30)** : maximum 1,8 à 2,0 (masculin, féminin), 4,2 (Maria, toutes méthodes).
- Contrôle LBS contre Blender : erreur < 1e-6 m sur les trois.

## 4. Performances CPU
- Comparatif v2 : environ 8 s par personnage (28 poses × 4 méthodes, défauts et captures), machine de la session.
- Suite de tests synthétiques : voir le log (durée en fin de fichier).

## 5. Priorités non faites dans cette étape
- Priorité 4 (corrective blendshapes, PSD, DQS avec correction de volume, musculaire/anatomique) : **non commencée**.
  Aucune technique n'a été comparée ni intégrée. Aucune affirmation sur leurs gains n'est faite ici.
- Priorité 5 (généralisation par morphologie) : non commencée. Les trois personnages sont traités séparément,
  sans correction spécifique.
- Hi-res (MULTIRES) : seul le masculin a des poids transférés par Blender ; le féminin et Maria sont comparés sur le
  maillage de base (même condition pour les trois).

## 6. Limites restantes
- Cause du défaut hanche non établie. La localisation (bassin et bas-ventre, poids Hips/Spine/UpLeg) suggère un
  mélange de poids trop large sur une zone qui glisse, mais ce n'est pas une preuve ; la voie « lissage des poids »
  a déjà été réfutée (entrée 118).
- Le maximum local reste élevé à la hanche et au genou pour les trois personnages.
- Le critère de comptage des retournements reste sensible à 2–4 % de poids asymétriques (entrée 154).
- Pas de mesure d'intersection entre parties du corps sur le personnage réel (seul le test synthétique existe).
- Le résidu par os dominant est grand au pli (16 cm à flex120) parce qu'il inclut le mélange de bassin et de cuisse.

## 7. Commits
Voir l'historique git : 95d34b3 (signe, normalisation, test symétrie), 7a9dc21 (diagnostic retournements,
critère Maria), et le commit de cette étape (métriques synthétiques, défauts locaux, comparatif v2).

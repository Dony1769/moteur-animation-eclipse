# Bornes d'étirement de la peau aux articulations (phase 4)

Objectif : fixer la borne d'étirement admise dans la bande de jonction, sur une source lue, et dire ce qui n'est pas sourcé.

## Sources lues (2026-11-05)
- [S1] Sednieva et al. 2020, Frontiers Bioeng. Biotechnol. (primaire, revue par des pairs) : mesure le fascia lata
  (et non la peau) sur 3 cadavres âgés, genou seulement. Déformation de traction moyenne maximale 10–12 % sur le
  fascia latéral et la bandelette ilio-tibiale. Non utilisable comme borne de peau.
  https://www.frontiersin.org/articles/10.3389/fbioe.2020.00750/full
- [S2] PMC6783393 (3D-DIC, moignon transtibial in vivo, 1 sujet, preuve de principe) : genou, référence 15°.
  À ~30° de flexion : traction maximale ≈ +15 % (au-dessus de la rotule), compression ≈ −25 % (creux postérieur).
  Valeurs lues sur les figures, donc approximatives. Peau de moignon, pas de peau de hanche.
  https://pmc.ncbi.nlm.nih.gov/articles/PMC6783393
- [S3] Emerald, IJCST 2016 (résumé seulement, 1 sujet) : déformation de la longueur de peau ±6 % dans la cuisse
  médiale haute, à 90° de flexion de genou ou en squat. Sens (traction ou compression) non précisé.
  https://www.emeraldinsight.com/insight/content/doi/10.1108/IJCST-08-2016-0090/full/html

## Borne retenue (provisoire)
- Bande de jonction (genou et hanche) : étirement p99 ≤ 1,15 (traction de 15 %, S2 au genou).
- Hors bande : étirement p99 ≤ 1,00 (critère de phase 4, inchangé).
- Justification : la seule mesure de peau vivante au genou donne 15 % de traction ; elle est sur un seul sujet.

## Ce qui n'est PAS sourcé
- Aucune mesure de déformation de peau de hanche à la flexion : la borne 1,15 pour la hanche est une extrapolation.
- Les valeurs de S2 sont lues sur des figures ; S3 n'a que le résumé.
- Un seul sujet pour chaque mesure : à confirmer sur une population plus large avant de figer la borne.

## Conséquence
- Genou (chaîne validée, numpy) : étirement p99 bande 1,08 à 60°, 1,21 à 120° : légèrement au-dessus de 1,15 à partir de
  ~105°.
- Hanche (chaîne, numpy) : 1,21 à 30° puis 1,85 à 120° : au-dessus de 1,15 dès 30°. Non passé.

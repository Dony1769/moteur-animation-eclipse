# Articulations humaines : type, mouvements, déclencheur, nerfs et sources

Objectif : pour chaque articulation du corps, savoir (1) ce qu'elle relie, (2) quels mouvements elle permet,
(3) ce qui déclenche le mouvement (muscles moteurs, nerf qui les commande), et (4) quelles amplitudes sont
sourcées. Chaque chiffre porte sa source. « non sourcé » signifie qu'aucune source consultée ne le donne.

Sources :
- **[S-NCBI]** StatPearls (NCBI Bookshelf), officiel : https://www.ncbi.nlm.nih.gov/books/NBK536933/ (épaule) ; StatPearls coude : https://www.statpearls.com/point-of-care/32402
- **[S-SP]** StatPearls, page de fiche (accessible) : coude ci-dessus ; poignet : fiche en formulaire seulement, non utilisable
- **[NS-PHY]** Physiopedia, non officiel : https://www.physio-Pedia.com/Functional_Anatomy_of_the_Ankle
- **[NS-MM]** Muscle and Motion, non officiel : https://www.muscleandmotion.com/?p=14570 (hanche) ; https://www.muscleandmotion.com/?p=11943 (genou)
- **[NS-TMA]** TeachMeAnatomy, non officiel : https://teachmeanatomy.info/upper-limb/wrist-joint/ (poignet)
- **[OFF-AMP]** Limites articulaires déjà utilisées dans le moteur : CDC/NCHS (voir `engine/skinning/limites_articulations.py`).

Statut des sources : StatPearls hanche, genou et poignet n'ont pas été lisibles (blocage d'accès) ; ces articles
ont donc été remplacés par des sources non officielles, signalées comme telles.

## Déclencheur : ce qui fait bouger une articulation
Un mouvement commence quand un motoneurone active un muscle. Le muscle se contracte, sa tendon tire sur l'os
au-delà de l'axe de l'articulation, et l'os tourne autour de cet axe. Le nerf moteur donne donc le déclencheur,
et le muscle moteur donne le sens. Le moteur doit reproduire ce couple : axe, sens, et muscle qui tire.

## 1. Coude (huméro-ulnaire, huméro-radiale, radio-ulnaire proximale)
- Type : charnière synoviale (huméro-ulnaire) ; pivot pour la radio-ulnaire proximale. [S-SP]
- Relie : humérus ↔ ulna et radius (bras ↔ avant-bras). Ligaments : collatéraux médial et latéral (limitent la
  stabilité latérale et médiale). [S-SP]
- Mouvements et déclencheurs :
  - Flexion : biceps brachial, brachial, brachio-radial. Nerfs : musculo-cutané (biceps, brachial) ; radial (brachial, brachio-radial). [S-SP]
  - Extension : triceps brachial (principal), anconé (accessoire). Nerf radial. [S-SP]
  - Supination : biceps brachial (principal), muscle supinateur. Nerfs : musculo-cutané ; radial. [S-SP]
  - Pronation : muscle rond pronateur (non détaillé dans la fiche). Nerf non précisé. [S-SP]
- Amplitudes : flexion 0 à 145° et extension 0° (ordre de grandeur, [OFF-AMP] : non confirmé par une source
  officielle consultée). Pronation/supination 80–90° : non sourcé.

## 2. Épaule (gléno-humérale)
- Type : synoviale sphérique (ball-and-socket), très mobile. [S-NCBI]
- Relie : omoplate (glène) ↔ humérus. Le mouvement s'accompagne de l'omoplate et de la clavicule (rythme
  scapulo-huméral, non sourcé ici).
- Mouvements et déclencheurs [S-NCBI] :
  - Flexion : deltoïde antérieur, pectoral majeur (faisceau claviculaire), coraco-brachial. Nerfs : axillaire ; médian/pectoraux ; musculo-cutané.
  - Extension : deltoïde postérieur ; grand dorsal. Nerfs : axillaire ; thoraco-dorsal.
  - Abduction : deltoïde moyen (jusqu'à 90°) ; supra-épineux (premiers 15°) ; trapèze et dentelé antérieur au-delà de 90°. Nerfs : axillaire ; suprascapulaire ; accessoire ; thoracique long.
  - Adduction : grand rond, grand dorsal, pectoral majeur, coraco-brachial, sous-scapulaire.
  - Rotation médiale : deltoïde antérieur, grand rond, sous-scapulaire, grand dorsal, pectoral majeur.
  - Rotation latérale : deltoïde postérieur, sus-épineux, petit rond. Nerfs : axillaire ; suprascapulaire.
- Amplitudes : non sourcées dans la fiche. L'amplitude 180° de flexion et d'abduction du moteur est
  non sourcée ici et doit être confirmée avant d'être figée.

## 3. Poignet (radio-carpienne)
- Type : condyloïde (ellipsoïde), 2 axes : flexion/extension et inclinaisons radiale/ulnaire. [NS-TMA]
- Relie : radius ↔ carpe.
- Mouvements et déclencheurs [NS-TMA] :
  - Flexion : fléchisseur ulnaire du carpe, fléchisseur radial du carpe ; assistant : fléchisseur superficiel des doigts.
  - Extension : extenseurs radiaux du carpe (long et court), extenseur ulnaire du carpe ; assistant : extenseur commun des doigts.
  - Inclinaison ulnaire : extenseur ulnaire, fléchisseur ulnaire du carpe.
  - Inclinaison radiale : long abducteur du pouce, fléchisseur radial, extenseurs radiaux.
- Nerfs (général, non par mouvement) : médian (branche interosseuse antérieure), radial (branche interosseuse postérieure), ulnaire. [NS-TMA]
- Amplitudes : non données par la source. Ordre de grandeur du moteur (flexion 80°, extension 70°) : non sourcé.
  Ce point reste ouvert (erreur à enregistrer si confirmé).

## 4. Hanche (coxo-fémorale)
- Type : sphérique (ball-and-socket). [NS-MM]
- Relie : bassin (acétabulum) ↔ fémur (tête).
- Amplitudes actives [NS-MM] : flexion 120° ; extension 10° ; abduction 45° ; adduction 25° ; rotation interne 15° ;
  rotation externe 35°. (Le document précédent du dépôt donnait extension 20–30°, rotation 30–45° : valeurs
  non sourcées et plus larges ; la source ci-dessus les remplace jusqu'à confirmation officielle.)
- Muscles par mouvement [NS-MM] (sans distinction moteur principal) :
  - Flexion : psoas, iliaque, droit fémoral, couturier, tenseur du fascia lata, gracile.
  - Extension : grand fessier, ischio-jambiers.
  - Abduction : moyen et petit fessiers, tenseur du fascia lata.
  - Adduction : grand, moyen et petit adducteurs, gracile, pectiné.
  - Rotation interne : petit fessier, moyen fessier, tenseur du fascia lata, adducteurs.
  - Rotation externe : grand fessier, jumeaux, obturateurs, carré fémoral, piriforme.
- Nerfs : non précisés par la source ; à compléter (fessiers : gluténaux ; psoas/iliaque : fémoral ; adducteurs : obturateur).

## 5. Genou (fémoro-tibiale et fémoro-patellaire)
- Type : charnière synoviale. [NS-MM]
- Relie : fémur ↔ tibia (+ patella).
- Mouvements et déclencheurs [NS-MM] :
  - Flexion : ischio-jambiers (semi-membraneux, semi-tendineux, biceps fémoral), assistés par couturier, gracile, gastrocnémien, poplité.
  - Extension : quadriceps fémoral, assisté par le tenseur du fascia lata.
  - Rotation interne et externe : uniquement genou fléchi ou en fin d'extension (mécanisme de « screw-home » entre 0° et 20° de flexion). Amplitude non donnée.
- Ligaments limitants [NS-MM] : LCM (valgus), LCL (varus et rotation postéro-latérale), LCA (glissement antérieur du tibia), LPC (glissement postérieur).
- Amplitudes : flexion 0 à 150° (échantillon de danse, [mesure du dépôt]) ; limites humaines [OFF-AMP] 130–140°. Non sourcées dans la fiche.
- Nerfs : non précisés par la source.

## 6. Cheville (talo-crurale) et sous-talienne
- Talo-crurale : charnière. Flexion dorsale 12–20°, flexion plantaire 50–56° [NS-PHY].
  - Flexion dorsale : jambier antérieur, extenseur commun des orteils, extenseur propre du gros orteil, fibulaire tertius. Nerf fibulaire profond (L4–S1).
  - Flexion plantaire : gastrocnémien, soléaire, plantaire grêle, fléchisseur commun et propre des orteils, jambier postérieur, fibulaire court. Nerf tibial (L5–S2).
- Sous-talienne : condyloïde. Inversion moyenne 30°, éversion moyenne 18° [NS-PHY].
  - Inversion : jambier antérieur, jambier postérieur, extenseur propre du gros orteil, fléchisseur propre du gros orteil.
  - Éversion : fibulaire long, fibulaire court, extenseur commun, fibulaire tertius.
  - Nerfs : éversion par le nerf fibulaire superficiel (L5–S2) ; inversion par le nerf tibial et le nerf fibulaire profond.

## 7. Liens avec le squelette du moteur
- Le rig à 21 os (`engine/rigging`, `os_repos.json`) contient : hanche (UpLeg/Hips), genou (Leg), cheville (Foot),
  épaule (Arm/Shoulder), coude (ForeArm), poignet (Hand). Les doigts et orteils ne sont pas dans ce rig.
- Pour chaque articulation : le moteur doit imposer (a) l'axe et le sens, (b) les bornes d'amplitude, (c) un
  muscle moteur fictif ou un déclencheur (le couple axe-sens + amplitude suffit pour la géométrie).

## 8. Ce qui reste à faire
- Hanche, genou, poignet : sources officielles StatPearls à relire quand l'accès sera possible ; les nerfs de la hanche et du genou sont à compléter.
- Épaule : amplitudes (flexion, abduction, rotation) à sourcer ; rythme scapulo-huméral à ajouter.
- Coude et poignet : amplitudes à sourcer (la fiche StatPearls coude ne les donne pas).
- Colonne, pouce, doigts, orteils : non traités ici.

## 9. Statut de la recherche d'amplitudes (2026-11-05)
Requêtes Europe PMC testées sans valeur normative exploitable pour coude, poignet, épaule (journal complet dans
docs/recherches_phase4.md). Les amplitudes du coude (0–145°), du poignet (80°/70°) et de l'épaule restent
NON SOURCÉES et ne doivent pas être figées dans le rig avant une source lue.

## 10. Amplitudes actives de référence (sourcées, 2026-11-05)
Sources lues :
- [NS-PHY2] Physiopedia, « Range of Motion Normative Values » (non officiel) : https://www.physio-pedia.com:443/Range_of_Motion_Normative_Values
  Cite les valeurs AAOS tirées de Botman et al. (2020, matériel supplémentaire). La publication primaire n'a pas été
  retrouvée par l'API Europe PMC (0 résultat) : valeurs à confirmer dans la source primaire.
- [S-PMC-BRN] PMC9218764 table 1 (Burn Model System, J Burn Care Res 2018) : plages de mouvement « définies », pour
  décrire un arc normal ; population de brûlés adultes, donc pas une référence de population saine.

| Articulation | Mouvement | Valeur retenue (degrés) | Source | Désaccord constaté |
|---|---|---|---|---|
| Épaule | flexion | 180 | NS-PHY2 | — |
| Épaule | extension | 40–60 | NS-PHY2 | — |
| Épaule | abduction | 160–180 | NS-PHY2 | — |
| Épaule | rotation médiale / latérale | 70 / 90 | NS-PHY2 | — |
| Coude | flexion | 140–150 (borne 0–140 pour S-PMC-BRN) | NS-PHY2, S-PMC-BRN | 140 vs 145 du moteur |
| Coude | extension | 0 | NS-PHY2, S-PMC-BRN | — |
| Avant-bras | pronation / supination | 80–90 | NS-PHY2 | — |
| Poignet | flexion / extension | 60–80 / 60–70 (S-PMC-BRN : 60 / 60) | NS-PHY2, S-PMC-BRN | moteur : 80 / 70, confirmé seulement pour la flexion haute |
| Poignet | inclinaison radiale / ulnaire | 20 / 30 | NS-PHY2 | — |
| Hanche | flexion | 120 | NS-PHY2, NS-MM | — |
| Hanche | extension | 10 (NS-MM) ou 20 (NS-PHY2) | conflit | à arbitrer |
| Hanche | abduction / adduction | 40 / 20 (NS-PHY2) ; 45 / 25 (NS-MM) | conflit | à arbitrer |
| Hanche | rotation médiale / latérale | 45 / 45 (NS-PHY2) ; 15 / 35 (NS-MM) | conflit | fort écart |
| Genou | flexion | 135 (NS-PHY2) ; 150 (S-PMC-BRN) | conflit | moteur : 150 (danse) |
| Genou | extension | 0 | NS-PHY2, S-PMC-BRN | — |
| Cheville | dorsiflexion / plantaroflexion | 20 / 50 (NS-PHY2) | NS-PHY2, NS-PHY | cohérent avec section 6 |

Règle adoptée : pour borner le rig, prendre la plage basse quand les sources divergent (sécurité anatomique),
et noter le désaccord. Les valeurs « conflit » ne doivent pas être figées sans lecture de la source primaire.

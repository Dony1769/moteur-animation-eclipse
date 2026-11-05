# Recherches phase 4 : jointures, couture, calotte

Méthode : une recherche ne suffit pas. Sources officielles d'abord (publications, dépôts de référence),
puis sources non officielles (articles de praticiens, issues de projets) quand l'officiel ne répond pas.

## Sources officielles
- Kavan, Collins, Žára, O'Sullivan, « Geometric Skinning with Approximate Dual Quaternion Blending », ACM TOG 2008.
  https://users.cs.utah.edu/~ladislav/kavan08geometric/kavan08geometric.pdf
  Apport : la moyenne linéaire des matrices (LBS) fait rétrécir les jointures ; les dual quaternions conservent le volume.
- Kavan, Collins, O'Sullivan, « Spherical Blend Skinning », 2005 (déjà utilisé : rejeté pour déplacement du tronc, erreur 82).
- Jacobson, Sorkine, « Stretchable and Twistable Bones for Skeletal Shape Deformation », SIGGRAPH Asia 2011.
  https://igl.ethz.ch/projects/skinning/stretchable-twistable-bones/stretchable-twistable-bones-siggraph-asia-2011-compressed-jacobson-sorkine.pdf

## Sources non officielles (utilisées parce que l'officiel ne traite pas la couture de jointure)
- Article « The Cause of Wrist Skin Collapse is Skinning, Not Pose » (dev.to, praticien).
  https://dev.to/orca_forge/the-cause-of-wrist-skin-collapse-is-skinning-not-pose-583k
  Apport : l'écrasement vient des poids de skinning, pas de la pose. Lissage local des poids (30 itérations, facteur 0,5,
  sommets à moins de 8 cm), renormalisation, mesure du rapport de longueur d'arête (déformée / repos) dans la zone de jointure.
  Limite : cela reste un mélange de poids, pas une couture.
- Issue GitHub rig-c/parts #349 (fermée, PR #362) : « limbs are always cut at their joints into rigid parts ».
  https://github.com/rig-c/parts/issues/349
  Apport : chaque membre est coupé en pièces rigides au niveau du joint ; chaque pièce inférieure se prolonge
  au-delà du joint d'une largeur de membre, et la pièce supérieure la recouvre ; la couture est une calotte (cap)
  générée, et non un mélange de poids. Critère : refuser toute pièce de membre pondérée sur un second os.

## Ce que ça change pour le moteur
1. Les pièces sont rigides (une pièce = un os). Aucune pondération partagée au coude.
2. La couture doit être une géométrie générée : une calotte (sphère ou disque) reliée aux deux bords ouverts.
3. Mesures obligatoires : pénétration, plis retournés, étirement des faces de couture, ouverture de couture.
4. Une calotte sans couture (trou) donne une ouverture de plusieurs centimètres : mesuré à 48-88 mm au coude (erreur 93).

## Union booléenne (méthode retenue pour la couture)
- Bibliothèque : Manifold (Emmett Lalish), https://github.com/elalish/manifold — licence Apache-2.0. Garantit une sortie
  manifold pour les booléens, à condition que les entrées soient manifold (vérifié ici : le corps au repos est fermé).
- Wrapper Python : trimesh 5.2 + manifold3d (installés par pip).
- Résultat : l'union du corps posé et d'une sphère de jonction donne un maillage fermé à 30, 60, 90 et 120°, volume conservé.
  C'est ce qui manquait aux couture approximées (erreurs 93 et 94).
- Limite : la fermeture ne prouve pas l'absence de pénétration visible. Il faut mesurer la surface unie.

## Coude au-dela de 120 deg (recherche du 4 nov. 2026)
- Officiel (Kavan et al. 2008, Dual quaternion skinning, page du projet https://users.cs.utah.edu/~ladislav/dq/) : DQS supprime l'effondrement du coude par melange de quaternions duaux ; limite connue : bascule du sens de rotation (le plus court chemin). Peau continue, donc pas une methode de contact pour segments rigides.
- Officiel-academique (Rohmer et al., « Exact volume preserving skinning with shape control », DOI 10.1145/1599470.1599481) : correction geometrique post-skinning qui conserve le volume exactement ; forme controlee par profils 1D. Pertinent pour le volume, mais demande une peau continue.
- Non officiel (dev.to, orca_forge, « Elbow Interference Correction Jumps Back and Forth », https://dev.to/orca_forge/elbow-interference-correction-jumps-back-and-forth-1k70) : la correction de penetration saute d'un cote a l'autre d'une image a l'autre si la direction est choisie image par image. Methodes retenues : choisir la direction sur toute la sequence (programmation dynamique), normale de surface lissee sur 16 voisins, pole du coude deplace avec l'avant-bras, correction limitee a la partie distale du bras.
- Application au moteur : poussee bornee et lissee (test_coude_correction_contact.py) : resultat partiel, voir erreur 96. Le saut d'image n'est pas le probleme ici (pose statique) ; la limite est la metrique sur sommets d'origine au joint.

## Pli fléchisseur du coude : correction de pose (recherche du 5 nov. 2026)
- Officiel (Lewis, Cordner, Fong, SIGGRAPH 2000, Pose Space Deformation, PDF de l'auteur https://www.scribblethink.org/Work/PSD/PSD.pdf) : p_final = p_rigide + δ(pose). δ est stocké en repère local à quelques poses échantillonnées (coude plié), puis interpolé par RBF gaussienne sur l'angle (poids w = (ΦᵀΦ)⁻¹Φᵀd). Le coude plié est corrigé par des formes sculptées, pas par une boule.
- Non officiel (praticien, Sol G. Brennan, Medium, https://sol-g-brennan.medium.com/rigging-tips-methods-for-extra-character-deformation-in-game-dev-e4c0e89e7b00) : blendshapes correctifs pilotés par l'angle, helper joints (set driven keys, RBF), limites : pas de rayon de contrôle en dehors des échantillons, dérive (« swimming ») si les intermédiaires ne sont pas cohérents, invalidation si le maillage change.
- Décision : la correction de pose (PSD) est la méthode retenue pour le pli fléchisseur. Elle remplace la sphère fixe (erreur 103).
- Verrou : PSD exige une cible sculptée à l'angle fléchi. Les données disponibles (skin Mixamo de la danse) sont en skinning linéaire, donc arrondies au coude : pas une cible anatomique. Il faut une source de forme de pli (modèle anatomique ou scan) avant d'échantillonner δ.

## Source anatomique de la chair au coude (recherche du 5 nov. 2026)
- Source publiée et académique (Hermawati & Marshall, « Realistic elbow flesh deformation based on anthropometrical data for ergonomics modeling », https://core.ac.uk/download/288385532.pdf) : sections transversales du bras à 4 postures (extension, 90°, 135°, flexion maximale), 16 distances radiales par section, base PCA. Données : 23 sujets (scanner TC2-NX12 + fil physique à la flexion).
- Loi reprise : rapport UAF/UAM (surface de chair haute / milieu) en fonction de l'angle, ajustement y = −6e−06·x² − 0,0018·x + 0,9478 (R² 0,937), x en degrés (fig. 5 de l'article, données propres à l'étude).
- Limites : 5 à 6 sujets par groupe ; le scanner ne capture pas la chair à la flexion ≥ 100° (mesures au fil à la place) ; pas de mesure de maillage complet à l'angle fléchi.
- Écarté : arXiv 2509.06607 (SKEL) ne traite pas de la chair ni du pli, seulement du squelette et de SMPL.
- Usage prévu : fixer les postures-clés de PSD (0, 90, 135°, flexion max) et la loi d'échelle de la chair fléchisseur ; le maillage cible reste à construire à partir des 16 distances radiales (non publiées en brut : à reconstituer).

## Accès aux sources d'articulations (5 nov. 2026)
- Contournement de la vérification du navigateur (NCBI Bookshelf) : refusé. C'est un contrôle contre les clients automatisés ; l'autorisation de l'utilisateur ne le lève pas. Accès légitime retenu : APIs officielles.
- NCBI E-utilities (efetch, db=pubmed) : fonctionne. Pour une fiche StatPearls, n'expose que le résumé et les titres de section (corps absent). PMID 29262200 = « Anatomy, Bony Pelvis and Lower Limb, Hip Joint » (NBK470555) : résumé seulement.
- NCBI E-utilities esearch : erreur 500 au moment de l'essai.
- Europe PMC (API REST officielle, EBI) : fonctionne ; résultats = études récentes (marche, rééducation). Aucune valeur normale de référence trouvée en 1 requête. À affiner par mots-clés goniométrie + revue systématique.
- Conséquence : hanche, genou et poignet restent sourcés par des pages non officielles (Muscle and Motion, TeachMeAnatomy), en attendant une source officielle lisible.

## Journal : recherche des amplitudes normatives (coude, poignet, épaule, hanche, genou)
Date : 2026-11-05. Objectif : sourcer les amplitudes actives de référence adultes.
- Europe PMC (API officielle REST), requêtes testées :
  - « hip AND reference values AND goniometer… » (encodage correct) : résultats hors sujet (chiens, dynamomètre, marche).
  - « normal range of motion joints adults goniometry reference » : 169 résultats, aucune valeur normative extraite ;
    articles pertinents seulement pour genou/hanche chez athlètes (PMID 42091667, 41829622) sans tableau de référence accessible.
  - « Norkin White goniometry normal values » : hors sujet pour l'adulte (enfants, sujets épaule).
  - « normative joint range of motion ages 20 to 59 adults » : hors sujet.
- Conclusion : aucune source consultée ne donne les amplitudes normatives du coude, du poignet ni de l'épaule
  avec tableau exploitable. Ces valeurs restent NON SOURCÉES dans docs/articulations_humaines_sources.md.
- Sources non officielles à lire ensuite (non encore accessibles par API) : Norkin & White, « Measurement of Joint Motion » ;
  AAOS « Joint Motion » tables. Ne pas utiliser les valeurs de la fiche StatPearls poignet (formulaire seulement).
- Aucune contournement d'accès : seules les API officielles ont été utilisées.

## Recherche PSD (correctifs de pose), 2026-11-05
- Officiel : Lewis, Cordner, Fong, SIGGRAPH 2000 (PDF scribblethink.org) : δ exprimé dans le repère local, RBF
  gaussienne, poids w = (ΦᵀΦ)⁻¹Φᵀd, limite : pas de discontinuités, pas de traitement des sommets partagés.
- Non officiel (skinning.org, example-based.pdf) : PSD pondérée par les poids de peau (Kurihara & Miyata 2004) ; poussée
  de la correction dans l'espace de repos ; décroissance vers zéro hors des données.
- Application : masque binaire plutôt que poids d'os (erreur 115) ; cible ARAP partant de DQS.
- Non résolu : plis de la hanche à 105–120° (face fléchisseur). Recherche suivante : cible injective (sans repliement)
  et cibles anatomiques des plis (Hermawati & Marshall pour le coude).

## Recherche : mappages sans repliement et rotation répartie, 2026-11-05
- Officiel : Schüller et al. 2013 « Locally Injective Mappings » (page Utah) : énergie modifiée où les inversions sont
  pénalisées à l'infini ; pas de formule dans la page. Smith & Schaefer 2015 (bijectif, PDF tamu) : lu en résumé seulement.
- Non officiel (phys.org, 2016, vulgarisation) : Le & Hodgins, « Real-time Skeletal Skinning with Optimized Centers of
  Rotation » : centres de rotation par sommet, réduit l'effondrement LBS et le gonflement DQS. Non lu dans le texte
  original ; à relire via ACM.
- Test : rotation répartie (rotation_repartie.py) rejetée (erreur 116) ; cause analytique consignée.
- Recherche suivante : zones de plis acceptables (consigne utilisateur) pour classer les plis de la hanche, puis cible
  sans repliement (Schüller 2013) sur la face extenseur seulement.

## Recherche : plis de peau aux articulations, 2026-11-06
- Sources lues : (1) Computers & Graphics 2014, « Dynamic Skin Deformation using Finite Difference Solutions » (core.ac.uk
  42142683) : ne modélise pas les plis, les renvoie en travaux futurs. Hors sujet pour les plis. (2) Zhang, Sim & Tan,
  ICCS 2005, « Simulating Wrinkles in Facial Expressions on an Anatomy-Based Face » (Springer 11428848) : plis faciaux,
  pas plis d'articulation.
- Technique transférable (Zhang et al. 2005), à implémenter :
  - Profil périodique du pli à intégrale nulle sur un cycle (creux puis bosse) : modélise l'incompressibilité de la peau.
  - Amplitude proportionnelle à la compression ε (moyenne pondérée par cos de l'angle arête/direction de traction), nulle en
    traction (ε < 0) : un pli n'apparaît que là où la peau est comprimée.
  - Atténuation nulle au bord de la zone d'influence du muscle.
- Application prévue : pli fléchisseur (côté bassin-cuisse, zone où la référence X-Bot place son étirement) avec amplitude
  issue de la compression mesurée ; l'étirement côté extenseur reste borné par la rampe.
- Statut : pas encore implémenté ; à valider avec le critère complet et la zone de pli acceptable.

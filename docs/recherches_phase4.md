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

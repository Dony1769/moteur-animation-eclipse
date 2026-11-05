# Mémoire du moteur : ce qu'il faut toujours faire (combat, chute, victoire, son)

Chaque règle vient d'une lecture ou d'un test. Une règle non testée est marquée « à vérifier ».

## 1. Son calé sur les images
- Image Blender n (1 au début) = instant (n − 1) / 24 s dans le fichier son.
- Erreur courante : prendre n / 24 décale tout de 42 ms. Corrigé dans `engine/son.py` (piste à partir de n − 1).
- Les bruitages sont posés sur l'image exacte de l'impact (`evenements.json`), jamais à l'oreille.
- À vérifier par écoute ou par spectrogramme : le son arrive sur le contact visuel.

## 2. Chute au sol
- Ne jamais faire tomber un personnage en pivotant seulement autour des pieds : le corps s'enfonce dans le sol.
- Méthode : pendant la chute, calculer à chaque image la hauteur la plus basse du maillage (après déformation) et régler la position verticale pour que ce point soit exactement à z = 0.
- Vérifier : la hauteur minimale du maillage pendant la chute reste ≥ 0 (contrôle automatique à faire dans le script).

## 3. Pose de victoire
- Une pose se valide seulement par une image rendue en gros plan, lue à l'œil : bras levé, épée visible, tête droite.
- Test rapide : rendre une seule image à la fin du combat à petite résolution, puis regarder.

## 4. Arrêt sur impact (principe d'animation, article « Animating Sword Combat », sword-cartoon.pages.dev)
- Au contact, ralentir le mouvement puis le réaccélérer à la sortie.
- Une pose tenue 2 à 4 images après un coup fort renforce le choc. À faire par répétition de l'image d'impact dans la piste (à vérifier).
- Réaction immédiate de la cible, avec une intensité adaptée (le coup du gagnant est plus lourd).

## 5. Lisibilité des personnages
- Une teinte multipliée trop sombre rend un personnage invisible sur une roche sombre : garder une teinte claire (valeurs autour de 0,6 à 0,8 par canal).
- Vérifier chaque personnage sur au moins une image où il est seul au centre du cadre.

## 6. Rendu et contrôle
- Tests : tranches de moins de 20 minutes de calcul, images de contrôle regardées une par une.
- Ne jamais écrire « validé » sans avoir regardé l'image ou écouté le son.
- Le rendu complet ne se lance qu'après ces contrôles.

## Sources
- Blender 4.5, documentation de l'API Action (slots et canaux) : https://docs.blender.org/api/4.5/bpy.types.Action.html
- « Animating Sword Combat & Action Sequences with Real Weight and Impact » : https://sword-cartoon.pages.dev/posts/animating-sword-combat-action-sequences
- Blender Audio Sequences (wiki 2015) : https://archive.blender.org/wiki/2015/index.php/Manual/Audio_Sequences

## État au moment de cette mise à jour (à lire avant de reprendre)
- Son : décalage d'une image corrigé dans engine/son.py. Non écouté.
- Victoire : bras de A levé (rotation de 2,4 rad autour de X), vérifié par lecture des quaternions. Lisibilité à l'image non confirmée.
- Chute de B : BUG OUVERT. La hauteur au sol calculée donne −1,73 m, la position finale reste à z = 1,73. Ne pas lancer le rendu avant correction. Piste : vérifier les bornes du maillage évalué (ce qui inclut peut-être l'épée ou un os mal orienté), ou faire la chute par rotation simple sans compensation puis contrôler à l'œil.
- Teinte de B : éclaircie (0,62 ; 0,8 ; 1,0). Non vérifiée à l'image.
- Cadrage : plan de victoire passé en plan large.

## 7. Mesure des positions (quel que soit l'angle de la caméra)
- Sources lues : discussions Blender sur depsgraph et données évaluées (developer.blender.org, blenderartists) et documentation bpy_extras (world_to_camera_view).
- Règle 1 : `obj.bound_box` d'un objet déformé par une armature peut être périmé. Mesurer les sommets évalués : `obj.evaluated_get(depsgraph).to_mesh()`, puis transformer chaque sommet par la matrice monde (module `engine/mesure.py`, fonction `sommets_monde`).
- Règle 2 : la hauteur au sol d'un personnage est le minimum des z de tous ses sommets évalués. Une chute est correcte si ce minimum vaut 0 (à 1 mm près).
- Règle 3 : pour vérifier une position à l'image, projeter le point avec `world_to_camera_view` : x et y entre 0 et 1 = dans le cadre, distance positive = devant la caméra. Ceci marche pour tout angle de caméra.
- Règle 4 : toujours mesurer avant de rendre. Une valeur mesurée se consigne dans le journal de test.

## 8. Plans dédiés : caméra qui vise un point mesuré
- Sources lues : discussions Blender sur la contrainte « Track To » (blenderartists, archive.blender.org).
- Méthode : mesurer le centre du personnage (`mesure.sommets_monde`, moyenne des min et max), créer un point cible (empty) à cet endroit, placer la caméra à distance fixe devant le sujet, et ajouter une contrainte Track To vers la cible (axe −Z, haut Y).
- Contrôle obligatoire : `mesure.position_image` doit donner x et y entre 0,1 et 0,9 pour le centre du sujet. Si le sujet sort du cadre, reculer la caméra ou changer la focale.
- Le plan est lié à un marqueur de timeline (voir plus haut), donc il se déclenche à l'image voulue.

## 9. Vérifier le son sans l'écouter
- Méthode : mixer le WAV, calculer son enveloppe d'énergie par tranches de 10 ms, et repérer les débuts de bruitage (montées nettes).
- Comparer chaque début mesuré à l'instant attendu (image − 1) / 24 s. Tolérance : 15 ms. Un écart au-delà = erreur à corriger.
- Contrôle visuel complémentaire : spectrogramme en image (ffmpeg, filtre showspectrumpic), à regarder avec l'outil de lecture d'images.
- Ce contrôle prouve le calage, pas la qualité du bruit. La qualité reste à juger à l'oreille par l'utilisateur.

## 10. Valider une pose
- Une pose se valide seulement par une image rendue en plan rapproché, avec le sujet centré (règle 8) et le bras ou l'épée visibles.
- Si le sujet n'est pas lisible, ne pas écrire « validé ».

## État vérifié (dernière mise à jour)
- Chute de B : corps couché visible sur le sol, plan dédié à 1245 (contrôle image). Mesure : point le plus bas à 0 m.
- Victoire de A : profil, épée levée au-dessus de la tête, plan dédié à 1290 (contrôle image). Lisibilité confirmée à 640×270.
- Son : 60 événements contrôlés par mesure (engine/verif_son.py) : écart de 3,3 ms au plus, constant (fenêtre de mesure). Calage numériquement validé. La qualité sonore n'est PAS validée : à juger à l'oreille.

## 11. Créer des personnages et des objets (état honnête)

Sources lues :
- Poly Haven (polyhaven.com) : textures PBR photoscannées et modèles, licence CC0 sans restriction, résolution 8k, téléchargement direct sans inscription. Confirmé par la page.
- Documentation Blender Rigify (docs.blender.org, Basic Usage) : la page récupérée ne contenait que la navigation, donc la procédure exacte n'est pas confirmée. À vérifier par test dans Blender.
- Recherches sur la création de personnages dans Blender (shape keys, MakeHuman, Manuel Bastioni Lab, UniHuman) : pistes seulement. MakeHuman et Bastioni Lab ont des licences à vérifier avant usage (MB-Lab est AGPL et reste interdit par la règle du projet).

Ce que le moteur sait faire déjà (testé) :
- Modifier un personnage existant : taille, teinte, texture (Maria : teinte bleue, éclaircie à 0,62 / 0,8 / 1,0).
- Réutiliser le squelette Rigify du corps Human Base Meshes (CC0), avec ses contrôles FK, dans guerrier_rig.blend.
- Produire des clips procéduraux sur le squelette (marche, victoire).
- Exporter un FBX depuis Blender (à faire et tester).

Ce qui n'est PAS encore fait ni testé :
- Créer un personnage entièrement nouveau et réaliste à partir de rien.
- Appliquer Rigify à un maillage qui n'est pas Human Base Meshes (procédure à apprendre par test : métarig, ajustement, génération, poids automatiques, vérification de la déformation sur plusieurs poses).
- Peau et textures réalistes sur un nouveau visage : texture CC0 à choisir et contrôler à l'image.

Règle de travail :
- Pour un épisode, le script demande un personnage par son nom (dans le registre `engine/personnages.py`), avec ses variantes. Un personnage absent du registre n'est pas inventé à la volée : il est créé et contrôlé d'abord, puis ajouté au registre.
- Tout personnage nouveau passe par : mesure (hauteur, z minimal), contrôle d'image sous deux angles, contrôle de la déformation sur trois poses, puis seulement l'usage dans un épisode.

## 12. Rigify sur un nouveau maillage, visage, peau (recherches approfondies)
Les licences sont ignorées pour cet apprentissage ; elles restent à vérifier avant d'utiliser un asset dans une vidéo publiée.

### 12.1 Rigify sur un nouveau maillage (source : guide Neural4D, blog.neural4d.com, lu et résumé)
1. Edit > Preferences > Add-ons : activer Rigify (livré avec Blender).
2. Shift+A > Armature > Human Meta-Rig, puis Tab (Edit Mode).
3. Placer chaque articulation sur l'anatomie du maillage (épaules, coudes, genoux, hanches), de profil ; garder la symétrie (.L / .R, outil de symétrisation du menu Armature).
4. Armature Properties > Rigify > Generate Rig. Le rig généré porte les contrôles (IK bras et jambes, doigts). On anime ce rig, pas le metarig.
5. Sélectionner le maillage, puis shift-cliquer le rig généré, Ctrl+P > With Automatic Weights.
6. Contrôle : Pose Mode, bouger épaules, genoux, hanches. Vérifier le modificateur Armature dans Modifier Properties et les groupes de sommets dans Object Data.
7. Corrections : Weight Paint, pinceau Subtract pour retirer l'influence parasite, Blur pour adoucir, Weights > Normalize All.
- Statut : procédure lue, pas encore testée sur un maillage nouveau. Test à faire sur Maria ou sur un corps de test, avec contrôle de déformation sur trois poses.

### 12.2 Peau réaliste (source : Blender Base Camp, lu)
- Méthode : Principled BSDF, sous-surface (Subsurface) faible pour la translucidité, rayon faible pour les détails fins et plus grand pour les zones fines (oreilles), couleur de base proche du teint, couleur de sous-surface plus chaude, rugosité ajustée sous plusieurs éclairages, cartes de normales pour pores et rides, texture de veines sur Subsurface Color.
- Les valeurs chiffrées ne sont PAS dans la source : elles seront trouvées par rendus de test (balayage de Subsurface et Radius, un rendu par valeur, contrôle à l'œil sous deux éclairages).
- Rendu : réglages SSS modérés pour l'animation, sinon le temps de rendu explose.

### 12.3 Visage : blendshapes (sources : tutoriels et articles ARKit, lus en résumé)
- Méthode : créer des formes-clés (shape keys) pour les expressions de base, selon le jeu ARKit de 52 formes (tutoriel Blender Artists « 52 ARKit blendshapes »).
- Commencer par un petit jeu : sourire, fermeture des yeux, ouverture de la bouche, sourcils. Tester chaque forme seule, puis en combinaison.
- Statut : principe lu, pas encore testé. Le moteur utilise déjà les visages du rig Rain pour l'autre projet ; pour Maria, le visage n'est pas encore animé.

### 12.4 Ce qui reste à tester (dans l'ordre)
1. Rigify sur un corps de test : métarig, génération, poids automatiques, déformation sur trois poses.
2. Skin : balayage des valeurs de sous-surface, un rendu par valeur, choix à l'œil.
3. Visage : quelques formes-clés, contrôle image par image.

## 13. Apprentissage du 3 novembre : texte réellement lu

Règle appliquée : un sujet est « lu » seulement si le texte de la méthode a été obtenu. Les pages du manuel officiel Blender renvoient seulement la navigation via l'outil de lecture ; les tutoriels vidéo sans transcription ne donnent rien. Ces cas sont marqués « non lu ».

### 13.1 Cheveux (système de particules) : lu (résumé, pas testé)
- Création (Growing) : nombre et longueur des cheveux ; le trajet de chaque particule est calculé à l'avance.
- Style : réglages de physique de base, puis « Children » (cheveux enfants greffés) pour la forme.
- Retouche : Particle Edit Mode (peigner, couper, allonger à la main ; les réglages de particules sont alors désactivés).
- Dynamique : solveur de tissu appliqué aux cheveux.
- Rendu Cycles : shaders Hair BSDF ou Hair Principled BSDF ; Particle Instance Modifier pour des brins épais.
- État : lu. Valeurs exactes et test de rendu : NON FAIT.

### 13.2 Épée tenue en main (parentage à un os) : lu (procédure, pas testée)
- Créer des os « hand hold » détachés, parentés à chaque os de main (symétrie X activée) ; orienter ces os sans toucher à la main.
- Placer l'épée à la tête de l'os « hand hold » droit, puis la parenter à cet os.
- Prise (grip) : actions d'une seule image par main, doigts fermés autour de l'arme, jouées par-dessus les autres animations avec un masque limité aux os des doigts.
- Source : tutoriel écrit de rosetta.to (sebastianlague, « RPG graphics E10 »).
- État : lu. Test : NON FAIT. Le retrait d'une épée d'une main (lâcher, transfert) et le fourreau ne sont pas couverts par cette source.

### 13.3 Attaque à l'épée (animation) : lu (procédure, pas testée)
- Posture de repos pied avant, corps abaissé, petit mouvement de haut en bas sur une vingtaine d'images, première pose dupliquée pour boucler.
- Bras de l'épée ramené par-dessus l'épaule vers l'image 9-10, avance, levée du pied, trajectoire diagonale.
- Trajectoire de la lame : os temporaire à la pointe, chemin de mouvement affiché depuis l'image 9, à recalculer après modification.
- Retour à la pose initiale vers l'image 30 pour éviter le glissement du pied.

### 13.4 Ce qui est NON LU (sources vidéo seulement, ou pages du manuel inaccessibles)
- Cape et tissu : simulation, pin group, réglages mass / stiffness / damping / distance de collision : non lu (article blendernation = vidéo).
- Assise, IK des pieds, pose assise : non lu (aucune source textuelle obtenue).
- Lueur et effets magiques (émission, bloom, volumétrie) : non lu (résultats : liens et forums).
- Hard surface (Bevel, Weighted Normal) : non lu (le billet blendernation ne contient pas les réglages).
- Gain de maillage, caméra cinéma, rigging Rigify, squelette, textures : Rigify = guide Neural4D déjà lu (section 11) ; le reste non lu.
- Fourreau et retrait de l'épée de la main : non lu.

### Conclusion
Le moteur n'a appris de façon vérifiable que la partie cheveux (lu) et la prise d'épée et l'attaque (lues). Tout le reste reste à lire ou à tester. Les tests sont la prochaine étape : une épée parentée à la main et une lueur sur un objet, rendus et mesurés, avant toute écriture dans le moteur comme « appris ».

## 14. Apprentissage hors site Blender (sources externes lues)

Règle : un sujet est « lu » seulement si le texte de la méthode a été obtenu. Les titres, plans de cours et questions de forum ne comptent pas. Tous les points ci-dessous sont à TESTER après la livraison du MP4 (pas avant).

### 14.1 Modélisation hard surface (épée, armure) : lu (80.lv, article « hard surface tips » sur un pistolet)
- Blockout : tout modéliser en détail, nommer chaque pièce, flat shading pendant la phase.
- Bevels : Bevel modifier en « Limit Method : Weight », Bevel Weight sur les arêtes à arrondir ; désactiver Clamp Overlap et Loop Slide ; Outer Miter « Arc ».
- Normales : ajouter Weighted Normal (Weighting Mode Corner Angle, Face Influence) ; Triangulate avec Keep Normals avant bake.
- Booleans : soustraction avec modificateurs non destructifs réordonnables.
- Edge loops près des arêtes qui doivent rester vives ; creases pour esquisser, puis remplacer par des loops.
- Cavités : traitées au texturing (Substance), pas dans le modèle.
- Source : https://80.lv/articles/hard-surface-modeling-tips-tricks-for-creating-a-vintage-quirky-looking-gun
- Statut : lu. Test : À FAIRE (une lame d'épée).

### 14.2 Cheveux en cartes (hair cards) : plan de cours seulement (non lu en détail)
- Principe lu : des cartes plates avec texture de cheveux, plus légères que des mèches individuelles.
- Workflow (plan de cours PixelicaCG, 3 h de vidéo) : préparer les cartes, couche 1, lisser, tresses, couche 2, mèches finales, fusion, export.
- Statut : principe lu ; réglages et valeurs NON LUS.

### 14.3 Épée et fourreau sur un personnage (Unreal, forums) : question seulement
- Le piège décrit : si l'arme et le fourreau sont sur le même acteur, attacher l'arme à la main entraîne aussi le fourreau.
- Solution et réglages : NON LUS (réponses du fil non accessibles).
- Statut : piège lu ; méthode NON LUE.

### 14.4 Cape et vêtements (Marvelous Designer) : NON LU
- L'article gametextures a été redirigé ; l'outil de lecture a refusé l'URL de redirection (provenance).

### 14.5 Effets magiques lumineux : NON LU
- Article realtimevfx sur la couleur : seulement les règles de palette et de valeur (lu), pas l'émission, l'additif ou le bloom.
- Le fil polycount n'a pas pu être lu.

### 14.6 Assise, pose sur chaise, IK des pieds : NON LU
- Résultats : forums Unreal, Reallusion, Roblox, sans procédure lisible.

### Bilan
Lu et utilisable après test : hard surface (14.1) ; principe des cheveux en cartes (14.2) ; piège fourreau/arme (14.3). Non lu : cape, lueur/magie, assise, fourreau complet. Ces sujets demandent une autre source textuelle ou des notes fournies par l'utilisateur.

## 15. Réglages lus (documentation officielle Epic, Houdini) : à TESTER après le MP4

Règle : seuls les réglages présents dans le texte lu sont notés. Rien n'est inventé. Les valeurs Blender ne sont pas obtenues (la page API Blender ne renvoie que la navigation) ; elles seront lues dans Blender même (`bpy.types.ClothSettings.bl_rna.properties`) pendant le test.

### 15.1 Lueur magique (Unreal Niagara, « particules lumineuses ») : lu, valeurs lues
Source : dev.epicgames.com, « how to create particle effects that emit light in niagara ».
- Émetteur : Life Cycle Mode = System ; Spawn Rate = 500.
- Initialize Particle : Lifetime Mode = Random ; durée min 1.75, max 2.5.
- Couleur HDR : Red 0.1, Green 0.3, Blue 50 (valeur > 1 = émission).
- Sprite : Sprite Size Mode = Random Uniform ; min 2.5, max 8.0.
- Sphere Location : Sphere Radius 15.
- Add Velocity in Cone : Velocity Strength min 300, max 600.
- Particle Update : module Collision (laisser par défaut, corriger l'erreur « Fix Issue »).
- Render : Light Renderer, Radius Scale 5.0, Color Add (0, 0, 15).
- Non couvert par la source : matériau du sprite, bloom.
- État : lu. À transposer dans Blender (Cycles, émission HDR) puis tester : NON FAIT.

### 15.2 Attacher un objet à la main ou à la hanche (Unreal, socket) : lu
Source : udn.epicgames.com, SkeletalMeshSockets.
1. Ouvrir le skeletal mesh, Socket Manager, New Socket, choisir l'os.
2. Nommer le socket (unique dans ce mesh).
3. Régler l'offset : Relative Location (X, Y, Z), Relative Rotation (Pitch, Yaw, Roll), Relative Scale.
4. Pour le fourreau : socket sur la hanche (os du bassin), séparé du socket de la main ; l'arme et le fourreau sont des objets distincts (voir 14.3, piège lu).
- Équivalent Blender : os « hand hold » parenté (section 13.2). Les deux méthodes concordent : un point d'attache par os, décalage fixe.
- État : lu. Test : NON FAIT.

### 15.3 Cartes de cheveux (groom, Unreal) : réglages lus, valeurs absentes
Source : dev.epicgames.com, « setting up cards and meshes for grooms ».
- LOD : nombre de niveaux ; chaque LOD = strands, cartes ou maillage.
- Carte : Mesh, Guide Type (Generated ou Guide-Based), Material, Layout (Default ou Compact), textures optionnelles (Depth, Coverage, Tangent, RootUV, CoordU, Seed, Auxiliary), Group Index, LOD Index.
- Maillage : Minimum LOD par plateforme.
- Non couvert : UV, canal alpha, nombre de cartes, orientation, nommage.
- État : réglages lus. Valeurs : NON LUES.

### 15.4 Simulation de tissu (Houdini Cloth, paramètres par nom) : lu, sans valeurs par défaut
Source : sidefx.com, Cloth Configure Object.
- Overall Damping Ratio : 0 (aucune perte) à 1 (amortissement critique).
- Relative Stiffness / Relative Damping : entre 0 et 1 pour étirement, cisaillement et flexion (Weak Bend, Strong Bend).
- Surface Mass Density : masse par m² (pas de valeur par défaut).
- Collision Radius (appelée Thickness) : ne pas dépasser 1 % de la longueur moyenne des arêtes.
- Collide within this object : auto-collision ; Friction : 0 = sans friction.
- Coutures (seam angle), attribut quality.
- Pas de paramètre « pin » documenté sur ce nœud.
- Équivalent Blender (ClothSettings) : à lire dans Blender au moment du test ; NON LU.
- État : concepts lus. Valeurs Blender : NON LUES.

### 15.5 Non lu (à chercher ensuite)
- Assise et IK des pieds : aucune source Epic/Blender textuelle obtenue (forums seulement).
- Pin de cape dans Blender (groupe de sommets, Pin Stiffness) : vidéos seulement.
- Peau (subsurface), visage (formes-clés) : voir section 12 (lus en résumé, valeurs non lues).

## 16. Caméra, composition, étalonnage, sound design, synchro labiale (sources hors site officiel)

Règle : « lu » = texte de la méthode obtenu. Tout ce qui suit n'est PAS testé ; le test se fera après la livraison du MP4.

### 16.1 Focales (Cinema 4D, School of Motion) : lu
- 36 mm : grand-angle (valeur par défaut C4D), accentue la vitesse sur l'axe Z.
- ~50 mm : objectif moyen, proche de la vision humaine.
- ~150 mm : téléobjectif, compresse l'espace, bon pour les travellings latéraux et l'orbite.
- Visages et personnages : éviter le grand-angle rapproché (déformation).
- Alterner plans larges et longs pour le rythme.
- Dolly zoom : passer d'un grand-angle à un long objectif, subtilement.
- Décor : construire seulement ce qui est visible par la caméra (« fake walls »).
- Source : https://www.schoolofmotion.com/blog/professional-guide-renders-look-better-choose-focal-length

### 16.2 Composition (filmlifestyle) : lu, partiellement
- Règle des tiers, lignes directrices, équilibre asymétrique vs symétrique.
- Plans : gros plan (intimité), large (établir le lieu), plongée (vulnérabilité), contre-plongée (puissance), plan hollandais (tension), profondeur de champ.
- Mouvements : panoramique, tilt, travelling, dolly, grue ; chaque mouvement doit être motivé.
- Effet Koulechov : l'ordre des plans change l'émotion.
- Non lu : headroom, lead room, règle des 180° (non traités dans la page).
- Source : https://filmlifestyle.com/shot-composition/

### 16.3 Continuité de caméra (article sur les règles de montage) : lu
- Règle de l'axe : garder le personnage du même côté de l'écran d'un plan à l'autre.
- Champ/contrechamp : les regards vont dans des directions opposées.
- Déplacement : garder la même direction d'écran d'un plan à l'autre.
- Source : article en anglais (lien conservé dans l'historique de la session), relu.

### 16.4 Rendu cinématique 3D (RenderHub) : lu, sans valeurs
- Éclairage : scène de nuit avec lumières dures sur le sujet, fond diffus ; bleu, vert possibles.
- Étalonnage : corriger balance des blancs, exposition, saturation ; ombres froides, hautes lumières chaudes.
- Format cinéma : bandes noires horizontales, léger flou sur les bords.
- Aberration chromatique : faible.
- Non lu : valeurs chiffrées (bandes, aberration, couleurs), grain, flou de mouvement.

### 16.5 Sound design (bruitages de sabre, armure) : lu, sans valeurs
- Enregistrer des sources réelles, plusieurs variantes (frotter un tissu pour un « whoosh »).
- Doubler, transposer (pitch vers le haut et le bas), compresser.
- Superposer des couches : copies transposées, EQ légèrement différent à chaque couche, réverbération différente à chaque couche.
- Tester plusieurs objets métalliques pour le bruit d'armure.
- Non lu : semitons, réglages EQ, durées de réverbération.
- Source : https://www.moddb.com/tutorials/making-sound-effects-for-video-games-4

### 16.6 Synchronisation labiale expressive (JALI) : lu, en grandes lignes
- Entrées : audio + transcription.
- Phonème → visème : correspondance multiple (un son peut avoir plusieurs formes).
- Décomposition en deux composantes : mâchoire (jaw) et lèvres (lip).
- Pilotage d'un rig facial par unités d'action FACS.
- Sortie modifiable par l'animateur.
- Non lu : algorithmes exacts de jaw/lip.
- Source : https://www.dgp.toronto.edu/~elf/jali.html

### 16.7 Non encore lu
- Voix de personnage (synthèse, clonage) : pas de source de méthode lue.
- Effets magiques volumétriques, grain et flou de mouvement : non lus.
- Étalonnage LUT détaillé : résultats de liens seulement.

## 17. Voix, flou de mouvement, LUT, volumes : statut après lecture (à TESTER après le MP4)

### 17.1 Clonage de voix zero-shot (MiniMax-Speech, arXiv 2505.07916) : lu en partie
- Entrée : un extrait audio de référence, sans transcription, de longueur variable (durée non précisée).
- Speaker encoder : transforme la référence en un vecteur de taille fixe qui conditionne le Transformer ; capte timbre et prosodie.
- Entraînement : l'encodeur est entraîné avec le Transformer (pas pré-entraîné).
- Règle : la référence doit être différente de la cible (sinon fuite sémantique).
- Inférence : tokens audio à 25 tokens/s, conditionnés par le vecteur ; mode one-shot optionnel avec une paire texte-audio.
- Chiffres du texte : 32 langues ; test 24 langues × 100 phrases ; compression PCA à 128 dimensions.
- Non dit : dimension du vecteur, nombre de paramètres, volume total des données.
- Statut : méthode lue ; valeurs d'entraînement NON LUES.

### 17.2 Flou de mouvement (angle d'obturation, Insta360) : lu, avec valeurs
- Vitesse d'obturation = 1 ÷ (cadence × angle/360).
- 180° : standard ; 24 i/s → 1/48 s ; 25 i/s → 1/50 s ; 30 i/s → 1/60 s ; 60 i/s → 1/120 s.
- 90° : flou réduit, mouvement plus saccadé ; 270° : flou plus marqué.
- Angle 45–90° pour l'action, au-delà de 180° pour les ambiances.
- Statut : lu avec valeurs. Le grain (intensité) reste NON LU.

### 17.3 LUT (méthode d'étalonnage, Pixflow) : lu, avec valeurs
- Types : calibration, transform (LOG vers Rec.709), creative.
- 1D : luminance seule ; 3D : cube RGB, teinte, saturation et luminance ensemble (le standard cinéma).
- Grilles : 17, 33 (standard pro), 65. Format .cube (3D presque toujours).
- Ordre : scopes → correction de base → LUT de transformation → corrections secondaires → LUT créative → finitions.
- Valeurs : opacité de la LUT créative 60 à 80 %. Luminance 100 = surexposition, 0 = noir pur.
- Statut : lu avec valeurs. Les espaces AgX et Filmic dans Blender : NON LUS (seulement des commits de code).

### 17.4 Volumes et brouillard lumineux (Blender) : NON LU
- La page du manuel Blender renvoie seulement la navigation ; pas de texte sur Density, Anisotropy, Absorption, Scatter, Emission.
- Statut : NON LU. À chercher ailleurs (article de blog ou thread de forum avec valeurs).

## 18. Sujets 2 à 8 : rigging, skinning, texture, visage, animation, secondaire, environnement

Règle : « lu » = texte de la méthode obtenu. Rien ici n'est testé ; les tests viendront après le MP4.

### 18.2 Rigging (contrôleurs IK/FK, contraintes, contrôles faciaux) : NON LU ce tour
- Recherches faites : IK/FK switch Rigify, contrôles faciaux. Résultats = liens vers la doc Blender (navigation seulement) et des forums.
- À faire : lire un tutoriel texte sur IK/FK (Rigify) et sur les contrôles faciaux.

### 18.3 Skinning et weight painting : lu (article 13 étapes)
- Nommer les os en L/R pour le miroir ; binding automatique (≈ 70–80 % correct, retouche ensuite).
- Influences par sommet : mobile 2–4, console/PC 4–8 (4 le compromis le plus courant).
- Retouche sur épaules, hanches, coudes, genoux ; heat map (bleu = 0, rouge = 1).
- Miroir pour peindre un côté, désactiver pour la finition ; verrouiller les os stables avant de peindre les voisins.
- Normalisation : somme des poids = 1.0 (Normalize All).
- Retirer les poids < 0.01 pour l'export.
- Défauts : candy wrapper (os de torsion ou blend shapes), effondrement articulaire (DQS aux articulations très fléchies), perte de volume.
- Blend shapes correctifs : 10 à 20 pour les articulations majeures, pilotés par l'angle (au coude, au-delà de 90°).
- Test : animation de 60 s qui parcourt toutes les articulations.
- Source : https://mocaponline.com/blogs/mocap-news/weight-painting-skinning-guide
- Statut : lu. Test : À FAIRE.

### 18.4 Texturing, matériaux, peau, cheveux : peau lue (sans valeurs), cheveux non lus
- Peau (subsurface) : couleur de diffusion distincte de l'albédo ; rayon par canal RGB (le bleu diffuse plus loin) ; rayon plus petit dans les zones fines (oreilles, doigts) ; thickness map (blanc = épais) bakée depuis un high-poly ; calibrage itératif sous lumière neutre puis HDRI.
- Source : https://aitextured.com/articles/creating-calibrating-accurate-subsurface-scattering-maps-pbr-materials.html
- Statut : méthode lue ; valeurs NON LUES.
- Cheveux shader : non lu.

### 18.5 Animation faciale (yeux, visèmes, clignement, sourcils) : lu (DAZ, méthode et noms)
- Visèmes : 15 formes (SIL, PP, FF, TH, DD, KK, CH, SS, NN, RR, AA, E, I, O, U). Minimum utile : PP, FF, AA, E, I, O, U.
- Regard : 4 contrôles par œil (haut/bas, gauche/droite) ; Genesis 9 : regard par os (tête, œil gauche, œil droit).
- Ordre de réglage : clignement → yeux → sourcils → visèmes → poids.
- Sourcils : détection par mots-clés (brow + raise, down, furrow…).
- Pas de valeurs numériques de poids dans la source.
- Source : arawn-software-publishing (gitbook, DAZ, Crystal LipSync).
- Statut : lu (méthode et noms). Valeurs : NON LUES. Note : c'est une doc de plugin DAZ ; les noms ne s'appliquent pas tels quels à Blender.

### 18.6 Animation de personnage (marche) : lu (article), valeurs partielles
- Cycle : 8 à 16 images ; à 24 i/s, 12 images par pas soit 24 pour le cycle complet.
- Quatre poses clés : contact, descente, passage, montée.
- Rebond pendant la montée ; symétrie de la seconde moitié ; bras à l'opposé des jambes ; hanches et épaules en sens inverse ; tête discrète ; contrôle des pieds.
- Première et dernière image identiques pour une boucle.
- Source : https://prolificstudio.co/blog/walking-animation/
- Statut : lu. Amplitudes NON LUES. Course et sauts : NON LUS.

### 18.7 Mouvement secondaire (cheveux, vêtements, accessoires, inertie) : lu (ordre et méthode), valeurs NON LUES
- Ordre : mouvement primaire (torse) puis overlapping puis follow-through.
- Décalage : analyser des références image par image.
- Rig : segments liés, IK pour l'extrémité, FK par segment, switch IK/FK, dynamique automatique.
- Source : https://blog.cg-wire.com/follow-through-overlapping-action
- Statut : lu. Décalage en images et amortissement : NON LUS.

### 18.8 Environnement et éclairage : lu (méthode et ratios)
- Trois points : clé à 45°, remplissage à 50 % de la clé, contre-jour pour détacher (puissance non lue).
- Types : point, sun, spot, area ; area = ombres douces.
- HDRI seul : plat ; compléter par soleil et lumières d'aire ; lumières d'aire proches de la température du soleil.
- Éviter la lumière frontale comme clé ; plusieurs petites sources plutôt qu'une seule grande.
- Light linking pour cibler les objets.
- Sources : https://uhiyama-lab.com/en/notes/blender/lighting-fundamentals-realistic-light/ et https://schoolofmotion.com/blog/lighting-scene-with-hrdi-and-area-lights
- Statut : lu. Puissances absolues et tailles : NON LUES.

### Bilan 2 à 8
- Lu avec méthode utilisable : skinning (3), visèmes (5), marche (6), secondaire (7), éclairage (8), peau (4, sans valeurs).
- Non lu : rigging IK/FK et contrôles faciaux (2), cheveux shader (4), course et sauts (6), valeurs de secondaire, puissances d'éclairage.

## 19. Pipeline complet : son final, champ/contrechamp, encodage, compositing, topologie (statuts)

Règle : « lu » = texte de la méthode obtenu. Rien ici n'est testé ; tests après chaque bloc.

### 19.1 Son final, dialogue et loudness : lu (valeurs)
- Streaming : -14 à -16 LUFS (Spotify et YouTube ~-14, Apple Music -16) ; broadcast EBU R128 -23 LUFS, ATSC A/85 -24 LKFS.
- True peak : -1 dBTP (streaming, EBU), -2 dBTP (ATSC).
- LRA max broadcast : 18 LU.
- Pics avant masterisation : entre -6 et -3 dBFS.
- Méthode : mixer avec headroom, limiteur true peak à -1 dBTP, mesurer le LUFS intégré, gain linéaire = cible - mesure, revérifier le true peak après gain.
- Non lu : cibles séparées dialogue / musique, règles de ducking chiffrées.
- Source : https://www.soundbridge.io/loudness-normalization-a-mixing-and-mastering-guide

### 19.2 Champ/contrechamp, dialogue : lu (règles)
- Axe d'action, ne jamais franchir la ligne ; plan de référence moyen d'abord.
- Géographie fixe (A à gauche reste à gauche) ; regards en raccord (eyeline match) ; le plus grand regarde légèrement vers le bas, le plus petit vers le haut.
- Échelle selon l'émotion ; angle selon le rapport de force ; plans de réaction pour le sous-texte.
- Source : https://blog.indiecinema.co/shot-reverse-shot/
- Distance à l'axe : non lue.

### 19.3 Encodage H.264 (ffmpeg) : NON LU
- La page ffmpeg a refusé l'accès (protection anti-robot). À retenter par une autre source écrite.

### 19.4 Retargeting et bibliothèque de mouvements (Mixamo, Unreal) : NON LU
- Résultats : forums et une fiche de vente. À retenter.

### 19.5 Compositing Blender (glare, bloom, étalonnage nœuds) : NON LU
- Résultats : billets de vente et pages de blog sans méthode lisible. À retenter.

### 19.6 Topologie de personnage (visage, bouche, yeux) : NON LU
- Résultats : wiki Reallusion (topologie CC) et forums polycount. À lire la page Reallusion « CC Face Topology Guide ».

### 19.7 Restant du pipeline à lire
- Dialogue (synthèse, phonèmes) : voir section 17.
- Motion library (bibliothèque réutilisable) : 19.4.
- Montage (rythme) : partiellement lu (section 16.2).
- Export final : 19.3.

### 19.8 Topologie du visage (guide Reallusion CC) : lu (règles, sans nombre de boucles)
- Yeux : arcade sourcilière, pli de paupière supérieure aligné sur le pli réel, bord externe des paupières (point clé), globe non déformé ; cornée semi-transparente.
- Bouche : plis des narines, crêtes internes des narines, plis internes des joues (ligne max), philtrum, contour des lèvres (ligne max), bord rouge, commissures sans croisement, répartition régulière des sommets.
- Symétrie : coins des yeux, commissures, extrémités des sourcils.
- Contrôle : morph vers la base puis retour pour repérer les zones compressées ; tests d'animation courts pendant la modélisation.
- Source : https://wiki.reallusion.com/Content_Dev:CC_Face_Topology_Guide
- Statut : lu. Nombre de boucles : NON LU.

### 19.9 Encodage H.264 (guide académique) : lu (valeurs)
- CRF 18 recommandé (23 jugé bas en qualité) ; preset medium ou slow suffisent.
- pix_fmt yuv420p (web, QuickTime) ; profil high pour compatibilité ; -movflags faststart pour le streaming.
- Tune : animation (aplats de couleur), film (prises réelles), grain.
- Couleur : bt709 (primaries, colorspace), trc iec61966-2-1 pour sRGB.
- Dimensions paires : non traité ici (déjà appliqué via pad dans le pipeline).
- Source : https://academysoftwarefoundation.github.io/EncodingGuidelines/Encodeh264.html
- Statut : lu. Test : À FAIRE pour le prochain MP4 (CRF 18, tune animation, faststart).

### 19.10 Retargeting Mixamo vers un autre rig (Auto-Rig Pro, BlenderNation) : lu (procédure, sans réglages de pieds)
- Générer le rig cible, match to rig ; FBX Mixamo : Alt+S pour l'échelle en pose de repos.
- Source = armature Mixamo (freeze armature) ; cible = rig généré ; Build bones list ; preset de correspondance Mixamo.
- Nettoyage : effacer les clés à remplacer ; push down au NLA pour corriger ; effacer les clés du haut du corps pour ne garder que jambes et pieds.
- Correction des pieds et de la racine : NON LUE (l'article ne la traite pas).
- Statut : lu (procédure). Test : À FAIRE.

### 19.11 Fumée et effets lumineux (Cycles) : méthode lue, valeurs NON LUES
- Principled Volume : une seule node pour fumée et flammes (texte lu) ; réglages chiffrés dans une vidéo, non lus.
- Particules plutôt que volume : animer la taille des particules sur leur durée de vie ; plans de fumée transparents ; environ 150 plans cités par un lecteur (remarque, pas une règle).
- Statut : méthodes lues ; valeurs NON LUES.

### 19.12 Lecture sans résultat utilisable ce tour
- Principled Hair BSDF : page de manuel (navigation seulement).
- Fourreau et sangle : forums et articles sans procédure.

## 20. Correction des pliages : méthode lue et mesurée (étape 3, suite)

Sources lues (réseau) :
- Pose Space Deformation, cours INRIA (imagine.inrialpes.fr/people/Francois.Faure/htmlCourses/PoseSpaceDeformation.html) : une correction est une différence par rapport à la forme de base, interpolée selon la pose. Le cours ne donne ni le noyau ni la procédure de choix des poses.
- Guide DCC skinning (seeles.ai) : le LBS (déformation linéaire) fait s'effondrer le coude (« elbow collapse »). Remèdes listés : os de torsion, transition repeinte, DQS (dual quaternion) au milieu de l'avant-bras, petite correction pilotée plutôt que gonflement global des poids.
- Manuel Blender, formes correctives (docs.blender.org/manual/es/2.92/addons/animation/corrective_shape_keys.html) : clé de forme pilotée par un os.

Ce qui est mesuré (HBM, corps 1,69 m) :
- Témoin : 0 pli au repos, avec ou sans correction.
- Élargir la transition seule : 47 → 39 replis à 90° (-17 %). Insuffisant.
- Correction par décalage vers l'intérieur (« moins normale ») calibrée à 90° : bras 24 → 3 replis à 90°, 6 → 1 à 60°, 0 au repos.
- Calibrée à 120° : échec (27 replis restants). Limite : une seule forme ne couvre pas 120°.
- Vérification : le calcul explicite LBS reproduit le modificateur Blender à 0,0005 mm.

Erreurs commises pendant cette étape et règle à retenir (voir docs/erreurs_apprises.md).

## 21. Os d'aide à l'épaule (répartition de rotation), mesuré

Méthode combinée : distribuer la rotation du bras sur un os d'aide (idée des os de torsion lue dans le guide DCC) + contrainte Copy Rotation de Blender à influence 0,5, puis recalcul des poids par chaleur.
Mesure LBS sans clé, bras gauche seul : 90° 24 -> 12 replis ; 120° 31 -> 19 ; 479 sommets pondérés sur l'os d'aide (max 0,5). Rapports : docs/rapports/hbm_os_aide_epaule.json et hbm_os_aide_temoin.json.

## 22. Contrôle de gonflement (volume et étirement), mesuré

- Méthode : volume signé du maillage évalué par Blender (modificateur Armature actif, Multires désactivé) par rapport au volume de repos, et étirement des arêtes (longueur pose / longueur repos). Module : `engine/skinning/controle_gonflement.py`.
- Résultat principal : le DQS « preserve volume » ne conserve pas mieux le volume du bras que le LBS (0,940 contre 0,961 à 120°). Il n'est pas adopté.
- Défaut trouvé : les clés correctives créent des arêtes très étirées (5,9 fois à 120° contre 3,4 sans clés). Cause : décalage limité aux sommets repliés, donc frontière brutale.
- Essai de correction : lissage laplacien du champ de décalage. Il retrouve l'étirement de référence mais affaiblit la correction des replis. Aucun pipeline ne domine : le pipeline de référence reste sans lissage, en attendant une méthode qui satisfasse les deux critères.
- Sources : méthode standard de lissage laplacien ; non relue dans cette session. Les références précédentes (sections 20 et 21) restent les seules sources lues.

## 23. Contrôle visuel : vérifier l'état rendu
- Une image de contrôle doit reproduire l'état exact mesuré (pose, clés, couleurs). Une image trompeuse est pire que pas d'image.
- Méthode : `engine/skinning/rendu_etirement.py` (carte d'étirement par sommet, rendu Workbench en arrière-plan, sans GPU).
- Référence : docs/rapports/visuel_etirement_bras120_profil.png.

## 24. Comparer deux squelettes par liste de noms avant de conclure à un écart
- Un écart de comptage (69 os contre 65 annoncés) se résout en comparant les listes exactes d'os, pas en devinant.
- Méthode : exporter les noms d'os des deux fichiers dans Blender (`liste_os.py`, sortie JSON), puis comparer les ensembles, après retrait du préfixe `mixamorig:`.
- Résultat : les 65 os du corps sont communs ; les 4 en plus sont des os de visage et d'arme. Le squelette de référence est donc le même.

## 25. Valider un mouvement importé : unités, racine, slot, fondu
- Trois erreurs de mesure successives ont donné des résultats impossibles avant le bon. Ordre de contrôle à suivre pour tout clip importé : (1) distances en mètres monde ; (2) déformation relative à la hanche ; (3) slot d'action affecté et pose visible ; (4) seulement ensuite, transitions.
- Transitions : le passage direct entre deux clips crée un saut ; un fondu NLA de 12 images le réduit au niveau du mouvement normal.
- Méthode : `engine/validation/test_maria_anim.py` (sorties dans le dossier scratchpad du test). Résultat : déformation OK, transition OK (ratio 1,02, seuil 3, valeur fixée a priori).
- Sources : aucune source externe lue dans cette section ; méthode de fondu NLA de la documentation Blender 4.5, non relue dans cette session.

## 26. Pic de 40 cm par image : mouvement réel, pas artefact de skinning
- Constat : le pic de déplacement par image est porté par des extrémités (orteils, doigts, pied), avec un poids dominant de 1,0. Le sommet suit son os à 0,01 m près (ex. 0,40 contre 0,36 m par image pour l'orteil gauche).
- Cause : le clip Running ne compte que 16 images pour un cycle complet ; un pas par image est donc grand. Ce n'est pas une déformation parasite.
- Limite : la mesure par image dépend de l'échantillonnage du clip. Les comparaisons se font entre clips, pas en valeur absolue.

## 27. Transitions : trois paires de clips validées
- Idle → Running : ratio 1,02 (fondu 12 images).
- Idle → Jump : ratio 1,64.
- Running → Sword_Slash : ratio 1,45.
- Seuil 3 fixé avant les mesures : les trois paires passent. Le test accepte désormais `CLIP_A` et `CLIP_B`.
- Le nom du contrôle `running_deformation` est historique : il mesure le clip B.

## 28. Contrôleurs et rig facial de Maria : inventaire, pas validation
- Contrôleurs absents (5) : IK mains, IK pieds, cibles de pôle, commutation IK/FK, contrôle racine. Constat, non corrigé ici : leur construction relève de l'étape 5.
- Rig facial absent : 0 forme-clé, 0 os facial. Le moteur ne sait pas encore le faire ; c'est l'étape faciale (≥ 15 expressions).
- Règle : un inventaire complet n'est pas une fonctionnalité. Le statut « absent » est reporté tel quel.

## 29. Retargeting et export animé de Maria (Test A, items 9 et 12)
- Couverture : les 52 os animés par le clip Running existent tous sur le squelette de Maria (65 os). Les 13 autres os ne sont pas animés par ce clip.
- Export : Maria + Running exportés en FBX, réimportés ; même nombre de sommets (8 094), 65 os, 4 influences au plus, mouvement identique à 0,26 mm.
- Méthode : `engine/validation/test_maria_export.py`. Erreurs de procédure 37 et 38 consignées.
- Limite : un seul clip exporté ; l'export des autres clips et de la transition reste à tester.

## 30. Test B, items 1 à 4 : corps HBM sans skinning (source brute)
- Source : `GEO-body_male_realistic` extrait du bundle HBM (`human_base_meshes_bundle.blend`, copié avant lecture).
- Constats : 10 582 sommets, 10 590 faces (10 570 quads), 0 bord ouvert (maillage fermé), 1 jeu d'UV, 0 groupe de sommets, aucun parent. Un modificateur Multires est présent : ce n'est pas du skinning.
- Dimensions : hauteur 1,690 m, pied à z = −0,006 m, envergure X 0,881 m (bras écartés, pas la largeur d'épaules), profondeur 0,290 m.
- Méthode : `engine/validation/test_hbm_corps.py`. Items 5 à 15 non faits : articulations, armature, poids, contrôleurs, tests de flexion, visage, animations, export.
- Règle : mesurer la largeur sur un corps à bras écartés donne l'envergure, pas la largeur d'épaules. Nommer la mesure selon ce qu'elle est.

## 31. Test B, item 5 : articulations du corps HBM
- Genou : validé. La section de jambe la plus fine (profondeur) est à 0,290 h ; l'estimation anatomique donne 0,285 h (écart 0,005 h, seuil 0,03).
- Non validées (estimées par proportions) : cheville, hanche, épaule, cou, tête. Aucun contrôle géométrique fiable n'a été écrit pour elles ; elles restent marquées « estimée ».
- Symétrie X après recentrage : x min −0,440 m, x max +0,440 m.
- Méthode : `engine/validation/test_hbm_articulations.py`. Erreur 39 consignée.
- Limite : la métrique de profondeur a été choisie après un échec ; à confirmer sur un second corps (le corps féminin du bundle).

## 32. Corps féminin confirmé, bras mesurés
- Genou féminin : section la plus fine (profondeur) à 0,280 h, contre 0,285 h estimé (écart 0,005 h). La métrique de profondeur est donc confirmée sur un second corps.
- Bras masculin : pose inclinée mesurée (épaule 0,74 h → poignet 0,46 h). Chemin consigné dans le rapport du test. Le coude n'est pas encore validé.
- Prochaine étape : item 6 (armature). Commencer par le tronc et les jambes ; les bras attendent un coude validé. Erreur 40 consignée.

## 33. Test B, item 6 partiel : armature du tronc et des jambes
- Créée : 11 os (Hips, Spine, Chest, Neck, Head ; LeftUpLeg, LeftLeg, LeftFoot ; symétriques à droite). Racine Hips. Aucun os de longueur nulle. Symétrie des chemins de jambe : 7,8 mm.
- Mesuré : chemin des jambes (centroïdes bornés à |x| < 0,25 m) ; pointe du pied (sommet le plus avancé près du sol). Estimé : hanche (altitude 0,53 h), tronc (fractions de hauteur).
- Contrôle d'intérieur : milieu de chaque os dans le maillage (parité des intersections de rayons, sur X pour les membres). C'est un test faible : un point par os, pas le volume entier.
- Non fait : bras (coude et poignet non validés), poids automatiques (item 7), contrôleurs (item 8).
- Méthode : `engine/validation/test_hbm_armature.py`. Erreurs 41 à 44 consignées.

## 34. Intégration Ara 3D Gen : génération externe, testée par notre importeur
- Adaptateur : `engine/generation/ara_adapter.py` appelle l'export Ara (`npm run export`, preset « Athletic woman ») et écrit une provenance (commit `a4947ff`, licence code MIT, données CC0). Dépendance externe, non copiée.
- Le FBX produit (69 os, 10 matériaux, 1,70 m, 4 influences au plus, poids normalisés, zéro anomalie) passe notre importeur comme un personnage externe. Test : `engine/validation/test_ara_integration.py`.
- Une seule correction nécessaire : la convention Mixamo sans préfixe (erreur 45), désormais reconnue par ensemble de noms de référence. Maria inchangée.
- Limites : seul le FBX statique est importé (pas de clips Ara) ; le dépôt Ara est attendu dans le dossier de travail (variable ARA_REPO) et doit être recloné si la session est réinitialisée.

## 35. Optimisation des poids de skinning (ARAP-LBS) : premier résultat validé, pas encore adopté
- Méthode : poids optimisés pour réduire la déformation des arêtes sur des poses d'exemple, LBS standard (exportable). Inspirée d'ARAP-LBS (Thiery et al.).
- Témoin : le harnais numpy reproduit exactement la mesure Blender du projet (étirement 3,3584 à 120°).
- Meilleur résultat validé : bras entraîné sur 60/90/105°, testé sur 120° : étirement max 3,36 → 1,65, compression min 0,11 → 0,55, mouvement du bras conservé (confirmé dans Blender).
- Échecs consignés : chaînes conjointes, masque par os, exposant 4, séquence bras/jambe (erreurs 46 à 48). Aucune variante n'améliore les trois chaînes à la fois.
- Non adopté : le pipeline de référence reste en vigueur. Prochaine étape : pondération par longueur de repos et garde de rejet.
- Sources lues : ARAP-LBS (Thiery) ; billet non officiel sur le « candy wrapper » (https://jessyleite.dev/posts/blender-candy-wrap-twist-deformation/) qui recommande l'os de torsion pour l'export, ce qui rejoint notre test d'os d'aide.

## 36. Pondération par aire et garde : bras amélioré, jambe non résolue par les poids
- Pondération par aires barycentriques des arêtes (erreur 49) : bras à 120° 1,65 → 1,63 (test). Marginal mais propre.
- Entraînement conjoint 60/90/105 avec garde : passe la garde, mais la jambe régresse à 120° (erreur 50). Entraînement 60/90/120, testé à 105° : bras 3,00 → 1,45 ; avant-bras 1,78 → 1,37 ; jambe neutre (1,23 → 1,24). Garde refusée : jambe à 120°, 1,27 → 1,49.
- Conclusion : aucun réglage de poids n'améliore les trois chaînes sans dégrader la jambe. Le maximum de la jambe est local (cheville, puis genou) : il faut un correctif géométrique dédié (genou, cheville), pas une optimisation globale.
- Non adopté. Pipeline de référence inchangé. Prochaine étape : garde à angles de validation, puis correctif dédié à la jambe.
- Sources lues : brevet US10061871B2 (pondération par aires barycentriques, échantillonnage de poses, ancrage aux extrémités) ; Jacobson & Baran 2012 (poids cotangents, pas de règle de longueur).

## 37. Mesure de plis : calibrer avant de conclure
- Un comptage de faces repliées calculé en numpy a donné des milliers de plis, là où le projet en compte une dizaine. Cause : la normale de repos était comparée sans la rotation de l'os dominant (erreur 51).
- Méthode : reproduire exactement la définition du projet (vote des sommets pour l'os dominant, normale de Newell, rotation par la matrice 3×3 normalisée), puis comparer aux comptes Blender sur le même fichier. Ici l'écart maximal est de 4 faces.
- Résultat : les poids du haut du corps réduisent l'étirement du bras mais doublent les faces repliées. Non adoptés. Le critère de garde doit inclure les plis.
- Outil : `engine/skinning/plis_numpy.py`.

## 38. Garde de plis et limites des poids seuls
- La garde contrôle désormais l'étirement et le nombre de plis, sur entraînement et validation (`engine/skinning/optimiser_poids.py`, `garde_max`).
- Recherche : ARAP-LBS n'a pas de contrôle de plis ; son échantillonnage est limité à roulis ±60° et torsion ±10°. Au-delà, les poids seuls ne suffisent pas : prévoir des formes correctives pour le coude et l'épaule, comme `construit_final.py`.
- Méthode de contrôle : toute garde d'optimisation doit mesurer les plis sur des poses non utilisées à l'entraînement.

## 39. Formes correctives : rester déterministe et tester hors entraînement
- Les clés correctives donnent 13 plis à 120° contre 28 à 32 pour les poids seuls : la voie à suivre pour le coude et l'épaule.
- Source non officielle (projet Maya, correctif appris) : intéressante mais métriques non définies et test non exclu de l'entraînement. Non retenue comme preuve.
- Prochaine étape : correctifs déterministes par angle, calculés depuis la différence cible − LBS, puis validés hors entraînement avec la garde (plis et étirement).

## 40. Correctifs ARAP déterministes : première validation hors entraînement
- Cible ARAP (locale-globale) par pose, correctif = cible − LBS, interpolé entre angles d'entraînement. Test à 75° et 105°, jamais utilisés pour construire les correctifs.
- Résultat numpy : plis et étirement améliorés sur les trois chaînes. Témoin 0° exact.
- Piège : 12 itérations ne suffisent pas (erreur 54). Toujours vérifier la convergence.
- À faire : vérification Blender, puis garde (plis et étirement) avant toute adoption.

## 41. Validation Blender des correctifs : LBS exact, correctifs en formes-clés
- Le LBS de Blender (modificateur Armature) et le LBS numpy coïncident à 2e-6 près : le pipeline numérique est fiable.
- Les correctifs ARAP appliqués en formes-clés dans l'espace de repos (inversion de la matrice de skinning) donnent un étirement de 1,1 à 1,2 sur toutes les poses testées, contre 3,36 à l'origine à 120°.
- Résidu : plis à 105° et 120°, car la cible ARAP elle-même plie à grand angle.
- Échecs : amortissement des plis (erreur 56). Pondération cotangente : gain mixte (erreur 57).
- Prochaine étape : réduire le résidu de pli à grand angle, sans nouvel amortissement.

## 42. Limitation de rotation et sélection par entraînement
- Limiter la rotation des sommets repliés dans l'ARAP : efficace sur l'avant-bras et la jambe, cascade sur le bras (erreur 58).
- Sélection de la variante par pose d'entraînement uniquement, puis revalidation Blender : avant-bras et jambe sans plis à 105° (erreur 59).
- Reste : bras à 105° et 120°.

## 43. Ancrage, densité et protocole du bras
- Ancrage : seuil 0,99 conservé ; un ancrage plus large fait exploser l'étirement (erreur 60).
- Densité : ajouter 100 et 110° à l'entraînement améliore le bras à 105° de 4 à 3 plis, sans résoudre le problème à 120° (le bras passe de 4 à 12 plis entre 110 et 120°).
- Protocole : l'humérus seul à 120° est un cas extrême ; la répartition réaliste avec l'os d'épaule reste à tester (erreur 61).

## 44. Épaule réaliste : l'hypothèse du protocole est largement infirmée
- Répartir la rotation entre os d'épaule et bras (1/3 et 2/3) ne réduit les plis que de 3 à 4 à 105–120°, et dégrade un peu l'étirement (erreur 62).
- Le repliement de l'épaule est donc intrinsèque aux poids LBS : il faut une correction (formes-clés spécifiques à l'épaule, ou poids de l'épaule dédiés).
- Prochaine étape : correctifs ARAP pour les poses réparties épaule + bras, entraînés sur l'entraînement uniquement.

## 45. Correctifs sur poses réparties : validés dans Blender sauf 120°
- Les correctifs ARAP fonctionnent sur la répartition épaule + bras comme sur le bras seul (erreur 63).
- Résidu à 120° : 11 plis, identique à l'origine. Piste : correctif dédié à l'épaule à grand angle, ou poids de l'épaule.

## 46. Bras HBM : articulations, armature et test
- Articulations placées par chemin mesuré sur le maillage (épaule, poignet) ; coude et bout de main estimés (anthropométrie) et signalés comme tels.
- Résultat test (`engine/validation/test_hbm_bras.py`, Blender, copie) : 8 os, symétrie G/D 0,8 mm, longueurs dans les plages, milieux à l'intérieur du maillage.
- Limite : le bout de la main est extrapolé (le chemin mesuré est trop court) ; les doigts ne sont pas faits.
- Défaut trouvé et corrigé pendant le test (erreur 64).

## 47. Phase 3 sur le corps HBM : squelette complet (47 os) et doigts mesurés
- Squelette unique : jambes et tronc (11), bras (8), doigts (28), construits par `engine/validation/test_hbm_complet.py` ; le fichier `.blend` produit est dans le dossier de travail, pas dans le dépôt.
- Doigts : les lobes distaux (regroupement par largeur, découpe des lobes trop larges, ordre depuis le pouce) donnent 4 doigts mesurés par côté ; le petit doigt est estimé (80 % du majeur), la base du pouce est estimée (paume non résolue).
- Ligne médiane mesurée : les articulations suivent le doigt courbé (erreur 67).
- Résultat : 47 os ; symétrie jambes 7,8 mm, bras 0,8 mm, doigts 0,6 mm ; 20 phalanges mesurées dans le maillage, aucune hors ; 4 phalanges estimées non testées (nommées dans le test).
- Ce qui reste estimé, sans preuve dans le maillage : coude (anthropométrie), base du pouce, auriculaire, bout de main (la main mesurée va plus loin, erreur 66).
- Tests d'articulation : Blender uniquement (pas de numpy), sur une copie du corps source.

## 48. Phase 4 : plis à 120° sur le bras, diagnostic
- Localisation : plis sur le bras supérieur, dominés par l'os auxiliaire de torsion (erreur 68).
- Report de poids vers le bras : insuffisant (17 à 23 plis). Abandonné comme correction.
- Piste suivante (lue seulement par son résumé) : déformation avec séparation de la torsion et de la flexion d'un même os. À lire, puis à tester en Blender avant toute écriture comme « appris ».
- État : phase 4 ouverte. Résidu à 120° : 11 plis avec le correctif ARAP, 20 sans correctif.

## 49. Phase 4 : base heat, transfert à l'épaule, confiance
- Base : poids heat de Blender meilleure que la référence optimisée sur le bras (erreur 71). Sur le bras, ARAP interpolé avec cette base donne 0 pli à 75° et 105° hors entraînement, étirement ≈ 1,14.
- Résidu à 120° du bras : 0 pli après transfert de 50 % du poids du bras vers l'épaule (rayon 0,16 m), sélection sur l'entraînement (erreur 72).
- Rejeté : torsion pure de l'os auxiliaire (erreur 69), poids par distance bruts (erreur 70).
- Ouvert : plis au coude (6 à 120°) et au genou (9 à 120°) après ARAP. Les formes-clés de seconde pose existent mais ne sont pas relancées avec la nouvelle base (erreur 73).
- Ouvert : aucune de ces mesures n'a été rejouée dans Blender avec la nouvelle base (la validation Blender de la phase 4 précédente porte sur l'ancienne base).

## 50. Phase 4 : base finale validée dans Blender (sauf 2 plis à la jambe)
- Base : heat (Blender) + transfert de 50 % du poids du bras vers l'épaule (rayon 0,16 m) + transfert de l'avant-bras vers le bras au coude (rayon 0,16 m) + transfert de la jambe vers la cuisse au genou (rayon 0,16 m). Sélection sur l'entraînement (120°) uniquement.
- Correctifs : ARAP interpolé, ramenés à l'espace de repos (d = A⁻¹·δ), mesurés dans Blender (`engine/skinning/valide_base_blender.py`).
- Blender : bras 0 pli à 60/75/90/105/120° ; avant-bras 0 pli ; jambe 0 pli à 60–90°, 2 à 105° et 120° ; étirement 1,05 à 1,22 partout (la référence était à 6,0 avant).
- Non fait : la phase 4 n'est pas terminée. Reste : résidu de 2 plis à la jambe (erreur 76) ; confiance validée (erreur 74) ; poids par distance rejetés en brut (erreur 70) ; heat retenue comme base du bras (erreur 71).
- Rapport : `docs/rapports/phase4_validation_base_blender.json`.

## 51. Anatomie des articulations : jonctions, DDL et amplitudes
- Une articulation a un type (charnière, condylienne, sphérique, pivot, sellaire, glissement) qui fixe ses degrés de liberté. Le rig doit suivre ce type : une charnière n'a qu'un axe.
- Le fléchissement se fait toujours à la jonction : sans nœud de jonction, la déformation se répartit dans le maillage et l'aplatit.
- Articulations à nœud : hanche (sphérique, 3 DDL), genou (charnière), cheville (charnière + sous-talienne), épaule (sphérique + clavicule), coude (charnière + pivot radio-ulnaire), poignet (condylienne), orteils et doigts (chaînes de charnières et de condyliennes), colonne (segments en série).
- Référence : `docs/anatomie_articulations.md`. Amplitudes : ordres de grandeur, à confirmer par une source officielle avant de les figer dans le rig.

## 52. Articulation par chaîne de nœuds coaxiaux (genou)
- Un pli se produit quand l'angle entier est appliqué sur une bande étroite : la corde entre deux rotations de même axe rétrécit de cos(Δθ/2). Une bande large réduit Δθ et supprime les plis, au prix d'un étirement localisé.
- Mesure : 0 pli à 90° et 120° avec B = 0,15 m (étirement max 1,37, p99 1,00). Le critère max ≤ 1,25 n'est pas atteint.
- Voir erreur 77 et `engine/skinning/test_chaine_genou.py`.

## 53. Genou validé dans Blender par chaîne de nœuds
- La chaîne de nœuds coaxiaux donne en LBS réelle : 0 pli, segments rigides, section du genou conservée (0,995–0,999).
- Critère de section : perpendiculaire à l'axe du segment, jamais sur le plan horizontal.
- Voir erreur 78 et `docs/rapports/phase4_genou_chaine_blender.json`.

## 54. Coude validé ; cheville en échec partiel
- Méthode générique : `engine/skinning/articulation_chaine.py` (pivot et axe mesurés depuis la pose, projection du pivot sur la jointure) et `engine/skinning/criteres_articulation.py` (plis, rigidité, section).
- Le coude passe les critères dans Blender. La cheville échoue en flexion dorsale : un segment enfant rigide qui n'est pas dans l'axe du parent pénètre le parent. Voir erreur 79.

## 55. Cheville : amplitude humaine normale et bande sur la bissectrice
- Règle : une articulation se modélise dans son amplitude humaine normale (cheville : dorsale 20°, plantaire 50°), jamais au-delà ; l'amplitude est bornée par la butée osseuse.
- La bande d'articulation doit suivre la normale de jointure (bissectrice des segments), pas la direction du seul segment parent, quand l'enfant n'est pas dans l'axe.
- Voir erreur 80.

## 56. Hanche : échec de la chaîne seule
- Une chaîne coaxiale traite une seule rotation ; la hanche est une sphère à 3 DDL. Les plis sont à la frontière tronc / cuisse. Quatre variantes testées, aucune sous 15 plis. Voir erreur 81.

## 57. Recherche sur la hanche : SBS (rotations mélangées)
- Source : Kavan et al. (I3D 2005), mélange de rotations par quaternions autour d'un centre de rotation. Supprime le rétrécissement de la LBS entre deux rotations.
- Appliqué à la hanche : les plis ne disparaissent que si le tronc voisin se déplace de 12 à 26 cm, ce qui est non anatomique. Vérifier le voisinage avant de conclure (erreur 82).
- Ce qui reste : un correctif de pose sur la frontière cuisse / tronc.

## 58. Plis acceptables par zone anatomique
- Un pli n'est acceptable que dans une zone de pli réelle (aine, pli fessier, creux poplité, pli du coude, aisselle) et sans pénétration. Hors zone, c'est un défaut.
- Hanche : la majorité des plis sont sur le côté (trochanter, fessier externe), pas à l'aine. Ils sont donc des défauts. Voir erreur 83 et `engine/skinning/plis_zones_acceptables.py`.

## 59. Hanche : vérifier le sous-arbre et le déplacement du voisinage
- Le sous-arbre d'une articulation (ici la jambe entière) doit suivre la rotation ; sinon les plis apparaissent à l'articulation voisine (erreur 84).
- Un correctif qui réduit les plis en déplaçant le voisinage de plus de quelques centimètres n'est pas un correctif valable.
- Hanche : 0 pli jusqu'à 30°. Au-delà : non résolu (erreur 84).

## 60. Limite de plage : ne pas valider au-delà de ce qui est mesuré
- Une articulation n'est validée que dans la plage où le test donne 0 pli et où la mesure est faite. Hanche : 30°. Épaule : 20°. Poignet : 50°. La plage normale du corps humain (hanche 120°, épaule 180°, poignet 80°) n'est pas atteinte.
- Quand un correctif de repli échoue (erreur 85), on passe à la variante sans correctif et on le dit clairement, au lieu d'élargir la bande jusqu'à ce que les plis disparaissent (cela déplace le tronc, voir section 59).
- L'étirement n'est pas bloquant : il est signalé. Il reste élevé à la hanche (5,10 à 30°), ce qui doit être regardé visuellement avant toute revendication.

## 61. Mesurer la pénétration avant de parler de validation
- Un critère de plis ne suffit pas : un membre peut traverser le corps sans créer de pli dans sa propre surface. Toute validation doit inclure une mesure de pénétration (erreur 86).
- Mesure retenue : distance signée à la face la plus proche du reste du corps. Elle doit passer un contrôle positif (forcer un membre dans le tronc) avant d'être crue.
- Le repos peut contenir des chevauchements du maillage source. Les compter comme défauts de la pose fausse le résultat : on compare à la pose de repos (pénétrations nouvelles seulement).
- Pour une articulation, la pénétration se joue dans la calotte de jonction. Une bande de poids ne suffit pas : les segments durs suppriment la pénétration mais ouvrent des fentes (variante testée au coude).

## 62. Chaque jonction a un sens : bornes avant tout calcul
- Une articulation n'autorise qu'un ensemble de mouvements. Le modèle doit refuser une pose hors de cet ensemble avant de mesurer le reste (erreur 87).
- Source officielle des bornes : CDC / NCHS (jeu de données sur les amplitudes normales, 674 sujets). Les fiches et les sites de révision ne suffisent pas.
- Le squelette de référence X-Bot donne les centres et les axes de flexion. Il faut le lire dans Blender (lecture des axes locaux des os) avant de poser une chaîne.
- Une jonction se pose sur ses axes réels, pas sur un axe fixe commun à tous les membres.

## 63. Une exclusion de zone ne doit jamais servir à valider une articulation
- Exclure la zone de jonction du test fait disparaître précisément la pénétration à mesurer (erreur 88). Toute exclusion doit être justifiée et mesurée à part.
- Une calotte définie seulement par un plan de coupure sur les sommets existants ne supprime pas la pénétration. Il faut générer la géométrie de jonction et la mesurer comme matière.

## 64. Chaque charniere a son axe : le lire sur les os, verifier le sens, repli explicite
- Un axe fixe commun (X) fait pénétrer le coude incline de 19 degres. L'axe lu sur les os (produit vectoriel des deux segments) corrige le coude.
- Le sens de rotation est un choix a verifier par mesure (ici -h), pas une convention a supposer.
- Si les os sont alignes (jambe verticale), l'axe n'est pas defini : repli explicite sur l'axe anatomique et signalement, jamais un axe silencieux.
- La calotte de 8 cm marche au coude, pas forcement au genou : le rayon se calibre par articulation.

## 65. Un residu dans une zone de pli se traite par gonflement, pas par coupure
- Le residu du genou est dans le creux poplite, zone ou un pli est admis. La coupure de la jonction ne le resout pas ; il faut un gonflement de la peau hors du volume voisin, sans penetration.
- Verifier le sens d'un axe par un critere anatomique (ici le talon recule en flexion) avant de le tester numeriquement.

## 66. Une correction qui supprime la penetration doit aussi etre bornee
- Zero penetration ne suffit pas : mesurer l'amplitude du deplacement, la localisation, les plis et l'etirement. Une poussee non bornee peut tout 'reparer' en gonflant la peau de plusieurs centimetres (erreur 91).

## 67. Mesurer plis et etirement avant de juger une jointure
- Une jointure peut avoir zero penetration et se dechirer : l'etirement de 8,7 et 745 plis cachaient le probleme. Mesurer les trois (penetration, plis, etirement) a chaque angle, avant toute conclusion.
- Une separation de segments sans couture cree un dechirement. La couture doit etre generee, pas approximee par des poids.

## 68. Couture : pièces rigides + calotte générée, jamais un trou
- Méthode retenue (recherche officielle + praticiens, `docs/recherches_phase4.md`) : chaque membre est une pièce rigide par os, coupée au joint ; chaque pièce se prolonge au-delà du joint et la pièce supérieure la recouvre ; la couture est une calotte générée et cousue aux bords.
- Une coupure qui ne supprime aucune face n'est pas une coupure : vérifier le nombre de faces avant toute mesure (erreur 93).
- Une couture sans géométrie ouvre un trou : mesurer l'ouverture, pas seulement la pénétration.
- Recherche : au moins une source officielle, puis une source non officielle si l'officiel ne traite pas le problème ; noter les deux.

## 69. Fermer le maillage avant de mesurer ; utiliser une union booléenne robuste
- Un étirement de 1,00 sur un maillage ouvert ne prouve rien : vérifier d'abord la fermeture (arêtes de bord = 0).
- Une couture par sommets voisins reste ouverte. Une union booléenne (Manifold, licence Apache-2.0, sortie manifold garantie) ferme le maillage à chaque angle.
- Méthode : vérifier que l'entrée est fermée, faire l'union, vérifier la fermeture et le volume, puis mesurer la surface unie.

## 70. Volume d'interpénétration : orienter les bouchons, puis tester un témoin positif
- Un bouchon en éventail doit suivre le sens inverse de l'arête de bord ; sinon le volume devient négatif sur une pièce et positif sur l'autre, et le booléen échoue (erreur 95). Après bouchon : `trimesh.repair.fix_winding` puis `fix_inversion`, et vérifier `is_volume`.
- Avant d'accepter un zéro d'interpénétration, prouver que la méthode voit un chevauchement : décaler une pièce d'une distance connue et vérifier qu'un volume positif apparaît. Ici : 46 cm³ pour 10 cm en +Z.
- Résultat coude (Rs 7 cm, sphère exclue) : 0 cm³ à 0–90°, 4,95 à 120°, 84,46 à 145°. Le coude n'est pas validé au-delà de 120° ; le tronc n'est pas encore inclus.

## 71. Métrique de pli et d'étirement : ne pas l'appliquer à une jointure en pièces rigides
- Sur les sommets d'origine, une rotation rigide d'une seule pièce étire les faces qui traversent la jointure, même sans pénétration (plis 3 à 11, étirement 2,4 à 4,7 à 30–90° au coude). Un résultat « pli 0 » ou « pénétration 0 » ne suffit donc pas.
- Une correction de contact doit être mesurée après lissage : le lissage peut ramener les sommets dans l'autre pièce (5 et 28 sommets restants à 120 et 145°).
- Source non officielle utile : choisir la direction de correction sur toute la séquence, pas image par image (orca_forge, dev.to). Voir `docs/recherches_phase4.md`.

## 72. Lire une animation de référence FBX : vérifier la convention avant les chiffres
- Un FBX avec peau et un sans peau : le premier donne les poids et le maillage, le second donne seulement le squelette et les courbes. Compter les `Mesh`, `Skin`, `Cluster` avant de choisir le fichier.
- Les noms d'os portent un préfixe (`mixamorig1:`) : chercher par suffixe.
- Mesurer l'angle de flexion comme 180° moins l'angle entre segments, et vérifier sur membre tendu.
- Les plages de la danse donnent un plancher d'entraînement, pas la limite humaine. Les limites restent sourcées séparément (CDC/NCHS).
- Un profil de poids échantillonné sur peu de sommets ne tranche pas une largeur de zone de fusion.

## 73. Rejouer une animation réelle : compter les images, pas seulement les angles
- Extraire l'angle image par image (`engine/skinning/reference/serie_flexion.py`), puis mesurer chaque angle distinct : une seule métrique par image, pour que le résultat dise combien d'images passent.
- Coude de la danse : 0 image sur 250 avec pénétration hors sphère. Ne valide pas les plis ni l'étirement de la surface unie.

## 74. Étirement : séparer la zone de jonction du corps de la peau
- L'étirement est attendu au pli d'une articulation, et doit être borné là. Il est interdit sur le corps de la peau.
- Mesurer deux métriques : étirement hors jonction (cible ≈ 1) et étirement dans la bande de jonction (borné, séparé). Ne jamais les agréger.
- Source : consigne explicite de l'utilisateur, à retenir comme critère de référence (erreur 99).

## 75. Axe de charnière quand le membre est aligné : normale au plan sagittal
- Un produit vectoriel de deux segments alignés est nul : l'axe devient NaN. Fallback anatomique : normale au plan sagittal, (membre) × (direction des orteils) pour le genou.
- Vérifier le signe en flexion (le talon recule) avant tout rejeu.
- Un zéro de pénétration sur une animation réelle ne vaut que si le témoin positif, sur les mêmes pièces, détecte un chevauchement connu.

## 76. Plis sur une surface unie : valider la correspondance avant le chiffre
- Séparer étirement et plis en bande de jonction et hors bande (critère utilisateur, erreur 99).
- Sur les faces d'origine, la métrique est valide jusqu'à 90° au coude ; au-delà, les faces qui traversent la jointure produisent de faux plis.
- Sur la surface unie, un témoin identique (θ = 0) ne suffit pas : vérifier aussi la correspondance dans la région où le repos se chevauche.

## 77. Correspondance matérielle avant tout compte de plis
- Une correspondance par face la plus proche n'a de sens que si la surface est proche de son repos. Mesurer la distance de correspondance (médiane 9 cm ici) avant d'interpréter un compte.
- Pour un segment rigide, la correspondance est la transformation rigide : pli zéro par construction. Un pli n'apparaît qu'à la jointure, et il doit être mesuré là seulement.

## 78. Juger la jonction par sa forme, pas seulement par la pénétration
- Une sphère de jonction donne une saillie constante (1,5 cm ici) à tous les angles : elle ne crée pas de pli. Le côté fléchisseur doit devenir concave en flexion, le côté extenseur rester lisse.
- Mesurer la saillie séparément côté fléchisseur et extenseur, à chaque angle, avant de déclarer la jonction valide.

## 79. Pli fléchisseur : correction de pose, cible anatomique requise
- Une correction de pose (PSD) stocke des décalages à quelques angles, puis les interpole : le pli se crée là où il est sculpté, pas là où une sphère fixe gonfle.
- Une cible anatomique est indispensable : un skinning linéaire ne peut pas la fournir (il arrondit le coude).
- Ordre : trouver la cible de pli, puis calculer δ aux angles échantillonnés, puis interpoler et mesurer (saillie fléchisseur / extenseur, erreur 103).

## 80. Cible anatomique de pli : vérifier le type de donnée publiée
- Une étude peut donner une loi d'échelle et des postures-clés sans donner le maillage. Ici : rapport chair haute/milieu en fonction de l'angle (ajustement publié), et 4 postures.
- Reconstruire la cible à partir de la loi, en le signalant comme approximation, avant de déclarer la jonction valide.

## 81. Une correction ne vaut que si elle dépasse le bruit de la mesure
- Réduire la saillie de la sphère selon une loi publiée n'a changé la médiane que de 0,01 à 0,03 cm, contre 0,5 cm de variation de base avec l'angle.
- Avant de conclure à une correction, mesurer le bruit (variation de la base, classification des sommets). Si l'effet est plus petit, le résultat est négatif.
- Une sphère ne peut pas exprimer un pli : il faut une géométrie de pli explicite.

## 82. Passer à la peau continue : la correspondance par sommet rend les mesures valides
- Avec une peau continue, le même sommet garde son index à chaque pose : plis et étirement se mesurent sans correspondance par proximité.
- Le choix méthodologique est acté : DQS (officiel, Kavan 2008) puis correctives de pose (PSD).

## 83. Un pli se mesure dans le repère local, pas en monde
- Comparer une normale monde au repos à une normale posée signale toute rotation rigide de plus de 90°. Un pli réel est un retournement après correction de la rotation locale.
- Témoin à appliquer à toute métrique : une transformation rigide doit donner zéro pli.
- Les anciens comptes de plis sont à remesurer (erreur 108).

## 84. Mesurer une pénétration sur peau continue : décaler les points avant le test
- Tester des sommets de surface dans un maillage fermé est ambigu : 215 faux positifs au repos. Décaler les points de 1 mm vers l'extérieur, puis contrôler au repos (zéro attendu) et avec témoin positif.
- DQS au coude (un seul angle, rapport `docs/rapports/phase4_dqs_coude.json`) : hors bande, 0 pli et étirement 1,00 au 99e centile. Dans la bande, plis à partir de 90° et étirement élevé : à juger.

## 85. Vérifier le sens de flexion avant tout : déplacement du segment distal vers l'avant
- Un axe de flexion au signe inversé donne une hyperextension et des mesures plausibles. Vérifier : à θ > 0, le segment distal (poignet, cheville) doit se déplacer vers l'avant (sens des orteils).
- Le genou se vérifie de la même façon (talon qui recule). Le coude était mal vérifié (erreur 110).
- Contrôle de torsion : le segment proximal ne bouge pas ; l'axe ajusté du segment distal est égal à l'axe de flexion.
- Tous les résultats antérieurs du coude sont à remesurer.

## 86. Apprendre les articulations avant de modeler : type, sens, liens, déclencheur
- Pour chaque jonction : type (charnière, sphérique, condyloïde, pivot, sellaire), mouvements avec amplitude sourcée, muscles moteurs qui tirent au-delà de l'axe, nerf qui commande le muscle.
- Le déclencheur d'un mouvement est un motoneurone qui active un muscle ; la tendon tire l'os autour de l'axe. Le moteur doit reproduire couple, axe et sens.
- Une amplitude non sourcée n'est pas une donnée : la marquer et la remplacer dès qu'une source la donne (hanche corrigée, erreur 111).
- Référence : `docs/articulations_humaines_sources.md`.

## 87. Sources bloquées : API officielle, pas contournement
- Une vérification de navigateur est un contrôle d'accès : ne pas la contourner, même avec autorisation.
- Essayer les APIs officielles : NCBI E-utilities (efetch PubMed, résumé des fiches StatPearls) et Europe PMC (résumés d'études). Elles n'ont pas le corps des fiches.
- Quand la source reste inaccessible, signaler la lacune dans le document et marquer les chiffres non officiels.

## 88. Amplitudes : source secondaire, désaccords, plage basse pour les bornes
Une valeur d'articulation n'est sourcée que si une source primaire a été lue. Quand la primaire est inaccessible, la valeur
reste marquée « secondaire non vérifiée ». Chaque désaccord entre sources est écrit dans le tableau. Pour une borne
physique du rig, on prend la plage basse tant que le désaccord n'est pas tranché. Voir docs/erreurs_apprises.md entrée 113.

## 89. Étirement : percentile, pas maximum ; DQS seul insuffisant pour la hanche et le genou
Le maximum d'étirement est une statistique d'arêtes isolées. Le critère de phase 4 se mesure au 99e percentile hors
bande, avec un témoin identité égal à 1,0. Sur hanche et genou, DQS seul donne p99 hors bande ≥ 1,01 et dans la bande
jusqu'à 2,6 : il faut des correctifs de pose (PSD) pour la jonction, puis remesurer. Voir erreurs_apprises entrée 114.

## 90. Correctif de pose : vérifier la reproduction des exemples avant de juger
Une correction PSD doit reproduire sa cible aux angles d'entraînement. Un multiplicateur (poids d'os) qui n'est pas 1
sur la cible la fait diverger : le vérifier par le témoin d'exactitude. Un filtre de rotation sur faces repliées peut
aggraver les plis ; le mesurer avec et sans. Une cible ARAP réduit l'étirement mais pas forcément les plis. Voir
erreurs_apprises entrée 115.

## 91. Gradient de rotation : la répartition sur bande étroite crée un cisaillement borné par la géométrie
Une rotation qui varie le long du membre sur une bande 2b induit un allongement ≈ 1 + r·1,5·θ/(2b). Pour une flexion
de 120° avec une bande de 10 cm, l'allongement est ≈ 2,6 : hors de portée. La peau doit donc se plier (pli
fléchisseur) et s'étirer (côté extenseur) plutôt que tourner en continu. Le critère de plis doit tenir compte des zones
acceptables. Voir erreurs_apprises entrée 116.

## 92. Zone de plis : règle qualitative tant que les coordonnées ne sont pas sourcées
Quand une source décrit une zone sans coordonnée, on écrit une règle qualitative vérifiable (côté, distance) et on
déclare la coordonnée non sourcée. Appliquer la règle aux deux méthodes avant de les comparer : la correction PSD a créé
des plis postérieurs interdits que le DQS n'avait pas. Voir erreurs_apprises entrée 117.

## 93. Pondération spatiale : lisse, jamais dure
Une correction limitée à un côté par un masque binaire crée une discontinuité de déplacement au bord, donc des plis.
La restriction doit être une transition lisse. Voir erreurs_apprises entrée 118.

## 94. Ne pas atténuer une correction après coup : intégrer la restriction dans la cible
Multiplier une correction par un poids spatial partiel crée un cisaillement entre voisins, quelle que soit la douceur de
la transition (erreurs 118 et 119). La restriction doit être dans l'énergie de la cible (ancres souples), puis la
correction reproduit cette cible. Voir erreurs_apprises entrée 119.

## 95. Réutiliser la méthode validée : contrôle d'abord, puis transposition
Avant de transposer une méthode validée à une nouvelle articulation, la reproduire sur le cas témoin (ici le genou) en
numpy. Si le témoin passe, la transposition est fiable. Ne jamais écrire « fonctionne » sans mesure. Voir
erreurs_apprises entrée 120.

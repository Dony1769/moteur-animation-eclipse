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

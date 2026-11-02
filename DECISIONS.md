# Décisions techniques

## D1 — Dépôt local au lieu de GitHub
- Choix : `git init` dans `/home/claude/moteur_3_0`, branche `autonome`, pas de push.
- Raison : le jeton GitHub est invalide et l'utilisateur a indiqué qu'il n'y a pas de dépôt à utiliser. Le suivi reste possible en local.
- Alternative écartée : créer un dépôt GitHub (refusé par l'utilisateur, et impossible sans jeton valide).

## D2 — Outils libres et gratuits
- Tous les modèles retenus sont locaux : DWPose (onnx), Real-ESRGAN anime 6B, Depth-Anything-V2 small (Hugging Face, licence Apache 2.0), rembg isnet-anime, Piper (voix), Rhubarb Lip Sync (MIT).
- Alternative écartée : générateurs d'images payants (quotas épuisés, refusés par l'utilisateur).

## D3 — Format de sortie
- MP4 720p 12 images/s (`engine/PIPELINE.md`), libx264, yuv420p, CRF 20.
- Raison : format léger, lisible sur téléphone, déjà utilisé.

## M1 — parseur Fountain
- Parseur écrit à la main (sous-ensemble du standard) plutôt qu'une dépendance : le standard est court, et les écarts volontaires sont documentés (`FADE IN:` accepté, `FADE OUT.` en transition). Alternative écartée : une bibliothèque Fountain tierce, non vérifiée dans cette session.
- Transitions sans scène stockées dans `transitions_debut` plutôt que dans une scène vide : une scène fictive faussait le compte des scènes.

## M2 — exercices
- Dessins procéduraux pour la balle et le visage de l'exercice labial : suffisant pour tester timing et synchro, pas pour le rendu final.
- Le cycle de marche utilise les sprites existants de `out/cycle/hanche/`. Passage 2 normalisé sur la hauteur médiane (537 px contre 718-725 px) : sans cela le personnage pulse.
- Les MP4 de test sont versionnés dans `renders/` ; `.gitignore` laisse passer `renders/**/*.mp4`.

## M3 — personnages
- Format `monteur/personnage/1` : chaque élément (vues, poses, expressions, bouche) pointe vers un fichier. Fichier manquant = erreur.
- Ensemble minimal requis : marche_1..4, neutre + 4 expressions, bouches A E I M O U. Kaël le satisfait avec les dessins de `universes/eclipse_royale/characters/kael/dessins/`.
- `neutre` de Kaël = `vues/face_g.png` (visage de référence du gabarit), pas un dessin d'expression dédié.
- Aiko et Darius : manifests créés mais vides. Les planches de `/home/claude/references/eclipse_royale/` sont trop petites (≈300 px) et contiennent des éléments hors cadre : elles ne servent pas de sprites.

## M4 — voix et lèvres
- Synchro : Rhubarb, mode par défaut (formes A à F et X). Table vers les six bouches disponibles dans `engine/voix/plan_parlant.py` ; G et H ne sont pas dessinées.
- Alignement des bustes de bouche sur les yeux (DWPose, 68 points du visage) : sans cela la tête sautait entre les images.
- Durée de la voix : recherche itérative de l'échelle Piper, car la durée n'est pas linéaire.
- Alternative écartée : composer une bouche sur un visage. Les bustes sont des images complètes, la commutation directe suffit pour ce test.

## Téléchargements (traçabilité)
- Rhubarb Lip Sync v1.14.0 Linux : `https://github.com/DanielSWolf/rhubarb-lip-sync/releases/download/v1.14.0/Rhubarb-Lip-Sync-1.14.0-Linux.zip`, SHA-256 `a9a9074862cff47b2d59b8bf399a678a3b0b74f9452ad6ad94cb292913dd8667`. Empreinte calculée localement, non comparée à une somme publiée. Installé hors dépôt dans `/home/claude/outils/rhubarb/`.

## Planches de base : découpe et manifestes (2 novembre 2026)
- Découpe par cellules explicites (`engine/gen/decouper_grille.py`), pas de détection automatique. Corps : 4 colonnes égales. Têtes : 6 colonnes, rangées bornées à la main.
- Repères magenta retirés par couleur franche (r > 200, b > 200, écart au vert ≥ 60) puis interpolation (`cv2.inpaint`). Seuil choisi pour ne pas toucher la peau ni le violet des vêtements. Résidu : ≈ 700 px magenta pâles dans 10 cellules sur 60, visible sur les têtes de Vorthaz. Consigné, non bloquant.
- Vue « face » de chaque personnage = cellule « neutre » (pas de vue de face dédiée dans les planches).
- Bouches alignées sur les yeux (DWPose) dans `tete_alignee/` ; échelles inter-oculaires dans 1 % d'écart entre formes.
- Alaric : 3 rangées générées, seules les 2 premières sont utilisées.

## NPR — rendu animé non photoréaliste (2 novembre 2026)
- Périmètre : le moteur reste 2D (planches). Le module `engine/npr/` est une chaîne 3D-style (G-buffer). Il ne traite pas une planche tant qu'il n'existe ni profondeur ni normales pour elle. Alternative écartée : plaquer des effets 3D sur les planches sans géométrie.
- OpenGL 3.3 core via EGL headless (llvmpipe). Raison : contexte réel vérifié, compilation des shaders par Mesa. Pas de `glslangValidator` : la compilation remplace la validation statique.
- Normales stockées brutes en RGBA32F (pas d'encodage 0..1) : le fond vaut 0 sans décodage.
- Sobel sur `log(profondeur)`, fond substitué par `profondeur_fond`. Raison : le seuil absolu sur la profondeur linéaire dépendait de la distance de la caméra.
- Rampe lue en RGB uniquement. La version « masque visage » lisait le canal R de la rampe : écarté pour éviter deux conventions.
- Masque visage opt-in (`masque_visage`). Raison : « hors masque = pleine lumière » éclairerait tout le corps.
- Masques lus en UV de surface (canaux g, b du G-buffer), jamais en coordonnées d'écran.
- `HeadCenter` en uniform, espace vue. La pièce jointe le déclarait `in` dans le fragment shader, ce qui est invalide.
- Non implémenté : coque inversée (pas de maillage à contourner, pseudo-code non exécutable), anisotropie des cheveux (tangentes absentes), transfert de normales Blender (pas d'outil de ce type dans le dépôt).
- Banc d'essai : sphère avec bosse analytique, pas un personnage. Raison : vérifier les formules sur une géométrie connue, sans attendre un modèle 3D.

## NPR, suite — cheveux, 2.5D, corrections (2 novembre 2026)
- Reflet des cheveux : Kajiya-Kay sur le demi-vecteur (`T'·H`), seuil binaire. Raison : la forme de la pièce (`T·L`) ne bouge pas avec la caméra, le demi-vecteur oui.
- Tangente en sortie 3 du G-buffer, zéro = pas de cheveux. Raison : une sortie séparée ; la normale brute doit rester exacte pour le Sobel, donc elle ne porte pas la tangente.
- Décalage `T + N·hairShift` : déplace la bande de reflet le long de la mèche (technique de Kajiya-Kay décalé). Valeur par défaut 0,1.
- Relief 2.5D : pentes calculées en pixels (`h · rayon_biseau`), Sobel centré, flou avant les pentes. Raison : un relief en unités de profondeur donne des normales quasi plates, et l'alpha binaire crée des dents sans flou.
- Composition des calques en CPU (z-buffer dans `composer`), pas en GPU. Raison : quelques calques, lisibilité, référence simple à tester. Un tri GPU viendra si la scène grossit.
- Test mémoire GPU : création et libération répétées, sans mesure de mémoire. Raison : Python ne lit pas la mémoire GPU sur llvmpipe ; le test ne détecte que les erreurs.
- Démos gardées comme bancs d'essai (tête à quatre panneaux, calques procéduraux). Raison : aucun personnage du projet n'est utilisable en 3D pour l'instant.

## Calques articulés 2.5D (2 novembre 2026)
- Deux outils de déformation : squelette 2D rigide pour les rotations (tête, mèche), grille FFD pour le clignement. Raison : une FFD seule ne fait pas tourner une pièce rigide sans l'écraser ; un squelette seul ne donne pas un clignement propre.
- Poids par distance gaussienne au segment de chaque os, en softmax, restreints aux `os_actifs` de chaque calque. Raison : un calque ne doit suivre que ses os ; sans cela la tête déforme le corps.
- Sommets en coordonnées image, profondeur par sommet tirée du relief au repos, projection avec la même convention que l'ombrage. Raison : cohérence avec le chemin 2.5D et test de profondeur GPU = `relief.composer`.
- VBO dynamiques réécrits en entier à chaque image, topologie fixe. Raison : simple, et suffisant pour quelques milliers de sommets ; une écriture partielle n'apporte rien à cette taille.
- Tri par profondeur moyenne sur le CPU, z-buffer matériel pour l'image. Raison : le tri rend l'ordre explicite et réduit le travail ; c'est le z-buffer qui garantit l'image (test : ordre inversé = même image).
- Découpe alpha dans le shader de géométrie (`seuilAlpha`) plutôt que triangles découpés sur le CPU. Raison : exacte au pixel près, sans recalcul du maillage quand la forme change.
- Clignement = écrasement linéaire, fermeture plafonnée à 0,9. Raison : à 1,0 les triangles s'écrasent en segments dégénérés et laissent des points parasites.
- Piste cubique = interpolation de Hermite à tangentes de Catmull-Rom. Raison : elle passe par les clés et sa dérivée est continue.
- Rotation 2D seulement, pas de lacet 3D. Raison : les personnages du projet n'ont pas de géométrie 3D ; une rotation de visage en 3D relèverait d'un autre chantier.

## Personnage réel, normales sous FFD, cheveux Verlet, vues multiples (2 novembre 2026)
- Normales poussées par la jacobienne moyenne par triangle, et non plus tournées par os. Raison : une seule règle couvre la FFD et le skinning ; une rotation rigide donne le même résultat qu'avant (test de régression). Le gradient de la hauteur implicite est transformé par `J⁻ᵀ`, ce qui correspond à la règle de la chaîne inverse.
- Atlas unique, une seule texture GPU partagée. Raison : un upload par couche gaspille la mémoire et le temps ; la correspondance UV est linéaire, donc exacte au pixel avec `GL_NEAREST`.
- Marge de déformation FFD. Raison : sans elle, la grille déforme toute la boîte, et fermer un œil écrase toute la tête.
- Verlet dans le repère de la tête, avant skinning, avec forces apparentes (Euler, centrifuge, Coriolis, entraînement du pivot). Raison : le FFD s'applique avant le squelette. Placer la racine dans le monde aurait demandé de convertir les positions entre deux repères à chaque pas.
- Contraintes corrigées par masses inverses, et non à moitié. Raison : le document de conception laissait une racine épinglée glisser.
- Gravité 540 px/s² (équivalent à 0,15 px/image² à 60 Hz). Raison : le document donnait une valeur par image, sans durée d'image.
- Vues multiples par fondu entre vues réelles, sans invention de profil. Raison : seules la face et le trois quarts existent ; un profil généré serait une fausse donnée. Un fondu n'est pas une rotation et le dit.
- Pas de géométrie 3D ajoutée. Raison : les données de Kaël sont des images découpées en 2D ; une rotation 3D relèverait d'un autre chantier.

## Encre fine, bascule nette, rampes teintées, découpe par matériaux (2 novembre 2026)
- Silhouette tirée du bord du masque de profondeur, et non du Sobel. Raison : un seuil sur le gradient laisse des trous ; le bord du masque est continu par construction.
- Épaisseur du trait selon la luminance (1/2/3 px). Raison : c'est la modulation demandée, et elle se lit sans texture supplémentaire.
- Bascule nette au point médian, et non fondu. Raison : un fondu entre deux vues non recalées dessine deux personnages superposés.
- Rampe par pixel via un masque sur l'atlas, et non par calque. Raison : une même couche peut mélanger peau et tissu ; un masque suit la découpe réelle.
- Découpe en partition complète, et non en calques bruts. Raison : un pixel sans couche devient un trou transparent, et chaque trou crée une silhouette parasite.
- Reflets internes remplis seulement sous 1 % de la boîte. Raison : au-delà, la zone est du fond (espace entre bras et torse) ; un seuil unique ne distingue pas les deux cas, donc le seuil est une règle de taille, et ce choix est testé.
- Spéculaire désactivé dans la démo de référence seulement. Raison : la référence n'a pas de reflets durs sur ses vêtements ; le réglage de Kaël n'est pas touché, son spéculaire reste à régler.
- Découpe par couleur, sans annotation de parties. Raison : aucune donnée de parties pour cette illustration ; l'approximation est signalée comme telle dans la documentation.

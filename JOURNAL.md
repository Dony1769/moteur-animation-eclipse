# Journal de la mission « monteur 2D » (Éclipse Royale)

Dépôt : `/home/claude/moteur_3_0`, branche `autonome`, git local (pas de GitHub, voir DECISIONS.md D1).

## 2026-11-01 — M0 audit : fait
- Python 3.13.18, FFmpeg 6.1.1, git 2.43.0. Pas de GPU. 2 cœurs, 7,8 Go RAM, 22 Go disque.
- Commit `74344b4`. Tests de base verts (`tests/test_base.py`).

## M1 script : fait
- Parseur Fountain (`engine/script/fountain.py`), schéma `docs/schema_plan.md`, validateur `schema.py`.
- 14 tests verts (script de 2 pages dans `tests/donnees/`). Note `docs/apprentissage/fountain.md`.
- Commits `f779709`, `02647f3`.

## M2 exercices : fait (avec une correction)
- (a) balle `renders/exercices/a_balle.mp4` ; (b) marche `b_marche.mp4` ; (c) labiale `c_labiale.mp4` ; (d) travelling `d_travelling.mp4`.
- Vérification image par image : planches de contrôle regardées. Défaut trouvé et corrigé : le passage 2 du cycle était 25 % plus petit.
- Commit `02a2c1c`.

## M3 personnages : partiel, BLOQUÉ pour 2 personnages sur 3
- Validateur `engine/personnages/valider.py`, manifests dans `personnages/`.
- Kaël : OK (dessins réels). Aiko et Darius : incomplets. Aucun dessin de poses, d'expressions ni de bouches n'existe pour eux.
- Raison : les planches de référence sont trop petites (≈300 px) et ne sont pas des sprites. Pas de GPU pour en générer de nouveaux. Déblocage : fournir des dessins propres des deux personnages, ou accepter un manifest réduit.
- Commit `076b979`.

## M4 voix : fait, qualité limitée
- Plan parlant de 10 s : `renders/m4_plan_parlant.mp4`. Piper (siwis) + Rhubarb 1.14.0 + bustes alignés sur les yeux.
- Limites connues : barre noire sur le bord de certains cadres source ; les formes E et I portent un sourire, donc la synchro se lit aussi comme changement d'expression ; G et H non dessinées.

## M5 premier épisode : NON COMMENCÉ
- Bloqué par M3 (il faut trois personnages valides) et par l'absence de décor et de musique libres dans le dépôt.

## M6 finition : NON COMMENCÉ

## Prochaine étape
Déblocage humain (hors autonomie) : dessins de Aiko et Darius. Sinon, la prochaine étape technique est M3 avec un manifest réduit pour Kaël seul, puis M5 sur un épisode à un personnage.

## 2026-11-02 — Planches de base des personnages : découpe et contrôle
- Génération : Hugging Face connecté, mais `invoke` désactivé sur tous les Spaces (`gradio=none`). Génération faite par l'utilisateur dans Gemini à partir des briefs (docs/briefs/planches_personnages.md).
- Contrôle des planches : lot v1 (4 acceptées), lot v2 (2 acceptées), lot v3 (2 acceptées). Toutes les 8 planches de base sont acceptées (docs/briefs/controle_planches_v*.md).
- Découpe : engine/gen/decouper_grille.py, cellules explicites (4 colonnes pour les corps, 6 colonnes et rangées bornées pour les têtes). 60 cellules dans assets/personnages/.
- Reste à faire : les repères magenta anti-aliasés subsistent dans environ 31 cellules sur 60 (traits fins, pâles). Il faut un nettoyage plus fin avant alignement et détourage.
- Reste à faire : mettre à jour les manifestes M3 (Aiko, Darius, Alaric, Vorthaz) pointant vers assets/personnages/, puis aligner les bouches par les yeux (aligner_bouches) pour chaque personnage.

## 2026-11-02 — NPR (rendu animé non photoréaliste) : fait, sur banc d'essai
- Demande : analyser les six pièces jointes (toon ramp, Sobel G-buffer, normales sphériques, masque d'ombre visage, rim et spéculaire, pipeline studio), installer les dépendances, écrire les shaders et les passes, sauvegarder la compétence.
- Environnement : pas de GPU, mais contexte OpenGL headless EGL fonctionnel (Mesa llvmpipe, OpenGL 4.5 core). moderngl 5.13.0 installé.
- Livré : `engine/npr/` (passes MRT, ombrage, contour, référence numpy, banc d'essai), shaders GLSL 330 dans `engine/npr/shaders/`, `tests/test_npr.py`, `docs/npr.md`, `requirements.txt`, image de test `out/npr/test_tete_npr.png`.
- Tests : 13 tests NPR, 32 au total, verts. Écart GPU/numpy ≈ 3·10⁻⁶.
- Défaut trouvé et corrigé : les textures du G-buffer étaient en `REPEAT`, donc le Sobel lisait le bord opposé. Détecté par le test GPU sur un saut de profondeur en bord d'image.
- Défaut de test trouvé et corrigé : le test contour ne vérifiait pas le terme de profondeur seul. Ajout de cas isolés (saut vertical et horizontal, profondeur et normale) ; deux mutations vérifiées.
- Limite constatée : l'ombre de nez du masque visage est très petite sur la tête de test, car le masque n'ajoute pas d'ombre. Consigné dans docs/npr.md.
- Non fait : coque inversée, anisotropie des cheveux, mesure de performance GPU, application aux planches 2D (il faut une profondeur et des normales).
- Compétence : proposition de skill « moteur-rendu-anime-npr » à enregistrer par l'utilisateur.

## 2026-11-02 — NPR, suite : cheveux, 2.5D, corrections du second lot
- Demande : appliquer trois pièces jointes (kit correctif, relief de sprite, boucle C++), mettre à jour tests et documentation, proposer la mise à jour de la compétence.
- Fait : reflet anisotrope des cheveux (tangente en sortie 3 du G-buffer, Kajiya-Kay sur le demi-vecteur) ; chemin 2.5D (`engine/npr/relief.py` : calques, relief, normales, composition z-buffer) ; démo `demo_calque.py` ; banc `demo_tete.py` à quatre panneaux.
- Corrigé dans les pièces : formule de reflet fausse (elle ne bougeait pas avec la caméra), gradient décalé et flou annoncé mais absent dans le relief, boucle C++ non applicable (langage différent, appels invalides).
- Défauts trouvés en cours de route, corrigés : relief quasi plat (hauteur en unités de profondeur au lieu de pixels) ; dents au menton (alpha binaire, d'où le flou) ; reflet saturé en blanc sur la démo (mèches verticales, couleur trop vive).
- Erreur de mon test (pas du moteur) : un test lisait la texture après libération. Corrigé.
- Tests : 25 NPR (dont 7 GL), 44 au total dans le dépôt, tous verts. Mutations faites sur des copies : CLAMP remis en REPEAT détecté ; `th*th` remplacé par `th` détecté.
- Limites : relief estimé (intérieur plat) ; démo avec formes procédurales ; calotte du panneau D fine et vue de biais, non ajustée ; mémoire GPU non mesurée ; pas d'image de référence pour b4414824 (non jointe).
- Commit local sur `autonome`, pas de push.
- Compétence : proposition de mise à jour « moteur-rendu-anime-npr » soumise à l'utilisateur ; non enregistrée tant qu'il ne la sauve pas.

## 2026-11-02 — Calques articulés 2.5D : squelette, FFD, animation, VBO dynamiques
- Demande : pipeline de calques articulés (ordre et tri des calques, déformation par FFD et squelette avec poids, interpolation temporelle, VBO dynamiques avant les shaders NPR, tests).
- Fait : `engine/npr/rig.py` (squelette 2D rigide, skinning linéaire, poids par distance avec os actifs, grille FFD de Bernstein, pistes linéaires et cubiques, timeline) ; `engine/npr/calques_anim.py` (calque découpé en grille, sommets à la pose, tri par profondeur) ; `RenduNPR.dessiner_calques` (VBO dynamiques, z-buffer) ; `Maillage.mettre_a_jour` ; démo `engine/npr/demo_articule.py` (cinq calques, planche de six instants).
- Shader de géométrie : découpe alpha (`seuilAlpha`) et tangente nulle écrite sans NaN. Le comportement de la sphère ne change pas (suite existante verte).
- Défauts trouvés à la démo, corrigés : le corps se courbait quand la tête bougeait (os trop larges : ensembles d'os actifs par calque, avec test de régression) ; points parasites à fermeture complète des paupières (fermeture plafonnée à 0,9) ; frange en coupe droite, effet casque (bord en arc).
- Tests : 46 pour le rig et les calques (dont 8 GL), 90 au total, tous verts. Mutations faites sur copies : découpe alpha retirée (6 échecs), garde de tangente retirée (1 échec), test de profondeur désactivé (1 échec), rotation du squelette inversée (5 échecs).
- Vérification : la planche a été regardée image par image (corps rigide, paupière en trait fin, mèches qui suivent la tête).
- Limites : articulation 2D seulement (roulis, pas de lacet 3D) ; clignement linéaire ; normales non recalculées par la FFD ; relief figé au repos ; démo procédurale ; pas de vidéo rendue.
- Commit local sur `autonome`, pas de push.

## 2026-11-02 — Personnage réel : chargeur, atlas, normales sous FFD, cheveux Verlet, vues multiples
- Demande : remplacer les formes procédurales par de vraies illustrations découpées (chargeur et atlas), recalculer normales et tangentes sous déformation, passer de la face au trois quarts selon l'angle, simuler les cheveux et la frange en Verlet sur la grille FFD, tester et documenter.
- Données trouvées : le dépôt contient le personnage de Kaël (`universes/eclipse_royale/characters/kael`) : deux vues (face, trois quarts), couches par polygones au format `personnage-couches/2`, squelette à points-clés. Aucun profil. Aucune couche séparée pour les cheveux arrière, la frange, les yeux ou le visage.
- Fait :
  - `engine/npr/chargeur.py` : lecture du format, masque = polygone ∩ premier plan (fond = canaux ≥ 245), atlas 1024 px en rangées, correspondance image → UV par couche ;
  - `engine/npr/calques_anim.py` : normales et tangentes poussées par la jacobienne de la déformation totale (`jacobiennes`, `pousser_normales`), à la place de la rotation par os ; `construire` accepte un atlas (`texture`, `uv_de`) ;
  - `engine/npr/rig.py` : `GrilleFFD(marge=...)`, déformation localisée qui s'arrête hors de la boîte ;
  - `engine/npr/physique.py` : `ChevelureSimulee`, Verlet sur grille FFD, racine épinglée, repère de la tête avec forces apparentes ;
  - `engine/npr/multivue.py` : poids entre vues réelles, fondu, bascule, signalement du profil absent ;
  - `engine/npr/demo_personnage.py` : personnage réel de Kaël, rangées tête inclinée et fondu ;
  - `engine/npr/demo_articule.py` : grilles FFD sur la chevelure arrière et la frange, pilotées par Verlet ;
  - `engine/npr/rendu.py` : une seule texture GPU par atlas, partagée entre calques, libérée proprement.
- Défauts trouvés en cours de route, corrigés :
  - la FFD déformait toute la boîte : fermer les yeux aurait écrasé toute la tête. Ajout de la marge (déformation qui décroît et s'arrête) ;
  - le document de conception n'appliquait que la moitié de la correction des contraintes pour une racine épinglée : la racine glisse. Corrigé avec les masses inverses et testé ;
  - sa formule de Verlet était absente du texte : la forme standard est utilisée et la gravité est exprimée en px/s² (y vers le bas) ;
  - mutation « marge retirée » non détectée au premier passage : ajout de deux tests de marge, puis détection ;
  - deux de mes assertions étaient fausses (bas de la tête à y = 169, pas 200 ; décroissance testée au-delà de la marge) : corrigées, le code était juste.
- Tests : 42 nouveaux tests (`tests/test_personnage_reel.py`, dont 1 GL), 132 au total, tous verts. Mutations sur copies : normales non poussées (2 échecs), correction à moitié (1 échec), signe d'Euler (2), marge retirée (2 après ajout), atlas décalé d'un texel (1).
- Vérification visuelle : planche Kaël et planche de cheveux regardées avec Read. Le clignement, l'inclinaison de la tête et le fondu s'y voient. La frange suit la tête avec un léger retard, non quantifié sur une séquence.
- Limites :
  - pas de profil : l'angle 90° est signalé « hors plage », rien n'est rendu ;
  - pas de cheveux, frange ni yeux séparés dans les données : clignement et physique des cheveux ne tournent que sur la démo procédurale ;
  - fondu entre face et trois quarts sans recalage : contours doublés à mi-chemin ;
  - squelette réel à deux os seulement ; contour noir épais non réglé ;
  - jacobienne moyennée par triangle ; relief figé au repos ;
  - temps de rendu non remesuré après ajout de la physique.
- Pas de push. Commit local sur `autonome`.

## 2026-11-02 — Encre fine, bascule nette, rampes teintées, découpe par matériaux
- Demande : supprimer l'aspect brouillon (traits épais, fondu à 22,5°, illustration remplacée par des formes) et se rapprocher de l'illustration de référence.
- Fait :
  - `engine/npr/encre.py` : silhouette continue 1/2/3 px selon l'éclairage ; arêtes internes amincies (non-maxima, hystérésis) ;
  - `multivue.vue_nette` et `appliquer_transition` : bascule nette au point médian, cisaillement FFD nul aux bornes ; le fondu est conservé pour comparaison ;
  - `rampe_chaude` / `rampe_froide` et `masqueMateriau` : rampe choisie par pixel dans `ombrage.frag` ;
  - `engine/npr/decoupe_materiaux.py` : découpe par couleur, en partition complète (trous comblés par le voisin, reflets clairs internes remplis sous 1 % de la boîte) ;
  - `engine/npr/demo_reference.py` : planche de l'illustration de référence.
- Défauts trouvés en cours de route, corrigés :
  - des trous transparents dans le personnage créaient une silhouette à chaque trou (points noirs). Corrigé par la partition complète ;
  - des reflets clairs de la référence sortaient du masque et laissaient voir le fond. Corrigé par le remplissage des petites zones fermées ; un premier remplissage sans seuil comblait l'espace entre bras et torse, donc il a été limité en taille ;
  - le spéculaire dur de la démo (`step` sur N·H) produisait des traits blancs sur les calques sombres. Désactivé dans la démo de référence seulement ;
  - hypothèses écartées : le relief (même image à 0 et 0,04) et les marches de profondeur entre couches (même image avec un plan commun).
- Tests : 165 au total, tous verts (dont 10 encre, 13 découpe, 8 bascule, 3 rampes).
- Vérification visuelle : planches regardées avec Read (`planche_reference_v7.png`, dans le dossier de travail de la session).
- Limites : la référence est un autre personnage, sa découpe est une approximation par couleur ; l'inclinaison de tête est à peine visible ; le spéculaire dur reste à régler dans la démo de Kaël ; l'encre interne reste fragmentaire.
- Pas de push. Commit local sur `autonome`.

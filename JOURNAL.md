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

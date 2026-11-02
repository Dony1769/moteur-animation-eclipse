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

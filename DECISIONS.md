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

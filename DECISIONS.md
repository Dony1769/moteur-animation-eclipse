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

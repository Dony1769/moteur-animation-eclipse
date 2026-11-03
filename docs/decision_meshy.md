# Décision : rôle de Meshy (ou Tripo) dans le moteur

- Meshy (ou Tripo) sert uniquement à fournir un maillage de personnage (géométrie, textures).
- Le rig, le skinning et toutes les animations sont produits par le moteur, pas par le service.
- Ne pas utiliser les clips d'animation, le rig automatique ou le retargeting du service.
- Chaque personnage issu d'un service passe par le diagnostic (engine/importer) comme n'importe quel FBX externe.

Décidé par l'utilisateur le 3 novembre 2026.

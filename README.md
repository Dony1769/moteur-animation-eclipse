# Moteur d'animation 3D à tracés

Moteur d'animation écrit de zéro, piloté par Blender 4.5 LTS en mode headless. Les traits visibles
sont générés par le moteur (Line Art de Grease Pencil) à partir de la géométrie et du mouvement.

## Lancer une scène

    tools/rendre.sh out/essai --duree 4

Produit `out/essai/scene.mp4` (24 images par seconde, H.264). Blender doit être installé à
`/home/claude/moteur3d/tools/blender-4.5.15-linux-x64/blender` (ou variable `BLENDER`).

## Installer MB-Lab (jalon 3)

    git clone https://github.com/animate1978/MB-Lab.git /home/claude/moteur3d/deps/mblab/src
    cd /home/claude/moteur3d/deps/mblab/src && git checkout 063bff04e60f3e7c651fda628c30f5d83f3f3078
    mkdir -p /home/claude/moteur3d/scripts/addons && ln -sfn /home/claude/moteur3d/deps/mblab/src /home/claude/moteur3d/scripts/addons/mblab

## Tests

Tests purs Python :

    python3 -m unittest discover -s tests -v

Tests Blender (doigts, pose) :

    tools/tester_blender.sh tests/blender_personnage.py

    python3 -m unittest discover -s tests -v

## État des jalons

| Jalon | Contenu | État |
|---|---|---|
| 1 | Archive et nettoyage de main | fait |
| 2 | Squelette, configuration, commande de rendu | fait : scène vide, pas de forme visible |
| 3 | Personnage MB-Lab, rig avec doigts | partiel : corps m_an01 (non Kaël), 71 os dont 5 doigts par main, test de pose vert ; traits de Kaël à faire |
| 4 | Mouvement : course, saut, coup | à faire |
| 5 | Extraction des tracés (Line Art) | à faire |
| 6 | Décor procédural | à faire |
| 7 | Caméra et effets | à faire |
| 8 | Scène de 4 s en MP4 | à faire |

## Mesures

Machine : 2 CPU, 7 Go de RAM, pas de GPU. Blender 4.5.15 LTS.

| Mesure | Valeur |
|---|---|
| Blender Workbench, 960×540, première image (démarrage compris) | environ 4,4 s |
| Blender Cycles CPU, 32 échantillons, 960×540, par image | environ 10,4 s |
| Scène vide de 1 s (24 images) de bout en bout, dont FFmpeg | 7,5 s |
| Ligne Art Grease Pencil, par image | à mesurer au jalon 5 |
| Simulation de cape, coût | à mesurer au jalon 4 |
| Estimation 15 min à 24 i/s, Cycles 32 échantillons | 21 600 images × 10,4 s ≈ 62 h (à réduire) |

## Choix

- Blender 4.5.15 LTS : le Line Art de Grease Pencil v3 est disponible (`GreasePencilLineartModifier`).
- FFmpeg 6.1.1 (paquet système) : suffisant pour l'encodage H.264.
- MB-Lab (personnage) : prévu au jalon 3, version 1.8.1, code sous GPL-3.0 (voir `CREDITS.md`).

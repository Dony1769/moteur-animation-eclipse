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
| 2 | Squelette, configuration, commande de rendu | fait |
| 3 | Personnage MB-Lab m_an01, rig avec doigts, costume (chemise, pantalon, ceinture, bottes), cheveux noir-bleu à pointes bleues, yeux bleus, épée | fait en partie : pas de cape, pas de broche |
| 4 | Mouvement : course, saut, coup, retour (angles en code) | fait ; sens des articulations validés sur rendus de contrôle |
| 5 | Tracés | fait avec Freestyle au lieu de Line Art (voir Choix) |
| 6 | Décor procédural | fait en partie : sol et buissons, sans végétation fine |
| 7 | Caméra et effets | fait : secousse, flash une image, traits de vitesse |
| 8 | Scène de 4 s en MP4 | fait : `out/final/scene_4s.mp4` (rendu local, non versionné) |

## Sens des articulations (rig MB-Lab)

Validés par rendus de contrôle, pas supposés :
- Repos : les épaules sont en T dans le rig ; une rotation Z de +1,0 rad abaisse le bras droit (−1,0 pour le gauche).
- Épaule X positif : bras vers l'avant. Coude X positif : avant-bras vers l'avant.
- Doigts X positif : flexion (poing). Négatif : hyperextension (c'était l'erreur précédente).

## Choix

- Blender 4.5.15 LTS. Le Line Art Grease Pencil rendait noir en headless (Workbench et EEVEE testés) : on utilise Freestyle (Cycles CPU), dont les contours sont mesurés et propres.
- Le corps est en aplats à deux tons ; seuls les contours Freestyle sont tracés.
- Caméra de profil, objectif 42 mm, suivi partiel sur l'axe Y.
- FFmpeg 6.1.1 (paquet système) pour l'encodage H.264.
- Mocap CMU non utilisée : licence non vérifiée. Mouvement écrit en code.

## Mesures

Machine : 2 CPU, 7 Go de RAM, pas de GPU. Blender 4.5.15 LTS.

| Mesure | Valeur |
|---|---|
| Workbench, 960×540, première image (démarrage compris) | environ 4,4 s |
| Cycles CPU, 32 échantillons, 960×540, scène vide | environ 10,4 s |
| Scène 4 s, 960×540, 2 échantillons + débruitage, avec Freestyle | environ 18 s par image |
| Scène 4 s, même réglage, sans Freestyle | environ 4,8 s par image |
| Scène 4 s, 2 échantillons contre 4 | pratiquement le même temps : le goulot est Freestyle |
| Rendu 4 s complet (96 images) | à relever dans le journal du rendu final |
| Épisode de 15 min à 24 i/s, même réglage | 21 600 images × 18 s ≈ 108 h (à réduire) |

Optimisations possibles, non faites : réduire la résolution de calcul de Freestyle, ou n'activer Freestyle que sur les images vues.

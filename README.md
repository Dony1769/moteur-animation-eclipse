# The Chase : décor et personnage en animation Blender

Projet d'animation en rendu Blender 4.5 LTS (headless, Cycles CPU ou GPU). Aucune primitive : décor en maillages
téléchargés (Poly Haven, CC0), personnage Mixamo (fichiers non versionnés, déposés à part).

## Lancer une scène

    BLENDER=/chemin/vers/blender ASSETS=/chemin/vers/assets \
      RX=640 RY=270 SPP=4 FRAME=8 $BLENDER -b --factory-startup --python scenes/chase_mixamo.py -- out/image

- `scenes/chase_a.py` : décor seul. Variables : `RX`, `RY` (résolution), `SPP` (échantillons).
- `scenes/chase_mixamo.py` : décor + personnage Mixamo en course sur place. `FRAME` choisit l'image.
- `ASSETS` : dossier contenant `ph/` (Poly Haven) et `mixamo/` (FBX). Par défaut `assets/` à la racine du dépôt.

## Notebooks

- `notebooks/colab_render.ipynb` : repli sur Google Colab (GPU T4 si disponible, sinon CPU). Clip Mixamo
  facultatif : il demande de déposer les deux FBX.
- `notebooks/kaggle_render.ipynb` : version Kaggle, bloquée tant que la vérification par téléphone n'est pas faite.

## Budget

`budget/plan.py` : planificateur à partir des mesures de `docs/budget.md`.

## Documentation

- `docs/todo.md` : état des étapes et blocages.
- `docs/style-chase.md` : mesures de l'étape A.
- `docs/assets.md` : sources et licences des assets.

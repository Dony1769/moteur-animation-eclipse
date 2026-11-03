# Méthode Blender 4.5 LTS : état au 2 novembre 2026

Ce document décrit ce qui a été testé, pas ce qui est prévu.

## Versions
- Blender 4.5.15 LTS, headless (`-b`), Cycles CPU, Freestyle pour les tracés.
- FFmpeg 6.1.1 (libx264, 24 images/s) pour l'assemblage MP4.

## Base du personnage
- **CharMorph 0.3.5** (GPL-3.0) : dépôt Upliner/CharMorph. Son manifeste indique `blender: (3, 3, 0)`, donc
  la compatibilité 4.5 n'est pas garantie. Ses bases de la bibliothèque (CharMorph-db) sont soit AGPL-3
  (mb_male, mb_female : exclues), soit CC-BY (antonia, reom). Aucune n'est CC0.
- **Vitruvian Project 142** (CC0, withinamnesia.itch.io/vitruvian-project-cc0) : fichier
  `VitruvianProject142.blend` (162 Mio). Il est déjà rigé en Rigify, avec 809 os, dont trois phalanges par
  doigt et un pouce, et une tête rigée. Il est chargé dans Blender 4.5 sans erreur. C'est la base retenue.

## Squelette
- Rig Rigify inclus dans la base : os DEF (déformants) + os de contrôle. Les contraintes des os DEF
  (Copy Transforms vers les os de contrôle) sont retirées pour poser directement les os DEF.

## Mouvement
- Clips CMU (mocap.cs.cmu.edu, sans restriction d'usage selon le README de la conversion BVH :
  https://github.com/Shriinivas/cmubvh) : course 09_01, saut 13_11, coup d'épée 02_09.
- Retargeting : delta de rotation monde par rapport à une image neutre de la source, composé avec le repos
  de la cible. Les bras sont légèrement écartés au repos. Le déplacement horizontal est ignoré.
- Limites observées : tronc penché, pieds et orteils déformés, lame collée à la cuisse, main qui ne tient
  pas l'épée. Le retargeting actuel n'est pas valide sur le rig Rigify.

## Temps mesurés (CPU, sans GPU)
- Chargement du fichier de base : environ 2 minutes.
- Retargeting d'un clip de 36 images : 1 070 secondes (la boucle de mise à jour du rig est lente sur le
  maillage subdivisé).
- Rendu d'une image 960×540, 2 échantillons, débruitage, tracés Freestyle : 31 secondes.

## Ce qui n'est pas fait
- Cape simulée (modificateur Cloth) : pas encore.
- Vêtements en maillages séparés : pas encore (zones de couleur seulement).
- Line Art Grease Pencil : non intégré à ce rendu. Le test précédent en mode headless produisait un rendu
  noir ; il reste à retester avec la source par collection.
- Mains : la densité du maillage Vitruvian est suffisante, mais la pose des doigts n'est pas validée.

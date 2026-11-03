# Apprentissage : combat cinématique, effets et son (Blender 4.5)

Notes prises avant d'écrire la scène. Ce qui est « lu » n'est pas encore « testé » : chaque point est vérifié par un rendu avant d'être présenté.

## Sources lues

- BlenderNation, « Real time impact VFX in Blender 2.92 » (tutoriel de P2Design, 2021) : effet d'impact poussiéreux animé. La page ne donne pas les réglages ; la vidéo de l'auteur est la source complète.
- Archive Blender (wiki 2015, Blender 2.4) « Audio Sequences » : strip audio dans l'éditeur vidéo, décalage à la souris, volume par courbe, mixage automatique. Méthode ancienne, mais les principes restent valables en 4.5.
- Recherches complémentaires : tutoriels de poussière et de particules (lesterbanks.com), retargeting Mixamo vers Rigify (cgtrader, retargetkit, mixaify).

## Ce que je retiens

### Effets (FX)
- Poussière au sol : système de particules émis depuis une surface (le sol), avec de petits débris instanciés. Les débris sont des maillages Poly Haven déjà présents (pas de primitive).
- Étincelles au contact des lames : particules courtes et rapides, émises au moment du coup (image d'impact connue).
- Secousse de caméra et flou de mouvement : déjà en place, à garder sur les impacts.
- Aucun effet ne doit être un cube, une sphère ou un plan visible.

### Son
- Le son se pose dans l'éditeur vidéo (strip audio, `sequence_editor.sequences.new_sound`) à l'image exacte de l'impact.
- Les bruitages sont synthétisés en Python (bruit filtré, enveloppes, sinus) : pas de fichiers tiers.
  - Frottement de lame : bruit filtré passe-bande, enveloppe courte.
  - Impact : basse sinusoïdale courte et bruit percussif.
  - Pas : bruit sourd, un par appui.
- Mixage : les strips se mélangent au rendu ; le rendu doit encoder l'audio (codec AAC dans le conteneur MP4), à vérifier par un test.

### Mouvements
- Rythme : marche, puis course, puis affrontement. Un clip par phase.
- Le personnage original gagne : une séquence de coups du gagnant, puis le perdant encaisse et tombe.
- Retargeting Mixamo vers Rigify : appris comme méthode (contrôles FK, copie de la rotation monde, bake), non appliqué.

## Points bloquants

- Pas de clip de marche disponible en local. Il faut un Walking.fbx (et des coups supplémentaires, par exemple un coup de poing ou une garde) dans le dossier Drive « The_Chase_FBX ».
- Les sons et les FX ne sont pas encore écrits ni testés.

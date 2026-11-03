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

## Apprentissage 2 : créer des clips à partir d'un seul squelette (sans nouveau FBX)

Sources lues : documentation Blender 4.5 (Action, slots, couches et canaux), recherches sur les cycles de marche en Python (keyframe_insert sur os de pose). La documentation Action ne décrit pas les slots en détail : la méthode est donc confirmée par test, pas par la seule lecture.

Méthode retenue :
- Un clip procédural est une action créée en Python : on assigne une action vide à l'armature, puis on pose les rotations des os image par image et on insère les images-clés (keyframe_insert sur rotation_euler, avec rotation_mode XYZ pendant la création).
- Le clip de marche suit un cycle sinusoïdal : cuisse et genou en opposition, bras en contre-phase, bassin qui oscille. Une foulée complète tient en 24 images.
- Les déplacements (approche, fuite, chute) sont des images-clés sur l'objet armature lui-même, pas sur les os.
- Pour un montage propre, on place chaque clip dans la pile NLA, puis on cuit le résultat (bake) : une action unique par personnage, image par image, en quaternions. Cela évite les conflits entre bandes.
- Une seule Maria (un seul FBX) suffit : marche, course, coups et victoire viennent de ce squelette.

Points à vérifier par rendu : le signe des rotations (les genoux ne doivent plier que dans un sens), le glissement des pieds, et la pose de victoire.

## Effets et son (méthode retenue)

- Impacts : petits débris Poly Haven instanciés, lancés en arc balistique à partir du point de contact, puis retirés au bout de quelques images.
- Son : bruitages synthétisés en Python (numpy) et mixés dans une piste WAV, calés sur les images d'impact. Le MP4 est produit par ffmpeg à partir des images et de la piste son.
- Limite : pas de poussière simulée à ce stade.

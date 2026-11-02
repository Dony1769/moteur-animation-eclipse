# Moteur 3.0 — architecture et feuille de route

## Principe

Le moteur 2.0 dessinait tout en vecteur (skia) : c'était trop schématique. Le 3.0 sépare
deux rôles :

- **La génération visuelle** (univers, personnages, objets, planches de design) est confiée à des
  modèles d'image Hugging Face via des Spaces Gradio (Qwen-Image, Qwen-Image-Edit-Angles, SAM3
  pour la segmentation, depth estimation pour la profondeur). Le moteur ne fait pas de dessin
  à la main.
- **Le moteur** assemble, anime, place, éclaire et filme : calques, profondeur, caméra, montage,
  effets. Il lit des fichiers JSON (univers, personnage, scène, plan) et produit la vidéo.

Chaque élément visuel est une ressource versionnée avec un manifeste, pour que le même
personnage, le même lieu ou le même objet reste identique d'un plan à l'autre.

## Structure

```
moteur_3_0/
  ARCHITECTURE.md          ce document
  tools/hf_client.py       appel direct d'un Space Gradio (jeton HF_TOKEN dans l'environnement)
  tools/make_universe.py   génère les lieux d'un univers à partir de universe.json
  universes/<slug>/
      universe.json        bible de style + lieux + personnages + objets (source de vérité)
      locations/*.png      décors générés
      characters/<id>/     planche de design, vues tournées, couches segmentées
      objects/<id>/        objets manipulables (image, masque, points de contact)
  engine/                  (à venir) rendu, caméra, interactions, FX
  out/                     rendus de test
```

## Phases

### Phase 1 — Univers (en cours)
- Bible de style d'un univers : palette, lumière, rendu, éléments à éviter.
- Lieux générés à partir d'un préfixe de style commun + un texte par lieu, en 16:9.
- Manifeste `universe.json` : chaque lieu pointe vers son image et ses métadonnées.
- Contrôle : relecture humaine de chaque lieu avant de passer à la suite.

### Phase 2 — Personnages (base faite pour Kaël)
- Planche de face puis vues tournées (Qwen-Image-Edit-Angles, ±45°, ±90°, dos par rotation
  successive).
- Segmentation des parties (tête, cheveux, cape, bras, jambes) avec SAM3 pour pouvoir les
  animer séparément en 2.5D.
- Contrôle : même personnage sur toutes les vues (cheveux, cape, ceinture, couleurs).

### Phase 3 — Animation et interactions
- Le mouvement est produit uniquement par le moteur : rig et poses, rotations, caméra, lip-sync, expressions.
  Hugging Face ne génère jamais une image animée ni une interpolation entre deux images.

- Objets manipulables : chaque objet a une image, un masque, et des points de contact
  (main, assise, appui) dans son JSON. Le personnage est placé sur le point de contact.
- Interaction avec n'importe quel objet : la liste des points de contact décide ce qui est
  possible ; un objet sans point de contact ne peut être que déplacé.

### Phase 4 — Caméra, plans, montage
- Plans décrits en JSON : cadrage, mouvement de caméra, profondeur de champ, mise au point.
- Profondeur estimée par un modèle de depth pour appliquer des flous et des mises au point
  réalistes.
- Transitions (coupe, fondu, volet, flou directionnel) et changements de scène.

### Phase 5 — FX et VFX
- Particules, lumières portées par les objets (torche, brasero), brume, pluie, magie.
- Tous les effets lisent le même éclairage et la même profondeur que la scène, pour rester
  cohérents entre eux et avec les personnages.

## Limites connues

- La cohérence d'un personnage d'un plan à l'autre dépend des modèles : elle doit être
  vérifiée sur une planche avant toute animation.
- Les rendus passent par des Spaces ZeroGPU : chaque image consomme le quota du compte. Pour
  une série complète il faudra un abonnement PRO ou un endpoint dédié.
- L'animation « ultra détaillée » par IA vidéo reste inégale : les mains et les tissus sont
  les points faibles. Le moteur doit donc garder la main sur la composition et le timing.

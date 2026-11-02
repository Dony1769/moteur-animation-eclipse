# Pipeline 2.5D : Kaël dans la grotte (état au 1er novembre 2026)

Tout tourne en local, sans API payante. Modèles dans `models/`.

## Modèles et dépendances
- DWPose `dw-ll_ucoco_384.onnx` (133 points : corps 17, pieds 6, visage 68, mains 42), `yolox_l.onnx`
- Real-ESRGAN x4plus anime 6B `RealESRGAN_x4plus_anime_6B.pth` (BSD-3)
- Depth-Anything-V2 small (`models/depth_anything_v2_small`, Hugging Face)
- rembg 2.0.86, modèle `isnet-anime` (détourage)
- PyTorch CPU, transformers, onnxruntime, OpenCV, numpy, ffmpeg

## 1. Gabarit et planches (génération externe)
- `engine/gen/gabarit.py gabarit <sortie>` : canevas 856×900 avec repères magenta (yeux y=107, bouche y=137, menton y=156, pieds y=876, axe x=285).
- `engine/gen/gabarit.py controler <image>` : refuse une image dont les yeux dérivent de plus de 4 px ou dont l'échelle sort de 0,92–1,08.
- Brief : toujours joindre la référence et le gabarit ; fond blanc ; un seul personnage ; une image par fichier ; nom explicite.

## 2. Découpe des planches
- `engine/gen/decouper_planche.py <planche> <sortie> <préfixe> "x0,y0,x1,y1;..."` : cellules explicites (les découpes automatiques fusionnent les figures). Détourage isnet-anime, garde la plus grande zone, hauteur 840 px, pieds y=876, centre x=428.
- Contrôle visuel obligatoire : planche de contrôle avec ligne de sol et axe central.

## 3. Agrandissement
- `engine/gen/agrandir.py` (Real-ESRGAN, tuiles 192 px) : environ 45 s par image 856×900.
- `engine/gen/agrandir_planches.py` : agrandit toutes les figures de `out/sheets` vers `out/sheets_x4`.
- Plateau de grotte : `out/scene/grotte_x4.png` (crop de la grotte sans bordure blanche, puis x4).

## 4. Pose et cycles
- `engine/rig2d/pose.py` : DWPose (`detecter(img_rgb, session)`), à lancer sur des images isolées (détourage + fond blanc).
- Cycle de profil : `out/cycle/*_sprite.png`, recentrés sur le bassin : `out/cycle/hanche/`.
- Cycle de dos : `out/cycle/dos/dos_03..05.png` (cadres de la planche de marche), recentrés sur le bassin.
- Règle : centrer chaque pose sur le bassin, jamais sur la boîte englobante (sinon le corps saute).

## 5. Intégration dans le décor
- `engine/rig2d/integrer_grotte.py` :
  - `plateau_et_profondeur()` : plateau 1280×720 + carte de profondeur.
  - `lumiere_ouverture()` : source lumineuse = zone la plus lumineuse de la moitié haute.
  - `eclairer()` : deux tons selon la direction de la lumière, teinte chaude/froide, liseré de contre-jour.
  - `ombre_portee()` et ombre de contact sous les pieds.
  - Exposition du personnage recalée sur la luminosité du décor.
  - Masquage par les rochers : désactivé dans les tests actuels, car la profondeur monoculaire rend la tête invisible. Limité aux jambes (tiers bas) avec une marge de 0,12 ; non prouvé.
- Hauteur à l'écran = hauteur monde × zoom / 2 (monde 2560×1440).

## 6. Plans
- `engine/rig2d/plan_zoom.py` : plan large (zoom 1,0, personnage ~233 px), zoom vers 2,4 (personnage 560 px), pieds fixes à y=640.
- `engine/rig2d/plan_marche.py` : phase de zoom puis marche vers le fond ; cycle de dos ; pieds avancent pendant les passages ; accentuation légère ; balancement de caméra.
- Sortie : `out/rendu_plan_1_opt/plan_1.mp4` (12 s, 12 images/s, 4 images par pose).

## Limites connues
- Masquage par les rochers non prouvé.
- Cycle de dos : 3 cadres réels + répétition (le cycle complet demande le brief de dos, pas encore livré).
- Pas de mouvement de cape ni de poussière.
- Glissement résiduel du sol (les pieds avancent par à-coups).
- Zoom 2,4 : netteté limitée par le plateau d'origine (1166 px de large).

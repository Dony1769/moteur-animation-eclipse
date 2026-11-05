# Recherches : génération humaine (mission humaine, phases 2 à 6)

## Hunyuan3D 2.1 (Tencent) : étude d'architecture, sans copie de code ni de poids
Clause de licence respectée : aucun code, aucun poids, aucune sortie de Hunyuan3D n'est utilisé ni n'entraîne un autre modèle
(clause 5(b) de la licence communautaire). Seules les idées sont retenues, réimplémentées à notre façon.

Sources :
- Officielle : rapport arXiv 2506.15442 (https://arxiv.org/html/2506.15442v1), lu le 5 novembre 2026. Sections 3.1 (forme) et 3.2 (texture).
- Non officielle : DeepWiki, pages sur Hunyuan3D-2 (https://deepwiki.com/Tencent/Hunyuan3D-2/4.2-texture-generation-(hunyuan3d-paint)),
  lu le même jour. Source tierce : à confirmer contre le code officiel avant toute décision technique.

Idées retenues :
1. Texturage par fusion de vues (texture) : chaque vue contribue à une face selon le cosinus de sa normale élevé à 4, et un
   poids par vue (avant 1,0, arrière 0,5, côtés 0,1, dessus et dessous 0,05). Réimplémenté : engine/texturing/fusion_vues.py,
   testé dans test_fusion.py (VALIDE_TECHNIQUE, limite : pas d'occlusion).
2. Remplissage des zones non vues : prévu, non implémenté (méthode cv2 inpainting, à valider).

Idées notées, non retenues pour l'instant :
3. Forme par VAE sur des échantillons de surface (vecteurs de latents) et diffusion sur ce latent : demande des données
   d'entraînement et un GPU (la mission l'exclut sur cette machine). À étudier plus tard si un GPU distant est accepté.
4. Conditionnement par normales et cartes de coordonnées canoniques : utile pour le texturage ; à réutiliser sans réseau.

Matériel exigé par Hunyuan3D (relevé) : au moins 16 Go de VRAM pour forme et texture ensemble ; texture seule : 180 jours-GPU
d'entraînement, non reproductible ici.

## Dépôt MakeHuman : asset CC0 utilisé (phase 2 et 3)
- LICENSE.ASSETS.md : CC0 1.0 ; le code (AGPL) n'est pas utilisé. Données lues : 3dobjs/base.obj et targets/.
- Unité : décimètres (apps/gui/guiexport.py).
- 8 cibles sur 1 280 n'ont aucune donnée (macrodetails universal-*) : écartées (entrée 136).

## Le Hodgins 2016 (centres de rotation) : code non officiel lu, méthode réécrite
Voir docs/rapports/phase4_centres_rotation_hanche.json et erreurs_apprises entrée 135.

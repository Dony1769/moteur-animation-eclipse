# Rendu animé non photoréaliste (NPR)

Module `engine/npr/` : chaîne OpenGL 3.3 (G-buffer MRT, ombrage toon, contour Sobel), référence numpy et tests. Ce module ne rend pas encore les planches 2D du projet : il lui faut une géométrie, ou au moins une profondeur et des normales (voir « Limites »).

## Vérification des six pièces jointes

| Pièce | Affirmation | Verdict | Traitement dans le code |
|---|---|---|---|
| Toon ramp (15476050) | Half-Lambert `N·L·0,5+0,5` puis rampe 256×1 en `GL_NEAREST` | Valide | Rampe 256×1, filtre `NEAREST`. La rampe est utilisée en RGB : le `.r` de la pièce « masque visage » est écarté (deux conventions contradictoires). |
| Cel-shading à seuils (2ba4a70b) | `if/else` sur `diff` | Équivalent à la rampe, moins flexible | Non retenu : la rampe couvre le même cas. |
| Coque inversée (2ba4a70b) | Extrusion le long des normales + culling des faces avant | Principe correct, pseudo-code non exécutable, pas de maillage à contourner | Non implémenté. |
| Sobel G-buffer (950751dc) | Sobel sur normales et profondeur, seuils | Principe valide, trois corrections | Gx/Gy inversés dans la pièce (sans effet sur la magnitude). Normales lues sans décodage. Seuil de profondeur absolu : il dépend de la distance. Corrigé : Sobel sur `log(profondeur)`, fond substitué par `profondeur_fond`. |
| Normales sphériques (4959cb8a) | `normalize(FragPos − HeadCenter)` mélangé à la normale réelle | Formule valide, deux erreurs | `HeadCenter` déclaré `in` dans le fragment shader : invalide. Corrigé en uniform en espace vue. Mélange 100 % sphérique : l'ombre du nez disparaît. Corrigé par `masque_sphere` (0 autour du nez). Le « Data Transfer » de Blender n'a pas d'équivalent ici. |
| Masque d'ombre visage (fb41840d) | `mix(1, rampe, masque)` avec décalage `L + avant·0,3` | Valide comme contrôle artistique, mais il ne crée pas d'ombre | Le masque autorise la rampe à agir ; l'ombre vient de la normale. Hors masque = pleine lumière : opt-in (`masque_visage`), sinon tout le corps serait éclairé. Décalage = choix artistique, non une loi physique. |
| Rim light et spéculaire (0998e796) | Fresnel × N·L, seuil lissé ; Blinn-Phong durci par `step` | Valide | `rimSmoothness = 0` rend `smoothstep` indéfini : borné à 1e-4. Anisotropie des cheveux non faite (demande des tangentes). |

Affirmations non vérifiées et non utilisées : pipelines de Chainsaw Man, Genshin, Guilty Gear, Cygames. La pièce 2ba4a70b cite « Claude 3.5 Haiku » sans rapport avec le sujet.

## Architecture

Trois passes, toutes en espace vue (caméra à l'origine, regard vers −Z, profondeur `d = −z > 0`).

1. **Géométrie** (`shaders/geometrie.vert|frag`) : MRT dans un FBO et un tampon de profondeur matériel.
   - sortie 0 : albédo RGBA32F ;
   - sortie 1 : normale vue, **brute**, non encodée (fond = 0) ;
   - sortie 2 : `r` = profondeur linéaire, `g,b` = UV de surface (fond = 0).
2. **Ombrage** (`shaders/ombrage.frag`, plein écran) : lit le G-buffer, applique la rampe, les normales sphériques masquées, le masque visage, le rim et le spéculaire. Sortie RGBA32F.
3. **Contour** (`shaders/contour.frag`, plein écran) : Sobel 3×3 sur les normales (`|Gx|+|Gy|` en longueur vectorielle) et sur `log(profondeur)`. Trait noir si l'un des deux seuils est dépassé. Sortie RGBA8.

Les masques sont peints en **UV de surface** (lus via `g,b` du G-buffer), jamais en coordonnées d'écran : ils suivent la tête quand elle tourne.

Toutes les textures d'échantillonnage sont en `GL_NEAREST` et `GL_CLAMP_TO_EDGE`. Le Sobel lit au-delà du bord ; avec le mode `REPEAT` par défaut, le bord gauche recevait la valeur du bord droit (bug trouvé par les tests GPU/numpy et corrigé).

## Formules retenues

- Demi-lambert : `u = N·L · 0,5 + 0,5`, couleur = `rampe[floor(u·256)]`.
- Normale sphérique masquée : `N = normalize(mix(N_réelle, normalize(P − C_tête), w))`, avec `w = masque_sphere(UV) · poids_sphere`.
- Masque d'ombre visage (si `masque_visage`) : `u = mix(1, demi_lambert(N, normalize(L + avant·0,3)), masque_ombre(UV))`.
- Rim : `f = 1 − max(N·V, 0)`, `r = f · max(N·L, 0)`, `rim = smoothstep(seuil − s, seuil + s, r)` avec `s = max(douceur, 1e-4)`.
- Spéculaire durci : `step(seuil, max(N·H, 0))`, `H = normalize(L + V)`.
- Contour : `edN = |Gx_N| + |Gy_N| > seuil_normale` ou `edD = |Gx_log| + |Gy_log| > seuil_profondeur`. Fond : couleur de fond, sans trait.

## Dépendances et environnement

- Python 3.13, numpy 2.5.3, OpenCV 5.0.0 (headless), moderngl 5.13.0, pytest 9.1.1. Versions dans `requirements.txt`.
- Installation : `pip install --break-system-packages -r requirements.txt`.
- OpenGL : contexte headless EGL, Mesa llvmpipe 25.2.8 (OpenGL 4.5 core). Il n'y a pas de GPU (`/dev/dri` absent) : les rendus sont logiciels, donc lents, mais exacts pour la validation.
- Pas de `glslangValidator` : la validation des shaders est leur compilation par Mesa, lancée par `RenduNPR`.
- Une uniform que le GLSL n'utilise pas est éliminée à la compilation. Toute uniform passée depuis `rendu.py` doit donc être lue par son shader, sinon `KeyError`.
- Sans libEGL ou sans contexte, les tests GL sont ignorés ; les tests numpy tournent toujours.

## Tests (`tests/test_npr.py`)

- Rampe : bandes exactes (texels 89/90 pour 0,35 ; 179/180 pour 0,70).
- Formules : bornes du demi-lambert, indice de rampe, spéculaire binaire, smoothstep, plan face caméra égal à la couleur la plus claire, fond vide.
- Contour (numpy) : trait exactement aux colonnes 9 et 10 sur un saut de profondeur ; silhouette contre le fond.
- GL :
  - compilation des trois programmes ;
  - ombrage GPU = référence numpy (écart mesuré ≈ 3·10⁻⁶) ;
  - contour GPU = référence sur la tête de test ;
  - chaque terme du Sobel isolé (saut de profondeur ou de normale, vertical ou horizontal) : GPU = référence, et traits exactement aux bonnes lignes ou colonnes.
- Mutations vérifiées : retirer la composante `gy` du Sobel de profondeur, ou celle du Sobel de normales, fait échouer le test isolé correspondant.
- Résultat : 13 tests NPR et 32 tests au total dans le dépôt, tous verts.

## Image de test

`python3 engine/npr/demo_tete.py` produit `out/npr/test_tete_npr.png` (dossier ignoré par git), avec trois réglages sur une tête de banc d'essai :
- A : normales réelles (le relief du nez se lit) ;
- B : normales sphériques (ombrage plat, le nez disparaît) ;
- C : hybride, masque visage et contour.

La tête est une sphère avec une bosse gaussienne, pas un personnage.

## Limites

1. **Pas de géométrie dans le moteur 2D.** Les planches n'ont ni normales ni profondeur. Le module ne sert à une planche qu'avec une profondeur estimée (par exemple Depth-Anything-V2, déjà dans le pipeline) dont on dérive les normales.
2. **Le masque d'ombre ne crée pas d'ombre.** L'ombre sous le nez vient de la normale. Sur la tête de test, elle reste très petite (image C). Pour des planches, l'approche pratique serait un masque peint qui sélectionne directement la bande d'ombre : non fait.
3. **Liseré à la frontière des normales.** Entre normales réelles et sphériques, le spéculaire présente un léger artefact au bord du masque.
4. **Masques en `GL_NEAREST`.** Un masque peint à basse résolution donne des contours en escalier.
5. **Non implémenté :** coque inversée, anisotropie des cheveux (tangentes), transfert de normales Blender, épaisseur de trait qui varie avec la distance (Sobel multi-échelle).
6. **Épaisseur de trait fixe** en texels entiers.
7. **Pas de mesure de performance GPU** : tout tourne sur llvmpipe, CPU.

## Fichiers

- `engine/npr/parametres.py` : paramètres partagés ;
- `engine/npr/rampe.py` : rampes toon ;
- `engine/npr/reference.py` : référence numpy ;
- `engine/npr/rendu.py` : passes OpenGL ;
- `engine/npr/shaders/*.vert|frag` : GLSL 330 ;
- `engine/npr/tete_test.py` : banc d'essai (sphère, bosse, masques UV) ;
- `engine/npr/demo_tete.py` : image de test ;
- `tests/test_npr.py` : tests.

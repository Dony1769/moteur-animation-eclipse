# Rendu animé non photoréaliste (NPR)

Module `engine/npr/` : chaîne OpenGL 3.3 (G-buffer MRT, ombrage toon, reflet anisotrope des cheveux, contour Sobel), chemin 2.5D (calques → relief → G-buffer), calques articulés (squelette 2D, FFD, animation par clés, VBO dynamiques), référence numpy et tests. Ce module ne rend pas encore les planches 2D du projet : il lui faut une géométrie, ou un relief, et ce relief reste une estimation (voir « Limites »).

## Vérification des pièces jointes

### Premier lot (six pièces)

| Pièce | Affirmation | Verdict | Traitement dans le code |
|---|---|---|---|
| Toon ramp (15476050) | Half-Lambert `N·L·0,5+0,5` puis rampe 256×1 en `GL_NEAREST` | Valide | Rampe 256×1, filtre `NEAREST`. La rampe est utilisée en RGB : le `.r` de la pièce « masque visage » est écarté (deux conventions contradictoires). |
| Cel-shading à seuils (2ba4a70b) | `if/else` sur `diff` | Équivalent à la rampe, moins flexible | Non retenu : la rampe couvre le même cas. |
| Coque inversée (2ba4a70b) | Extrusion le long des normales + culling des faces avant | Principe correct, pseudo-code non exécutable, pas de maillage à contourner | Non implémenté. |
| Sobel G-buffer (950751dc) | Sobel sur normales et profondeur, seuils | Principe valide, trois corrections | Gx/Gy inversés dans la pièce (sans effet sur la magnitude). Normales lues sans décodage. Seuil de profondeur absolu : il dépend de la distance. Corrigé : Sobel sur `log(profondeur)`, fond substitué par `profondeur_fond`. |
| Normales sphériques (4959cb8a) | `normalize(FragPos − HeadCenter)` mélangé à la normale réelle | Formule valide, deux erreurs | `HeadCenter` déclaré `in` dans le fragment shader : invalide. Corrigé en uniform en espace vue. Mélange 100 % sphérique : l'ombre du nez disparaît. Corrigé par `masque_sphere` (0 autour du nez). Le « Data Transfer » de Blender n'a pas d'équivalent ici. |
| Masque d'ombre visage (fb41840d) | `mix(1, rampe, masque)` avec décalage `L + avant·0,3` | Valide comme contrôle artistique, mais il ne crée pas d'ombre | Le masque autorise la rampe à agir ; l'ombre vient de la normale. Hors masque = pleine lumière : opt-in (`masque_visage`), sinon tout le corps serait éclairé. Décalage = choix artistique, non une loi physique. |
| Rim light et spéculaire (0998e796) | Fresnel × N·L, seuil lissé ; Blinn-Phong durci par `step` | Valide | `rimSmoothness = 0` rend `smoothstep` indéfini : borné à 1e-4. Reflet des cheveux : faite depuis, voir « Formules ». |

### Second lot (trois pièces : b4414824, 7ed982b8, 284b0bf5)

| Pièce | Affirmation | Verdict | Traitement dans le code |
|---|---|---|---|
| Kit correctif (b4414824) : `GL_CLAMP_TO_EDGE` | Les textures du G-buffer doivent être en CLAMP | Valide | Appliqué à toutes les textures échantillonnées (G-buffer, contour, albédo par défaut). Régression testée : `test_bord_clamp_regression` (mutation REPEAT détectée). |
| Kit correctif (b4414824) : Kajiya-Kay | Le reflet ne dépend que de `T·L` | Faux pour un reflet de cheveux : il ne bouge pas avec la caméra. `tDotV` inutilisé, `pow()` sur une base possiblement négative | Remplacé par la forme sur le demi-vecteur `H` (voir « Formules »). `pow()` remplacé par `th*th`. `tDotV` non repris. |
| Kit correctif (b4414824) : image de référence | Comparaison avec une image cible | Non vérifiable : l'image n'était pas jointe au message | Aucune comparaison faite. |
| Hauteur depuis alpha et luminance (7ed982b8) | Relief en quart de cercle depuis le bord de l'alpha, mélangé à la luminance | Principe utile, relief estimé | Implémenté dans `relief.py` (`Calque`, `relief`). L'intérieur d'un aplat reste plat : ce n'est pas du volume interne, c'est documenté. |
| Pente du sprite (7ed982b8) | Gradient par différence avec le voisin de droite ; flou annoncé | Erreurs : gradient décalé, flou absent | Remplacé par un Sobel centré (`cv2.Sobel`), flou gaussien `flou` (3 px par défaut) avant les pentes. Sans ce flou, le bord du menton présentait des dents (alpha binaire en escalier). |
| MRT du sprite (7ed982b8) | Sorties de profondeur et de tangente | Valide | Intégré au G-buffer : quatre sorties, la tangente en sortie 3. |
| Boucle C++ multi-passes (284b0bf5) | G-buffer, ombrage, Sobel, composition, tri des sprites | Non applicable tel quel : le moteur est en Python/moderngl. Appels invalides : texture passée à `setUniform`, sortie d'éclairage non stockée, pas de tampon de profondeur, pas de tri | Intention reprise en Python : passes de `dessiner_gbuffer`, composition par z-buffer dans `composer` (tri par profondeur). |
| Test de mémoire GPU (284b0bf5) | Vérifier la libération des ressources | Partiel : Python ne mesure pas la mémoire GPU | `test_cycles_creation_liberation` : création et libération répétées sans erreur. Le test ne voit que les erreurs. |

Affirmations non vérifiées et non utilisées : pipelines de Chainsaw Man, Genshin, Guilty Gear, Cygames. La pièce 2ba4a70b cite « Claude 3.5 Haiku » sans rapport avec le sujet.

## Architecture

Deux entrées, une même chaîne. Tout est en espace vue (caméra à l'origine, regard vers −Z, profondeur `d = −z > 0`).

- **Entrée 3D** : `RenduNPR.dessiner(maillage, …)` rend un maillage, puis `lire_gbuffer()`.
- **Entrée 2.5D** : `relief.composer(calques, …)` produit le même G-buffer à partir de calques 2D, puis `RenduNPR.dessiner_gbuffer(gbuf, …)`.
- **Entrée calques articulés** : `RenduNPR.dessiner_calques(calques, pose, …)` recalcule les sommets de chaque calque à la pose, les écrit dans son VBO dynamique, puis dessine dans le même G-buffer (voir « Calques articulés »).

Passes :

1. **Géométrie** (`shaders/geometrie.vert|frag`) : MRT dans un FBO et un tampon de profondeur matériel.
   - sortie 0 : albédo RGBA32F ;
   - sortie 1 : normale vue, **brute**, non encodée (fond = 0) ;
   - sortie 2 : `r` = profondeur linéaire, `g,b` = UV de surface (fond = 0) ;
   - sortie 3 : tangente vue unitaire des mèches (zéro = pas de cheveux). Attribut `in_tangent` du maillage.
2. **Ombrage** (`shaders/ombrage.frag`, plein écran) : lit le G-buffer et applique la rampe, les normales sphériques masquées, le masque visage, le rim, le spéculaire et le reflet des cheveux. Sortie RGBA32F.
3. **Contour** (`shaders/contour.frag`, plein écran) : Sobel 3×3 sur les normales (`|Gx|+|Gy|` en longueur vectorielle) et sur `log(profondeur)`. Trait noir si l'un des deux seuils est dépassé. Sortie RGBA8.

Les masques sont peints en **UV de surface** (lus via `g,b`), jamais en coordonnées d'écran : ils suivent la tête quand elle tourne. Dans le chemin 2.5D, il n'y a pas d'UV de surface : l'UV est la position normalisée du pixel à l'écran, et le masque de cheveux du calque est dans ce même repère.

Toutes les textures d'échantillonnage sont en `GL_NEAREST` et `GL_CLAMP_TO_EDGE`. Le Sobel lit au-delà du bord ; avec le mode `REPEAT` par défaut, le bord gauche recevait la valeur du bord droit (bug trouvé par les tests GPU/numpy et corrigé).

### Chemin 2.5D (`engine/npr/relief.py`)

- `Calque` : RGBA en ordre image, plan de base, `relief_max`, `rayon_biseau`, `pente`, `poids_luminance`, `flou`, et en option `flux` (direction des mèches) et `masque_cheveux`.
- `relief(calque)` : hauteur 0..1 en quart de cercle depuis le bord de l'alpha, mélangée à la luminance si `poids_luminance > 0`, puis floutée.
- `normales(h, pente)` : pentes par Sobel sur la hauteur.
- `composer(calques, largeur, hauteur)` : z-buffer CPU ; le calque le plus proche gagne, les pixels sans calque opaque sont du fond. Renvoie le G-buffer en ordre OpenGL (ligne 0 en bas).

### Calques articulés (`engine/npr/rig.py`, `engine/npr/calques_anim.py`)

Un calque (`relief.Calque`) est découpé en grille de sommets au repos par `calques_anim.construire` (cellules de 4 px par défaut ; seules les cellules touchant un pixel opaque sont gardées). À chaque pose, dans cet ordre :

1. la grille FFD (`rig.GrilleFFD`) déforme les positions au repos (clignement, piste `cligne`) ;
2. le squelette (`rig.Squelette`, os rigides 2D) déforme positions, normales et tangentes (skinning linéaire) ;
3. chaque sommet garde la profondeur de son relief au repos et passe en coordonnées vue (`calques_anim.vers_vue`, même convention que l'ombrage).

Les sommets sont écrits dans un VBO dynamique par calque (`Maillage.mettre_a_jour`). `RenduNPR.dessiner_calques` trie les calques par profondeur moyenne (`trier_par_profondeur`), les dessine dans le G-buffer, et le z-buffer tranche pixel par pixel. La découpe se fait dans le shader de géométrie (`seuilAlpha` : un fragment dont l'alpha de texture est sous le seuil est retiré).

Chaque calque n'est influencé que par ses `os_actifs` : un corps ne suit que son propre os, sans quoi ses bords se courbent quand la tête bouge (bug trouvé à la démo, corrigé et testé).

Animation : `rig.Piste` (clés `(temps, valeur)`, interpolation `lineaire` ou `cubique`) et `rig.Timeline` (pistes nommées, `pose(t)`).

## Formules retenues

- Demi-lambert : `u = N·L · 0,5 + 0,5`, couleur = `rampe[floor(u·256)]`.
- Normale sphérique masquée : `N = normalize(mix(N_réelle, normalize(P − C_tête), w))`, avec `w = masque_sphere(UV) · poids_sphere`.
- Masque d'ombre visage (si `masque_visage`) : `u = mix(1, demi_lambert(N, normalize(L + avant·0,3)), masque_ombre(UV))`.
- Rim : `f = 1 − max(N·V, 0)`, `r = f · max(N·L, 0)`, `rim = smoothstep(seuil − s, seuil + s, r)` avec `s = max(douceur, 1e-4)`.
- Spéculaire durci : `step(seuil, max(N·H, 0))`, `H = normalize(L + V)`.
- Reflet des cheveux (Kajiya-Kay sur le demi-vecteur) :
  - `T' = normalize(T + N·hairShift)` (décalage le long de la normale : déplace la bande de reflet le long de la mèche) ;
  - `sinTH = sqrt(max(0, 1 − (T'·H)²))` ;
  - `reflet = step(hairThreshold, sinTH) · masque_cheveux(UV) · hairColor`, seulement si `masque_cheveux > 0` et `|T| > 0,5`.
  - Le reflet bouge avec la caméra par `V` (via `H`). Un seuil élevé (0,97 à 0,997) le réduit à une bande fine.
- Relief (2.5D) :
  - `h_alpha = sqrt(1 − (1 − t)²)` avec `t = min(d / rayon_biseau, 1)`, `d` = distance au bord de l'alpha (masque alpha ≥ 0,1) ;
  - `h = (1 − w)·h_alpha + w·lum·masque` (`w = poids_luminance`), puis flou gaussien `flou` ;
  - `n = normalize(−pente·∂h/∂x, +pente·∂h/∂y_image, 1)`, avec `h` en pixels (`h · rayon_biseau`), car les pentes sont en pixels ;
  - profondeur `d = plan − relief_max · h`.
- Tangente depuis le flux : `T = normalize(dx, −dy_image, 0)`.
- Contour : `edN = |Gx_N| + |Gy_N| > seuil_normale` ou `edD = |Gx_log| + |Gy_log| > seuil_profondeur`. Fond : couleur de fond, sans trait.

### Formules du rig

- Squelette : `G_os(pose) = G_parent · T(pivot) · R(θ) · T(−pivot)`, avec `G_os(repos) = I`.
- Skinning : `p' = Σ_k w_k · G_k · p`. Normales et tangentes ne reçoivent que la partie rotation : `n' = normalize(Σ_k w_k · R_k · n)`, z inchangé. Le calcul se fait dans le repère image (y vers le bas) : un angle positif tourne dans le sens horaire à l'écran.
- Poids : `w_k ∝ exp(−d_k² / (2 σ_k²))`, où `d_k` est la distance au segment de l'os (pivot → extrémité), calculé en softmax (jamais de ligne nulle), restreint aux `os_actifs` du calque.
- FFD (Sederberg-Parry, base de Bernstein) : `p' = p + Σ_ij B_i(s) · B_j(t) · d_ij`. Un champ de décalage linéaire est reproduit exactement.
- Clignement : `d_y = −c · (y − y_milieu)`, donc `p'_y = (1 − c) · y + c · y_milieu`, x inchangé.
- Piste cubique : interpolation de Hermite entre clés, tangentes de Catmull-Rom non uniformes (`(v_{k+1} − v_{k−1}) / (t_{k+1} − t_{k−1})`), bords en différence simple. La courbe passe par chaque clé et sa dérivée est continue.

## Dépendances et environnement

- Python 3.13, numpy 2.5.3, OpenCV 5.0.0 (headless), moderngl 5.13.0, pytest 9.1.1. Versions dans `requirements.txt`.
- Installation : `pip install --break-system-packages -r requirements.txt`.
- OpenGL : contexte headless EGL, Mesa llvmpipe 25.2.8 (OpenGL 4.5 core). Il n'y a pas de GPU (`/dev/dri` absent) : les rendus sont logiciels, donc lents, mais exacts pour la validation.
- Pas de `glslangValidator` : la validation des shaders est leur compilation par Mesa, lancée par `RenduNPR`.
- Une uniform que le GLSL n'utilise pas est éliminée à la compilation. Toute uniform passée depuis `rendu.py` doit donc être lue par son shader, sinon `KeyError`.
- Sans libEGL ou sans contexte, les tests GL sont ignorés ; les tests numpy tournent toujours.

## Tests (`tests/test_npr.py`, `tests/test_rig.py`)

- Rampe : bandes exactes (texels 89/90 pour 0,35 ; 179/180 pour 0,70).
- Formules : bornes du demi-lambert, indice de rampe, spéculaire binaire, smoothstep, plan face caméra égal à la couleur la plus claire, fond vide.
- Cheveux (numpy) : reflet quand la tangente est perpendiculaire au demi-vecteur ; pas de reflet quand elle lui est parallèle ; pas de reflet sans masque ni tangente.
- Relief et composition (numpy) : normales sortantes sur les quatre flancs du biseau ; ordre OpenGL et fond ; un calque avant gagne dans le recouvrement ; alpha sous le seuil = fond ; convention du flux.
- Contour (numpy) : trait exactement aux colonnes 9 et 10 sur un saut de profondeur ; silhouette contre le fond.
- GL :
  - ombrage GPU = référence numpy (écart ≈ 3·10⁻⁶) ;
  - contour GPU = référence sur la tête de test ;
  - chaque terme du Sobel isolé (saut de profondeur ou de normale, vertical ou horizontal) : GPU = référence, et traits exactement aux bonnes lignes ou colonnes ;
  - bord CLAMP : un saut au bord droit ne crée pas de trait au bord gauche ;
  - reflet des cheveux GPU = référence, et le reflet est bien présent ;
  - chemin 2.5D GPU = référence sur le même G-buffer ;
  - création et libération répétées de `RenduNPR` : aucune erreur. Python ne mesure pas la mémoire GPU : le test ne détecte que les erreurs visibles.
- Mutations vérifiées (sur des copies, pas sur l'arbre de travail) :
  - retirer la composante `gy` du Sobel de profondeur, ou celle du Sobel de normales : le test isolé correspondant échoue ;
  - remplacer CLAMP par REPEAT : `test_bord_clamp_regression` échoue ;
  - remplacer `th*th` par `th` dans le GLSL des cheveux : `test_cheveux_gpu_egal_reference` échoue.
- Rig et calques (`tests/test_rig.py`), numpy :
  - squelette : repos = identité, rotation autour du pivot (distance et angle conservés), enfant qui suit le parent, normales qui gardent leur norme ;
  - poids : sommes à 1, os le plus proche dominant, pas de ligne nulle loin des os, masque `os_actifs` (et refus d'un nom inconnu) ;
  - FFD : identité, translation uniforme exacte, clignement linéaire exact, fermeture complète sur la médiane ;
  - pistes : passage par les clés (linéaire et cubique), droite reproduite par la cubique, continuité de la dérivée, clamp hors plage, erreurs de saisie ;
  - calques : convention `vers_vue`, profondeur du plateau = plan − relief, normales qui tournent avec l'os, FFD sur les yeux seulement, tri par profondeur et départage par ordre, corps qui ne suit que son os (régression), pose neutre inchangée.
- Rig et calques, GPU (même fichier) :
  - VBO réécrit puis relu sur le GPU ; forme incorrecte refusée ;
  - profondeur du chemin articulé = `relief.composer` au plateau (écart < 10⁻⁴) ;
  - couverture GPU = alpha (désaccord < 2 %) ;
  - rotation GPU d'un calque = `cv2.warpAffine` de son alpha (IoU > 0,9) ;
  - ordre de dessin inversé : même G-buffer (le z-buffer tranche), et le premier plan gagne au recouvrement ;
  - tangente nulle hors cheveux, sans NaN ;
  - création, mise à jour et libération répétées des calques.
- Mutations vérifiées sur copies (sans toucher l'arbre de travail) : découpe alpha retirée (6 échecs), garde de tangente retirée (`test_tangente_nulle_hors_cheveux` échoue), test de profondeur désactivé (test d'ordre inverse échoue), rotation du squelette inversée (5 échecs).
- Résultat : 25 tests NPR (dont 7 GL), 46 tests rig et calques (dont 8 GL), 90 tests au total dans le dépôt, tous verts.

## Images de test

- `python3 engine/npr/demo_tete.py` produit `out/npr/test_tete_npr.png` (dossier ignoré par git), avec quatre panneaux sur une tête de banc d'essai :
  - A : normales réelles (le relief du nez se lit) ;
  - B : normales sphériques (ombrage plat, le nez disparaît) ;
  - C : hybride, masque visage et contour ;
  - D : comme C, plus la calotte de cheveux.
  - Écarts GPU/numpy : A ≈ 2·10⁻⁶, B, C et D ≈ 3·10⁻⁶.
  - Sur D, la calotte n'occupe qu'une bande fine en haut de la sphère, vue de biais : le reflet y est discret. Non ajusté (`CALOTTE_V` dans `tete_test.py`).
- `python3 engine/npr/demo_calque.py` produit `out/npr/test_calque_npr.png` : deux calques procéduraux (visage, puis cheveux devant), A sans reflet, B avec le reflet anisotrope des mèches (flux radial depuis le haut du crâne).
- `python3 engine/npr/demo_articule.py` produit `out/npr/test_articule_npr.png` : une planche de six instants (0 ; 0,25 ; 0,46 ; 0,5 ; 0,75 ; 1 s) d'un personnage à cinq calques (cheveux arrière, corps, visage, yeux, frange). Pistes : `tete` (inclinaison, cubique), `cligne` (linéaire, fermeture à 0,9), `meche` (balancement, cubique). Vérifiée à l'œil sur la planche : le corps reste rigide, la paupière se ferme en trait fin, la frange et les cheveux suivent la tête, la mèche se balance (jusqu'à environ 36 px en bout pour 0,25 rad). Démo complète : environ 0,6 s sur llvmpipe, contexte compris.

La tête est une sphère avec une bosse gaussienne, et les calques sont des formes dessinées en code : ni l'une ni l'autre n'est un personnage du projet.

## Limites

1. **Pas de géométrie dans le moteur 2D.** Les planches n'ont ni normales ni profondeur. Le module ne sert à une planche qu'avec une profondeur estimée (par exemple Depth-Anything-V2, déjà dans le pipeline) dont on dérive les normales.
2. **Le relief 2.5D est une estimation artistique.** Le volume n'apparaît qu'au bord de chaque aplat (biseau). L'intérieur reste plat ; le volume interne demande une profondeur estimée, hors de ce module.
3. **Le masque d'ombre ne crée pas d'ombre.** L'ombre sous le nez vient de la normale. Sur la tête de test, elle reste très petite (panneau C). Pour des planches, l'approche pratique serait un masque peint qui sélectionne directement la bande d'ombre : non fait.
4. **Liseré à la frontière des normales.** Entre normales réelles et sphériques, le spéculaire présente un léger artefact au bord du masque.
5. **Masques en `GL_NEAREST`.** Un masque peint à basse résolution donne des contours en escalier.
6. **Non implémenté :** coque inversée, transfert de normales Blender, épaisseur de trait qui varie avec la distance (Sobel multi-échelle).
7. **Cheveux dessinés à la main.** Les mèches (`flux`) et le masque de cheveux sont fixés dans la démo. Aucune détection de cheveux sur une image réelle.
8. **Composition des calques en CPU.** `composer` est un z-buffer Python, sans tri GPU : acceptable pour quelques calques, à revoir pour une scène chargée.
9. **Épaisseur de trait fixe** en texels entiers.
10. **Pas de mesure de performance GPU** : tout tourne sur llvmpipe, CPU.
11. **Image de référence de b4414824 non jointe** : aucune comparaison faite.
12. **Articulation 2D seulement.** Les os sont rigides dans le plan de l'image : « tourner la tête » est une inclinaison dans le plan (roulis), pas un lacet 3D. Une vraie rotation du visage demande une géométrie 3D.
13. **Clignement linéaire.** La paupière est un écrasement vertical de la grille, sans forme courbe. À une fermeture de 1,0, les triangles s'écrasent en segments dégénérés et laissent des points parasites : la démo plafonne à 0,9.
14. **FFD sans recalcul des normales.** La grille FFD déplace les positions, mais normales et tangentes ne suivent que le squelette.
15. **Relief figé au repos.** La profondeur d'un sommet vient du relief au repos : une déformation ne recalcule pas le biseau. Les sommets sont échantillonnés au pixel le plus proche (cellules de 4 px).
16. **Ordre de dessin et transparence.** Le tri par profondeur est fait sur le CPU ; le z-buffer assure la correction pixel par pixel. Il n'y a pas de transparence semi-translucide (découpe seulement, sans alpha blending).
17. **Démo procédurale.** Les formes sont dessinées en code. Ce ne sont ni un personnage du projet ni un masque de cheveux peint.
18. **Images, pas de vidéo.** La démo produit une planche de six instants ; aucun MP4 n'est rendu en continu. Le chemin 2.5D statique (`relief.composer`, limite 8) reste en CPU ; le chemin articulé est sur GPU.

## Fichiers

- `engine/npr/parametres.py` : paramètres partagés (ombrage, cheveux, contour) ;
- `engine/npr/rampe.py` : rampes toon ;
- `engine/npr/reference.py` : référence numpy ;
- `engine/npr/rig.py` : squelette 2D, poids, grille FFD, pistes et timeline (numpy pur) ;
- `engine/npr/calques_anim.py` : calques articulés, sommets à la pose, tri par profondeur ;
- `engine/npr/demo_articule.py` : personnage à cinq calques et planche d'instants ;
- `engine/npr/rendu.py` : passes OpenGL (`RenduNPR` : `dessiner`, `dessiner_gbuffer`, `contour_sur`) ;
- `engine/npr/relief.py` : calques 2.5D, relief, normales, composition ;
- `engine/npr/shaders/*.vert|frag` : GLSL 330 ;
- `engine/npr/tete_test.py` : banc d'essai (sphère, bosse, masques UV, calotte) ;
- `engine/npr/demo_tete.py`, `engine/npr/demo_calque.py` : images de test ;
- `tests/test_npr.py` : tests.

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
2. le squelette (`rig.Squelette`, os rigides 2D) déforme les positions (skinning linéaire) ;
3. normales et tangentes sont poussées par la jacobienne de la déformation totale (section suivante) ;
4. chaque sommet garde la profondeur de son relief au repos et passe en coordonnées vue (`calques_anim.vers_vue`, même convention que l'ombrage).

Les sommets sont écrits dans un VBO dynamique par calque (`Maillage.mettre_a_jour`). `RenduNPR.dessiner_calques` trie les calques par profondeur moyenne (`trier_par_profondeur`), les dessine dans le G-buffer, et le z-buffer tranche pixel par pixel. La découpe se fait dans le shader de géométrie (`seuilAlpha` : un fragment dont l'alpha de texture est sous le seuil est retiré).

Chaque calque n'est influencé que par ses `os_actifs` : un corps ne suit que son propre os, sans quoi ses bords se courbent quand la tête bouge (bug trouvé à la démo, corrigé et testé).

Animation : `rig.Piste` (clés `(temps, valeur)`, interpolation `lineaire` ou `cubique`) et `rig.Timeline` (pistes nommées, `pose(t)`).

### Normales sous déformation (`engine/npr/calques_anim.py`)

Les normales ne sont plus tournées os par os. À chaque pose, elles sont recalculées à partir de la jacobienne `J` de la déformation totale (FFD puis squelette) :

- `jacobiennes` : pour chaque triangle (topologie fixe), `J_t = [b1−b0, b2−b0] · [a1−a0, a2−a0]⁻¹`, où `a` sont les positions au repos et `b` les positions déformées. `J` est la moyenne par sommet des triangles voisins, pondérée par l'aire au repos. Un triangle dégénéré au repos ne compte pas.
- `pousser_normales` : la hauteur implicite a pour gradient `g = (−n_x/n_z, n_y/n_z)` dans le repère image. Sous la déformation, `g' = J⁻ᵀ g` (règle de la chaîne inverse), et `n' ∝ (−g'_x, g'_y, 1)` en repère vue. La tangente (flux) suit `t' = J t`.
- Rotation rigide : `J = R`, donc `g' = R g` et la normale tourne comme avant. Au repos, `J = I`.
- Jacobienne dégénérée (déterminant ≤ 10⁻⁶) : la normale reste inchangée.
- Sans déformation, les normales du repos sont renvoyées telles quelles, sans calcul.

La profondeur des sommets reste celle du relief au repos (limite 15).

### Calques réels et atlas (`engine/npr/chargeur.py`)

Le chargeur lit le format `moteur-3.0/personnage-couches/2` : un JSON par vue, avec l'illustration de référence, le squelette à points-clés et les couches (polygones, ordre, chaîne d'os).

- Masque d'une couche = polygone ∩ premier plan. Le fond est un pixel dont les trois canaux sont tous ≥ 245. Les couleurs viennent de la référence.
- Atlas : une seule texture de 1024 px de large, sprites rangés par rangées, marge transparente de 2 px. Chaque couche a un rectangle dans l'atlas et une correspondance image → UV : `u = (x_atlas + (x − x0)) / L_atlas`. Avec `GL_NEAREST`, l'échantillonnage redonne le pixel source exactement.
- Une seule texture GPU pour tous les calques d'un atlas (`RenduNPR._texture_du_calque`), uploadée une fois.
- Données de Kaël : face (8 couches) et trois quarts (7 couches), 41 points-clés. Les couches sont tête, tunique, cape, bras, jambes et col. Les cheveux arrière, la frange, les yeux et le visage séparé ne sont pas dans les données : ils ne sont donc pas chargés.

### Cheveux : Verlet sur la grille FFD (`engine/npr/physique.py`)

- Une grille FFD de cheveux : la rangée du haut est épinglée au crâne, les autres points sont libres, reliés à leurs voisins horizontaux et verticaux à leur longueur au repos.
- La simulation se fait dans le repère de la tête, avant skinning, car le FFD s'applique avant le squelette. La racine reste donc fixe dans ce repère et le mouvement de la tête entre comme forces d'inertie : `a_local = Rᵀ(g − a_pivot) − α ẑ×r + ω² r − 2ω ẑ×v`, avec `r` la position relative au pivot, `ω` et `α` la vitesse et l'accélération angulaires de la chaîne d'os, `v` la vitesse locale.
- Intégration de Verlet à pas fixe (`dt = 1/240 s`) : `x_{n+1} = x_n + d·(x_n − x_{n−1}) + a·dt²`, avec `d = amortissement^(60·dt)` et `amortissement = 0,98` par image à 60 Hz.
- Gravité : `g = (0, +540)` px/s², y vers le bas dans l'image. C'est l'équivalent de 0,15 px/image² à 60 Hz du document de conception, dont la formule était absente du texte fourni.
- Contraintes de longueur corrigées en proportion des masses inverses : `Δ_i = w_i/(w_i + w_j) · corr`. Le document de conception n'appliquait que la moitié de la correction, ce qui laisse une racine épinglée glisser. C'est corrigé et testé.
- Les décalages `x − repos` vont dans `GrilleFFD.decalages` ; le FFD déforme alors les calques de cheveux.

### Vues multiples (`engine/npr/multivue.py`)

- `poids_vues(angle, {0: "face", 45: "trois_quarts"})` : fondu linéaire entre les deux vues réelles qui encadrent l'angle, avec des poids positifs de somme 1.
- Au-delà de la dernière vue réelle, la vue la plus proche est reprise sans fondu, et `hors_plage` vaut `True`. Un profil demandé ne produit donc rien d'inventé.
- `fondre` mélange les images (CPU). `bascule` prend la vue de poids maximal, sans fondu.
- Un fondu est un doublement de contours à mi-chemin, pas une rotation : les vues ne sont pas recalées entre elles.

### Démo personnage (`engine/npr/demo_personnage.py`)

Calques réels de Kaël, atlas, squelette de deux os (corps : bassin → cou ; tête : cou → sommet du crâne). Rendu de la face avec la tête inclinée, puis fondu face / trois quarts.

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
- Skinning : `p' = Σ_k w_k · G_k · p`. Les normales ne sont pas tournées os par os : elles suivent la jacobienne de la déformation totale (section « Normales sous déformation »). Le calcul se fait dans le repère image (y vers le bas) : un angle positif tourne dans le sens horaire à l'écran.
- Poids : `w_k ∝ exp(−d_k² / (2 σ_k²))`, où `d_k` est la distance au segment de l'os (pivot → extrémité), calculé en softmax (jamais de ligne nulle), restreint aux `os_actifs` du calque.
- FFD (Sederberg-Parry, base de Bernstein) : `p' = p + Σ_ij B_i(s) · B_j(t) · d_ij`. Un champ de décalage linéaire est reproduit exactement.
- Clignement : `d_y = −c · (y − y_milieu)`, donc `p'_y = (1 − c) · y + c · y_milieu`, x inchangé.
- Piste cubique : interpolation de Hermite entre clés, tangentes de Catmull-Rom non uniformes (`(v_{k+1} − v_{k−1}) / (t_{k+1} − t_{k−1})`), bords en différence simple. La courbe passe par chaque clé et sa dérivée est continue.

### Formules des nouveaux modules

- Jacobienne d'un triangle : `J_t = [b1−b0, b2−b0] · [a1−a0, a2−a0]⁻¹`, moyennée par sommet et pondérée par l'aire au repos.
- Normale poussée : `g = (−n_x/n_z, n_y/n_z)`, `g' = J⁻ᵀ g`, `n' ∝ (−g'_x, g'_y, 1)` ; tangente `t' = J t`.
- Verlet : `x_{n+1} = x_n + d·(x_n − x_{n−1}) + a·dt²`, `d = amortissement^(60·dt)`.
- Forces apparentes dans le repère de la tête : Euler `−α ẑ×r`, centrifuge `ω² r`, Coriolis `−2ω ẑ×v`, entraînement `Rᵀ(g − a_pivot)`.
- Correction de contrainte : `Δ_i = w_i/(w_i + w_j) · (d − L)·(x_j − x_i)/d`, `Δ_j = −w_j/(w_i + w_j) · (d − L)·(x_j − x_i)/d`, avec `w = 1/masse`.
- Marge FFD : décalage pondéré par `(1 − smoothstep(d/marge))` par axe, produit des deux axes, `d` = distance à la boîte.
- Fondu : `I = (1 − s)·I_a + s·I_b`, `s = (angle − a_0)/(a_1 − a_0)`.

## Dépendances et environnement

- Python 3.13, numpy 2.5.3, OpenCV 5.0.0 (headless), moderngl 5.13.0, pytest 9.1.1. Versions dans `requirements.txt`.
- Installation : `pip install --break-system-packages -r requirements.txt`.
- OpenGL : contexte headless EGL, Mesa llvmpipe 25.2.8 (OpenGL 4.5 core). Il n'y a pas de GPU (`/dev/dri` absent) : les rendus sont logiciels, donc lents, mais exacts pour la validation.
- Pas de `glslangValidator` : la validation des shaders est leur compilation par Mesa, lancée par `RenduNPR`.
- Une uniform que le GLSL n'utilise pas est éliminée à la compilation. Toute uniform passée depuis `rendu.py` doit donc être lue par son shader, sinon `KeyError`.
- Sans libEGL ou sans contexte, les tests GL sont ignorés ; les tests numpy tournent toujours.

## Tests (`tests/test_npr.py`, `tests/test_rig.py`, `tests/test_personnage_reel.py`)

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
- Personnage réel, numpy (`tests/test_personnage_reel.py`) :
  - chargeur : couches et ordre de Kaël, masque exclu du fond, boîtes dans la vue, points-clés présents, format inconnu, couche hors personnage, `poly` et `polys` ensemble : refus explicites ;
  - atlas : rectangles disjoints et dans la texture ; pour 200 points par couche, la couleur de l'atlas à l'UV égale le pixel de la référence ; l'alpha de l'atlas égale le masque ;
  - normales : jacobienne identité, mise à l'échelle, triangle dégénéré ; pente linéaire étirée donne `(−a/s, 0, 1)` ; normale égale à la dérivée numérique de `H' = h∘F⁻¹` (différences finies, sans formule de pousse) ; rotation rigide ; tangente poussée ; jacobienne singulière : repli sur la normale ; clignement FFD : normales des paupières changent, restent unitaires et face caméra ;
  - forces apparentes : centrifuge, Euler (signe), Coriolis ;
  - physique : racine épinglée immobile ; longueurs conservées à 1 % près ; pas de glissement sans mouvement de tête ; inertie : retard de la rangée basse en +x quand la tête accélère (α > 0) ; pivot porté par un parent : accélération `ω²·r` ; décalages alimentant la FFD ; retour arrière refusé ; paramètres invalides refusés ;
  - FFD locale : la marge arrête la déformation hors de la boîte, et la décroissance est douce ;
  - vues multiples : fondu, bornes, profil hors plage signalé, somme des poids à 1, `fondre` et `bascule`, poids non normalisés refusés ;
  - GPU (1 test) : tous les calques d'un atlas partagent une seule texture, libérée proprement.
- Mutations vérifiées sur copies (sans toucher l'arbre de travail) :
  - normales non poussées : 2 échecs (`test_normales_tournent_avec_l_os`, `test_ffd_clignement_change_les_normales_des_yeux`) ;
  - correction de contrainte à moitié (le défaut du document de conception) : `test_racine_epinglee_reste_au_repos` échoue ;
  - signe d'Euler inversé : 2 échecs (`test_euler_signe`, `test_inertie_tete_decalage_oppose_au_mouvement`) ;
  - marge FFD retirée : d'abord non détectée, puis 2 échecs après ajout des tests de marge ;
  - atlas décalé d'un texel : `test_echantillon_atlas_egal_au_sprite` échoue.
- Résultat : 25 tests NPR (dont 7 GL), 46 tests rig et calques (dont 8 GL), 42 tests du personnage réel (dont 1 GL), 132 tests au total dans le dépôt, tous verts.

## Images de test

- `python3 engine/npr/demo_tete.py` produit `out/npr/test_tete_npr.png` (dossier ignoré par git), avec quatre panneaux sur une tête de banc d'essai :
  - A : normales réelles (le relief du nez se lit) ;
  - B : normales sphériques (ombrage plat, le nez disparaît) ;
  - C : hybride, masque visage et contour ;
  - D : comme C, plus la calotte de cheveux.
  - Écarts GPU/numpy : A ≈ 2·10⁻⁶, B, C et D ≈ 3·10⁻⁶.
  - Sur D, la calotte n'occupe qu'une bande fine en haut de la sphère, vue de biais : le reflet y est discret. Non ajusté (`CALOTTE_V` dans `tete_test.py`).
- `python3 engine/npr/demo_calque.py` produit `out/npr/test_calque_npr.png` : deux calques procéduraux (visage, puis cheveux devant), A sans reflet, B avec le reflet anisotrope des mèches (flux radial depuis le haut du crâne).
- `python3 engine/npr/demo_articule.py` produit `out/npr/test_articule_npr.png` : une planche de six instants (0 ; 0,25 ; 0,46 ; 0,5 ; 0,75 ; 1 s) d'un personnage à cinq calques (cheveux arrière, corps, visage, yeux, frange). Pistes : `tete` (inclinaison, cubique), `cligne` (linéaire, fermeture à 0,9), `meche` (balancement, cubique). Vérifiée à l'œil sur la planche : le corps reste rigide, la paupière se ferme en trait fin, la frange et les cheveux suivent la tête avec un retard (Verlet), la mèche se balance (jusqu'à environ 36 px en bout pour 0,25 rad). La chevelure arrière et la frange ont désormais une grille FFD simulée par Verlet (`ChevelureSimulee`, racine épinglée au crâne) : elles suivent la tête avec un léger retard, à vérifier sur une séquence animée (la planche ne montre que six instants). Sur la planche, la paupière se ferme à 0,46 s. Le temps de rendu n'a pas été remesuré depuis l'ajout de la physique.
- `python3 engine/npr/demo_personnage.py` produit `out/npr/test_personnage_kael.png` : personnage réel de Kaël, couches découpées et atlas. Rangée haute : face, tête inclinée de −0,12 ; 0 ; +0,12 rad. Rangée basse : fondu entre face et trois quarts à 0°, 22,5° et 45°. Vue à l'œil : les textures sont celles de la référence, la tête tourne autour du cou. Le fondu à 22,5° montre les contours doublés attendu. Le profil n'existe pas dans les données et n'est pas rendu. Les contours noirs sont épais : c'est le réglage par défaut du contour, non ajusté.

La tête de test est une sphère avec une bosse gaussienne, et les calques de `demo_articule` sont des formes dessinées en code : ni l'une ni l'autre n'est un personnage du projet. `demo_personnage` est la seule démo qui utilise des calques réels.

## Encre fine, bascule nette, rampes teintées, découpe par matériaux (2 novembre 2026)
- Encre : `engine/npr/encre.py` remplace le Sobel épais de la passe contour. La silhouette est la frontière intérieure continue du masque de profondeur, large de 1 px sur la face éclairée, 2 px au milieu, 3 px sur la face ombrée (luminance). Les arêtes internes passent par Sobel sur normales et log-profondeur, suppression des non-maxima, hystérésis et retrait des composantes courtes. Raison : un trait épais et une silhouette percée (points noirs) rendaient le dessin brouillon. Tests : `tests/test_encre.py` (10, CPU).
- Multi-vues : `multivue.vue_nette` bascule nettement sur la vue réelle la plus proche, au point médian entre deux angles ; `appliquer_transition` ajoute un cisaillement FFD qui est nul aux bornes. Le fondu (`poids_vues`, `fondre`) reste dans le module, pour comparaison seulement. Tests : `TestBasculeNette` (8).
- Rampes : `rampe_chaude` (peau) et `rampe_froide` (vêtements sombres). Le masque `masqueMateriau`, sur l'atlas, choisit la rampe par pixel dans `ombrage.frag`. Tests : `TestRampesTeintees` (3), dont un test GPU qui compare la dominante bleue des zones froides et chaudes.
- Découpe par matériaux (`decoupe_materiaux.py`) : k-moyennes sur les couleurs RGB, filtre médian des étiquettes, nom de matériau par heuristique de couleur. La carte de couches est une partition : chaque pixel du personnage appartient à exactement une couche (les trous créés par l'ouverture morphologique sont rendus au voisin le plus proche). Les reflets clairs enfermés dans la silhouette sont remplis s'ils font moins de 1 % de la boîte ; une grande zone claire enfermée (l'espace entre bras et torse) reste du fond. Tests : `tests/test_decoupe_materiaux.py` (13).
- Démo de référence (`demo_reference.py`) : planche à partir de l'illustration jointe, avec trois inclinaisons de tête. Le spéculaire dur est désactivé dans cette démo seulement (`spec_seuil=1.5`), car il produisait des traits blancs sur les vêtements sombres.

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
14. **Jacobienne moyennée par triangle.** Les normales sont poussées par la jacobienne moyenne des triangles voisins de chaque sommet. C'est exact pour une déformation affine par morceaux, approché là où la déformation est très courbe. Les tangentes suivent la même jacobienne.
15. **Relief figé au repos.** La profondeur d'un sommet vient du relief au repos : une déformation ne recalcule pas le biseau. Les sommets sont échantillonnés au pixel le plus proche (cellules de 4 px).
16. **Ordre de dessin et transparence.** Le tri par profondeur est fait sur le CPU ; le z-buffer assure la correction pixel par pixel. Il n'y a pas de transparence semi-translucide (découpe seulement, sans alpha blending).
17. **Démo procédurale.** `demo_articule` dessine ses formes en code : ce n'est ni un personnage du projet ni un masque de cheveux peint. Le personnage réel est dans `demo_personnage` (limites 19 à 26).
18. **Images, pas de vidéo.** La démo produit une planche de six instants ; aucun MP4 n'est rendu en continu. Le chemin 2.5D statique (`relief.composer`, limite 8) reste en CPU ; le chemin articulé est sur GPU.

19. **Pas de yeux, cheveux ni frange séparés dans les données de Kaël.** Les couches sont tête, tunique, cape, bras, jambes et col. Le clignement et la physique des cheveux ne sont donc appliqués qu'à la démo procédurale, pas au personnage réel.
20. **Pas de vue de profil.** Seules la face et le trois quarts existent. Au-delà de 45°, `poids_vues` signale `hors_plage` et l'image ne rend rien d'inventé.
21. **Fondu, pas rotation.** Entre la face et le trois quarts, les contours se doublent à mi-chemin : les vues ne sont pas recalées entre elles.
22. **Masques par polygones.** Les polygones débordent parfois (note du fichier de données). Le fond est exclu par seuil de couleur, pas par segmentation : un fond non blanc resterait dans le masque.
23. **Squelette à deux os.** Le personnage réel est tourné par deux os (corps, tête) déduits des points-clés. Bras et jambes ne suivent aucun os.
24. **Chevelure sans flexion ni collision.** Les liens sont structurels seulement (horizontaux et verticaux) : pas de rigidité de flexion, pas de collision avec le crâne ou le visage. La physique reste en deux dimensions.
25. **Relief figé au repos (limite 15).** Le relief et la profondeur des sommets ne sont pas recalculés par la déformation ; seules les normales le sont.
26. **Contour non réglé sur les calques réels.** Le trait noir est épais sur le personnage réel : c'est le réglage par défaut, pas une valeur choisie pour ce dessin.

27. **Référence = autre personnage.** L'illustration de référence n'est pas Kaël. Ses calques sont des groupes de couleur, pas des parties du corps : cheveux avant et arrière fusionnés, veste et pantalon sombres peuvent se mélanger. Les points-clés (cou, sommet du crâne, bassin) sont placés à l'œil, sans détection.
28. **Mouvement de tête très faible dans la démo de référence.** L'inclinaison de ±0,12 rad est à peine visible sur la planche.
29. **Spéculaire dur.** Le spéculaire reste un `step` sur N·H : il est coupé sous un albédo de luminance 0,35 (`spec_lum_min`), donc sur les tissus sombres, mais un reflet clair peut toujours s'allumer d'une image à l'autre.
30. **Relief : profondeur seulement.** `relief_max` règle la profondeur des sommets, pas les normales : l'éclairage du relief se règle par `pente` et `rayon_biseau`. Le couplage a été écarté, car il changerait le rendu de Kaël (relief 0,10) et de la référence (0,04) sans calibrage.
31. **Encre fragmentaire à l'intérieur.** Seule la silhouette est continue ; les arêtes internes restent interrompues sur les surfaces courbes.
32. **Scintillement non résolu.** Sur un balayage monotone de 25 images (`engine/npr/sequence_kael.py`), 5,2 % des pixels sombres de Kaël scintillent avec l'encre, contre 3,4 % avec le Sobel d'origine. Le scintillement vient des frontières entre calques qui se chevauchent et bougent l'un par rapport à l'autre (mèche bleue sur la joue), pas des traits d'encre : sans arêtes internes, sans spéculaire et sans rim light, le chiffre ne baisse pas. Ni le lissage des entrées de l'encre, ni le filtrage bilinéaire de l'atlas, ni l'écart de plans n'ont réduit la mesure.
33. **Découpe de référence fragmentée.** La découpe en composantes connexes donne 57 calques (6 avant). Tous les calques de cheveux ont l'ordre 0 : les mèches de devant ne passent pas devant le visage si elles sont séparées du reste par la couleur.

## Relief, spéculaire, tête, découpe et séquence (2 novembre 2026, suite)
- Relief : contrat vérifié, pas de changement de rendu. Les normales sont renormalisées dans la passe géométrie et dans l'ombrage, puis atteignent la rampe (test GPU `test_pente_atteint_la_rampe_gpu`). `relief_max` ne touche que la profondeur (test `test_relief_max_ne_change_que_la_profondeur`).
- Spéculaire : coupé là où l'albédo a une luminance inférieure à `spec_lum_min` (0,35 par défaut), dans le shader, dans `reference.ombrage` et dans les uniforms. Raison : la référence n'a pas de reflets durs sur ses vêtements sombres. Le réglage s'applique aussi à Kaël. Tests : `tests/test_tissus_sombres.py` (8, GPU compris).
- Tête : inclinaison de ±0,4 rad dans les deux démos. La rotation de la tête est un os du squelette, pas la grille FFD : changer les poids FFD n'aurait rien changé à l'inclinaison.
- Kaël : la démo utilise l'encre fine, et la rangée de bascule remplace le fondu à 22,5° par une bascule nette (`vue_nette`). Les calques sont séparés en profondeur par 0,15 par rang d'ordre, au lieu de 0,06, pour dépasser le relief de 0,10 (test `test_ecart_de_plans_depasse_le_relief`).
- Découpe : les traits d'encre (chapeau noir) sont retirés avant le découpage en composantes connexes ; deux zones de même couleur séparées par un trait deviennent deux calques. Repli si aucune composante ne subsiste. Tests : 16 au total dans `tests/test_decoupe_materiaux.py`.
- Séquence : `engine/npr/sequence_kael.py <dossier> [n]` rend un balayage monotone de +0,4 à −0,4 rad, encode un MP4 par mode (encre, Sobel) et écrit `metriques.json`. Métrique : un pixel scintille s'il fait deux inversions rapides (écart de deux images au plus). Tests : `tests/test_sequence.py` (8).

## Fichiers
- `engine/npr/parametres.py` : paramètres partagés (ombrage, cheveux, contour) ;
- `engine/npr/rampe.py` : rampes toon ;
- `engine/npr/reference.py` : référence numpy ;
- `engine/npr/rig.py` : squelette 2D, poids, grille FFD, pistes et timeline (numpy pur) ;
- `engine/npr/calques_anim.py` : calques articulés, sommets à la pose, tri par profondeur ;
- `engine/npr/demo_articule.py` : personnage à cinq calques, chevelure en Verlet, planche d'instants ;
- `engine/npr/chargeur.py` : chargeur de calques réels (format couches/2), masques, atlas et correspondance UV ;
- `engine/npr/physique.py` : cheveux FFD simulés par Verlet, forces apparentes du repère de la tête ;
- `engine/npr/multivue.py` : choix et fondu entre vues réelles, bascule, signalement des vues absentes ;
- `engine/npr/demo_personnage.py` : personnage réel de Kaël, rangées de tête inclinée et de fondu entre vues ;
- `engine/npr/rendu.py` : passes OpenGL (`RenduNPR` : `dessiner`, `dessiner_gbuffer`, `contour_sur`) ;
- `engine/npr/relief.py` : calques 2.5D, relief, normales, composition ;
- `engine/npr/shaders/*.vert|frag` : GLSL 330 ;
- `engine/npr/tete_test.py` : banc d'essai (sphère, bosse, masques UV, calotte) ;
- `engine/npr/demo_tete.py`, `engine/npr/demo_calque.py` : images de test ;
- `tests/test_npr.py`, `tests/test_rig.py`, `tests/test_personnage_reel.py` : tests.
- `engine/npr/encre.py` : encre fine (silhouette continue, épaisseur selon l'éclairage, arêtes internes minces) ;
- `engine/npr/decoupe_materiaux.py` : découpe d'une illustration aplatie en couches par matériau (partition, nommage, masque froid/chaud) ;
- `engine/npr/demo_reference.py` : planche à partir de l'illustration de référence (découpe par couleur, trois inclinaisons) ;
- `tests/test_encre.py`, `tests/test_decoupe_materiaux.py` : tests de l'encre et de la découpe ;
- `tests/test_tissus_sombres.py` : spéculaire coupé sur les tissus sombres, chaîne normale -> rampe ;
- `engine/npr/sequence_kael.py`, `tests/test_sequence.py` : séquence de test et métrique de scintillement ;

## Pipeline 3D hybride (prototype)

Modules : `maillage3d.py` (import OBJ, normales, tangentes, UV planaires, squelette 3D, poids par proximité,
skinning linéaire), `buste.py` (proxy low-poly généré, 3 os : torse, cou, tête), `rendu3d.py` (`Avatar3D` :
skinning CPU puis chemin maillage de `rendu.py`, mêmes rampes, rim, spéculaire et contour que le 2.5D),
`demo_buste3d.py` (planche), `sequence_3d.py` (balayages yaw ±45° et tête ±0,4 rad, MP4, métriques).

Limites, à lire avant toute conclusion :
- Le buste est un **proxy généré**, pas Kaël. Aucun modèle 3D du personnage n'existe dans le dépôt.
- Import OBJ seulement ; le glTF n'est pas implanté.
- UV planaires depuis la face : de face, la texture est juste ; à ±45° elle s'étire et le fond clair du
  recadrage apparaît sur les flancs. Corriger demande des UV peints ou une projection multi-vues.
- Scintillement mesuré sur le balayage yaw : 24 % des pixels sombres (sans encre fine : 23 %). L'encre n'en est
  pas la cause. Hypothèse non vérifiée : échantillonnage de la texture sur les UV étirés.
- Tête (tilt) : 7 % de scintillement, régularité du mouvement 1,04 (un à-coup donnerait un rapport élevé).

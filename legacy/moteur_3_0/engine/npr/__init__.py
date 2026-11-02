"""Rendu animé non photoréaliste (NPR) : toon ramp, Sobel, rim light, spéculaire, masques visage.

Modules :
- parametres : réglages des passes (partagés GLSL / numpy) ;
- rampe      : rampes toon 1 x 256 ;
- reference  : formules en numpy (référence et tests) ;
- rendu      : passes OpenGL 3.3 (moderngl) et G-buffer MRT ;
- shaders/   : GLSL 330 (géométrie, ombrage, contour, plein écran) ;
- tete_test  : banc d'essai (sphère avec bosse de nez, masques UV).

Documentation : docs/npr.md.
"""

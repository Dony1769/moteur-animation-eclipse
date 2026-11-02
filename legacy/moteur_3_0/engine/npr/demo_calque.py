"""Démo 2.5D : deux calques procéduraux (visage, puis cheveux devant) -> relief -> G-buffer -> NPR GPU.

A : sans reflet de cheveux. B : avec le reflet anisotrope des mèches (flux vertical).
Les calques sont des formes dessinées en code, pas un personnage du projet : c'est un banc
d'essai du chemin 2.5D (alpha -> relief -> normales -> ombrage -> contour).

Usage : python3 engine/npr/demo_calque.py [sortie.png]
Sortie par défaut : out/npr/test_calque_npr.png (dossier ignoré par git).
"""
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from npr import relief as RL  # noqa: E402
from npr import tete_test as T  # noqa: E402
from npr.parametres import ParamsContour, ParamsOmbrage  # noqa: E402
from npr.rendu import RenduNPR, creer_contexte  # noqa: E402

TAILLE = 512
RACINE = Path(__file__).resolve().parent.parent.parent
LUMIERE_CALQUE = np.array([-0.5, 0.35, 0.8], np.float32)
LUMIERE_CALQUE = (LUMIERE_CALQUE / np.linalg.norm(LUMIERE_CALQUE)).astype(np.float32)


def calques_demo(taille=TAILLE):
    """Visage (fond) et chevelure (devant), en ordre image."""
    H = W = taille
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)

    def ellipse(cx, cy, ax, ay):
        return ((xx - cx) / ax) ** 2 + ((yy - cy) / ay) ** 2 <= 1.0

    visage = ellipse(256, 300, 118, 150)
    rgba_v = np.zeros((H, W, 4), np.float32)
    rgba_v[..., :3] = (0.96, 0.80, 0.72)
    rgba_v[..., 3] = visage
    for cx in (210, 302):                              # yeux : couleur seulement, relief du visage
        rgba_v[ellipse(cx, 300, 14, 9), :3] = (0.15, 0.12, 0.20)

    cheveux = (ellipse(256, 200, 150, 125) & (yy < 290)) | ellipse(122, 320, 42, 125) | ellipse(390, 320, 42, 125)
    rgba_c = np.zeros((H, W, 4), np.float32)
    rgba_c[..., :3] = (0.42, 0.22, 0.26)
    rgba_c[..., 3] = cheveux

    flux = np.zeros((H, W, 2), np.float32)             # mèches rayonnant depuis un point au-dessus du crâne
    flux[..., 0] = xx - 256
    flux[..., 1] = yy - 40

    return [
        RL.Calque(rgba_v, plan=5.0, relief_max=0.2, rayon_biseau=30.0),
        RL.Calque(rgba_c, plan=4.8, relief_max=0.35, rayon_biseau=18.0,
                  flux=flux, masque_cheveux=cheveux.astype(np.float32)),
    ]


def rendre(ctx, calques, avec_cheveux, taille=TAILLE):
    rendu = RenduNPR(
        ctx, taille, taille,
        ombrage=ParamsOmbrage(poids_sphere=0.0, spec_seuil=0.985, cheveux_seuil=0.997,
                              cheveux_couleur=(0.28, 0.24, 0.30)),
        contour=ParamsContour(epaisseur=1, seuil_profondeur=0.25, seuil_normale=0.4),
    )
    g = RL.composer(calques, taille, taille)
    if avec_cheveux:
        rendu.definir_masque_cheveux(g["masque_cheveux"])
    rendu.dessiner_gbuffer(g, tan_fov=T.tan_fov(taille, taille), centre_tete_vue=T.CENTRE_VUE,
                           lumiere_vue=LUMIERE_CALQUE, avant_tete_vue=T.AVANT_VUE)
    img = rendu.image_finale()[..., :3].copy()
    rendu.liberer()
    return img


def main():
    sortie = Path(sys.argv[1]) if len(sys.argv) > 1 else RACINE / "out" / "npr" / "test_calque_npr.png"
    sortie.parent.mkdir(parents=True, exist_ok=True)
    ctx = creer_contexte()
    if ctx is None:
        print("Aucun contexte OpenGL disponible : rendu impossible.")
        return 1
    print("OpenGL :", ctx.info["GL_RENDERER"])
    calques = calques_demo()
    panneaux = []
    for nom, avec in (("A  sans reflet de cheveux", False), ("B  reflet anisotrope des cheveux", True)):
        img = rendre(ctx, calques, avec)
        cv2.putText(img, nom, (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (30, 30, 30), 1, cv2.LINE_AA)
        panneaux.append(cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
    cv2.imwrite(str(sortie), np.hstack(panneaux))
    print("image :", sortie)
    return 0


if __name__ == "__main__":
    sys.exit(main())

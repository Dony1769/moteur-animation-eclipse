"""Image de test du rendu NPR : une tête de banc d'essai, trois réglages côte à côte.

A : normales réelles partout (relief du nez, pas de lissage)
B : normales sphériques partout (ombrage plat, le nez disparaît)
C : hybride : normales sphériques sauf autour du nez, masque d'ombre visage et contour

Usage : python3 engine/npr/demo_tete.py [sortie.png]
Sortie par défaut : out/npr/test_tete_npr.png (dossier out/, ignoré par git).
"""
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from npr import reference as R  # noqa: E402
from npr import tete_test as T  # noqa: E402
from npr.parametres import ParamsContour, ParamsOmbrage  # noqa: E402
from npr.rampe import rampe_par_defaut, vers_flottant  # noqa: E402
from npr.rendu import RenduNPR, creer_contexte  # noqa: E402

TAILLE = 384
RACINE = Path(__file__).resolve().parent.parent.parent

ALBEDO = (0.92, 0.72, 0.62)   # teinte de peau de test
SPEC = 0.985                  # spéculaire fin : seuil élevé sur N·H

CONFIGS = [
    ("A  normales reelles", ParamsOmbrage(poids_sphere=0.0, spec_seuil=SPEC), False),
    ("B  normales spheriques", ParamsOmbrage(poids_sphere=1.0, spec_seuil=SPEC), False),
    ("C  hybride + masque visage",
     ParamsOmbrage(poids_sphere=1.0, masque_visage=True, spec_seuil=SPEC), True),
]


def rendre(ctx, sortie=None):
    rendu = RenduNPR(ctx, TAILLE, TAILLE, contour=ParamsContour(epaisseur=1))
    maillage = T.charger(ctx, rendu.prog_geo)
    masque_sphere, masque_ombre = T.masques(512, 512)
    rendu.definir_masques(masque_sphere, masque_ombre)
    rampe_f = vers_flottant(rampe_par_defaut())
    tan = T.tan_fov(TAILLE, TAILLE)
    images, ecarts = [], []
    for nom, pombre, avec_masque in CONFIGS:
        if not avec_masque:
            rendu.definir_masques(None, None)
        else:
            rendu.definir_masques(masque_sphere, masque_ombre)
        rendu.p_ombrage = pombre
        rendu.dessiner(maillage, modele_vue=T.modele_vue(), projection=T.projection(TAILLE, TAILLE),
                       centre_tete_vue=T.CENTRE_VUE, lumiere_vue=T.LUMIERE_VUE,
                       avant_tete_vue=T.AVANT_VUE, tan_fov=tan, couleur_albedo=ALBEDO)
        g = rendu.lire_gbuffer()
        gl = rendu.lire_ombrage()
        ref = R.ombrage(g["albedo"], g["normale"], g["profondeur"], g["uv"], rampe_f, pombre, tan,
                        T.CENTRE_VUE, T.LUMIERE_VUE, T.AVANT_VUE,
                        masque_sphere if avec_masque else None,
                        masque_ombre if avec_masque else None)
        ecarts.append((nom, float(np.abs(ref - gl).max())))
        img = rendu.image_finale()[..., :3].copy()
        cv2.putText(img, nom, (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (30, 30, 30), 1, cv2.LINE_AA)
        images.append(cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
    rendu.liberer()
    planche = np.hstack(images)
    return planche, ecarts


def main():
    sortie = Path(sys.argv[1]) if len(sys.argv) > 1 else RACINE / "out" / "npr" / "test_tete_npr.png"
    sortie.parent.mkdir(parents=True, exist_ok=True)
    ctx = creer_contexte()
    if ctx is None:
        print("Aucun contexte OpenGL disponible : rendu impossible.")
        return 1
    print("OpenGL :", ctx.info["GL_RENDERER"])
    planche, ecarts = rendre(ctx)
    cv2.imwrite(str(sortie), planche)
    for nom, e in ecarts:
        print(f"ecart GPU/numpy {nom.strip()} : {e:.6f}")
    print("image :", sortie)
    return 0


if __name__ == "__main__":
    sys.exit(main())

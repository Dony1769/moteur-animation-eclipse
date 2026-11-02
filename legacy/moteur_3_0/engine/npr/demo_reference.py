"""Démo : illustration de référence aplatie, découpée par matériaux puis rendue en calques NPR.

Ce n'est pas une découpe par partie du corps (voir decoupe_materiaux.py pour les limites) :
- calques = groupes de couleur (peau, cheveux, veste, fourrure, cuir, sombre) ;
- squelette = deux os à placer à la main (cou, bassin, sommet du crâne) ; les calques au-dessus
  du cou suivent la tête, les autres suivent le corps ;
- masque matériau : les vêtements sombres prennent la rampe froide, la peau la rampe chaude.

Usage : python3 engine/npr/demo_reference.py [image.webp] [sortie.png]
Par défaut, l'image est celle jointe à la conversation (chemin d'attachement) : passer le chemin
en argument sur une autre machine.
"""
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from npr import relief as RL  # noqa: E402
from npr import tete_test as T  # noqa: E402
from npr.calques_anim import construire  # noqa: E402
from npr.chargeur import construire_atlas, rgba_couche  # noqa: E402
from npr.decoupe_materiaux import decouper, materiau_de  # noqa: E402
from npr.demo_articule import LUMIERE, PARAMS  # noqa: E402
from npr.encre import ParamsEncre  # noqa: E402
from npr.rendu import RenduNPR, creer_contexte  # noqa: E402
from npr.rig import Os, Squelette  # noqa: E402

RACINE = Path(__file__).resolve().parent.parent.parent
IMAGE_PAR_DEFAUT = Path("/mnt/user-data/attachments/9ce8e1e5-f7cf-5619-8a75-3c6d9a11ab1c/19eeea6d-image.webp")
BOITE = (0, 0, 296, 800)                 # gros plan de la première colonne (exclut le panneau voisin)
# Points-clés estimés à l'œil sur l'image (pas de détection) : cou, sommet du crâne, bassin.
POINTS = {"cou": (119.0, 244.0), "tete_haut": (125.0, 31.0), "bassin": (125.0, 560.0)}
SEUIL_TETE_Y = 250.0                     # calque dont le centre est au-dessus suit la tête
TILTS = (-0.4, 0.0, 0.4)                 # rad (≈ ±23°) : inclinaison franche de la tête


def squelette(points):
    return Squelette([
        Os("corps", pivot=points["bassin"], parent=None, bout=points["cou"], sigma=120.0),
        Os("tete", pivot=points["cou"], parent=0, bout=points["tete_haut"], sigma=80.0),
    ])


def construire_calques(vue, cellule=3.0):
    """Calques articulés et masque matériau (sur l'atlas) pour une vue découpée par matériaux."""
    sq = squelette(vue.points)
    atlas = construire_atlas(vue)
    masque_materiau = np.zeros(atlas.image.shape[:2], np.float32)
    calques = []
    for c in vue.couches:
        mat = materiau_de(c)
        rgba = rgba_couche(vue, c)
        ys = np.nonzero(c.masque)[0]
        os_actifs = {"tete"} if ys.mean() < SEUIL_TETE_Y else {"corps"}
        # Relief faible et flou fort : les masques par couleur sont fragmentés, leurs bords
        # produiraient sinon des normales bruitées (points noirs, éclats).
        calque = RL.Calque(rgba=rgba, plan=5.0 - 0.06 * mat.ordre, relief_max=0.04,
                           rayon_biseau=6.0, flou=3.0)
        calques.append(construire(c.id, calque, ordre=mat.ordre, squelette=sq, os_actifs=os_actifs,
                                  cellule=cellule, texture=atlas.image,
                                  uv_de=lambda P, a=atlas, nom=c.id: a.uv(nom, P)))
        if mat.froid:
            e = atlas.emplacements[c.id]
            x0, y0, x1, y1 = c.boite
            masque_materiau[e.y:e.y + e.h, e.x:e.x + e.l] = c.masque[y0:y1, x0:x1].astype(np.float32)
    calques.sort(key=lambda c: c.ordre)
    return calques, masque_materiau


def rendre(ctx, vue, calques, masque_materiau, tilt):
    H, W = vue.hauteur, vue.largeur
    rendu = RenduNPR(ctx, W, H, ombrage=PARAMS)
    # Arêtes internes peu sensibles : seuls la silhouette et les traits forts restent.
    rendu.definir_encre(ParamsEncre(seuil_normale=3.0, seuil_profondeur=1.0, longueur_min=30))
    rendu.definir_materiaux(masque_materiau)
    rendu.definir_masque_cheveux(np.ones((1, 1), np.float32))
    try:
        rendu.dessiner_calques(calques, {"tete": tilt}, projection=T.projection(W, H),
                               tan_fov=T.tan_fov(W, H), centre_tete_vue=T.CENTRE_VUE,
                               lumiere_vue=LUMIERE, avant_tete_vue=T.AVANT_VUE)
        img = rendu.image_finale()[..., :3]
        return img.copy()
    finally:
        rendu.liberer()


def main(argv):
    image = Path(argv[1]) if len(argv) > 1 else IMAGE_PAR_DEFAUT
    sortie = Path(argv[2]) if len(argv) > 2 else RACINE / "out" / "npr" / "test_reference_materiaux.png"
    sortie.parent.mkdir(parents=True, exist_ok=True)
    bgr = cv2.imread(str(image), cv2.IMREAD_COLOR)
    if bgr is None:
        print("image illisible :", image)
        return 1
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    vue = decouper(rgb, BOITE, POINTS, k=6)
    print("couches :", [(c.id, c.ordre) for c in vue.couches])
    ctx = creer_contexte()
    if ctx is None:
        print("Aucun contexte OpenGL disponible.")
        return 1
    print("OpenGL :", ctx.info["GL_RENDERER"])
    calques, masque = construire_calques(vue)
    x0, y0, x1, y1 = BOITE
    cadres = [cv2.resize(cv2.cvtColor((rgb[y0:y1, x0:x1] * 255).astype(np.uint8), cv2.COLOR_RGB2BGR),
                         (296, 800), interpolation=cv2.INTER_AREA)]
    for t in TILTS:
        img = rendre(ctx, vue, calques, masque, t)[y0:y1, x0:x1]
        bgr_img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        cadres.append(cv2.resize(bgr_img, (296, 800), interpolation=cv2.INTER_AREA))
    for c, nom in zip(cadres, ("référence", "tête -0,40", "tête 0", "tête +0,40")):
        cv2.putText(c, nom, (8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (30, 30, 30), 2, cv2.LINE_AA)
    cv2.imwrite(str(sortie), np.hstack(cadres))
    print("planche :", sortie)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

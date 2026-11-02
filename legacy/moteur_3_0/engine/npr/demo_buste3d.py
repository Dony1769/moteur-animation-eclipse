"""Démo 3D : buste proxy skinné, texturé avec les vues réelles de Kaël, rendu NPR.

- Géométrie : buste proxy low-poly (buste.py), importé depuis engine/npr/modeles/buste_proxy.obj.
- Textures multi-vues : une texture par vue réelle (face à 0°, trois-quarts à 45°). Chaque vue a ses UV,
  projetés depuis son angle (géométrie tournée de l'angle de la vue, même échelle que la face), et sa
  texture est détourée par l'alpha du premier plan (le fond blanc de la référence n'est pas dessiné).
- Bascule nette ou fondu entre les vues ; mipmaps et filtrage anisotrope.
- Squelette : torse, cou, tête (rotation de la tête en 3D autour de l'articulation du cou).
- Limite : aucune vue de profil réelle. Au-delà de 45°, la vue trois-quarts est répétée et l'écart apparaît.

Usage : python3 engine/npr/demo_buste3d.py [planche.png]
"""
import dataclasses
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from npr import buste as B  # noqa: E402
from npr import demo_personnage as DP  # noqa: E402
from npr import maillage3d as M  # noqa: E402
from npr import rendu3d as R  # noqa: E402
from npr.chargeur import charger_vue, premier_plan  # noqa: E402
from npr.encre import ParamsEncre  # noqa: E402
from npr.rendu import creer_contexte  # noqa: E402

MODELE = Path(__file__).resolve().parent / "modeles" / "buste_proxy.obj"
# Recadrages (x0, y0, x1, y1, pixels de la vue de référence). Vue de face : boîte fixée à la main, qui
# couvre le buste. Vue trois-quarts : même décalage que la face par rapport au centre de la tête
# (tête de face (222..356, 36..169), centre (289, 102) ; tête trois-quarts (98..237, 1..136), centre (167, 68)).
RECADRAGE_FACE = (155, 36, 422, 396)
RECADRAGE_34 = (33, 2, 300, 362)
ANGLE_34 = np.radians(45.0)     # angle de la vue trois-quarts (même sens que le yaw de la caméra)
YAW_PLANCHE = (-np.pi / 4, 0.0, np.pi / 4)   # ±45°
TILT_PLANCHE = (-0.4, 0.0, 0.4)              # rad, inclinaison de tête


def texture_kael(vue, recadrage=RECADRAGE_FACE, avec_alpha=False):
    """Texture RGBA du recadrage d'une vue de Kaël (ligne 0 = haut de l'image, comme les UV planaires).

    avec_alpha : alpha = premier plan (le fond blanc devient transparent et sera retiré au rendu).
    """
    x0, y0, x1, y1 = recadrage
    rgb = (vue.reference[y0:y1, x0:x1] * 255.0).astype(np.uint8)
    tex = np.ones((rgb.shape[0], rgb.shape[1], 4), np.float32)
    tex[..., :3] = rgb.astype(np.float32) / 255.0
    if avec_alpha:
        tex[..., 3] = premier_plan(vue.reference)[y0:y1, x0:x1].astype(np.float32)
    return tex


def uv_vue(modele, angle, reference=None):
    """UV d'une vue : projection planaire depuis l'angle `angle` (rad), à l'échelle du modèle de repos.

    La géométrie est tournée de `angle` autour de y (comme la caméra), puis projetée en x, y. Les bornes
    viennent du modèle de repos (`reference`, par défaut `modele`) : toutes les vues ont la même échelle.
    """
    ref = modele if reference is None else reference
    mn, mx = ref.sommets.min(axis=0), ref.sommets.max(axis=0)
    etendue = np.maximum(mx - mn, 1e-12)
    rot = M.rotation_axe((0.0, 1.0, 0.0), float(angle))
    s = modele.sommets @ rot.T
    u = (s[:, 0] - mn[0]) / etendue[0]
    v = 1.0 - (s[:, 1] - mn[1]) / etendue[1]
    uv = np.stack([u, v], axis=1)
    tan = M.calculer_tangentes(modele.sommets, uv, modele.triangles, modele.normales)
    return dataclasses.replace(modele, uv=uv, tangentes=tan, uv_origine=f"vue {np.degrees(angle):.0f}°")


def charger_buste():
    """Buste proxy importé depuis le fichier OBJ, avec ses poids d'os calculés par proximité."""
    m = M.charger_obj(MODELE)
    sq = B.squelette_buste()
    m.poids = M.poids_proximite(m.sommets, sq, sigma=0.08, k=2)
    return m, sq


def vues_kael(modele, vue_face, vue_34):
    """Liste (angle_deg, modele_vue, texture) pour Avatar3D : face à 0°, trois-quarts à 45°."""
    return [
        (0.0, uv_vue(modele, 0.0), texture_kael(vue_face, RECADRAGE_FACE, avec_alpha=True)),
        (45.0, uv_vue(modele, ANGLE_34), texture_kael(vue_34, RECADRAGE_34, avec_alpha=True)),
    ]


def pose_tete(tilt):
    """Pose : rotation de la tête de `tilt` rad autour de l'axe z (inclinaison dans le plan)."""
    return {"tete": (np.array([0.0, 0.0, 1.0]), float(tilt))}


def construire_avatar(ctx, *, multivue=True, largeur=360, hauteur=480, encre=True):
    """Avatar prêt à rendre. multivue=False reproduit l'ancien rendu : une seule texture de face, sans détourage."""
    vue_face = charger_vue(DP.KAEL / DP.FICHIERS[0.0])
    modele, sq = charger_buste()
    enc = ParamsEncre() if encre else None
    if multivue:
        vue_34 = charger_vue(DP.KAEL / DP.FICHIERS[45.0])
        av = R.Avatar3D(ctx, modele, sq, largeur, hauteur, vues=vues_kael(modele, vue_face, vue_34),
                        encre=enc)
    else:
        av = R.Avatar3D(ctx, modele, sq, largeur, hauteur, texture_rgba=texture_kael(vue_face), encre=enc,
                        seuil_alpha=0.0)
    return av


def main(argv):
    sortie = Path(argv[1]) if len(argv) > 1 else Path("planche_buste3d.png")
    ctx = creer_contexte()
    if ctx is None:
        print("Aucun contexte OpenGL disponible.")
        return 1
    print("OpenGL :", ctx.info["GL_RENDERER"])
    rangees = {}
    for nom, multi in (("avant", False), ("apres", True)):
        av = construire_avatar(ctx, multivue=multi)
        try:
            rangees[nom] = [av.rendre(None, y) for y in YAW_PLANCHE]
        finally:
            av.liberer()
    lignes = []
    for nom, rangee in rangees.items():
        titres = [f"{nom} yaw {np.degrees(y):+.0f}°" for y in YAW_PLANCHE]
        cadres = []
        for img, titre in zip(rangee, titres):
            bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
            cv2.putText(bgr, titre, (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (30, 30, 30), 2, cv2.LINE_AA)
            cadres.append(bgr)
        lignes.append(np.hstack(cadres))
    cv2.imwrite(str(sortie), np.vstack(lignes))
    print("planche :", sortie)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

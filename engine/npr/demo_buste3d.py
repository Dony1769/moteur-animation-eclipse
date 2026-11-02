"""Démo 3D : buste proxy skinné, texturé avec la face de Kaël, rendu NPR.

- Géométrie : buste proxy low-poly (buste.py), importé depuis engine/npr/modeles/buste_proxy.obj.
- Texture : recadrage de la vue de face de Kaël (haut du corps). Les UV planaires du proxy projettent
  ce recadrage de face ; de profil, la texture s'étire (limite connue).
- Squelette : torse, cou, tête (rotation de la tête en 3D autour de l'articulation du cou).

Usage : python3 engine/npr/demo_buste3d.py [planche.png]
"""
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from npr import buste as B  # noqa: E402
from npr import demo_personnage as DP  # noqa: E402
from npr import maillage3d as M  # noqa: E402
from npr import rendu3d as R  # noqa: E402
from npr.chargeur import charger_vue  # noqa: E402
from npr.encre import ParamsEncre  # noqa: E402
from npr.rendu import creer_contexte  # noqa: E402

MODELE = Path(__file__).resolve().parent / "modeles" / "buste_proxy.obj"
# Recadrage de la vue de face de Kaël : boîte de la tête (222..355, 36..168) élargie au ratio du buste
# (0,48 × 0,65 unités), à ≈ 554 px par unité (la tête fait 0,24 unité, soit 133 px).
RECADRAGE = (155, 36, 422, 396)              # x0, y0, x1, y1 dans l'image de face (pixels)
YAW_PLANCHE = (-np.pi / 4, 0.0, np.pi / 4)   # ±45°
TILT_PLANCHE = (-0.4, 0.0, 0.4)              # rad, inclinaison de tête


def texture_kael(vue):
    """Texture RGBA du recadrage de Kaël (ligne 0 = haut de l'image, comme les UV planaires)."""
    x0, y0, x1, y1 = RECADRAGE
    rgb = (vue.reference[y0:y1, x0:x1] * 255.0).astype(np.uint8)
    tex = np.ones((rgb.shape[0], rgb.shape[1], 4), np.float32)
    tex[..., :3] = rgb.astype(np.float32) / 255.0
    return tex


def charger_buste():
    """Buste proxy importé depuis le fichier OBJ, avec ses poids d'os calculés par proximité."""
    m = M.charger_obj(MODELE)
    sq = B.squelette_buste()
    m.poids = M.poids_proximite(m.sommets, sq, sigma=0.08, k=2)
    return m, sq


def pose_tete(tilt):
    """Pose : rotation de la tête de `tilt` rad autour de l'axe z (inclinaison dans le plan)."""
    return {"tete": (np.array([0.0, 0.0, 1.0]), float(tilt))}


def main(argv):
    sortie = Path(argv[1]) if len(argv) > 1 else Path("planche_buste3d.png")
    ctx = creer_contexte()
    if ctx is None:
        print("Aucun contexte OpenGL disponible.")
        return 1
    print("OpenGL :", ctx.info["GL_RENDERER"])
    vue = charger_vue(DP.KAEL / DP.FICHIERS[0.0])
    tex = texture_kael(vue)
    modele, sq = charger_buste()
    print(f"buste : {len(modele.sommets)} sommets, UV {modele.uv_origine}")
    av = R.Avatar3D(ctx, modele, sq, 360, 480, texture_rgba=tex, encre=ParamsEncre())
    try:
        rangee1 = [av.rendre(None, y) for y in YAW_PLANCHE]
        rangee2 = [av.rendre(pose_tete(t), 0.0) for t in TILT_PLANCHE]
    finally:
        av.liberer()
    titres1 = ["yaw -45°", "yaw 0°", "yaw +45°"]
    titres2 = [f"tête {t:+.2f} rad" for t in TILT_PLANCHE]
    lignes = []
    for rangee, titres in ((rangee1, titres1), (rangee2, titres2)):
        cadres = []
        for img, titre in zip(rangee, titres):
            bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
            cv2.putText(bgr, titre, (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (30, 30, 30), 2, cv2.LINE_AA)
            cadres.append(bgr)
        lignes.append(np.hstack(cadres))
    cv2.imwrite(str(sortie), np.vstack(lignes))
    print("planche :", sortie)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

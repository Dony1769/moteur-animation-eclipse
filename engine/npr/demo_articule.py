"""Démo calques articulés : un personnage procédural à cinq calques, rigé, animé par clés.

Calques (du plus loin au plus proche) : cheveux arrière, corps, visage, yeux, frange.
- squelette : corps (racine) -> tête (pivot à la nuque) -> mèche (enfant de la tête) ;
- FFD sur les yeux, pilotée par la piste « cligne » (écrasement vertical = paupières) ;
- piste « tete » : inclinaison dans le plan ; piste « meche » : balancement de la mèche.
Les formes sont dessinées en code : c'est un banc d'essai du chemin articulé, pas un personnage du projet.

Usage : python3 engine/npr/demo_articule.py [sortie.png]
Sortie par défaut : out/npr/test_articule_npr.png (planche de six images, dossier ignoré par git).
"""
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from npr import relief as RL  # noqa: E402
from npr import tete_test as T  # noqa: E402
from npr.calques_anim import construire  # noqa: E402
from npr.parametres import ParamsOmbrage  # noqa: E402
from npr.rig import GrilleFFD, Os, Squelette, Timeline  # noqa: E402
from npr.rendu import RenduNPR, creer_contexte  # noqa: E402

TAILLE = 512
RACINE = Path(__file__).resolve().parent.parent.parent
LUMIERE = np.array([-0.5, 0.35, 0.8], np.float32)
LUMIERE = (LUMIERE / np.linalg.norm(LUMIERE)).astype(np.float32)
POINT_CHEVEUX = (256.0, 150.0)          # les mèches rayonnent depuis le haut du crâne
BOITE_YEUX = (176.0, 236.0, 336.0, 290.0)


def squelette():
    return Squelette([
        Os("corps", pivot=(256.0, 470.0), parent=None, bout=(256.0, 512.0), sigma=70.0),
        Os("tete", pivot=(256.0, 380.0), parent=0, bout=(256.0, 150.0), sigma=60.0),
        Os("meche", pivot=(256.0, 200.0), parent=1, bout=(256.0, 330.0), sigma=80.0),
    ])


def _formes():
    """Masques booléens des calques, en ordre image."""
    H = W = TAILLE
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)

    def ellipse(cx, cy, ax, ay):
        return ((xx - cx) / ax) ** 2 + ((yy - cy) / ay) ** 2 <= 1.0

    corps = np.zeros((H, W), np.uint8)
    cv2.fillPoly(corps, [np.array([[170, 340], [342, 340], [400, 512], [112, 512]], np.int32)], 1)
    return {
        "cheveux_arriere": (ellipse(256, 230, 160, 190) & (yy < 420)),
        "corps": corps.astype(bool),
        "visage": ellipse(256, 250, 105, 130),
        "yeux": ellipse(206, 262, 16, 10) | ellipse(306, 262, 16, 10),
        # Bord inférieur en arc : la frange descend sur les côtés (au lieu d'une coupe droite).
        "frange": ellipse(256, 150, 130, 85) & (yy < 180 + 90 * ((xx - 256) / 128) ** 2),
    }


def _rgba(masque, couleur):
    rgba = np.zeros(masque.shape + (4,), np.float32)
    rgba[..., :3] = couleur
    rgba[..., 3] = masque.astype(np.float32)
    return rgba


def _flux():
    H = W = TAILLE
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    flux = np.zeros((H, W, 2), np.float32)
    flux[..., 0] = xx - POINT_CHEVEUX[0]
    flux[..., 1] = yy - POINT_CHEVEUX[1]
    return flux


def construire_personnage(cellule=4.0):
    """Liste des CalqueArticule (ordre de dessin arrière -> avant) et le squelette."""
    sq = squelette()
    formes = _formes()
    flux = _flux()
    ffd = GrilleFFD(BOITE_YEUX, nx=3, ny=3)
    # Os actifs par calque : le corps ne suit que son os, la tête ne bouge pas les épaules.
    calques = [
        construire("cheveux_arriere", RL.Calque(_rgba(formes["cheveux_arriere"], (0.42, 0.22, 0.26)),
                                                plan=5.4, relief_max=0.3, rayon_biseau=30.0,
                                                flux=flux, masque_cheveux=formes["cheveux_arriere"].astype(np.float32)),
                   ordre=0, squelette=sq, os_actifs={"tete", "meche"}, cellule=cellule),
        construire("corps", RL.Calque(_rgba(formes["corps"], (0.25, 0.45, 0.70)),
                                      plan=5.0, relief_max=0.15, rayon_biseau=25.0),
                   ordre=1, squelette=sq, os_actifs={"corps"}, cellule=cellule),
        construire("visage", RL.Calque(_rgba(formes["visage"], (0.96, 0.80, 0.72)),
                                       plan=4.8, relief_max=0.2, rayon_biseau=30.0),
                   ordre=2, squelette=sq, os_actifs={"tete"}, cellule=cellule),
        construire("yeux", RL.Calque(_rgba(formes["yeux"], (0.15, 0.12, 0.20)),
                                     plan=4.45, relief_max=0.02, rayon_biseau=6.0, flou=1.0),
                   ordre=3, squelette=sq, ffd=ffd, cle_ffd="cligne", os_actifs={"tete"}, cellule=cellule),
        construire("frange", RL.Calque(_rgba(formes["frange"], (0.42, 0.22, 0.26)),
                                       plan=4.5, relief_max=0.35, rayon_biseau=16.0,
                                       flux=flux, masque_cheveux=formes["frange"].astype(np.float32)),
                   ordre=4, squelette=sq, os_actifs={"tete"}, cellule=cellule),
    ]
    return calques, sq


def timeline():
    tl = Timeline()
    tl.ajouter("tete", [(0.0, 0.0), (0.5, 0.14), (1.0, -0.10)], mode="cubique")
    # Fermeture à 0,9 et non 1 : à 1, les triangles de l'œil s'écrasent en segments dégénérés
    # (points isolés à la rastérisation). 0,9 laisse un trait fin de paupière.
    tl.ajouter("cligne", [(0.0, 0.0), (0.40, 0.0), (0.46, 0.9), (0.52, 0.0), (1.0, 0.0)])
    tl.ajouter("meche", [(0.0, 0.0), (0.5, 0.25), (1.0, -0.20)], mode="cubique")
    return tl


PARAMS = ParamsOmbrage(poids_sphere=0.0, spec_seuil=0.985, cheveux_seuil=0.997,
                       cheveux_couleur=(0.28, 0.24, 0.30))
INSTANTS = (0.0, 0.25, 0.46, 0.5, 0.75, 1.0)


def rendre_images(ctx, calques, tl, instants=INSTANTS):
    """Une image RGB par instant, dans un seul RenduNPR."""
    rendu = RenduNPR(ctx, TAILLE, TAILLE, ombrage=PARAMS)
    rendu.definir_masque_cheveux(np.ones((1, 1), np.float32))
    images = []
    try:
        for t in instants:
            pose = tl.pose(t)
            rendu.dessiner_calques(calques, pose, projection=T.projection(TAILLE, TAILLE),
                                   tan_fov=T.tan_fov(TAILLE, TAILLE), centre_tete_vue=T.CENTRE_VUE,
                                   lumiere_vue=LUMIERE, avant_tete_vue=T.AVANT_VUE)
            images.append(rendu.image_finale()[..., :3].copy())
    finally:
        rendu.liberer()
    return images


def planche(images, instants):
    """Grille 3 x 2 annotée, en BGR pour cv2."""
    cadres = []
    for img, t in zip(images, instants):
        bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        cv2.putText(bgr, f"t = {t:.2f} s", (10, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (30, 30, 30), 2, cv2.LINE_AA)
        cadres.append(bgr)
    lignes = [np.hstack(cadres[i:i + 3]) for i in range(0, len(cadres), 3)]
    return np.vstack(lignes)


def main():
    sortie = Path(sys.argv[1]) if len(sys.argv) > 1 else RACINE / "out" / "npr" / "test_articule_npr.png"
    sortie.parent.mkdir(parents=True, exist_ok=True)
    ctx = creer_contexte()
    if ctx is None:
        print("Aucun contexte OpenGL disponible : rendu impossible.")
        return 1
    print("OpenGL :", ctx.info["GL_RENDERER"])
    calques, _ = construire_personnage()
    print("triangles par calque :", {c.nom: len(c.triangles) for c in calques})
    images = rendre_images(ctx, calques, timeline())
    cv2.imwrite(str(sortie), planche(images, INSTANTS))
    print("planche :", sortie)
    return 0


if __name__ == "__main__":
    sys.exit(main())

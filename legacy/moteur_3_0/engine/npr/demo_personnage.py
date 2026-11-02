"""Démo personnage réel : calques découpés de Kaël (chargeur + atlas) et vues multiples.

- Calques : chargés depuis universes/eclipse_royale/characters/kael (format couches/2), masques
  = polygones ∩ premier plan, rangés dans un atlas unique. Aucune forme procédurale.
- Squelette : deux os tirés des points-clés (corps : bassin -> cou ; tête : cou -> sommet du crâne).
- Vues : face (0°) et trois quarts (45°). Le profil n'existe pas dans les données : l'angle 90° est
  signalé « hors plage » et non rendu.

Usage : python3 engine/npr/demo_personnage.py [sortie.png]
Sortie par défaut : out/npr/test_personnage_kael.png (dossier ignoré par git).
"""
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from npr import relief as RL  # noqa: E402
from npr import tete_test as T  # noqa: E402
from npr.calques_anim import construire  # noqa: E402
from npr.chargeur import charger_vue, construire_atlas, rgba_couche  # noqa: E402
from npr.demo_articule import LUMIERE, PARAMS  # noqa: E402
from npr.encre import ParamsEncre  # noqa: E402
from npr.multivue import vue_nette  # noqa: E402
from npr.rendu import RenduNPR, creer_contexte  # noqa: E402
from npr.rig import Os, Squelette, Timeline  # noqa: E402

RACINE = Path(__file__).resolve().parent.parent.parent
KAEL = RACINE / "universes" / "eclipse_royale" / "characters" / "kael"
FICHIERS = {0.0: "parts_v2_face_g.json", 45.0: "parts_v2_trois_quarts_g.json"}
OS_DES_COUCHES = {"tete": {"tete"}, "col_cape": {"tete"}}     # les autres couches suivent le corps
TILT = (-0.4, 0.0, 0.4)                                       # inclinaison de tête (rad) pour la planche
RELIEF_KAEL = 0.10             # relief_max des calques de Kaël
ECART_PLANS = 0.15             # écart de plan entre deux rangs d'ordre ; doit dépasser RELIEF_KAEL
                               # (sinon un calque arrière passe devant le calque avant à leur frontière,
                               #  et les deux se disputent les pixels d'une image à l'autre : scintillement)


def plan_de(ordre):
    """Distance caméra du plan de base d'un calque d'ordre donné (plus grand = plus devant)."""
    return 5.0 - ECART_PLANS * ordre


def squelette(vue):
    p = vue.points
    return Squelette([
        Os("corps", pivot=p["bassin"], parent=None, bout=p["cou"], sigma=90.0),
        Os("tete", pivot=p["cou"], parent=0, bout=p["tete_haut"], sigma=70.0),
    ])


def construire_vue(vue, cellule=6.0):
    """Calques articulés d'une vue réelle, dans un atlas unique."""
    sq = squelette(vue)
    atlas = construire_atlas(vue)
    calques = []
    for c in vue.couches:
        rgba = rgba_couche(vue, c)
        # Plus la couche est en avant (ordre grand), plus son plan est proche : ordre de dessin = profondeur.
        calque = RL.Calque(rgba=rgba, plan=plan_de(c.ordre), relief_max=RELIEF_KAEL,
                           rayon_biseau=12.0, flou=1.5)
        os_actifs = OS_DES_COUCHES.get(c.id, {"corps"})
        calques.append(construire(
            c.id, calque, ordre=c.ordre, squelette=sq, os_actifs=os_actifs, cellule=cellule,
            texture=atlas.image,
            uv_de=lambda P, a=atlas, nom=c.id: a.uv(nom, P)))
    return calques, atlas


def rendre(ctx, vue, calques, tilt, encre=ParamsEncre()):
    """Image RGB de la vue, tête inclinée de `tilt` radians. encre=None : contour Sobel d'origine."""
    rendu = RenduNPR(ctx, vue.largeur, vue.hauteur, ombrage=PARAMS)
    rendu.definir_masque_cheveux(np.ones((1, 1), np.float32))
    if encre is not None:
        rendu.definir_encre(encre)
    try:
        rendu.dessiner_calques(calques, {"tete": tilt}, projection=T.projection(vue.largeur, vue.hauteur),
                               tan_fov=T.tan_fov(vue.largeur, vue.hauteur), centre_tete_vue=T.CENTRE_VUE,
                               lumiere_vue=LUMIERE, avant_tete_vue=T.AVANT_VUE)
        img = rendu.image_finale()[..., :3]
        if img.dtype != np.uint8:
            img = (np.clip(img, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)
        return img.copy()
    finally:
        rendu.liberer()


def planche(rangees, titres):
    """Grille annotée (BGR) : rangées de cadres RGB, titres au-dessus de chaque cadre."""
    lignes = []
    for rangee, titre_rangee in zip(rangees, titres):
        cadres = []
        for img, titre in zip(rangee, titre_rangee):
            bgr = cv2.cvtColor(np.clip(img, 0, 255).astype(np.uint8), cv2.COLOR_RGB2BGR)
            cv2.putText(bgr, titre, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (30, 30, 30), 2, cv2.LINE_AA)
            cadres.append(cv2.resize(bgr, (428, 450), interpolation=cv2.INTER_AREA))
        lignes.append(np.hstack(cadres))
    return np.vstack(lignes)


def main():
    sortie = Path(sys.argv[1]) if len(sys.argv) > 1 else RACINE / "out" / "npr" / "test_personnage_kael.png"
    sortie.parent.mkdir(parents=True, exist_ok=True)
    ctx = creer_contexte()
    if ctx is None:
        print("Aucun contexte OpenGL disponible : rendu impossible.")
        return 1
    print("OpenGL :", ctx.info["GL_RENDERER"])

    vues = {a: charger_vue(KAEL / f) for a, f in FICHIERS.items()}
    construits = {a: construire_vue(v) for a, v in vues.items()}
    for a, v in vues.items():
        print(f"vue {v.nom} ({a:.0f}°) : {len(v.couches)} couches, atlas {construits[a][1].image.shape[:2]}")

    # Rangée 1 : face, tête inclinée. Rangée 2 : bascule nette entre face et trois quarts (sans fondu).
    face = {t: rendre(ctx, vues[0.0], construits[0.0][0], t) for t in TILT}
    sprites = {"face_g": face[0.0], "trois_quarts_g": rendre(ctx, vues[45.0], construits[45.0][0], 0.0)}
    vues_angle = {0.0: "face_g", 45.0: "trois_quarts_g"}
    rangee2, titres2 = [], []
    for angle in (0.0, 22.0, 45.0):
        nom, hors = vue_nette(angle, vues_angle)
        rangee2.append(sprites[nom])
        titres2.append(f"bascule {angle:.1f}° : {nom.replace('_g', '')}")
    _, hors = vue_nette(90.0, vues_angle)
    print("profil 90° hors plage :", hors)
    rangees = [[face[t] for t in TILT], rangee2]
    titres = [[f"face, tete {t:+.2f} rad" for t in TILT], titres2]
    cv2.imwrite(str(sortie), planche(rangees, titres))
    print("planche :", sortie)
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Découpe d'une illustration aplatie en calques par matériau (couleur), sans annotation.

Une illustration déjà aplatie (un seul calque, sans parties séparées) n'a pas de découpe par
partie. On en tire une approximation : les pixels du personnage sont regroupés par couleur
(k-moyennes dans l'espace RGB), chaque groupe devient un calque, et chaque calque reçoit un nom
de matériau d'après sa couleur moyenne (peau, cheveux, veste, fourrure, cuir, sombre).

Limites, à lire avant d'utiliser la sortie :
- un groupe de couleur ne correspond pas à une partie du corps : les cheveux de devant et de
  derrière forment un seul calque, la veste et le pantalon sombres peuvent se mélanger ;
- les contours sont ceux de la couleur, pas ceux du dessin : les traits noirs de l'illustration
  appartiennent à un groupe sombre ;
- le squelette ne vient pas de cette découpe : les points-clés sont fournis à la main.

Pur numpy + cv2, sans GPU.
"""
from dataclasses import dataclass

import cv2
import numpy as np

from .chargeur import SEUIL_FOND, Couche, Vue


@dataclass(frozen=True)
class Materiau:
    nom: str
    ordre: int          # ordre de dessin : plus grand = plus devant
    froid: bool         # vrai : rampe froide (vêtements sombres), faux : rampe chaude (peau)


# Ordre de dessin : cheveux arrière, corps, peau, vêtements, fourrure, cuir, sombre, cheveux de devant.
MATERIAUX = {
    "cheveux": Materiau("cheveux", 0, False),
    "peau": Materiau("peau", 2, False),
    "veste": Materiau("veste", 3, True),
    "fourrure": Materiau("fourrure", 4, True),
    "cuir": Materiau("cuir", 5, False),
    "sombre": Materiau("sombre", 6, True),
}


FRACTION_TROU_MAX = 0.01   # un trou plus grand que 1 % de la boîte est du fond (espace entre bras et torse)


def _remplir_trous(m, aire_max):
    """Ajoute au masque les zones de fond fermées, non reliées au bord de l'image, d'au plus aire_max px.

    Les reflets clairs à l'intérieur du personnage (cheveux, cuir brillant) sont petits : sans ce
    remplissage, ils sortiraient du masque et laisseraient voir le fond au rendu. Une grande zone
    claire enfermée reste du fond (ex. l'espace entre le bras et le torse) et n'est pas remplie.
    """
    libre = (~m).astype(np.uint8)
    n, etiquettes = cv2.connectedComponents(libre, connectivity=4)
    bord = np.unique(np.concatenate([etiquettes[0], etiquettes[-1], etiquettes[:, 0], etiquettes[:, -1]]))
    ouvert = np.zeros(n, bool)
    ouvert[bord] = True
    aire = np.bincount(etiquettes.ravel(), minlength=n)
    ferme = (~ouvert) & (aire <= aire_max)
    ferme[0] = False
    return m | ferme[etiquettes]


def premier_plan_region(rgb, boite):
    """Masque (H, W) bool : personnage dans la boîte (x0, y0, x1, y1), zéro ailleurs.

    Pixels non blancs, plus les petites zones claires enfermées dans la silhouette (_remplir_trous).
    """
    H, W = rgb.shape[:2]
    x0, y0, x1, y1 = boite
    m = np.zeros((H, W), bool)
    sous = rgb[y0:y1, x0:x1]
    m[y0:y1, x0:x1] = sous.min(axis=2) * 255.0 < SEUIL_FOND
    aire_max = int(FRACTION_TROU_MAX * (x1 - x0) * (y1 - y0))
    return _remplir_trous(m, aire_max)


def regions_couleur(rgb, masque, k=6, graine=0, lissage=7):
    """Étiquettes (H, W) int : groupe de couleur de chaque pixel du masque, -1 ailleurs.

    k-moyennes sur les couleurs RGB (0..255), puis filtre médian des étiquettes (taille `lissage`,
    impair ; 1 = aucun) pour supprimer les fragments de quelques pixels. Renvoie aussi les couleurs
    moyennes (k, 3).
    """
    pixels = rgb[masque].astype(np.float32) * 255.0
    if len(pixels) < k:
        raise ValueError("pas assez de pixels pour la découpe")
    criteres = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 50, 0.5)
    cv2.setRNGSeed(graine)
    _, etiquettes, centres = cv2.kmeans(pixels, k, None, criteres, 5, cv2.KMEANS_PP_CENTERS)
    labels = np.full(masque.shape, -1, np.int32)
    labels[masque] = etiquettes.ravel()
    if lissage > 1:
        # Filtre médian sur les étiquettes (uint8, -1 -> 255 hors personnage). Près du bord, le
        # filtre peut écrire 255 à l'intérieur du masque : on garde alors l'étiquette d'origine.
        carte = np.where(masque, labels, 255).astype(np.uint8)
        lisse = cv2.medianBlur(carte, lissage).astype(np.int32)
        labels = np.where(masque & (lisse < k), lisse, labels)
    return labels, centres.astype(np.float64) / 255.0


def nommer(couleur):
    """Nom de matériau d'après une couleur moyenne RGB 0..1 (heuristique sur luminance et saturation)."""
    r, g, b = couleur
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    mx, mn = max(couleur), min(couleur)
    sat = 0.0 if mx == 0 else (mx - mn) / mx
    if lum > 0.62 and sat < 0.12:
        return "fourrure"                     # gris clair, peu saturé
    if r > g + 0.06 and r > b + 0.10 and lum > 0.22:
        return "peau" if lum > 0.45 else "cuir"   # rosé clair = peau ; brun-rouge = cuir
    if lum < 0.22:
        return "sombre"                       # noir : gants, pantalon, traits
    if r > b + 0.04 and lum < 0.40:
        return "cheveux"                      # brun sombre
    return "veste"                            # gris moyen


def _voisin_dans(carte, dy, dx):
    """Valeur du voisin (dy, dx) de chaque pixel ; -1 hors de l'image."""
    out = np.roll(carte, (-dy, -dx), axis=(0, 1))
    if dy > 0:
        out[-dy:, :] = -1
    elif dy < 0:
        out[:-dy, :] = -1
    if dx > 0:
        out[:, -dx:] = -1
    elif dx < 0:
        out[:, :-dx] = -1
    return out


def _combler_trous(carte, masque, passes=None):
    """Remplit chaque pixel du masque resté sans étiquette (-1) avec un voisin étiqueté.

    Propagation par couches successives à 4 voisins : chaque passe étend les étiquettes d'un pixel.
    Garantit que les couches forment une partition du personnage, sans trou transparent.
    """
    carte = carte.copy()
    H, W = carte.shape
    passes = (H + W) if passes is None else passes
    for _ in range(passes):
        trou = masque & (carte < 0)
        if not trou.any():
            break
        voisin = np.full(carte.shape, -1, np.int32)
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            v = _voisin_dans(carte, dy, dx)
            voisin = np.where(voisin < 0, v, voisin)
        pose = trou & (voisin >= 0)
        carte[pose] = voisin[pose]
    return carte


SEUIL_TRAIT = 0.08          # chapeau noir : un trait plus sombre que son voisinage d'au moins cette valeur
NOYAU_TRAIT = 5             # largeur (px) au-delà de laquelle une zone sombre n'est plus un trait


def lignes_encre(rgb, masque, noyau=NOYAU_TRAIT, seuil=SEUIL_TRAIT):
    """Traits d'encre : bool (H, W), inclus dans le masque.

    Chapeau noir = fermeture de la luminance moins la luminance. Un trait sombre plus fin que le noyau
    ressort ; une zone sombre large (pantalon, veste) ne ressort pas. Ces traits séparent les zones
    de même couleur (cheveux et veste sombres) avant le découpage en composantes connexes.
    """
    lum = (0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]).astype(np.float32)
    ferme = cv2.morphologyEx(lum, cv2.MORPH_CLOSE, np.ones((noyau, noyau), np.uint8))
    return ((ferme - lum) > seuil) & masque


def decouper(rgb, boite, points, k=6, graine=0, aire_min=0.002):
    """Vue (chargeur.Vue) à calques par matériau, depuis une illustration aplatie.

    rgb : image (H, W, 3) 0..1 ; boite : (x0, y0, x1, y1) du personnage dans l'image ;
    points : {nom: (x, y)} points-clés estimés à la main (cou, bassin, tete_haut...).

    Procédure : (1) k-moyennes sur les couleurs ; (2) retrait des traits d'encre (lignes_encre) ;
    (3) chaque groupe de couleur est découpé en composantes connexes : deux zones de même couleur
    séparées par un trait deviennent deux calques ; (4) composantes plus petites que aire_min de la
    boîte retirées ; (5) les pixels restants, traits compris, reçoivent le voisin le plus proche.
    """
    masque = premier_plan_region(rgb, boite)
    labels, centres = regions_couleur(rgb, masque, k=k, graine=graine)
    traits = lignes_encre(rgb, masque)
    surface = (boite[2] - boite[0]) * (boite[3] - boite[1])
    seuil = aire_min * surface
    carte = np.full(masque.shape, -1, np.int32)
    noms = []
    for i in range(len(centres)):
        m = (labels == i) & ~traits
        if not m.any():
            continue
        m = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        n, etiquettes, stats, _ = cv2.connectedComponentsWithStats(m, connectivity=4)
        for j in range(1, n):
            if stats[j, cv2.CC_STAT_AREA] < seuil:
                continue
            comp = etiquettes == j
            carte[comp] = len(noms)
            noms.append(nommer(rgb[comp].mean(axis=0)))
    carte = _combler_trous(carte, masque)
    # Repli : si aucune composante ne subsiste (motif très fin), les pixels restants forment une couche.
    restant = masque & (carte < 0)
    if restant.any():
        carte[restant] = len(noms)
        noms.append(nommer(rgb[restant].mean(axis=0)))
    couches = []
    for idx, nm in enumerate(noms):
        m = carte == idx
        if not m.any():
            continue
        mat = MATERIAUX[nm]
        couches.append(Couche(id=f"{mat.nom}_{idx}", ordre=mat.ordre, masque=m,
                              chaine=(), ombre=True))
    couches.sort(key=lambda c: c.ordre)
    return Vue(nom="reference_materiaux", reference=rgb.astype(np.float32), couches=couches,
               points=dict(points), fiabilite={})


def materiau_de(couche):
    """Matériau d'une couche produite par decouper (le nom est préfixé)."""
    return MATERIAUX[couche.id.rsplit("_", 1)[0]]

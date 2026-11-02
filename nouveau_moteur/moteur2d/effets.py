"""Effets de compositing. Ne créent aucune couleur : elles viennent toutes des dessins fournis.

- décalage et zoom : transformations affines d'un calque ;
- smear : flou directionnel du calque du personnage, avec son alpha d'origine (pas de halo hors silhouette) ;
- secousse : décalage amorti de l'image entière (caméra), bord découvert blanc ;
- palette : N tons pris parmi les couleurs réelles des dessins ; le blanc du fond reste blanc.
"""
import cv2
import numpy as np

SEUIL_BLANC = 245   # un pixel dont tous les canaux atteignent ce seuil est du fond blanc


def decalage(calque, dx, dy):
    """Translation d'un calque (H, W, C float) ; le bord vide est transparent."""
    h, w = calque.shape[:2]
    m = np.float32([[1, 0, dx], [0, 1, dy]])
    return cv2.warpAffine(calque, m, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)


def zoom(calque, facteur, centre):
    """Zoom de `facteur` autour de `centre` (x, y) : le point `centre` ne bouge pas."""
    h, w = calque.shape[:2]
    cx, cy = centre
    m = np.float32([[facteur, 0, (1 - facteur) * cx], [0, facteur, (1 - facteur) * cy]])
    return cv2.warpAffine(calque, m, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)


def smear(calque, direction, longueur_px, pas=6):
    """Flou directionnel du calque (premultiplié RGBA) : moyenne des couleurs du personnage le long de la trajectoire.

    Seules les couleurs du personnage sont moyennées (le fond n'entre pas). L'alpha reste celui du calque :
    la traînée ne déborde pas de la silhouette.
    """
    dx, dy = float(direction[0]), float(direction[1])
    norme = max(np.hypot(dx, dy), 1e-9)
    dx, dy = dx / norme, dy / norme
    num = np.zeros(calque.shape[:2] + (3,), np.float32)
    den = np.zeros(calque.shape[:2], np.float32)
    for i in range(pas):
        s = longueur_px * i / max(pas - 1, 1)
        decale = decalage(calque, -dx * s, -dy * s)
        num += decale[..., :3]
        den += decale[..., 3]
    couleur = num / np.maximum(den, 1e-6)[..., None]
    sortie = np.empty_like(calque)
    alpha = calque[..., 3]
    sortie[..., :3] = couleur * alpha[..., None]
    sortie[..., 3] = alpha
    return sortie


def secousse(n, amplitude_px, amortissement):
    """Décalage (dx, dy) de la caméra à l'instant n (frames depuis le début) : oscillation alternée amortie."""
    decroissance = np.exp(-float(amortissement) * 0.5 * n)
    signe = -1.0 if n % 2 else 1.0
    return amplitude_px * decroissance * signe, 0.0


def decaler_image(rgb, dx, dy):
    """Décale une image RGB uint8 ; le bord découvert est blanc (fond du dessin)."""
    h, w = rgb.shape[:2]
    m = np.float32([[1, 0, dx], [0, 1, dy]])
    return cv2.warpAffine(rgb, m, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT,
                          borderValue=(255, 255, 255))


def couleurs_uniques(tableaux):
    """Couleurs RGB uint8 distinctes présentes dans une liste de tableaux (N, 3)."""
    pile = np.concatenate([t.reshape(-1, 3) for t in tableaux]).astype(np.uint8)
    return np.unique(pile, axis=0)


def ajuster_palette(couleurs, tons, graine=0):
    """`tons` couleurs choisies PARMI les couleurs réelles des dessins (k-means, puis ramenées à la couleur existante la plus proche)."""
    donnees = couleurs.astype(np.float32)
    if len(donnees) <= tons:
        return couleurs.copy()
    criteres = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 50, 0.5)
    cv2.setRNGSeed(graine)
    _, _, centres = cv2.kmeans(donnees, int(tons), None, criteres, 5, cv2.KMEANS_PP_CENTERS)
    d = ((centres[:, None, :] - donnees[None, :, :]) ** 2).sum(axis=2)
    choisies = np.unique(couleurs[d.argmin(axis=1)], axis=0)
    return choisies


def quantifier(rgb, palette):
    """Chaque pixel non blanc prend la couleur de la palette la plus proche ; le blanc reste blanc."""
    h, w = rgb.shape[:2]
    plat = rgb.reshape(-1, 3).astype(np.float32)
    p = palette.astype(np.float32)
    d = ((plat[:, None, :] - p[None, :, :]) ** 2).sum(axis=2)
    proche = palette[d.argmin(axis=1)].copy()
    blanc = plat.min(axis=1) >= SEUIL_BLANC
    proche[blanc] = 255
    return proche.reshape(h, w, 3)

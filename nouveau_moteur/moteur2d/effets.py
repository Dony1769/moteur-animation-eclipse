"""Effets de compositing. Chaque effet ne déplace ou ne mélange que des pixels existants (dessins).

- décalage et zoom : transformations affines d'un calque ;
- smear : copies décalées du calque du personnage, mélangées au calque (traînée, pixels du dessin seulement) ;
- secousse : décalage amorti de l'image entière (caméra) ;
- flash : image blanche sur les frames indiquées ;
- palette : quantification à N tons, couleurs tirées des dessins (k-means), appliquée à toutes les frames.
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
    """Traînée directionnelle : moyenne de copies décalées en arrière du mouvement, mélangée au calque (50/50)."""
    dx, dy = float(direction[0]), float(direction[1])
    norme = max(np.hypot(dx, dy), 1e-9)
    dx, dy = dx / norme, dy / norme
    acc = np.zeros_like(calque)
    for i in range(pas):
        s = longueur_px * i / max(pas - 1, 1)
        acc += decalage(calque, -dx * s, -dy * s)
    return 0.5 * calque + 0.5 * (acc / pas)


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


def ajuster_palette(images, tons, n_pixels=40000, graine=0):
    """`tons` couleurs du personnage (k-means sur les pixels non blancs de l'ensemble des frames).

    Le blanc du fond n'entre pas dans le calcul : il reste blanc, en plus des `tons` couleurs.
    """
    rng = np.random.RandomState(graine)
    pixels = np.concatenate([im.reshape(-1, 3) for im in images])
    pixels = pixels[pixels.min(axis=1) < SEUIL_BLANC]
    choix = rng.choice(len(pixels), size=min(n_pixels, len(pixels)), replace=False)
    donnees = pixels[choix].astype(np.float32)
    criteres = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 50, 0.5)
    _, _, centres = cv2.kmeans(donnees, int(tons), None, criteres, 3, cv2.KMEANS_PP_CENTERS)
    return np.clip(centres, 0, 255).astype(np.float32)


def quantifier(rgb, centres):
    """Chaque pixel non blanc prend la couleur du ton le plus proche ; le blanc reste blanc."""
    h, w = rgb.shape[:2]
    plat = rgb.reshape(-1, 3).astype(np.float32)
    d = ((plat[:, None, :] - centres[None, :, :]) ** 2).sum(axis=2)
    proche = centres[d.argmin(axis=1)]
    blanc = plat.min(axis=1) >= SEUIL_BLANC
    proche[blanc] = 255.0
    return proche.reshape(h, w, 3).astype(np.uint8)

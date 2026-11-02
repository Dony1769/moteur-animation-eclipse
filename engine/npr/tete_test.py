"""Tête de test pour le rendu NPR.

Sphère UV (rayon 1) avec une bosse gaussienne vers l'avant : c'est le « nez ».
Les masques sont analytiques en UV (fonction de la direction sur la sphère), donc
reproductibles sans fichier externe. Ce n'est pas un personnage : c'est un banc d'essai
pour vérifier les formules sur une géométrie connue.
"""
import numpy as np

from .rendu import Maillage, perspective, translation

DISTANCE = 5.0
CENTRE_VUE = np.array([0.0, 0.0, -DISTANCE], np.float32)
AVANT_VUE = np.array([0.0, 0.0, 1.0], np.float32)
FOVY = 30.0
PRES, LOIN = 0.1, 100.0


def _unitaire(v):
    v = np.asarray(v, np.float64)
    return (v / np.linalg.norm(v)).astype(np.float32)


LUMIERE_VUE = _unitaire((-0.85, 0.3, 0.45))    # latérale gauche : le terminateur traverse le visage
NEZ = _unitaire((0.0, -0.12, 1.0))             # direction du bout du nez
SOUS_NEZ = _unitaire((0.0, -0.35, 0.94))       # zone où l'ombre du nez est autorisée


def tan_fov(largeur, hauteur):
    t = np.tan(np.radians(FOVY) / 2.0)
    return (float(t * largeur / hauteur), float(t))


def direction_uv(u, v):
    """Direction unitaire sur la sphère pour les UV (u, v) ; front (+z) à u = 0.5, équateur à v = 0.5."""
    theta = v * np.pi
    phi = (u - 0.5) * 2.0 * np.pi
    s = np.sin(theta)
    return np.stack([s * np.sin(phi), np.cos(theta), s * np.cos(phi)], axis=-1)


def sphere_nez(nu=160, nv=120, bosse=0.18, sigma=0.26):
    """Sphère avec bosse. Renvoie (sommets, normales, uv, triangles)."""
    iu = np.arange(nu + 1) / nu
    iv = np.arange(nv + 1) / nv
    U, V = np.meshgrid(iu, iv)
    d = direction_uv(U, V)
    b = bosse * np.exp(-np.sum((d - NEZ) ** 2, axis=-1) / (2.0 * sigma ** 2))
    P = (d * (1.0 + b)[..., None]).reshape(-1, 3)
    uv = np.stack([U, V], axis=-1).reshape(-1, 2)

    a = (np.arange(nv)[:, None] * (nu + 1) + np.arange(nu)[None, :]).ravel()
    bb = a + 1
    c = a + (nu + 1)
    dd = c + 1
    tri = np.concatenate([np.stack([a, c, bb], 1), np.stack([bb, c, dd], 1)])

    fn = np.cross(P[tri[:, 1]] - P[tri[:, 0]], P[tri[:, 2]] - P[tri[:, 0]])
    N = np.zeros_like(P)
    for k in range(3):
        np.add.at(N, tri[:, k], fn)
    if np.mean(np.sum(N * P, axis=-1)) < 0.0:   # orientation vers l'extérieur
        N = -N
    N = N / np.maximum(np.linalg.norm(N, axis=-1, keepdims=True), 1e-12)
    return P.astype(np.float32), N.astype(np.float32), uv.astype(np.float32), tri.astype(np.uint32)


def masques(largeur, hauteur):
    """Masques (hauteur, largeur) en UV : (masque_sphere, masque_ombre).

    masque_sphere : 0 autour du bout du nez (normales réelles), 1 ailleurs.
    masque_ombre  : 1 sous le nez (ombre autorisée), 0 ailleurs.
    """
    u = (np.arange(largeur) + 0.5) / largeur
    v = (np.arange(hauteur) + 0.5) / hauteur
    U, V = np.meshgrid(u, v)
    d = direction_uv(U, V)
    m_sphere = 1.0 - np.exp(-np.sum((d - NEZ) ** 2, axis=-1) / (2.0 * 0.2 ** 2))
    m_ombre = np.exp(-np.sum((d - SOUS_NEZ) ** 2, axis=-1) / (2.0 * 0.16 ** 2))
    return m_sphere.astype(np.float32), m_ombre.astype(np.float32)


def modele_vue():
    return translation(0.0, 0.0, -DISTANCE)


def projection(largeur, hauteur):
    return perspective(FOVY, largeur / hauteur, PRES, LOIN)


def charger(ctx, programme_geo):
    """Maillage de la tête sur le GPU (programme géométrie du RenduNPR)."""
    P, N, uv, tri = sphere_nez()
    return Maillage(ctx, programme_geo, P, N, uv, tri)

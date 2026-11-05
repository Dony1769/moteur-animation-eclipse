"""Générateur de poses à angle arbitraire, à partir de l'anatomie réelle (phase 4, étape 3b).

Une articulation = (os enfant, centre, axe) lus dans le squelette extrait (étape 1) :
- centre = tête de l'os (point réel de l'articulation) ;
- axe = axe local X de l'os (matrice de repos réelle) ;
- chaîne = l'os et tous ses descendants (ils suivent la rotation, comme dans le rig).

Pour un angle θ, la transformation de la chaîne est T = [R(axe, θ) | c − R c] ; la matrice de pose d'un os k de la
chaîne est T @ B_k (B_k : matrice de repos monde), les autres os restent à leur repos (T = identité).

Vérification : pour les poses réelles de référence (L_flex90, L_genou90), l'angle et l'axe reconstruits doivent
correspondre à ceux de la pose réelle. Le signe est déterminé par cette comparaison, jamais supposé.
"""
import json

import numpy as np


def rodrigues(axe, theta):
    a = np.asarray(axe, float)
    a = a / np.linalg.norm(a)
    K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    return np.eye(3) + np.sin(theta) * K + (1 - np.cos(theta)) * (K @ K)


def chaine_descendants(json_squelette, nom_os):
    d = json.load(open(json_squelette, encoding="utf-8"))
    par = {o["nom"]: o for o in d["os"]}
    chaine, pile = [], [nom_os]
    while pile:
        n = pile.pop()
        chaine.append(n)
        pile.extend(par[n]["enfants"])
    return chaine, par


def articulation(json_squelette, nom_os):
    """(centre, axe_X, chaîne) réels pour l'os nom_os."""
    chaine, par = chaine_descendants(json_squelette, nom_os)
    o = par[nom_os]
    return np.array(o["tete"], float), np.array(o["axe_x"], float), chaine


def transformation_articulation(centre, axe, theta, sens=+1):
    R = rodrigues(axe, sens * theta)
    T = np.eye(4)
    T[:3, :3] = R
    T[:3, 3] = centre - R @ centre
    return T


def matrices_pose(B, noms, chaine, T):
    """Matrices de pose : pour les os de la chaîne, T @ B_k ; sinon B_k (repos). Retourne (J,4,4)."""
    pm = np.array(B, float).copy()
    for n in chaine:
        k = noms.index(n)
        pm[k] = T @ B[k]
    return pm


def angle_et_axe(R):
    """Angle (rad) et axe unitaire d'une rotation, sans ambiguïté de signe pour θ ∈ [0, π]."""
    c = (np.trace(R) - 1) / 2
    ang = np.arccos(np.clip(c, -1, 1))
    w = np.array([R[2, 1] - R[1, 2], R[0, 2] - R[2, 0], R[1, 0] - R[0, 1]])
    if np.linalg.norm(w) < 1e-9:
        return 0.0, np.zeros(3)
    return ang, w / np.linalg.norm(w)


if __name__ == "__main__":
    print("module poses_articulaires : importer les fonctions")

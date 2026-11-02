"""Buste proxy low-poly généré par code : tête, cou, torse, et squelette 3D à trois os.

Ce n'est PAS le personnage : aucun modèle 3D de Kaël n'existe dans le dépôt. Le proxy sert à valider
l'importeur, le skinning et le rendu NPR sur un volume réel. Ses proportions sont approximatives.

Usage : python3 engine/npr/buste.py <sortie.obj>   (écrit le fichier OBJ du proxy)
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from npr.maillage3d import Modele, Os3D, Squelette3D, calculer_normales, calculer_tangentes, uv_planaires  # noqa: E402


def ellipsoide(centre, rayons, nlat=8, nlon=12):
    """Ellipsoïde en UV-sphère : (sommets, triangles). φ = 0 correspond à +z (face du personnage)."""
    cx, cy, cz = centre
    rx, ry, rz = rayons
    s, t = [], []
    for i in range(nlat + 1):
        th = np.pi * i / nlat
        for j in range(nlon):
            ph = 2.0 * np.pi * j / nlon
            s.append((cx + rx * np.sin(th) * np.sin(ph), cy + ry * np.cos(th), cz + rz * np.sin(th) * np.cos(ph)))
    for i in range(nlat):
        for j in range(nlon):
            a = i * nlon + j
            b = i * nlon + (j + 1) % nlon
            c = (i + 1) * nlon + j
            d = (i + 1) * nlon + (j + 1) % nlon
            t.append((a, c, b))
            t.append((b, c, d))
    return np.asarray(s, np.float64), np.asarray(t, np.int64)


def cylindre(y0, y1, rayon, n=8):
    """Cylindre ouvert (sans couvercles) entre deux hauteurs : (sommets, triangles)."""
    s, t = [], []
    for y in (y0, y1):
        for j in range(n):
            ph = 2.0 * np.pi * j / n
            s.append((rayon * np.sin(ph), y, rayon * np.cos(ph)))
    for j in range(n):
        a, b = j, (j + 1) % n
        c, d = n + j, n + (j + 1) % n
        t.append((a, c, b))
        t.append((b, c, d))
    return np.asarray(s, np.float64), np.asarray(t, np.int64)


def _assembler(parties):
    """Concatène des (sommets, triangles) en un seul maillage, indices décalés."""
    sommets, triangles, decalage = [], [], 0
    for s, t in parties:
        sommets.append(s)
        triangles.append(t + decalage)
        decalage += len(s)
    return np.concatenate(sommets), np.concatenate(triangles)


def squelette_buste():
    """Trois os : torse (racine), cou, tête. Articulations au repos en unités modèle."""
    return Squelette3D([
        Os3D("torse", parent=-1, joint=(0.0, -0.05, 0.0), extremite=(0.0, 0.12, 0.0)),
        Os3D("cou", parent=0, joint=(0.0, 0.12, 0.0), extremite=(0.0, 0.22, 0.0)),
        Os3D("tete", parent=1, joint=(0.0, 0.22, 0.0), extremite=(0.0, 0.42, 0.0)),
    ])


def buste_proxy():
    """Modele du buste proxy (sans poids d'os : ils se calculent par maillage3d.poids_proximite)."""
    s, t = _assembler([
        ellipsoide((0.0, 0.31, 0.0), (0.12, 0.14, 0.13), nlat=8, nlon=12),     # tête
        cylindre(0.08, 0.26, 0.05, n=8),                                       # cou
        ellipsoide((0.0, 0.0, 0.0), (0.24, 0.20, 0.13), nlat=6, nlon=12),      # torse
    ])
    normales = calculer_normales(s, t)
    uv = uv_planaires(s)
    tangentes = calculer_tangentes(s, uv, t, normales)
    return Modele(sommets=s, normales=normales, uv=uv, triangles=t.astype(np.uint32),
                  tangentes=tangentes, uv_origine="projection", origine="buste proxy (généré)")


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 1
    from npr.maillage3d import ecrire_obj
    m = buste_proxy()
    ecrire_obj(m, argv[1])
    print(f"écrit : {argv[1]} ({len(m.sommets)} sommets, {len(m.triangles)} triangles)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

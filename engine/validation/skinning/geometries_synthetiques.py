"""Géométries synthétiques à résultat connu (phase 4, priorité 1). Aucune dépendance à Blender.

cube_subdivise(n, cote, centre) : cube fermé, chaque face en n x n quadrilatères, orientation sortante (comme
test_skinning.cube). Renvoie (points, boucle, tot) au même format que les données du banc.
"""
import numpy as np


def cube_subdivise(n=4, cote=1.0, centre=(0.0, 0.0, 0.0)):
    s = cote / 2.0
    c = np.array([[-s, -s, -s], [s, -s, -s], [s, s, -s], [-s, s, -s],
                  [-s, -s, s], [s, -s, s], [s, s, s], [-s, s, s]], float)
    faces = [[0, 3, 2, 1], [4, 5, 6, 7], [0, 1, 5, 4], [2, 3, 7, 6], [1, 2, 6, 5], [0, 4, 7, 3]]
    index = {}
    pts = []
    polys = []
    for f in faces:
        c0, c1, c2, c3 = c[f[0]], c[f[1]], c[f[2]], c[f[3]]
        def sommet(i, j):
            u, v = i / n, j / n
            P = (1 - u) * (1 - v) * c0 + u * (1 - v) * c1 + u * v * c2 + (1 - u) * v * c3
            cle = tuple(np.round(P * 1e9).astype(np.int64))
            if cle not in index:
                index[cle] = len(pts)
                pts.append(P)
            return index[cle]
        for i in range(n):
            for j in range(n):
                polys.append([sommet(i, j), sommet(i + 1, j), sommet(i + 1, j + 1), sommet(i, j + 1)])
    p = np.array(pts) + np.array(centre, float)
    boucle = np.array([v for q in polys for v in q], dtype=np.int64)
    tot = np.array([4] * len(polys), dtype=np.int64)
    return p, boucle, tot


def aretes_de(boucle, tot, N):
    debut = np.concatenate([[0], np.cumsum(tot)[:-1]]).astype(np.int64)
    poly = np.repeat(np.arange(len(tot)), tot)
    local = np.arange(len(boucle)) - debut[poly]
    nxt = debut[poly] + (local + 1) % tot[poly]
    lo = np.minimum(boucle, boucle[nxt]).astype(np.int64)
    hi = np.maximum(boucle, boucle[nxt]).astype(np.int64)
    code = np.unique(lo * N + hi)
    return np.stack([code // N, code % N], axis=1)


if __name__ == "__main__":
    p, b, t = cube_subdivise(4)
    print("sommets", len(p), "polygones", len(t), "arêtes", len(aretes_de(b, t, len(p))))

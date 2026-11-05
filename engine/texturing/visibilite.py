"""Visibilité des faces par tampon de profondeur (z-buffer) pour une vue orthographique.

Méthode (tampon de profondeur, courante en rendu, vue dans les sources de recherche d'entrée 138) : on projette les
sommets sur le plan de la vue, on rasterise chaque triangle en gardant la profondeur la plus proche de la caméra à chaque
pixel. Une face est visible si elle est tournée vers la caméra (normale · c > 0) et si la profondeur de son centroïde égale celle
du tampon à son pixel (à une tolérance près). La condition d'orientation a été ajoutée après un échec de test (entrée 139).

Réimplémentation maison, sans code tiers. Résolution par défaut 256 px ; tolérance en unités du maillage (dm).
"""
import numpy as np

# repère de projection par vue : (axe_u, axe_v, sens_profondeur) pour une caméra sur l'axe c
def _base_vue(c):
    c = np.asarray(c, dtype=float)
    k = int(np.argmax(np.abs(c)))
    axes = [i for i in range(3) if i != k]
    return axes[0], axes[1], k, float(np.sign(c[k]))


def visibilite(V, F, c, res=256, tol=0.05):
    """Retourne un booléen (F,) : vrai si la face est visible depuis la direction c (vers la caméra)."""
    iu, iv, ik, s = _base_vue(c)
    prof = s * V[:, ik]                          # plus grand = plus proche de la caméra
    u = V[:, iu]; v = V[:, iv]
    umin, umax = u.min(), u.max(); vmin, vmax = v.min(), v.max()
    su = (res - 1) / max(umax - umin, 1e-9); sv = (res - 1) / max(vmax - vmin, 1e-9)
    pu = (u - umin) * su; pv = (v - vmin) * sv
    zbuf = np.full((res, res), -np.inf)
    for f in F:
        a, b, cc = f[0], f[1], f[2]
        x0, y0, z0 = pu[a], pv[a], prof[a]
        x1, y1, z1 = pu[b], pv[b], prof[b]
        x2, y2, z2 = pu[cc], pv[cc], prof[cc]
        xmin = int(max(np.floor(min(x0, x1, x2)), 0)); xmax = int(min(np.ceil(max(x0, x1, x2)), res - 1))
        ymin = int(max(np.floor(min(y0, y1, y2)), 0)); ymax = int(min(np.ceil(max(y0, y1, y2)), res - 1))
        if xmin > xmax or ymin > ymax:
            continue
        den = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
        if abs(den) < 1e-12:
            continue
        gx, gy = np.meshgrid(np.arange(xmin, xmax + 1) + 0.5, np.arange(ymin, ymax + 1) + 0.5)
        l0 = ((y1 - y2) * (gx - x2) + (x2 - x1) * (gy - y2)) / den
        l1 = ((y2 - y0) * (gx - x2) + (x0 - x2) * (gy - y2)) / den
        l2 = 1 - l0 - l1
        dedans = (l0 >= -1e-9) & (l1 >= -1e-9) & (l2 >= -1e-9)
        if not dedans.any():
            continue
        z = l0 * z0 + l1 * z1 + l2 * z2
        sub = zbuf[ymin:ymax + 1, xmin:xmax + 1]
        sub[dedans] = np.maximum(sub[dedans], z[dedans])
    # visibilité : profondeur du centroïde comparée au tampon à son pixel
    cen = (V[F[:, 0]] + V[F[:, 1]] + V[F[:, 2]]) / 3.0
    pc = s * cen[:, ik]
    xi = np.clip(np.floor((u[F].mean(axis=1) - umin) * su).astype(int), 0, res - 1)
    yi = np.clip(np.floor((v[F].mean(axis=1) - vmin) * sv).astype(int), 0, res - 1)
    # une face doit aussi être tournée vers la caméra : normale · c > 0 (une face dos à la caméra n'est jamais visible)
    e1 = V[F[:, 1]] - V[F[:, 0]]; e2 = V[F[:, 2]] - V[F[:, 0]]
    n = np.cross(e1, e2)
    tournee = (n @ np.asarray(c, dtype=float)) > 0
    return tournee & (pc >= zbuf[yi, xi] - tol)


def visibilite_rayon(V, F, c, eps=1e-9):
    """Visibilité exacte : pour chaque face tournée vers c, lance un rayon vers la caméra et teste toutes les faces.

    Plus lent (≈ 1 ms par face, vectorisé sur les triangles) mais sans erreur de résolution. Utilisé pour le texturage ;
    le tampon de profondeur reste un aperçu rapide. Une face est visible si aucune autre face n'est coupée sur le rayon.
    Entrée 139 : le tampon à 1024 px n'atteint que 90 % d'accord avec ce calcul exact sur le corps.
    """
    d = np.asarray(c, dtype=float)
    d = d / np.linalg.norm(d)
    N = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])
    cen = V[F].mean(axis=1)
    A = V[F[:, 0]]; B = V[F[:, 1]]; C = V[F[:, 2]]
    BA = B - A; CA = C - A
    vis_out = np.zeros(len(F), dtype=bool)
    tournee = (N @ d) > 0
    p = np.cross(d, CA)                       # (F,3) : d × CA, indépendant du point
    det = np.einsum("ij,ij->i", BA, p)
    ok = np.abs(det) > eps
    inv = np.where(ok, 1.0 / np.where(ok, det, 1.0), 0.0)
    for i in np.where(tournee)[0]:
        o = cen[i] + 1e-5 * d
        tv = o - A                             # (F,3)
        uu = np.einsum("ij,ij->i", tv, p) * inv
        q = np.cross(tv, BA)
        vv = (q @ d) * inv
        t = np.einsum("ij,ij->i", CA, q) * inv
        hit = ok & (uu >= 0) & (vv >= 0) & (uu + vv <= 1) & (t > 1e-6)
        hit[i] = False
        vis_out[i] = not hit.any()
    return vis_out

"""Mesures géométriques communes à toutes les méthodes de skinning (phase 4). Mètres monde.

Principes (pour que les méthodes soient comparables) :
  - une même fonction mesure chaque méthode, sur le même maillage et les mêmes polygones ;
  - les retournements sont calculés sur les POLYGONES entiers (normale de Newell), sans triangulation préalable ;
  - le volume passe par une triangulation en éventail, identique pour toutes les méthodes ;
  - les seuils (1,15 ; 0,85 ; 1,5) ne servent qu'à compter, jamais à valider une méthode.
Non mesuré ici : intersections entre parties du corps (voir docs/rapports/skinning/limites.md).
"""
import numpy as np


def _debuts(tot):
    return np.concatenate([[0], np.cumsum(tot)[:-1]]).astype(np.int64)


def aretes(boucle, tot, N):
    """Arêtes uniques (E,2) à partir des boucles de polygones."""
    debut = _debuts(tot)
    poly = np.repeat(np.arange(len(tot)), tot)
    local = np.arange(len(boucle)) - debut[poly]
    nxt = debut[poly] + (local + 1) % tot[poly]
    a = boucle.astype(np.int64)
    b = boucle[nxt].astype(np.int64)
    lo, hi = np.minimum(a, b), np.maximum(a, b)
    code = np.unique(lo * N + hi)
    return np.stack([code // N, code % N], axis=1)


def _newell(pos, boucle, tot, nxt_arr):
    cr = np.cross(pos[boucle], pos[boucle[nxt_arr]])
    return np.add.reduceat(cr, _debuts(tot), axis=0)


def masque_retournes(pos, rest, boucle, tot, Mv):
    """Polygones retournés : la normale posée est opposée à la normale de repos tournée par le repère rigide local
    (moyenne de Mv sur les sommets du polygone). Sans Mv, compare au repos brut (méthode erronée, entrée 147)."""
    debut = _debuts(tot)
    poly = np.repeat(np.arange(len(tot)), tot)
    local = np.arange(len(boucle)) - debut[poly]
    nxt = debut[poly] + (local + 1) % tot[poly]
    n_pos = _newell(pos, boucle, tot, nxt)
    n_rest = _newell(rest, boucle, tot, nxt)
    if Mv is None:
        ref = n_rest
    else:
        Mp = np.add.reduceat(Mv[boucle], debut, axis=0) / tot[:, None, None]
        ref = np.einsum("pab,pb->pa", Mp, n_rest)
    ok = np.linalg.norm(ref, axis=1) > 1e-12
    return ok & (np.einsum("nc,nc->n", n_pos, ref) < 0), n_pos


def mesurer(pos, rest, boucle, tot, aretes_arr, Mv=None, seuils=(1.15, 0.85, 1.5)):
    """Retourne un dictionnaire de mesures pour une géométrie posée `pos` par rapport au repos `rest`.
    Mv : repère rigide local par sommet (methodes.repere_rigide), commun à toutes les méthodes."""
    N = len(rest)
    a, b = aretes_arr[:, 0], aretes_arr[:, 1]
    l_rest = np.linalg.norm(rest[a] - rest[b], axis=1)
    l_pos = np.linalg.norm(pos[a] - pos[b], axis=1)
    ok = l_rest > 1e-9
    ratio = l_pos[ok] / l_rest[ok]
    tri = np.sort(ratio)
    n = len(tri)
    # étirement / compression par arête
    res = {
        "etirement_max": float(tri[-1]),
        "etirement_p99": float(tri[int(0.99 * (n - 1))]),
        "part_aretes_etirees": float(np.mean(ratio > seuils[0])),
        "part_aretes_comprimees": float(np.mean(ratio < seuils[1])),
        "aretes": int(n),
    }
    # sommets aberrants : sommet dont une arête incidente dépasse seuils[2]
    vmax = np.zeros(N)
    rr = np.zeros(len(aretes_arr))
    rr[ok] = l_pos[ok] / l_rest[ok]
    np.maximum.at(vmax, a, rr)
    np.maximum.at(vmax, b, rr)
    res["sommets_aberrants"] = int(np.sum(vmax > seuils[2]))
    res["sommets_aberrants_part"] = float(res["sommets_aberrants"] / N)
    # retournements : normale de Newell de chaque polygone (sans triangulation)
    debut = _debuts(tot)
    poly = np.repeat(np.arange(len(tot)), tot)
    local = np.arange(len(boucle)) - debut[poly]
    nxt = debut[poly] + (local + 1) % tot[poly]
    n_rest = _newell(rest, boucle, tot, nxt)
    n_pos = _newell(pos, boucle, tot, nxt)
    nr = np.linalg.norm(n_rest, axis=1)
    npz = np.linalg.norm(n_pos, axis=1)
    masque, _ = masque_retournes(pos, rest, boucle, tot, Mv)
    res["polygones"] = int(len(tot))
    res["polygones_retournes"] = int(np.sum(masque))
    res["polygones_retournes_brut"] = int(np.sum((nr > 1e-12) & (np.einsum("nc,nc->n", n_pos, n_rest) < 0)))
    res["polygones_degeneres"] = int(np.sum((nr > 1e-12) & (npz < 1e-12)))
    # volume signé (divergence), triangulation en éventail identique pour toutes les méthodes
    res["volume_repos"] = float(_volume(rest, boucle, tot))
    res["volume_pose"] = float(_volume(pos, boucle, tot))
    res["variation_volume_relative"] = float((res["volume_pose"] - res["volume_repos"]) / abs(res["volume_repos"]))
    # déplacements
    dep = np.linalg.norm(pos - rest, axis=1)
    res["deplacement_max_m"] = float(dep.max())
    res["deplacement_p99_m"] = float(np.percentile(dep, 99))
    return res


def _volume(p, boucle, tot):
    debut = _debuts(tot)
    v = 0.0
    maxt = int(tot.max())
    for k in range(1, maxt - 1):
        m = tot >= k + 2
        i0 = debut[m]
        p0 = p[boucle[i0]]
        p1 = p[boucle[i0 + k]]
        p2 = p[boucle[i0 + k + 1]]
        v += float(np.einsum("ij,ij->i", p0, np.cross(p1, p2)).sum()) / 6.0
    return v

"""Métriques anatomiques locales (phase 4, priorité 1). Chaque fonction a un test synthétique (test_metriques_synthetiques.py).

  defauts(...)          : maximum local, p99, nombre d'arêtes et de sommets au-delà de plusieurs seuils, localisation,
                          surface affectée (cm²), sommets les plus touchés. Le p99 seul ne valide jamais une déformation.
  separer_rigide(...)   : ajustement rigide optimal (Kabsch) ; résidu = déformation locale. Un mouvement rigide donne 0.
  volume_local(...)     : variation de volume par polygone (tétraèdres sur l'origine), agrégée par zone.
  intersections(...)    : sommets de la zone B à l'intérieur de la surface de la zone A, profondeur et localisation.
Unités : mètres. Les seuils sont des seuils de comptage, jamais des critères de validation.
"""
import numpy as np
from scipy.spatial import cKDTree

from geometries_synthetiques import aretes_de  # noqa: F401  (réutilisé par les tests)


def _debuts(tot):
    return np.concatenate([[0], np.cumsum(tot)[:-1]]).astype(np.int64)


def _polygone_de_sommet(tot):
    return np.repeat(np.arange(len(tot)), tot)


def aires_polygones(p, boucle, tot):
    """Aire (m²) de chaque polygone (normale de Newell)."""
    debut = _debuts(tot)
    poly = _polygone_de_sommet(tot)
    local = np.arange(len(boucle)) - debut[poly]
    nxt = debut[poly] + (local + 1) % tot[poly]
    cr = np.cross(p[boucle], p[boucle[nxt]])
    return 0.5 * np.linalg.norm(np.add.reduceat(cr, debut, axis=0), axis=1)


def defauts(pos, rest, boucle, tot, A, seuils_etirement=(1.1, 1.25, 1.5), seuils_compression=(0.9, 0.8),
            longueur_min=0.005, nb_pires=10):
    """Défauts locaux. Arêtes de repos < longueur_min ignorées (entrée 151)."""
    a, b = A[:, 0], A[:, 1]
    l0 = np.linalg.norm(rest[a] - rest[b], axis=1)
    l1 = np.linalg.norm(pos[a] - pos[b], axis=1)
    ok = l0 >= longueur_min
    r = np.where(ok, l1 / np.maximum(l0, 1e-12), np.nan)
    rv = r[ok]
    res = {
        "aretes_mesurees": int(ok.sum()),
        "etirement_max": float(np.nanmax(r)),
        "etirement_p99": float(np.nanpercentile(r, 99)),
        "compression_min": float(np.nanmin(r)),
        "compression_p01": float(np.nanpercentile(r, 1)),
    }
    for s in seuils_etirement:
        res[f"aretes_etirees_>{s}"] = int(np.sum(rv > s))
    for s in seuils_compression:
        res[f"aretes_comprimees_<{s}"] = int(np.sum(rv < s))
    # sommets : rapport maximal de leurs arêtes incidentes
    N = len(rest)
    vmax = np.full(N, -np.inf)
    vmin = np.full(N, np.inf)
    rr = np.where(ok, r, -np.inf)
    rr2 = np.where(ok, r, np.inf)
    np.maximum.at(vmax, a, rr)
    np.maximum.at(vmax, b, rr)
    np.minimum.at(vmin, a, rr2)
    np.minimum.at(vmin, b, rr2)
    vmax_f = vmax[np.isfinite(vmax)]
    vmin_f = vmin[np.isfinite(vmin)]
    for s in seuils_etirement:
        res[f"sommets_etires_>{s}"] = int(np.sum(vmax_f > s))
    for s in seuils_compression:
        res[f"sommets_comprimes_<{s}"] = int(np.sum(vmin_f < s))
    # localisation : arêtes au-delà du premier seuil d'étirement, et pires sommets
    s1 = seuils_etirement[0]
    idx_ok = np.where(ok)[0]
    masque = np.where(ok, r, 0) > s1
    if masque.any():
        milieux = 0.5 * (pos[a[masque]] + pos[b[masque]])
        res["localisation_etirement_m"] = milieux.mean(axis=0).tolist()
        res["etendue_etirement_m"] = (milieux.max(axis=0) - milieux.min(axis=0)).tolist()
    else:
        res["localisation_etirement_m"] = None
        res["etendue_etirement_m"] = [0.0, 0.0, 0.0]
    sc = seuils_compression[0]
    masque_c = np.where(ok, r, 1.0) < sc
    if masque_c.any():
        mil_c = 0.5 * (pos[a[masque_c]] + pos[b[masque_c]])
        res["localisation_compression_m"] = mil_c.mean(axis=0).tolist()
        res["etendue_compression_m"] = (mil_c.max(axis=0) - mil_c.min(axis=0)).tolist()
    else:
        res["localisation_compression_m"] = None
        res["etendue_compression_m"] = [0.0, 0.0, 0.0]
    # surface : polygones touchant une arête au-delà du premier seuil
    poly_de_arete = {}
    debut = _debuts(tot)
    poly = _polygone_de_sommet(tot)
    aires = aires_polygones(rest, boucle, tot)
    marque = np.zeros(len(tot), dtype=bool)
    arete_marquee = set(map(tuple, A[masque].tolist()))
    for p_i in range(len(tot)):
        vs = boucle[debut[p_i]:debut[p_i] + tot[p_i]]
        cotes = [tuple(sorted((int(vs[k]), int(vs[(k + 1) % len(vs)])))) for k in range(len(vs))]
        if any(c in arete_marquee for c in cotes):
            marque[p_i] = True
    res["surface_affectee_cm2"] = float(aires[marque].sum() * 1e4)
    res["polygones_affectes"] = int(marque.sum())
    # sommets les plus touchés
    # sommets les plus touchés : nombre d'arêtes étirées incidentes (premier seuil), puis rapport maximal
    nb_etirees = np.zeros(N, dtype=np.int64)
    np.add.at(nb_etirees, a[masque], 1)
    np.add.at(nb_etirees, b[masque], 1)
    if len(vmax_f):
        cle_tri = np.lexsort((-np.where(np.isfinite(vmax), vmax, -np.inf), -nb_etirees))
        ordre = [int(v) for v in cle_tri if np.isfinite(vmax[v])][:nb_pires]
        res["pires_sommets"] = [{"sommet": int(v), "aretes_etirees": int(nb_etirees[v]), "etirement": float(vmax[v]),
                                 "xyz_m": pos[v].round(4).tolist()} for v in ordre]
    res["_vertex_etirement"] = np.where(np.isfinite(vmax), vmax, np.nan)
    res["_vertex_compression"] = np.where(np.isfinite(vmin), vmin, np.nan)
    return res


def separer_rigide(pos, rest, poids=None):
    """Ajustement rigide optimal (Kabsch) entre le repos et la pose. Retourne (R, t, residu_par_sommet).
    residu = déformation locale ; un mouvement purement rigide donne un résidu nul."""
    if poids is None:
        poids = np.ones(len(rest))
    w = poids / poids.sum()
    cr = (w[:, None] * rest).sum(0)
    cp = (w[:, None] * pos).sum(0)
    H = ((rest - cr) * w[:, None]).T @ (pos - cp)
    U, _, Vt = np.linalg.svd(H)
    d = np.sign(np.linalg.det(Vt.T @ U.T))
    D = np.diag([1, 1, d])
    R = Vt.T @ D @ U.T
    t = cp - R @ cr
    residu = np.linalg.norm(pos - (rest @ R.T + t), axis=1)
    return R, t, residu


def residu_os_dominant(pos, rest, Wi, Ww, T):
    """Déformation locale par rapport au mouvement rigide de l'os dominant de chaque sommet.
    T : (J,4,4) transformations d'os (pose monde @ inverse(repos monde)). Pour un sommet dont l'os dominant
    se déplace rigidement, le résidu est nul ; un mélange de deux os (LBS) donne un résidu égal à l'écart au
    mouvement rigide de l'os dominant. Retourne le résidu par sommet (m)."""
    dom = np.take_along_axis(Wi, np.argmax(np.where(Wi >= 0, Ww, -1.0), axis=1)[:, None], axis=1)[:, 0]
    dom = np.where(dom >= 0, dom, 0)
    Rd = T[dom, :3, :3]
    td = T[dom, :3, 3]
    rigide = np.einsum("nab,nb->na", Rd, rest) + td
    return np.linalg.norm(pos - rigide, axis=1)


def volume_local(pos, rest, boucle, tot, zone_polygone=None):
    """Variation de volume relative : contributions signées des tétraèdres (origine = centre du repos).
    zone_polygone : masque booléen de polygones ; renvoie la variation relative de la zone et le total."""
    origine = rest.mean(0)
    debut = _debuts(tot)
    poly = _polygone_de_sommet(tot)
    local = np.arange(len(boucle)) - debut[poly]

    def contributions(p):
        out = np.zeros(len(tot))
        maxt = int(tot.max())
        for k in range(1, maxt - 1):
            m = tot >= k + 2
            i0 = debut[m]
            p0 = p[boucle[i0]] - origine
            p1 = p[boucle[i0 + k]] - origine
            p2 = p[boucle[i0 + k + 1]] - origine
            v = np.einsum("ij,ij->i", p0, np.cross(p1, p2)) / 6.0
            out[np.where(m)[0]] += v
        return out

    cr = contributions(rest)
    cp = contributions(pos)
    total = cp.sum() / cr.sum() - 1.0
    res = {"variation_volume_total": float(total)}
    if zone_polygone is not None:
        z = zone_polygone
        res["variation_volume_zone"] = float(cp[z].sum() / cr[z].sum() - 1.0)
    res["_contrib_rest"] = cr
    res["_contrib_pos"] = cp
    return res


def _distance_point_segment(P, A, B):
    AB = B - A
    t = np.clip(np.einsum("...j,...j->...", P - A, AB) / np.maximum(np.einsum("...j,...j->...", AB, AB), 1e-18), 0, 1)
    proj = A + t[..., None] * AB
    return np.linalg.norm(P - proj, axis=-1)


def _distance_points_triangles(P, T0, T1, T2):
    """Distance minimale de chaque point de P (K,3) à l'ensemble des triangles (M,3). Plan si la projection tombe dans
    le triangle, sinon arêtes (approximation exacte pour les faces planes, bornée sinon)."""
    n = np.cross(T1 - T0, T2 - T0)
    nn = np.linalg.norm(n, axis=1, keepdims=True)
    n = n / np.maximum(nn, 1e-18)
    dplan = np.einsum("kj,mj->km", P, n) - np.einsum("mj,mj->m", T0, n)[None, :]
    proj = P[:, None, :] - dplan[..., None] * n[None, :, :]
    # coordonnées barycentriques de la projection
    v0 = T1 - T0
    v1 = T2 - T0
    v2 = proj - T0[None]
    d00 = np.einsum("mj,mj->m", v0, v0)
    d01 = np.einsum("mj,mj->m", v0, v1)
    d11 = np.einsum("mj,mj->m", v1, v1)
    d20 = np.einsum("kmj,mj->km", v2, v0)
    d21 = np.einsum("kmj,mj->km", v2, v1)
    den = np.maximum(d00 * d11 - d01 * d01, 1e-18)
    bv = (d11[None] * d20 - d01[None] * d21) / den[None]
    bw = (d00[None] * d21 - d01[None] * d20) / den[None]
    dedans = (bv >= 0) & (bw >= 0) & (bv + bw <= 1)
    d_plan = np.abs(dplan)
    # distance aux trois arêtes
    d_e = np.minimum(np.minimum(
        _distance_point_segment(P[:, None, :], T0[None], T1[None]),
        _distance_point_segment(P[:, None, :], T1[None], T2[None])),
        _distance_point_segment(P[:, None, :], T2[None], T0[None]))
    d = np.where(dedans, d_plan, d_e)
    return d.min(axis=1)


def _triangles_fan(boucle, tot, pos):
    debut = _debuts(tot)
    tris = []
    for p_i in range(len(tot)):
        vs = boucle[debut[p_i]:debut[p_i] + tot[p_i]]
        for k in range(1, len(vs) - 1):
            tris.append((vs[0], vs[k], vs[k + 1]))
    tris = np.array(tris, dtype=np.int64)
    return tris


def _dans_surface(P, T0, T1, T2):
    """Parité des intersections d'un rayon (direction irrationnelle) avec les triangles : vrai si P est à l'intérieur."""
    d = np.array([0.5773502691, 0.5773502691 * 1.0000003, 0.5773502691 * 0.9999991])
    d = d / np.linalg.norm(d)
    e1 = T1 - T0
    e2 = T2 - T0
    pvec = np.cross(np.broadcast_to(d, e2.shape), e2)
    det = np.einsum("mj,mj->m", e1, pvec)
    ok = np.abs(det) > 1e-14
    inv = np.where(ok, 1.0 / np.where(ok, det, 1.0), 0.0)
    res = np.zeros(len(P), dtype=bool)
    for i, p in enumerate(P):
        tvec = p[None] - T0
        u = np.einsum("mj,mj->m", tvec, pvec) * inv
        q = np.cross(tvec, e1)
        v = np.einsum("j,mj->m", d, q) * inv
        t = np.einsum("mj,mj->m", e2, q) * inv
        hit = ok & (u >= 0) & (v >= 0) & (u + v <= 1) & (t > 1e-12)
        res[i] = (np.count_nonzero(hit) % 2) == 1
    return res


def intersections(pos, boucle, tot, masque_a, masque_b):
    """Sommets de la zone B situés à l'intérieur de la surface fermée de la zone A.
    Surface de A : triangles dont les trois sommets sont dans A. Profondeur : distance du sommet à cette surface.
    Limite : seuls les sommets de B sont testés ; une interpénétration sans sommet de B à l'intérieur de A passe inaperçue."""
    tris = _triangles_fan(boucle, tot, pos)
    dans_a = masque_a[tris].all(axis=1)
    T = tris[dans_a]
    idx_b = np.where(masque_b)[0]
    P = pos[idx_b]
    if len(T) == 0 or len(P) == 0:
        return {"sommets_penetrants": 0, "profondeur_max_m": 0.0, "localisation_m": None}
    T0, T1, T2 = pos[T[:, 0]], pos[T[:, 1]], pos[T[:, 2]]
    inside = _dans_surface(P, T0, T1, T2)
    if not inside.any():
        return {"sommets_penetrants": 0, "profondeur_max_m": 0.0, "localisation_m": None}
    Q = P[inside]
    prof = _distance_points_triangles(Q, T0, T1, T2)
    return {
        "sommets_penetrants": int(inside.sum()),
        "profondeur_max_m": float(prof.max()),
        "profondeur_moy_m": float(prof.mean()),
        "localisation_m": Q.mean(axis=0).tolist(),
        "etendue_m": (Q.max(axis=0) - Q.min(axis=0)).tolist(),
        "indices_b": idx_b[inside].tolist(),
    }

"""Propagation de SQ sur géométries synthétiques à poids et transformations contrôlés.

Géométries : grilles planes de triangles (taille uniforme, ou mélange de deux tailles), dans [-1, 1]².
Deux os tournent autour de l'axe y passant par l'origine : os G (θ_G) et os D (θ_D). Le poids G varie comme :
  - « un_os »      : w_G = 1 partout (sanité : rigide) ;
  - « uniforme »   : w_G = 0,5 partout ;
  - « progressif » : w_G = clip((x + W/2)/W, 0, 1), W = 0,5 ;
  - « brutal »     : w_G = 1 si x > 0, sinon 0.
Somme des poids = 1 ; LBS et SQ utilisent exactement les mêmes poids, transformations, arêtes et λ.
SQ : même système que ARAP.solve_fixe (réimplémenté dans DEC.solve_R, écart 0 vérifié).

Mesures : déplacement LBS, déplacement SQ, écart SQ − LBS, étirement des arêtes, retournements, aire et anisotropie
des triangles, moyenne du déplacement (conservation), profil de propagation par distance de graphe à l'interface
(sommets dont un voisin a des poids différents). Le volume n'est pas mesuré : la surface est ouverte.
Aucun critère n'est modifié.
"""
import importlib.util
import json
import os
from collections import deque

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
SORTIE = os.path.join(RACINE, "docs", "rapports", "skinning", "propagation_synthetique")


def charger(nom):
    spec = importlib.util.spec_from_file_location(nom, os.path.join(HERE, nom + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


DEC = charger("investigation_decomposition")
INV = DEC.INV
ARAP = INV.ARAP


def rot_y(th):
    c, s = np.cos(th), np.sin(th)
    return np.array([[c, 0.0, s], [0.0, 1.0, 0.0], [-s, 0.0, c]])


def xs_uniforme(n):
    return np.linspace(-1, 1, n)


def xs_melange():
    """Mélange de deux tailles : grosses mailles sur les bords, mailles 4× plus fines au centre."""
    return np.concatenate([np.linspace(-1, -0.5, 6)[:-1], np.linspace(-0.5, 0.5, 21)[:-1], np.linspace(0.5, 1, 6)])


def grille(xs, ys):
    nx, ny = len(xs), len(ys)
    X, Y = np.meshgrid(xs, ys)
    rest = np.column_stack([X.ravel(), Y.ravel(), np.zeros(nx * ny)])
    idx = np.arange(nx * ny).reshape(ny, nx)
    tris = []
    for j in range(ny - 1):
        for i in range(nx - 1):
            p00, p10, p01, p11 = idx[j, i], idx[j, i + 1], idx[j + 1, i], idx[j + 1, i + 1]
            tris.append((p00, p10, p11))
            tris.append((p00, p11, p01))
    tris = np.array(tris)
    E = set()
    for t in tris:
        for k in range(3):
            E.add(tuple(sorted((int(t[k]), int(t[(k + 1) % 3])))))
    return rest, tris, np.array(sorted(E))


def construire(xs, ys, wkind, thG, thD, W=0.5):
    rest, tris, A = grille(xs, ys)
    x = rest[:, 0]
    if wkind == "un_os":
        wG = np.ones(len(x))
    elif wkind == "uniforme":
        wG = np.full(len(x), 0.5)
    elif wkind == "progressif":
        wG = np.clip((x + W / 2) / W, 0, 1)
    elif wkind == "brutal":
        wG = (x > 0).astype(float)
    else:
        raise ValueError(wkind)
    RG, RD = rot_y(thG), rot_y(thD)
    lbs = wG[:, None] * (rest @ RG.T) + (1 - wG)[:, None] * (rest @ RD.T)
    Mv = wG[:, None, None] * RG + (1 - wG)[:, None, None] * RD
    Rsq = DEC.polaire_gen(Mv)
    return rest, tris, A, wG, lbs, Mv, Rsq


def bfs(N, A, sources):
    adj = [[] for _ in range(N)]
    for u, v in A:
        adj[u].append(v)
        adj[v].append(u)
    dist = np.full(N, -1)
    q = deque(int(s) for s in sources)
    for s in sources:
        dist[s] = 0
    while q:
        u = q.popleft()
        for v in adj[u]:
            if dist[v] < 0:
                dist[v] = dist[u] + 1
                q.append(v)
    return dist


def interface(N, A, cle):
    """Sommets dont au moins un voisin a une valeur de `cle` différente."""
    a, c = A[:, 0], A[:, 1]
    diff = np.abs(cle[a] - cle[c]) > 1e-9
    s = np.zeros(N, bool)
    s[a[diff]] = True
    s[c[diff]] = True
    return np.where(s)[0]


def profil(N, A, cle, PG, PD, disp, h, dmax=7):
    src = interface(N, A, cle)
    dist = bfs(N, A, src) if len(src) else np.full(N, -1)
    out = {}
    for nom, P in (("pur_G", PG), ("pur_D", PD)):
        out[nom] = {}
        for d in range(dmax):
            m = P & (dist == d)
            if m.any():
                out[nom][str(d)] = {"n": int(m.sum()), "deplacement_SQ_LBS_sur_h_mediane": float(np.median(disp[m] / h))}
    return out


def stats(rest, lbs, sq, tris, A, Mv):
    a, c = A[:, 0], A[:, 1]
    lr = np.linalg.norm(rest[a] - rest[c], axis=1)
    out = {}
    for nom, p in (("LBS", lbs), ("SQ", sq)):
        r = np.linalg.norm(p[a] - p[c], axis=1) / lr
        out[nom] = {"etirement_max": float(r.max()), "etirement_p99": float(np.quantile(r, 0.99)),
                    "compression_min": float(r.min())}
    # Retournement : la normale déformée est opposée à la normale au repos tournée par le repère rigide local
    # (polaire de la moyenne de Mv sur le triangle). Comparer au seul repos compterait une rotation rigide de
    # 90° ou plus comme un retournement (faux positif, corrigé ici : voir entrée 193).
    n0 = np.cross(rest[tris[:, 1]] - rest[tris[:, 0]], rest[tris[:, 2]] - rest[tris[:, 0]])
    Rt = DEC.polaire_gen(Mv[tris].mean(1))
    nref = np.einsum("tij,tj->ti", Rt, n0)
    for nom, p in (("LBS", lbs), ("SQ", sq)):
        n1 = np.cross(p[tris[:, 1]] - p[tris[:, 0]], p[tris[:, 2]] - p[tris[:, 0]])
        out[nom]["retournements"] = int((np.einsum("ti,ti->t", nref, n1) < 0).sum())
    ar_L, ar_S, an_S = [], [], []
    for t in tris:
        m = DEC.tri_mesure(t, rest, lbs, sq, Mv)
        ar_L.append(m["LBS"]["aire_ratio"])
        ar_S.append(m["SQ"]["aire_ratio"])
        an_S.append(m["SQ"]["anisotropie"])
    ar_L, ar_S, an_S = np.array(ar_L), np.array(ar_S), np.array(an_S)
    out["triangles"] = {"aire_min_LBS": float(ar_L.min()), "aire_min_SQ": float(ar_S.min()),
                        "aire_max_SQ": float(ar_S.max()), "anisotropie_mediane_SQ": float(np.median(an_S)),
                        "ecart_aire_SQ_LBS_max": float(np.abs(ar_S - ar_L).max())}
    return out


def evaluer(nom, xs, ys, wkind, thG, thD, lam=0.1, W=0.5):
    rest, tris, A, wG, lbs, Mv, Rsq = construire(xs, ys, wkind, thG, thD, W)
    N = len(rest)
    sq = ARAP.solve_fixe(lbs, rest, A, Rsq, lam)
    lr = np.linalg.norm(rest[A[:, 0]] - rest[A[:, 1]], axis=1)
    h = float(np.mean(lr))
    disp = np.linalg.norm(sq - lbs, axis=1)
    PG = wG >= 1 - 1e-12
    PD = wG <= 1e-12
    cle = np.round(wG, 9)
    res = {"nom": nom, "N": N, "nb_aretes": len(A), "h_moyen": h, "lambda": lam,
           "wkind": wkind, "thG_deg": float(np.degrees(thG)), "thD_deg": float(np.degrees(thD)),
           "ecart_max_SQ_LBS_m": float(np.abs(sq - lbs).max()),
           "moyenne_SQ_moins_LBS": float(np.linalg.norm((sq - lbs).mean(0))),
           "stats": stats(rest, lbs, sq, tris, A, Mv),
           "deplacement_SQ_LBS_sur_h": {"mediane": float(np.median(disp / h)), "max": float((disp / h).max())},
           "profil_propagation": profil(N, A, cle, PG, PD, disp, h)}
    return res


def valeurs_propres(N, A, lam):
    M = np.zeros((N, N))
    deg = np.bincount(A.ravel(), minlength=N).astype(float)
    M[np.arange(N), np.arange(N)] = deg + lam
    M[A[:, 0], A[:, 1]] -= 1
    M[A[:, 1], A[:, 0]] -= 1
    ev = np.linalg.eigvalsh(M)
    return {"valeur_propre_min": float(ev[0]), "ecart_somme_lignes_a_lambda": float(np.abs(M.sum(1) - lam).max())}


def reel_profil():
    """Même configuration que le test de propagation sur le modèle masculin (t = 0, cuisse droite seule)."""
    z, noms, rest, Wi, Ww, B, b, tot, A, sortie = INV.tous_les_defauts()
    pm, _, _, _ = INV.pose_test(z, noms, INV.JSON_SQ, "hanche_G", 120)
    gG, gD = noms.index("mixamorig:LeftUpLeg"), noms.index("mixamorig:RightUpLeg")
    slotG, slotD = (Wi == gG), (Wi == gD)
    a, c = A[:, 0], A[:, 1]
    D = np.array(sortie["defauts_union"], int)
    voisin = np.unique(np.concatenate([D, a[np.isin(c, D)], c[np.isin(a, D)]]))
    S = np.where((slotG.any(1) & slotD.any(1)) & np.isin(np.arange(len(rest)), voisin))[0]
    Wt = Ww.copy()
    for v in S:
        kG = np.where(slotG[v])[0][0]
        kD = np.where(slotD[v])[0][0]
        s_ = Ww[v, kG] + Ww[v, kD]
        Wt[v, kG] = 0.0
        Wt[v, kD] = s_
    wG_t = np.where(slotG, Wt, 0).sum(1)
    wD_t = np.where(slotD, Wt, 0).sum(1)
    lbs, Mv, Rsq = DEC.pipeline(Wi, Wt, B, pm, rest)
    sq = ARAP.solve_fixe(lbs, rest, A, Rsq, 0.1)
    lr = np.linalg.norm(rest[a] - rest[c], axis=1)
    h = float(np.median(lr))
    disp = np.linalg.norm(sq - lbs, axis=1)
    PG = wG_t > 1 - 1e-6
    PD = wD_t > 1 - 1e-6
    cle = np.round(wG_t, 9)
    prof = profil(len(rest), A, cle, PG, PD, disp, h)
    return {"h_mediane_m": h, "lambda": 0.1, "profil_propagation": prof,
            "moyenne_SQ_moins_LBS": float(np.linalg.norm((sq - lbs).mean(0))),
            "defauts_deplacement_sur_h_mediane": float(np.median(disp[D] / h)),
            "pur_D_nb": int(PD.sum()), "pur_G_nb": int(PG.sum())}


if __name__ == "__main__":
    os.makedirs(SORTIE, exist_ok=True)
    n = 21
    lin = lambda k: xs_uniforme(k)
    cas = [
        ("sanite_un_os", dict(xs=lin(n), ys=lin(n), wkind="un_os", thG=np.radians(30), thD=0.0)),
        ("sanite_meme_rotation", dict(xs=lin(n), ys=lin(n), wkind="uniforme", thG=np.radians(30), thD=np.radians(30))),
        ("uniforme_opposes", dict(xs=lin(n), ys=lin(n), wkind="uniforme", thG=np.radians(30), thD=np.radians(-30))),
        ("progressif_opposes", dict(xs=lin(n), ys=lin(n), wkind="progressif", thG=np.radians(30), thD=np.radians(-30))),
        ("brutal_opposes", dict(xs=lin(n), ys=lin(n), wkind="brutal", thG=np.radians(30), thD=np.radians(-30))),
        ("progressif_D_fixe", dict(xs=lin(n), ys=lin(n), wkind="progressif", thG=np.radians(30), thD=0.0)),
        ("brutal_D_fixe", dict(xs=lin(n), ys=lin(n), wkind="brutal", thG=np.radians(30), thD=0.0)),
        ("progressif_opposes_grille11", dict(xs=lin(11), ys=lin(11), wkind="progressif", thG=np.radians(30), thD=np.radians(-30))),
        ("progressif_opposes_grille41", dict(xs=lin(41), ys=lin(41), wkind="progressif", thG=np.radians(30), thD=np.radians(-30))),
        ("brutal_opposes_grille11", dict(xs=lin(11), ys=lin(11), wkind="brutal", thG=np.radians(30), thD=np.radians(-30))),
        ("brutal_opposes_grille41", dict(xs=lin(41), ys=lin(41), wkind="brutal", thG=np.radians(30), thD=np.radians(-30))),
        ("melange_tailles_progressif", dict(xs=xs_melange(), ys=lin(n), wkind="progressif", thG=np.radians(30), thD=np.radians(-30))),
        ("melange_tailles_brutal", dict(xs=xs_melange(), ys=lin(n), wkind="brutal", thG=np.radians(30), thD=np.radians(-30))),
        ("brutal_opposes_lambda0.01", dict(xs=lin(n), ys=lin(n), wkind="brutal", thG=np.radians(30), thD=np.radians(-30), lam=0.01)),
        ("brutal_opposes_lambda1.0", dict(xs=lin(n), ys=lin(n), wkind="brutal", thG=np.radians(30), thD=np.radians(-30), lam=1.0)),
        ("progressif_opposes_lambda0.01", dict(xs=lin(n), ys=lin(n), wkind="progressif", thG=np.radians(30), thD=np.radians(-30), lam=0.01)),
        ("progressif_opposes_lambda1.0", dict(xs=lin(n), ys=lin(n), wkind="progressif", thG=np.radians(30), thD=np.radians(-30), lam=1.0)),
        ("brutal_opposes_angle60", dict(xs=lin(n), ys=lin(n), wkind="brutal", thG=np.radians(60), thD=np.radians(-60))),
    ]
    resultats = {"configurations": {}, "valeurs_propres": {}, "reel": None}
    for nom, kw in cas:
        kw = dict(kw)
        kw["thG"] = float(kw["thG"])
        kw["thD"] = float(kw["thD"])
        r = evaluer(nom, **kw)
        resultats["configurations"][nom] = r
        print(f"{nom:32s} SQ-LBS max {r['ecart_max_SQ_LBS_m']:.2e} moyenne {r['moyenne_SQ_moins_LBS']:.1e} | "
              f"etir SQ {r['stats']['SQ']['etirement_max']:.3f} LBS {r['stats']['LBS']['etirement_max']:.3f} | "
              f"retour SQ {r['stats']['SQ']['retournements']} LBS {r['stats']['LBS']['retournements']} | "
              f"depl/h med {r['deplacement_SQ_LBS_sur_h']['mediane']:.3f}", flush=True)
    for nn in (11, 21, 41):
        for lam in (0.01, 0.1, 1.0):
            resultats["valeurs_propres"][f"n{nn}_lambda{lam}"] = valeurs_propres(nn * nn, grille(xs_uniforme(nn), xs_uniforme(nn))[2], lam)
    print("valeurs propres :", resultats["valeurs_propres"], flush=True)
    resultats["reel"] = reel_profil()
    print("réel (entrejambe, t = 0) :", {k: v for k, v in resultats["reel"].items() if k != "profil_propagation"}, flush=True)
    print("réel profil pur_D :", resultats["reel"]["profil_propagation"].get("pur_D"), flush=True)
    with open(os.path.join(SORTIE, "resultats.json"), "w", encoding="utf-8") as f:
        json.dump(resultats, f, indent=1, ensure_ascii=False)
    print("ECRIT", os.path.join(SORTIE, "resultats.json"), flush=True)

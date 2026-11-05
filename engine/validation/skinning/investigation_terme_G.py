"""Étude du terme G dans la décomposition exacte d'arête LBS, puis plan de patchs de jonction (pelvis, cuisses).

Décomposition (démontrée dans RAPPORT_terme_G.md) :
    T_k(x) = R_k x + t_k                 (transformation affine de l'os k, repère monde, pose courante)
    lbs(x) = Σ_k w_k(x) T_k(x)
    pour une arête (a, c), d = r_a − r_c :
    lbs_a − lbs_c = Mv_a · d + G_ac,   Mv_a = Σ_k w_ak R_k,   G_ac = Σ_k (w_ak − w_ck) · T_k(r_c)

Ce script :
  1. vérifie l'identité à la précision machine sur tous les sommets, arêtes, os et poses aléatoires ;
  2. vérifie l'approximation de premier ordre G ≈ Σ_k (∇w_k · d) T_k(r_c) et sa vitesse de convergence ;
  3. vérifie le comportement sous translation globale (G invariant) et rotation globale (G ↦ Q G) ;
  4. construit des patchs de jonction (pelvis + deux cuisses, géométrie plane ou courbe, arêtes régulières ou
     non, deux triangulations) avec trois arrangements spatiaux d'un MÊME histogramme de poids ;
  5. compare SQ à LBS sur les mêmes données et mesure la régression sur les arêtes mixtes ;
  6. exécute une batterie de propriétés sur un cas témoin.
"""
import importlib.util
import json
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
SORTIE = os.path.join(RACINE, "docs", "rapports", "skinning", "terme_G")
LAM = 0.1
SEUIL_REGRESSION = 0.05  # écart d'étirement SQ − LBS sur une arête mixte au-delà duquel on parle de régression


def charger(nom):
    spec = importlib.util.spec_from_file_location(nom, os.path.join(HERE, nom + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


S = charger("investigation_synthetique")
DEC = S.DEC
ARAP = S.ARAP


# ---------------------------------------------------------------- transformations et LBS

def transformations(thetas_deg, centres):
    """Os k : rotation d'angle θ_k autour de y passant par c_k. T_k(x) = R_k x + t_k avec t_k = c_k − R_k c_k."""
    Rs, ts = [], []
    for th, c in zip(thetas_deg, centres):
        R = S.rot_y(np.radians(th))
        c = np.asarray(c, float)
        Rs.append(R)
        ts.append(c - R @ c)
    return np.array(Rs), np.array(ts)


def lbs_et_mv(rest, W, Rs, ts):
    """W : (N, K) poids (lignes de somme 1). Retourne lbs (N,3) et Mv (N,3,3)."""
    T_rest = np.einsum("kij,nj->nki", Rs, rest) + ts[None]  # (N, K, 3)
    lbs = np.einsum("nk,nki->ni", W, T_rest)
    Mv = np.einsum("nk,kij->nij", W, Rs)
    return lbs, Mv


def G_et_identite(rest, W, Rs, ts, A):
    """Pour chaque arête (a, c) : G = Σ_k (w_a − w_c)_k T_k(r_c), et l'erreur de l'identité."""
    a, c = A[:, 0], A[:, 1]
    lbs, Mv = lbs_et_mv(rest, W, Rs, ts)
    Tc = np.einsum("kij,ej->eki", Rs, rest[c]) + ts[None]  # (E, K, 3)
    dW = W[a] - W[c]
    G = np.einsum("ek,eki->ei", dW, Tc)
    d = rest[a] - rest[c]
    Mvd = np.einsum("eij,ej->ei", Mv[a], d)
    erreur = np.abs((lbs[a] - lbs[c]) - (Mvd + G)).max()
    return G, Mvd, erreur


# ---------------------------------------------------------------- 1 à 3 : identité et propriétés de G

def verifier_identite(rng, nb_cas=60):
    """Identité sur des configurations aléatoires : sommets, arêtes, os et poses variés."""
    erreurs = []
    for _ in range(nb_cas):
        N = int(rng.integers(20, 60))
        K = int(rng.integers(2, 5))
        rest = rng.normal(size=(N, 3))
        # arêtes : graphe aléatoire connexe approximatif
        A = np.array(sorted({tuple(sorted((int(i), int(j)))) for i, j in
                             zip(rng.integers(0, N, 3 * N), rng.integers(0, N, 3 * N)) if i != j}))
        Rs = np.array([DEC.polaire_gen(rng.normal(size=(3, 3))) for _ in range(K)])
        ts = rng.normal(size=(K, 3))
        W = rng.dirichlet(np.ones(K) * 0.5, size=N)
        _, _, err = G_et_identite(rest, W, Rs, ts, A)
        erreurs.append(float(err))
    return {"nb_cas": nb_cas, "erreur_max_m": float(max(erreurs)), "erreur_mediane_m": float(np.median(erreurs))}


def verifier_taylor(rng):
    """G ≈ Σ_k (∇w_k · d) T_k(r_c) pour des poids lisses ; l'erreur doit décroître avec |d|."""
    K = 3
    Rs, ts = transformations([50, -30, 0], [(0.1, 0.1, 0), (-0.1, 0.1, 0), (0, 0, 0)])
    grad = rng.normal(size=(K, 3))
    H = rng.normal(size=(K, 3, 3))
    H = H + H.transpose(0, 2, 1)  # Hessiens symétriques des poids (quadratiques)
    c0 = np.array([0.02, -0.03, 0.01])
    base = np.array([0.4, 0.3, 0.3])

    def w_fn(x):
        u = x - c0
        return base + grad @ u + 0.5 * np.einsum("kij,i,j->k", H, u, u)

    rows = []
    direction = rng.normal(size=3)
    direction /= np.linalg.norm(direction)
    Tc = np.einsum("kij,j->ki", Rs, c0) + ts
    for h in [1e-1, 3e-2, 1e-2, 3e-3, 1e-3]:
        d = h * direction
        G_exact = (w_fn(c0 + d) - w_fn(c0)) @ Tc
        G_lin = np.einsum("k,ki->i", grad @ d, Tc)  # approximation de premier ordre : ∇w · d
        rows.append({"h_m": h, "erreur_premier_ordre_m": float(np.linalg.norm(G_exact - G_lin)),
                     "norme_G_exacte_m": float(np.linalg.norm(G_exact))})
    # pente log-log de l'erreur : doit valoir ≈ 1 (erreur en O(h)) si le terme d'ordre 2 est présent
    e = np.array([r["erreur_premier_ordre_m"] for r in rows])
    hs = np.array([r["h_m"] for r in rows])
    pente = float(np.polyfit(np.log(hs), np.log(e), 1)[0])
    return {"lignes": rows, "pente_log_erreur": pente}


def verifier_transformations_globales(rng):
    """Translation et rotation du repère monde : comportement exact de Mv et G."""
    N, K = 30, 3
    rest = rng.normal(size=(N, 3))
    A = np.array([(i, (i + 1) % N) for i in range(N)] + [(i, (i + 7) % N) for i in range(N)])
    A = np.array(sorted({tuple(sorted(e)) for e in A}))
    Rs = np.array([DEC.polaire_gen(rng.normal(size=(3, 3))) for _ in range(K)])
    ts = rng.normal(size=(K, 3))
    W = rng.dirichlet(np.ones(K) * 0.7, size=N)
    G0, Mvd0, _ = G_et_identite(rest, W, Rs, ts, A)

    # translation globale c : rest' = rest + c, t'_k = t_k + c − R_k c
    c = rng.normal(size=3)
    ts_t = ts + c[None] - np.einsum("kij,j->ki", Rs, c)
    G1, Mvd1, _ = G_et_identite(rest + c, W, Rs, ts_t, A)
    err_trans = float(np.abs(G1 - G0).max())

    # rotation globale Q : rest' = Q rest, R'_k = Q R_k Q^T, t'_k = Q t_k
    Q = DEC.polaire_gen(rng.normal(size=(3, 3)))
    Rs_r = np.einsum("ij,kjl,ml->kim", Q, Rs, Q)
    ts_r = np.einsum("ij,kj->ki", Q, ts)
    G2, Mvd2, _ = G_et_identite(rest @ Q.T, W, Rs_r, ts_r, A)
    err_rot = float(np.abs(G2 - G0 @ Q.T).max())
    return {"erreur_invariance_translation_m": err_trans, "erreur_covariance_rotation_m": err_rot,
            "norme_G_moyenne_m": float(np.linalg.norm(G0, axis=1).mean())}


# ---------------------------------------------------------------- 4 : patchs de jonction

def grille(xs, ys, mode, kappa):
    nx, ny = len(xs), len(ys)
    X, Y = np.meshgrid(xs, ys)
    Z = kappa * X ** 2  # courbure contrôlée selon x (cylindre)
    rest = np.column_stack([X.ravel(), Y.ravel(), Z.ravel()])
    ix, iy = np.meshgrid(np.arange(nx), np.arange(ny))
    idx = np.arange(nx * ny).reshape(ny, nx)
    tris = []
    for j in range(ny - 1):
        for i in range(nx - 1):
            p00, p10, p01, p11 = idx[j, i], idx[j, i + 1], idx[j + 1, i], idx[j + 1, i + 1]
            if mode == "B" and (i + j) % 2 == 1:
                tris += [(p00, p10, p01), (p10, p11, p01)]
            else:
                tris += [(p00, p10, p11), (p00, p11, p01)]
    tris = np.array(tris)
    E = set()
    for t in tris:
        for k in range(3):
            E.add(tuple(sorted((int(t[k]), int(t[(k + 1) % 3])))))
    return rest, tris, np.array(sorted(E)), ix.ravel(), iy.ravel()


def histogramme_valeurs(hist, n):
    """Multiset de n valeurs de poids G dont la répartition suit l'histogramme (10 classes)."""
    centres = (np.arange(10) + 0.5) / 10
    prob = np.array(hist, float)
    prob /= prob.sum()
    comptes = np.floor(prob * n).astype(int)
    comptes[np.argmax(prob)] += n - comptes.sum()
    return np.repeat(centres, comptes)


def arranger(valeurs, ordre_x, arrangement, rng):
    """Assigne les valeurs aux sommets T (ordre_x : indices triés selon x).
    lisse : valeurs croissantes le long de x ; aleatoire : permutation ; alterne : zigzag maximal le long de x."""
    n = len(valeurs)
    v = np.sort(valeurs)
    s = np.empty(n)
    if arrangement == "lisse":
        s[:] = v
    elif arrangement == "aleatoire":
        s[:] = rng.permutation(v)
    elif arrangement == "alterne":
        pos = np.arange(n)
        rang = np.where(pos % 2 == 0, pos // 2, n - 1 - pos // 2)
        s[:] = v[rang]
    else:
        raise ValueError(arrangement)
    return s  # s[k] = valeur du k-ième sommet de ordre_x


def patch(geo, tri, nonuni, kappa, arrangement, hist, thetas, rng_seed=0):
    xs = 0.3 * S.xs_melange() if nonuni else np.linspace(-0.3, 0.3, 21)
    ys = np.linspace(-0.3, 0.3, 21)
    rest, tris, A, ix, iy = grille(xs, ys, tri, kappa if geo == "courbe" else 0.0)
    X, Y = rest[:, 0], rest[:, 1]
    N = len(rest)
    # pelvis : poids 1 pour y ≥ 0,15 ; transition linéaire sur 0 ≤ y ≤ 0,15 ; cuisses pour y ≤ 0
    pf = np.clip(Y / 0.15, 0, 1)
    thigh = 1 - pf
    T = np.where(thigh > 1e-12)[0]
    ordre_x = T[np.argsort(X[T], kind="stable")]
    rng = np.random.default_rng(rng_seed)
    valeurs = histogramme_valeurs(hist, len(T))
    s_vals = arranger(valeurs, ordre_x, arrangement, rng)
    s = np.full(N, 0.5)
    s[ordre_x] = s_vals
    W = np.column_stack([pf, thigh * s, thigh * (1 - s)])  # pelvis, G, D
    Rs, ts = transformations([0, thetas[0], thetas[1]], [(0, 0.15, 0), (0.1, 0.15, 0), (-0.1, 0.15, 0)])
    lbs, Mv = lbs_et_mv(rest, W, Rs, ts)
    Rsq = DEC.polaire_gen(Mv)
    sq = ARAP.solve_fixe(lbs, rest, A, Rsq, LAM)
    return {"rest": rest, "tris": tris, "A": A, "W": W, "Rs": Rs, "ts": ts, "lbs": lbs, "Mv": Mv, "sq": sq}


def mesurer(p):
    rest, A, W, Rs, ts = p["rest"], p["A"], p["W"], p["Rs"], p["ts"]
    a, c = A[:, 0], A[:, 1]
    lr = np.linalg.norm(rest[a] - rest[c], axis=1)
    mixte = np.any(np.abs(W[a] - W[c]) > 1e-9, axis=1)
    rho_L = np.linalg.norm(p["lbs"][a] - p["lbs"][c], axis=1) / lr
    rho_S = np.linalg.norm(p["sq"][a] - p["sq"][c], axis=1) / lr
    exc = rho_S - rho_L
    G, Mvd, err = G_et_identite(rest, W, Rs, ts, A)
    st = S.stats(rest, p["lbs"], p["sq"], p["tris"], A, p["Mv"])
    out = {
        "erreur_identite_m": float(err),
        "nb_aretes_mixtes": int(mixte.sum()),
        "etirement_max_LBS_mixte": float(rho_L[mixte].max()),
        "etirement_max_SQ_mixte": float(rho_S[mixte].max()),
        "excedent_max_SQ_moins_LBS": float(exc[mixte].max()),
        "nb_aretes_regression": int((exc[mixte] > SEUIL_REGRESSION).sum()),
        "part_regression_mixte": float((exc[mixte] > SEUIL_REGRESSION).mean()),
        "norme_G_sur_longueur_mediane": float(np.median(np.linalg.norm(G[mixte], axis=1) / lr[mixte])),
        "norme_Mvd_sur_longueur_mediane": float(np.median(np.linalg.norm(Mvd[mixte], axis=1) / lr[mixte])),
        "retournements_SQ": int(st["SQ"]["retournements"]),
        "retournements_LBS": int(st["LBS"]["retournements"]),
    }
    return out, G, lr, mixte, exc


def plan_patchs(hist_M, hist_F):
    res = []
    for geo in ("plat", "courbe"):
        for nonuni in (False, True):
            for tri in ("A", "B"):
                for arr in ("lisse", "aleatoire", "alterne"):
                    for hn, hist in (("M", hist_M), ("F", hist_F)):
                        for th in ((90, 0), (120, 0), (120, -60)):
                            p = patch(geo, tri, nonuni, 4.0, arr, hist, th)
                            m, _, _, _, _ = mesurer(p)
                            res.append({"geometrie": geo, "arretes_non_uniformes": nonuni, "triangulation": tri,
                                        "arrangement": arr, "histogramme": hn, "angles_cuisses_deg": list(th), **m})
    return res


def facteurs(res):
    """Moyennes par niveau pour les facteurs principaux. Mesure de régression : excédent max et part régressée."""
    cles = {"geometrie": "geometrie", "arretes": "arretes_non_uniformes", "triangulation": "triangulation",
            "arrangement": "arrangement", "histogramme": "histogramme"}
    out = {}
    for nom, k in cles.items():
        niveaux = sorted({str(r[k]) for r in res})
        out[nom] = {}
        for niv in niveaux:
            sub = [r for r in res if str(r[k]) == niv]
            out[nom][niv] = {
                "excedent_max_moyen": float(np.mean([r["excedent_max_SQ_moins_LBS"] for r in sub])),
                "part_regression_moyenne": float(np.mean([r["part_regression_mixte"] for r in sub])),
                "nb_cas_avec_regression": int(sum(r["nb_aretes_regression"] > 0 for r in sub)),
                "nb_cas": len(sub),
            }
    return out


# ---------------------------------------------------------------- 6 : batterie de propriétés (cas témoin)

def batterie(hist_M):
    rng = np.random.default_rng(7)
    rapport = {}
    base = patch("plat", "A", False, 0.0, "alterne", hist_M, (120, 0))
    rest, A, W, Rs, ts = base["rest"], base["A"], base["W"], base["Rs"], base["ts"]

    # 1. pose de repos : un seul os identité partout -> SQ = LBS = rest
    Rs1 = np.repeat(np.eye(3)[None], 3, 0)
    ts1 = np.zeros((3, 3))
    lbs1, Mv1 = lbs_et_mv(rest, W, Rs1, ts1)
    sq1 = ARAP.solve_fixe(lbs1, rest, A, DEC.polaire_gen(Mv1), LAM)
    rapport["pose_repos_erreur_m"] = float(np.abs(sq1 - rest).max())

    # 2. transformation rigide commune : tous les os identiques -> SQ = LBS
    Rr, tr = transformations([30, 30, 30], [(0, 0.15, 0), (0.1, 0.15, 0), (-0.1, 0.15, 0)])
    Rr = np.repeat(Rr[1:2], 3, 0)
    tr = np.repeat(tr[1:2], 3, 0)
    lbsr, Mvr = lbs_et_mv(rest, W, Rr, tr)
    sqr = ARAP.solve_fixe(lbsr, rest, A, DEC.polaire_gen(Mvr), LAM)
    rapport["rigide_commun_erreur_SQ_LBS_m"] = float(np.abs(sqr - lbsr).max())

    # 3. translation globale : SQ se translate exactement
    c = rng.normal(size=3) * 0.2
    ts_t = ts + c[None] - np.einsum("kij,j->ki", Rs, c)
    lbs_t, Mv_t = lbs_et_mv(rest + c, W, Rs, ts_t)
    sq_t = ARAP.solve_fixe(lbs_t, rest + c, A, DEC.polaire_gen(Mv_t), LAM)
    rapport["translation_erreur_m"] = float(np.abs(sq_t - (base["sq"] + c)).max())

    # 4. rotation globale : SQ ↦ Q SQ
    Q = DEC.polaire_gen(rng.normal(size=(3, 3)))
    Rq = np.einsum("ij,kjl,ml->kim", Q, Rs, Q)
    tq = np.einsum("ij,kj->ki", Q, ts)
    lbs_q, Mv_q = lbs_et_mv(rest @ Q.T, W, Rq, tq)
    sq_q = ARAP.solve_fixe(lbs_q, rest @ Q.T, A, DEC.polaire_gen(Mv_q), LAM)
    rapport["rotation_erreur_m"] = float(np.abs(sq_q - base["sq"] @ Q.T).max())

    # 5. poids purs : sommets dont tout le voisinage est pur -> écart SQ − LBS
    pur = np.all((W > 1 - 1e-9) | (W < 1e-9), axis=1)
    N = len(rest)
    voisin_pur = pur.copy()
    for u, v in A:
        if not pur[u] or not pur[v]:
            voisin_pur[u] = False
            voisin_pur[v] = False
    ecart_pur = np.abs(base["sq"] - base["lbs"]).max(1)
    rapport["poids_purs_ecart_max_voisinage_pur_m"] = float(ecart_pur[voisin_pur].max()) if voisin_pur.any() else None
    rapport["poids_purs_nb_sommets_voisinage_pur"] = int(voisin_pur.sum())

    # 6. continuité : petite perturbation des poids d'un sommet -> variation de SQ
    eps = 1e-4
    W2 = W.copy()
    i0 = int(np.argmax(np.linalg.norm(base["lbs"] - base["lbs"].mean(0), axis=1)))
    W2[i0, 1] += eps
    W2[i0, 2] -= eps
    lbs_c, Mv_c = lbs_et_mv(rest, W2, Rs, ts)
    sq_c = ARAP.solve_fixe(lbs_c, rest, A, DEC.polaire_gen(Mv_c), LAM)
    rapport["continuite_variation_SQ_par_unite_poids"] = float(np.abs(sq_c - base["sq"]).max() / eps)

    # 7. stabilité triangulation : même géométrie et poids, diagonales différentes
    alt = patch("plat", "B", False, 0.0, "alterne", hist_M, (120, 0))
    rapport["triangulation_difference_SQ_m"] = float(np.abs(alt["sq"] - base["sq"]).max())

    # 8. retournements et étirements : métriques du cas témoin
    m, _, _, _, _ = mesurer(base)
    rapport["cas_temoin"] = m
    return rapport


if __name__ == "__main__":
    os.makedirs(SORTIE, exist_ok=True)
    desc = json.load(open(os.path.join(RACINE, "docs", "rapports", "skinning", "factorielle", "descriptif_morphologies.json")))
    hist_M = desc["masculin"]["histogramme_wG_mixtes_10_classes"]
    hist_F = desc["feminin"]["histogramme_wG_mixtes_10_classes"]
    rng = np.random.default_rng(1)

    sortie = {}
    sortie["identite"] = verifier_identite(rng)
    print("identite", sortie["identite"], flush=True)
    sortie["taylor"] = verifier_taylor(np.random.default_rng(3))
    print("taylor", sortie["taylor"], flush=True)
    sortie["transformations_globales"] = verifier_transformations_globales(np.random.default_rng(5))
    print("transf", sortie["transformations_globales"], flush=True)
    sortie["batterie"] = batterie(hist_M)
    print("batterie", json.dumps(sortie["batterie"], indent=1, ensure_ascii=False), flush=True)
    res = plan_patchs(hist_M, hist_F)
    sortie["plan_patchs"] = res
    sortie["facteurs"] = facteurs(res)
    print("facteurs", json.dumps(sortie["facteurs"], indent=1, ensure_ascii=False), flush=True)
    with open(os.path.join(SORTIE, "resultats_terme_G.json"), "w", encoding="utf-8") as f:
        json.dump(sortie, f, indent=1, ensure_ascii=False)
    print("ECRIT", flush=True)

"""Origine géométrique des retournements SQ de Maria (sept triangles, voisinage, témoins, symétrie, expériences).

Phase 1 : voisinage immédiat (anneaux 1 et 2), longueurs, angles, aires, normales, courbure (défaut angulaire),
          valence, poids et gradients, transformations des os ; comparaison à des témoins appariés de l'entrejambe
          qui ne se retournent dans aucune des 11 poses.
Phase 2 : expériences à un seul facteur sur le maillage réel (angle d'articulation, répartition des poids, λ,
          déplacement normal et tangentiel des sommets concernés). Chaque variation mesure les retournements nouveaux
          sur les sept triangles et sur tout le maillage.
Phase 3 : symétrie gauche/droite (plan x = 0) : appariement des sommets et des triangles, comparaison des métriques
          et des retournements sur les paires miroir.
Phase 4 : trois mesures séparées (A référence locale, B forme LBS, C forme SQ propre) et contrôle des rotations
          rigides.
Aucun seuil n'est modifié, l'algorithme SQ n'est pas changé, aucune correction n'est faite pour les sept triangles.
"""
import importlib.util
import json
import os

import numpy as np
from scipy.spatial import cKDTree

HERE = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
SORTIE = os.path.join(RACINE, "docs", "rapports", "skinning", "maria_geometrie")
MECA = os.path.join(RACINE, "docs", "rapports", "skinning", "maria_retournements", "mecanisme_retournements.json")


def charger(nom):
    spec = importlib.util.spec_from_file_location(nom, os.path.join(HERE, nom + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


DEC = charger("investigation_decomposition")
CMP = charger("investigation_comparaison")
LM = charger("investigation_lambda_morphos")
DR = charger("investigation_defaut_reel")


def unit(v):
    return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-300)


def normales(p, tris):
    return np.cross(p[tris[:, 1]] - p[tris[:, 0]], p[tris[:, 2]] - p[tris[:, 0]])


def angle_rot(R):
    c = np.clip((np.trace(R, axis1=-2, axis2=-1) - 1) / 2, -1, 1)
    return np.degrees(np.arccos(c))


def angles_internes(p, tris):
    P = [p[tris[:, 0]], p[tris[:, 1]], p[tris[:, 2]]]
    out = np.zeros((len(tris), 3))
    for k in range(3):
        a, b, c = P[k], P[(k + 1) % 3], P[(k + 2) % 3]
        u, v = b - a, c - a
        cs = (u * v).sum(1) / (np.linalg.norm(u, axis=1) * np.linalg.norm(v, axis=1) + 1e-300)
        out[:, k] = np.arccos(np.clip(cs, -1, 1))
    return out


def longueurs(p, tris):
    return np.stack([np.linalg.norm(p[tris[:, 1]] - p[tris[:, 0]], axis=1),
                     np.linalg.norm(p[tris[:, 2]] - p[tris[:, 1]], axis=1),
                     np.linalg.norm(p[tris[:, 0]] - p[tris[:, 2]], axis=1)], axis=1)


def defaut_angulaire(p, tris, N, bord):
    """Courbure discrète : 2π − somme des angles (intérieur) ou π − somme (bord), par sommet."""
    S = np.zeros(N)
    np.add.at(S, tris.ravel(), angles_internes(p, tris).ravel())
    return np.where(bord, np.pi, 2 * np.pi) - S


def sommets_bord(tris, N):
    e = np.sort(np.concatenate([tris[:, [0, 1]], tris[:, [1, 2]], tris[:, [2, 0]]]), axis=1)
    u, cnt = np.unique(e, axis=0, return_counts=True)
    bord = np.zeros(N, bool)
    bord[u[cnt == 1].ravel()] = True
    return bord


def flags(rest, tris, lbs, sq, Mv):
    """Trois mesures séparées, par triangle.
    A : normale déformée opposée à la référence polaire(Mv moyen) appliquée à la normale de repos (LBS et SQ).
    B : normale SQ opposée à la normale LBS (inversion par rapport à la forme LBS).
    C : normale SQ opposée à la partie rigide polaire de sa propre déformation affine (inversion par rapport à la
        forme SQ), sans aucune référence externe.
    """
    n0 = unit(normales(rest, tris))
    nL = unit(normales(lbs, tris))
    nS = unit(normales(sq, tris))
    ref = np.einsum("tij,tj->ti", DEC.polaire_gen(Mv[tris].mean(1)), n0)
    AL = np.einsum("ti,ti->t", nL, ref) < 0
    AS = np.einsum("ti,ti->t", nS, ref) < 0
    B = np.einsum("ti,ti->t", nS, nL) < 0
    Dr = np.stack([rest[tris[:, 1]] - rest[tris[:, 0]], rest[tris[:, 2]] - rest[tris[:, 0]]], axis=2)
    Ds = np.stack([sq[tris[:, 1]] - sq[tris[:, 0]], sq[tris[:, 2]] - sq[tris[:, 0]]], axis=2)
    F = Ds @ np.linalg.pinv(Dr)
    RF = DEC.polaire_gen(F)
    C = np.einsum("ti,ti->t", nS, np.einsum("tij,tj->ti", RF, n0)) < 0
    return {"A_LBS": AL, "A_SQ": AS, "B_SQ_vs_LBS": B, "C_SQ_propre": C, "nouveau_A": AS & ~AL}


def indices_triangles(tris, sept):
    cle = {tuple(sorted(t)): i for i, t in enumerate(tris)}
    out = []
    for s in sept:
        out.append(cle[tuple(sorted(s))])
    return out


def mesure_pose(M, rest, pm, W=None, lam=CMP.LAM):
    lbs, sq, Mv, R, t = CMP.evaluer(M, pm, lam=lam, W=W, rest=rest)
    return lbs, sq, Mv, R


if __name__ == "__main__":
    os.makedirs(SORTIE, exist_ok=True)
    M = CMP.charger_morph("maria")
    rest, tris, A, W, N = M["rest"], M["tris"], M["A"], M["W"], M["N"]
    noms = M["noms"]
    labs = CMP.regions(M)
    meca = json.load(open(MECA, encoding="utf-8"))
    occ = meca["triangles"]
    sept = sorted({tuple(o["triangle"]) for o in occ})
    poses_flip = meca["poses_avec_nouveaux"]
    idx7 = indices_triangles(tris, sept)
    idx7_set = set(idx7)
    sommets7 = sorted({v for s in sept for v in s})
    dom = W.argmax(1)
    mix_v = 1 - W.max(1)
    bord = sommets_bord(tris, N)
    valence = np.bincount(A.ravel(), minlength=N)
    defv = defaut_angulaire(rest, tris, N, bord)
    ang = angles_internes(rest, tris)
    lg = longueurs(rest, tris)
    aire0 = 0.5 * np.linalg.norm(normales(rest, tris), axis=1)
    a_edge = np.abs
    # entropie des poids par sommet
    Wc = np.clip(W, 1e-300, 1)
    H_v = -(W * np.log(Wc)).sum(1)
    # gradient de poids par triangle : moyenne sur les trois arêtes de |ΔW|_1 / longueur
    gW = np.zeros(len(tris))
    for i, j in [(0, 1), (1, 2), (2, 0)]:
        a_, b_ = tris[:, i], tris[:, j]
        d = np.abs(W[a_] - W[b_]).sum(1) / np.maximum(np.linalg.norm(rest[a_] - rest[b_], axis=1), 1e-300)
        gW += d / 3

    def feats_repos(ti):
        return {"aire_repos": float(aire0[ti]), "angle_min_deg": float(np.degrees(ang[ti].min())),
                "angle_max_deg": float(np.degrees(ang[ti].max())), "longueurs_m": [round(float(x), 5) for x in lg[ti]],
                "rapport_longueurs_min_max": float(lg[ti].min() / lg[ti].max()),
                "courbure_defaut_moy_sommets": float(defv[tris[ti]].mean()),
                "valence_sommets": [int(valence[v]) for v in tris[ti]],
                "melange_moyen": float(mix_v[tris[ti]].mean()), "entropie_moy": float(H_v[tris[ti]].mean()),
                "gradient_poids": float(gW[ti]), "os_dominants": [noms[dom[v]] for v in tris[ti]],
                "poids_dominants": [round(float(W[v].max()), 4) for v in tris[ti]]}

    # ----- anneaux -----
    tri_par_arete = {}
    for ti, t in enumerate(tris):
        for i, j in [(0, 1), (1, 2), (2, 0)]:
            tri_par_arete.setdefault(tuple(sorted((t[i], t[j]))), []).append(ti)
    tri_par_sommet = [[] for _ in range(N)]
    for ti, t in enumerate(tris):
        for v in t:
            tri_par_sommet[v].append(ti)

    def anneaux(ti):
        t = tris[ti]
        a1 = set()
        for i, j in [(0, 1), (1, 2), (2, 0)]:
            a1.update(tri_par_arete[tuple(sorted((t[i], t[j])))])
        a1.discard(ti)
        s1 = set(t) | {v for k in a1 for v in tris[k]}
        a2 = set()
        for v in s1:
            a2.update(tri_par_sommet[v])
        a2 -= a1 | {ti}
        return sorted(a1), sorted(a2)

    # ----- témoins appariés (entrejambe, jamais retournés dans les poses de flip) -----
    # 1) calcul des indicateurs dynamiques et des retournements dans chaque pose de flip
    dyn = {}
    pose_flags = {}
    for nom in poses_flip:
        pm = CMP.pose_de(M, nom)
        lbs, sq, Mv, R, t = CMP.evaluer(M, pm)
        f = flags(rest, tris, lbs, sq, Mv)
        pose_flags[nom] = (lbs, sq, Mv, R, f)
    jamais = np.ones(len(tris), bool)
    for nom, (_, _, _, _, f) in pose_flags.items():
        jamais &= ~f["nouveau_A"]
    ent_tri = np.array([labs[t[0]] == labs[t[1]] == labs[t[2]] == "entrejambe" for t in tris])
    candidats = np.where(ent_tri & jamais)[0]
    candidats = np.array([c for c in candidats if c not in idx7_set])

    def vecteur_repos(ti_arr):
        """Caractéristiques de repos normalisées (log aire, angles min et max, courbure, mélange, longueurs, valence)."""
        f = np.stack([np.log(aire0[ti_arr]),
                      np.degrees(ang[ti_arr].min(1)),
                      np.degrees(ang[ti_arr].max(1)),
                      defv[tris[ti_arr]].mean(1),
                      mix_v[tris[ti_arr]].mean(1),
                      lg[ti_arr].mean(1),
                      valence[tris[ti_arr]].mean(1)], axis=1)
        return f

    V_c = vecteur_repos(candidats)
    mu, sd = V_c.mean(0), V_c.std(0) + 1e-12
    Z_c = (V_c - mu) / sd
    temoins = {}
    for ti in idx7:
        z = (vecteur_repos(np.array([ti])) - mu) / sd
        d = np.linalg.norm(Z_c - z, axis=1)
        k = np.argsort(d)[:8]
        temoins[ti] = candidats[k].tolist()

    # 2) comparaison dans les poses où le triangle se retourne
    temoins_resultat = []
    for ti in idx7:
        poses_ti = sorted({o["pose"] for o in occ if tuple(o["triangle"]) == tuple(tris[ti])})
        ligne = {"triangle": [int(x) for x in tris[ti]], "indice": int(ti), "poses_retournement": poses_ti,
                 "repos": feats_repos(ti), "voisins_anneau1": None, "voisins_anneau2": None,
                 "temoins": [int(x) for x in temoins[ti]], "dynamique": {}}
        a1, a2 = anneaux(ti)
        ligne["voisins_anneau1"] = {"n": len(a1), "triangles": [int(x) for x in a1],
                                    "aire_moy_rel": float(np.mean(aire0[a1] / aire0[ti]))}
        ligne["voisins_anneau2"] = {"n": len(a2), "triangles": [int(x) for x in a2],
                                    "aire_moy_rel": float(np.mean(aire0[a2] / aire0[ti]))}
        ligne["temoins_repos"] = [feats_repos(c) for c in temoins[ti][:4]]
        for nom in poses_ti:
            lbs, sq, Mv, R, f = pose_flags[nom]
            Mt = Mv[tris].mean(1)
            svs = np.linalg.svd(Mt, compute_uv=False)
            cand_pose = {}
            for label, tt in [("flip", [ti])] + [("temoins", temoins[ti])]:
                tt = np.array(tt)
                cand_pose[label] = {
                    "ratio_aire_LBS": float(np.linalg.norm(normales(lbs, tris)[tt], axis=1).mean() / (2 * aire0[tt]).mean()),
                    "ratio_aire_SQ": float(np.linalg.norm(normales(sq, tris)[tt], axis=1).mean() / (2 * aire0[tt]).mean()),
                    "sv_min_Mv": float(svs[tt, -1].mean()),
                    "angle_dom_max_deg": float(max(angle_rot(R)[dom[tris[j]]].max() for j in tt)),
                    "A_LBS": bool(f["A_LBS"][tt].any()), "A_SQ": bool(f["A_SQ"][tt].any()),
                    "nouveau_A": bool(f["nouveau_A"][tt].any()), "B": bool(f["B_SQ_vs_LBS"][tt].any()),
                    "C": bool(f["C_SQ_propre"][tt].any()),
                }
            ligne["dynamique"][nom] = cand_pose
        temoins_resultat.append(ligne)
        print("temoins", ligne["triangle"], ligne["poses_retournement"][:3], flush=True)

    # ----- mesures A / B / C par occurrence (sept triangles, poses de flip) -----
    occ_abc = []
    for nom in poses_flip:
        lbs, sq, Mv, R, f = pose_flags[nom]
        for ti in idx7:
            if f["nouveau_A"][ti]:
                cat = "nouveau_A_SQ_introduit"
            elif f["B_SQ_vs_LBS"][ti] or f["C_SQ_propre"][ti]:
                cat = "seulement_differences_de_forme"
            else:
                cat = "non_retourne"
            occ_abc.append({"pose": nom, "triangle": [int(x) for x in tris[ti]], "A_LBS": bool(f["A_LBS"][ti]),
                            "A_SQ": bool(f["A_SQ"][ti]), "B_SQ_vs_LBS": bool(f["B_SQ_vs_LBS"][ti]),
                            "C_SQ_propre": bool(f["C_SQ_propre"][ti]), "categorie": cat})
    # contrôle : rotation rigide globale -> aucune mesure ne doit compter de retournement
    rng = np.random.default_rng(3)
    Q = DEC.polaire_gen(rng.normal(size=(3, 3)))
    # déformation rigide globale : tout le maillage tourne de Q ; aucune mesure ne doit compter de retournement
    lbs_rig = rest @ Q.T
    Mv_rig = np.repeat(Q[None], N, 0)
    sq_rig = CMP.ARAP.solve_fixe(lbs_rig, rest, A, DEC.polaire_gen(Mv_rig), CMP.LAM)
    fr = flags(rest, tris, lbs_rig, sq_rig, Mv_rig)
    controle_rigide = {"A_LBS": int(fr["A_LBS"].sum()), "A_SQ": int(fr["A_SQ"].sum()),
                       "B": int(fr["B_SQ_vs_LBS"].sum()), "C": int(fr["C_SQ_propre"].sum())}
    print("controle rigide", controle_rigide, flush=True)

    # ----- Phase 2 : expériences à un seul facteur -----
    def compter(rest_c, lbs, sq, Mv):
        f = flags(rest_c, tris, lbs, sq, Mv)
        return {"nouveau_A_sur_7": int(f["nouveau_A"][idx7].sum()),
                "nouveau_A_total": int(f["nouveau_A"].sum()),
                "LBS_total": int(f["A_LBS"].sum()), "SQ_total": int(f["A_SQ"].sum())}

    exp = {}
    P1 = "generative_hanche_G_105"
    P2 = "reelle_R_flex120"
    pm1 = CMP.pose_de(M, P1)
    # E1 : angle d'articulation de la hanche gauche (un seul facteur)
    e1 = {}
    for th in range(0, 121, 15):
        pm = LM.pose_hanche_G(M["z"], noms, M["js"], th)
        lbs, sq, Mv, R, _ = CMP.evaluer(M, pm)
        e1[str(th)] = compter(rest, lbs, sq, Mv)
    exp["E1_angle_hanche_G"] = e1
    print("E1", {k: v["nouveau_A_sur_7"] for k, v in e1.items()}, flush=True)

    # E2 : répartition des poids (affectation progressive vers l'os dominant) sur les sommets des 7 triangles,
    # contrôle : même opération sur un ensemble de sommets témoins de même taille
    rng = np.random.default_rng(0)
    cand_v = np.array([v for v in range(N) if labs[v] == "entrejambe" and v not in set(sommets7)])
    e2 = {"sommets_concernes": {}, "controle": {}}
    for alpha in [0, 0.25, 0.5, 0.75, 1.0]:
        Wh = W.copy()
        for v in sommets7:
            Wh[v] = (1 - alpha) * W[v]
            Wh[v, dom[v]] += alpha
        lbs, sq, Mv, R = mesure_pose(M, rest, pm1, W=Wh)
        e2["sommets_concernes"][str(alpha)] = compter(rest, lbs, sq, Mv)
        ctrls = []
        for s in range(5):
            cs = rng.choice(cand_v, size=len(sommets7), replace=False)
            Wc2 = W.copy()
            for v in cs:
                Wc2[v] = (1 - alpha) * W[v]
                Wc2[v, dom[v]] += alpha
            l2, s2, M2, R2 = mesure_pose(M, rest, pm1, W=Wc2)
            ctrls.append(compter(rest, l2, s2, M2)["nouveau_A_sur_7"])
        e2["controle"][str(alpha)] = {"nouveau_A_sur_7_moyenne_5_tirages": float(np.mean(ctrls)), "tirages": ctrls}
    exp["E2_repartition_poids"] = e2
    print("E2", {k: v["nouveau_A_sur_7"] for k, v in e2["sommets_concernes"].items()}, flush=True)

    # E3 : paramètre de conditions aux limites (λ), deux poses
    e3 = {}
    for nom in [P1, P2]:
        pm = CMP.pose_de(M, nom)
        e3[nom] = {}
        for lam in [0.01, 0.03, 0.1, 0.3, 1.0, 3.0]:
            lbs, sq, Mv, R, _ = CMP.evaluer(M, pm, lam=lam)
            e3[nom][str(lam)] = compter(rest, lbs, sq, Mv)
    exp["E3_lambda"] = e3
    print("E3", {n: {k: v["nouveau_A_sur_7"] for k, v in d.items()} for n, d in e3.items()}, flush=True)

    # E4 : déplacement normal de chaque sommet concerné (±1 mm, repos seulement) : courbure locale
    # E5 : déplacement tangentiel (±5 % de la longueur moyenne d'arête, vers/depuis le centroïde voisin)
    nrm_v = np.zeros((N, 3))
    np.add.at(nrm_v, tris.ravel(), np.repeat(unit(normales(rest, tris)), 3, axis=0))
    nrm_v = unit(nrm_v)
    voisins = [set() for _ in range(N)]
    for a_, c_ in A:
        voisins[a_].add(c_)
        voisins[c_].add(a_)
    lmoy = lg.mean()
    e4, e5 = {}, {}
    base_pm = pm1
    for v in sommets7:
        e4[str(v)] = {}
        for d_mm in [-1.0, 1.0]:
            r2 = rest.copy()
            r2[v] = rest[v] + d_mm * 1e-3 * nrm_v[v]
            lbs, sq, Mv, R, _ = CMP.evaluer(M, base_pm, rest=r2)
            e4[str(v)][str(d_mm)] = compter(r2, lbs, sq, Mv)
        cen = rest[list(voisins[v])].mean(0)
        dirn = unit(rest[v] - cen)
        e5[str(v)] = {}
        for frac in [-0.05, 0.05]:
            r2 = rest.copy()
            r2[v] = rest[v] + frac * lmoy * dirn
            lbs, sq, Mv, R, _ = CMP.evaluer(M, base_pm, rest=r2)
            e5[str(v)][str(frac)] = compter(r2, lbs, sq, Mv)
    exp["E4_deplacement_normal_1mm"] = e4
    exp["E5_deplacement_tangentiel_5pct"] = e5
    base_c = compter(rest, *mesure_pose(M, rest, pm1)[:3])
    exp["reference_pose_P1"] = base_c
    print("E4/E5 terminés", flush=True)

    # ----- Phase 3 : symétrie gauche/droite (plan x = 0) -----
    x = rest[:, 0]
    miroir = rest.copy()
    miroir[:, 0] = -rest[:, 0]
    arbre = cKDTree(rest)
    dmir, imir = arbre.query(miroir)
    lmed = float(lg.mean())
    sym = {"distance_miroir_sur_longueur_moyenne": {"mediane": float(np.median(dmir) / lmed),
                                                   "p90": float(np.quantile(dmir, 0.9) / lmed),
                                                   "p99": float(np.quantile(dmir, 0.99) / lmed),
                                                   "max": float(dmir.max() / lmed)},
           "sommets_appariés_moins_0_2_arete": float((dmir < 0.2 * lmed).mean())}
    # triangles miroir
    cle = {tuple(sorted(t)): i for i, t in enumerate(tris)}
    mir_tri = np.full(len(tris), -1)
    for i, t in enumerate(tris):
        k = tuple(sorted(imir[t]))
        mir_tri[i] = cle.get(k, -1)
    sym["triangles_avec_miroir_exact"] = float((mir_tri >= 0).mean())

    # flips gauche / droite dans les poses miroir
    pairs = [("reelle_L_flex120", "reelle_R_flex120"), ("reelle_L_flex60", "reelle_R_flex60"),
             ("reelle_L_combo_flex120_genou90", "reelle_R_combo_flex120_genou90"),
             ("reelle_L_combo_flex60_abd20_int20_genou60", "reelle_R_combo_flex60_abd20_int20_genou60")]
    paires = []
    for pL, pR in pairs:
        fL_ = flags(rest, tris, *mesure_pose(M, rest, CMP.pose_de(M, pL))[:2], mesure_pose(M, rest, CMP.pose_de(M, pL))[2])
        fR_ = flags(rest, tris, *mesure_pose(M, rest, CMP.pose_de(M, pR))[:2], mesure_pose(M, rest, CMP.pose_de(M, pR))[2])
        paires.append({"pose_gauche": pL, "pose_droite": pR,
                       "nouveau_A_gauche": int(fL_["nouveau_A"].sum()), "nouveau_A_droite": int(fR_["nouveau_A"].sum()),
                       "nouveau_A_gauche_sur_7": int(fL_["nouveau_A"][idx7].sum()),
                       "nouveau_A_droite_sur_7": int(fR_["nouveau_A"][idx7].sum())})
        print("pair", paires[-1], flush=True)
    sym["paires_de_poses"] = paires

    # comparaison gauche/droite des sept triangles et de leurs miroirs
    miroir_des_7 = []
    for ti in idx7:
        mi = int(mir_tri[ti])
        if mi < 0:
            miroir_des_7.append({"triangle": [int(v) for v in tris[ti]], "miroir": None})
            continue
        miroir_des_7.append({"triangle": [int(v) for v in tris[ti]], "miroir": [int(v) for v in tris[mi]],
                             "indice_miroir": mi,
                             "repos_triangle": feats_repos(ti), "repos_miroir": feats_repos(mi),
                             "os_dominants_miroir": [noms[dom[v]] for v in tris[mi]]})
    sym["sept_triangles_et_miroirs"] = miroir_des_7
    sym["sept_avec_miroir_exact"] = int(sum(1 for m in miroir_des_7 if m["miroir"] is not None))
    # paires gauche/droite : comparaison de géométrie et de poids (même région)
    gauche = np.where(x > 0)[0]
    droite = imir[gauche]
    diff = {"longueur_arete_moy_diff": None}
    sym["comparaison_metriques_paires_miroir"] = {
        "courbure_defaut_moy_gauche": float(defv[gauche].mean()), "courbure_defaut_moy_droite": float(defv[droite].mean()),
        "valence_moy_gauche": float(valence[gauche].mean()), "valence_moy_droite": float(valence[droite].mean()),
        "entropie_moy_gauche": float(H_v[gauche].mean()), "entropie_moy_droite": float(H_v[droite].mean()),
        "melange_moy_gauche": float(mix_v[gauche].mean()), "melange_moy_droite": float(mix_v[droite].mean()),
    }
    # poids : mapping des os gauche <-> droite
    def miroir_nom(n):
        if "Left" in n:
            return n.replace("Left", "Right")
        if "Right" in n:
            return n.replace("Right", "Left")
        return n
    idx_nom = {n: i for i, n in enumerate(noms)}
    corr_os = []
    for n in noms:
        if "Left" in n:
            m_ = miroir_nom(n)
            if m_ in idx_nom:
                corr_os.append((idx_nom[n], idx_nom[m_]))
    poids_gauche = np.array([W[gauche, a].sum() for a, b in corr_os])
    poids_droite = np.array([W[droite, b].sum() for a, b in corr_os])
    sym["poids_os_gauche_vs_droite"] = {"n_paires_os": len(corr_os),
                                        "somme_poids_gauche": float(poids_gauche.sum()),
                                        "somme_poids_droite": float(poids_droite.sum()),
                                        "difference_relative_moyenne": float(np.mean(np.abs(poids_gauche - poids_droite) /
                                                                                     (poids_gauche + poids_droite + 1e-12)))}

    out = {
        "convention": "x>0 = côté gauche (LeftUpLeg à x>0) ; plan de symétrie x=0 ; métriques A/B/C séparées",
        "sept_triangles": [list(s) for s in sept],
        "sommets_concernes": sommets7,
        "poses_retournement": poses_flip,
        "phase1_voisinage_et_temoins": temoins_resultat,
        "phase2_experiences": exp,
        "phase3_symetrie": sym,
        "phase4_metriques_ABC_par_occurrence": occ_abc,
        "phase4_controle_rigide_globale": controle_rigide,
    }
    with open(os.path.join(SORTIE, "geometrie_retournements.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    print("ECRIT", flush=True)

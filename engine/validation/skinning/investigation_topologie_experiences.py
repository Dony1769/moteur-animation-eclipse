"""Expériences contrôlées sur la topologie autour des sept triangles de Maria (phases 2 à 4).

Tout reste fixé (poids, os, transformations, LBS, Mv, Rsq de chaque pose) ; seul le graphe d'arêtes ou le paramètre
de contrainte change. Le solveur est une copie de solve_fixe avec λ par sommet ; une vérification assure qu'avec λ
uniforme il reproduit solve_fixe.

A. Composante native (ouverte) : doit reproduire le résultat du maillage complet.
B. Même composante avec frontières fermées (éventail depuis le centre de chaque boucle). Mesure du changement
   géométrique introduit (aire ajoutée, déplacement des sept triangles).
C. Contraintes de frontière explicites : λ différent sur les sommets de frontière (0,1 ; 1 ; 10 ; 1000).
D. Distance aux frontières : sous-domaines centrés sur les sept triangles (rayon de 1 à maximum anneaux). La distance
   aux frontières et la taille du domaine varient ensemble ; c'est indiqué comme confondu.
E. Taille du domaine sans couplage : ajout de composantes disjointes ; la solution des sept triangles doit rester
   identique si les blocs sont indépendants.
F. Dépendance de tous les retournements de Maria à la composante et à la distance aux frontières, sur les poses
   réelles et génératives.
"""
import importlib.util
import json
import os
from collections import deque

import numpy as np
import scipy.sparse as sp
from scipy.sparse.csgraph import connected_components
from scipy.sparse.linalg import factorized

HERE = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
SORTIE = os.path.join(RACINE, "docs", "rapports", "skinning", "topologie")


def charger(nom):
    spec = importlib.util.spec_from_file_location(nom, os.path.join(HERE, nom + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


CMP = charger("investigation_comparaison")
DEC = charger("investigation_decomposition")
G = charger("investigation_maria_geometrie")
LM = charger("investigation_lambda_morphos")
TD = charger("investigation_topologie_detail")


def solve_lam(lbs, rest, A, Rfix, lam_v):
    """Copie de solve_fixe avec λ par sommet (lam_v : vecteur de longueur N)."""
    a, b = A[:, 0], A[:, 1]
    N = len(rest)
    d0 = rest[a] - rest[b]
    deg = np.bincount(np.concatenate([a, b]), minlength=N).astype(float)
    Mm = sp.coo_matrix((np.concatenate([deg + lam_v, -np.ones(2 * len(a))]),
                        (np.concatenate([np.arange(N), a, b]), np.concatenate([np.arange(N), b, a]))),
                       shape=(N, N)).tocsc()
    solve = factorized(Mm)
    Rab = 0.5 * (Rfix[a] + Rfix[b])
    re = np.einsum("eij,ej->ei", Rab, d0)
    rhs = np.zeros((N, 3))
    np.add.at(rhs, a, re)
    np.add.at(rhs, b, -re)
    rhs += lam_v[:, None] * lbs
    return np.column_stack([solve(rhs[:, c]) for c in range(3)])


def mesure(rest, tris, lbs, sq, Mv, cible):
    f = G.flags(rest, tris, lbs, sq, Mv)
    return {"nouveau_A_sur_7": int(f["nouveau_A"][cible].sum()), "nouveau_A_total": int(f["nouveau_A"].sum()),
            "SQ_total": int(f["A_SQ"].sum()), "LBS_total": int(f["A_LBS"].sum())}, f


def fermer_boucles(rest, tris, lbs, Mv, R, t, comp_v, A):
    """Ferme les boucles de frontière d'une composante par un éventail depuis le centre de chaque boucle.
    Retourne rest, lbs, Rsq, tris et A augmentés ; les indices des sommets existants sont conservés."""
    e_dir = np.concatenate([tris[:, [0, 1]], tris[:, [1, 2]], tris[:, [2, 0]]])
    e_key = np.sort(e_dir, axis=1)
    u, inv, cnt = np.unique(e_key, axis=0, return_inverse=True, return_counts=True)
    bord_idx = np.where(cnt[inv] == 1)[0]
    bords = e_dir[bord_idx]  # arêtes frontière orientées comme dans leur triangle
    bords = bords[np.isin(bords[:, 0], comp_v)]
    # boucles : composantes du graphe des arêtes frontière
    Gb = sp.coo_matrix((np.ones(len(bords)), (bords[:, 0], bords[:, 1])), shape=(len(rest), len(rest)))
    _, lab = connected_components(Gb, directed=False)
    N0 = len(rest)
    nouveaux_r, nouveaux_l, nouveaux_mv, nouveaux_tris = [], [], [], []
    k_new = 0
    for L in np.unique(lab[bords[:, 0]]):
        be = bords[lab[bords[:, 0]] == L]
        vs = np.unique(be.ravel())
        c_rest = rest[vs].mean(0)
        # poids moyens de la boucle (les poids viennent de Mv et lbs : on prend la moyenne des Mv)
        mv_c = Mv[vs].mean(0)
        r_c = c_rest
        # lbs du nouveau sommet : moyenne des lbs des sommets de la boucle (déplacement moyen approximé par la
        # moyenne des positions déformées ; sert de cible d'ancrage)
        l_c = lbs[vs].mean(0)
        idx = N0 + k_new
        k_new += 1
        nouveaux_r.append(r_c)
        nouveaux_l.append(l_c)
        nouveaux_mv.append(mv_c)
        for (p, q) in be:
            nouveaux_tris.append([q, p, idx])
    rest2 = np.vstack([rest, np.array(nouveaux_r)])
    lbs2 = np.vstack([lbs, np.array(nouveaux_l)])
    Mv2 = np.concatenate([Mv, np.array(nouveaux_mv)])
    tris2 = np.vstack([tris, np.array(nouveaux_tris)])
    # arêtes du maillage fermé
    e2 = np.sort(np.concatenate([tris2[:, [0, 1]], tris2[:, [1, 2]], tris2[:, [2, 0]]]), axis=1)
    A2 = np.unique(e2, axis=0)
    return rest2, lbs2, Mv2, tris2, A2, len(nouveaux_r)


def poses_etude(M):
    noms = ["generative_hanche_G_105", "reelle_R_flex120", "reelle_L_flex120"]
    return {n: CMP.pose_de(M, n) if not n.startswith("generative") else LM.pose_hanche_G(M["z"], M["noms"], M["js"], 105)
            for n in noms}


if __name__ == "__main__":
    os.makedirs(SORTIE, exist_ok=True)
    M = CMP.charger_morph("maria")
    rest, tris, A, W, N = M["rest"], M["tris"], M["A"], M["W"], M["N"]
    labs = CMP.regions(M)
    nc, comp = TD.composantes(N, A)
    c45 = 45
    v45 = np.where(comp == c45)[0]
    sept = sorted({tuple(o["triangle"]) for o in json.load(open(TD.MECA, encoding="utf-8"))["triangles"]})
    # indices des 7 triangles (triangles ordonnés comme dans tris, par ensemble de sommets)
    cle = {tuple(sorted(t)): i for i, t in enumerate(tris)}
    cible = [cle[tuple(sorted(s))] for s in sept]
    cible = np.array(cible)
    res = {"composante_des_sept": sorted({int(comp[v]) for s in sept for v in s}), "poses": {}}

    poses = poses_etude(M)
    for nom, pm in poses.items():
        lbs, sq, Mv, R, t = CMP.evaluer(M, pm)
        Rsq = DEC.polaire_gen(Mv)
        # vérification : solve_lam (λ uniforme) = solve_fixe
        sq_chk = solve_lam(lbs, rest, A, Rsq, np.full(N, CMP.LAM))
        ecart = float(np.abs(sq_chk - sq).max())
        m_full, f_full = mesure(rest, tris, lbs, sq, Mv, cible)
        cpose = {"verif_solve_lam_vs_solve_fixe_m": ecart, "maillage_complet": m_full}

        # A. composante native seule (blocs) : doit coïncider avec le maillage complet
        mask_t = np.isin(tris[:, 0], v45) & np.isin(tris[:, 1], v45) & np.isin(tris[:, 2], v45)
        A45 = A[np.isin(A[:, 0], v45) & np.isin(A[:, 1], v45)]
        sub = solve_lam(lbs, rest, A45, Rsq, np.full(N, CMP.LAM))
        ecart_A = float(np.abs(sub[v45] - sq[v45]).max())
        cpose["A_composante_native"] = {"ecart_max_vs_maillage_complet_m": ecart_A,
                                        "nouveau_A_sur_7": int(f_full["nouveau_A"][cible].sum())}

        # E. domaine plus grand, composantes disjointes ajoutées : la solution des sept doit être invariante
        # E : ajout d'une composante disjointe (bassin) : la solution de la composante 45 doit être inchangée
        tailles_c = np.bincount(comp)
        tailles_c[c45] = 0
        c_autre = int(np.argmax(tailles_c))
        v_autre = np.where(comp == c_autre)[0]
        A_seul = A45
        A_deux = A[np.isin(A[:, 0], np.concatenate([v45, v_autre])) & np.isin(A[:, 1], np.concatenate([v45, v_autre]))]
        s_seul = solve_lam(lbs, rest, A_seul, Rsq, np.full(N, CMP.LAM))
        s_deux = solve_lam(lbs, rest, A_deux, Rsq, np.full(N, CMP.LAM))
        cpose["E_disjoint_invariance"] = {"composante_ajoutee": c_autre,
                                          "ecart_max_composante_45_m": float(np.abs(s_deux[v45] - s_seul[v45]).max()),
                                          "ecart_max_composante_ajoutee_m": float(np.abs(s_deux[v_autre] - s_seul[v_autre]).max())}

        # B. fermeture de la composante 45 par éventail (copie de la géométrie, pas une amélioration)
        r2, l2, mv2, t2, A2, nfill = fermer_boucles(rest, tris, lbs, Mv, R, t, v45, A45)
        Rsq2 = DEC.polaire_gen(mv2)
        A_close = A2[np.isin(A2[:, 0], np.concatenate([v45, np.arange(N, len(r2))])) &
                     np.isin(A2[:, 1], np.concatenate([v45, np.arange(N, len(r2))]))]
        sq2 = solve_lam(l2, r2, A_close, Rsq2, np.full(len(r2), CMP.LAM))
        m_c, f_c = mesure(r2, t2, l2, sq2, mv2, cible)
        d_sept = np.linalg.norm(sq2[np.unique(sept)] - sq[np.unique(sept)], axis=1)
        nt = t2[len(tris):]
        aire_ajoutee = float(0.5 * np.linalg.norm(np.cross(r2[nt[:, 1]] - r2[nt[:, 0]], r2[nt[:, 2]] - r2[nt[:, 0]]), axis=1).sum())
        cpose["B_fermee"] = {"boucles_fermees": int(nfill), "faces_ajoutees": int(len(t2) - len(tris)),
                             "aire_ajoutee_m2": aire_ajoutee, "maillage": m_c,
                             "deplacement_max_sept_sommets_m": float(d_sept.max()),
                             "deplacement_moyen_sept_sommets_m": float(d_sept.mean())}

        # C. contraintes de frontière explicites (λ sur frontière)
        tris45 = tris[mask_t]
        ed = np.sort(np.concatenate([tris45[:, [0, 1]], tris45[:, [1, 2]], tris45[:, [2, 0]]]), axis=1)
        uu, cc = np.unique(ed, axis=0, return_counts=True)
        bord45 = np.unique(uu[cc == 1].ravel())
        cpose["C_contraintes_frontiere"] = {}
        for lb in [0.1, 1.0, 10.0, 1000.0]:
            lam_v = np.full(N, CMP.LAM)
            lam_v[bord45] = lb
            s3 = solve_lam(lbs, rest, A45, Rsq, lam_v)
            m3, _ = mesure(rest, tris, lbs, s3, Mv, cible)
            cpose["C_contraintes_frontiere"][str(lb)] = {"nouveau_A_sur_7": m3["nouveau_A_sur_7"],
                                                          "deplacement_max_sept_m": float(np.linalg.norm(s3[np.unique(sept)] - sq[np.unique(sept)], axis=1).max())}

        # D. distance aux frontières : sous-domaines de rayon h (anneaux) autour des sept
        voisins = {}
        for a_, c_ in A45:
            voisins.setdefault(a_, []).append(c_)
            voisins.setdefault(c_, []).append(a_)
        centre = set(np.unique(np.array(sept)).tolist())
        niveau = {v: 0 for v in centre}
        fil = deque(centre)
        while fil:
            u_ = fil.popleft()
            for v in voisins.get(u_, []):
                if v not in niveau:
                    niveau[v] = niveau[u_] + 1
                    fil.append(v)
        hmax = max(niveau.values())
        cpose["D_rayon"] = {}
        for h in range(1, hmax + 1):
            keep = np.array([v for v in v45 if niveau.get(v, 99) <= h])
            kmask = np.zeros(N, bool)
            kmask[keep] = True
            tk = tris[kmask[tris[:, 0]] & kmask[tris[:, 1]] & kmask[tris[:, 2]]]
            if len(tk) == 0:
                continue
            ek = np.sort(np.concatenate([tk[:, [0, 1]], tk[:, [1, 2]], tk[:, [2, 0]]]), axis=1)
            Ak = np.unique(ek, axis=0)
            sh = solve_lam(lbs, rest, Ak, Rsq, np.full(N, CMP.LAM))
            fS = G.flags(rest, tk, lbs, sh, Mv)
            # comptage sur les sept (dans le sous-domaine) : retrouver leur indice dans tk
            cle_k = {tuple(sorted(t)): i for i, t in enumerate(tk)}
            idx_k = [cle_k[tuple(sorted(sept[j]))] for j in range(len(sept)) if tuple(sorted(sept[j])) in cle_k]
            # distance au bord du sous-domaine des sept
            bk = tk
            ebk = np.sort(np.concatenate([bk[:, [0, 1]], bk[:, [1, 2]], bk[:, [2, 0]]]), axis=1)
            uk, ck_ = np.unique(ebk, axis=0, return_counts=True)
            cpose["D_rayon"][str(h)] = {"sommets": int(kmask.sum()), "faces": int(len(tk)),
                                        "aretes_frontiere": int((ck_ == 1).sum()),
                                        "sept_dans_domaine": int(len(idx_k)),
                                        "nouveau_A_sur_7_dans_domaine": int(fS["nouveau_A"][idx_k].sum()) if idx_k else 0,
                                        "nouveau_A_total_domaine": int(fS["nouveau_A"].sum())}
        res["poses"][nom] = cpose
        print(nom, {k: (v if not isinstance(v, dict) else "...") for k, v in cpose.items()}, flush=True)
        print("  A", cpose["A_composante_native"], " B", {k: v for k, v in cpose["B_fermee"].items() if k != "maillage"},
              "maillage_ferme", cpose["B_fermee"]["maillage"]["nouveau_A_sur_7"], flush=True)
        print("  C", {k: v["nouveau_A_sur_7"] for k, v in cpose["C_contraintes_frontiere"].items()}, flush=True)
        print("  D", {k: v["nouveau_A_sur_7_dans_domaine"] for k, v in cpose["D_rayon"].items()}, flush=True)

    with open(os.path.join(SORTIE, "experiences_topologie.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1, ensure_ascii=False, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    print("ECRIT", flush=True)

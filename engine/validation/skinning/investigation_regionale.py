"""Phase 3 et 4 : comparaison régionale complète (trois morphologies, 29 poses, mêmes métriques) et vérification de la
mesure du volume (fermeture, orientation, composantes, volume signé).

Métriques par région (région = comparaison.regions) :
  - nombre d'arêtes (≥ 5 mm), nombre régressées (SQ − LBS > 0,05), % amélioration (< −0,02), % régression (> 0,05) ;
  - percentiles 50/90/95/99 de SQ − LBS, non pondérés ET pondérés par la longueur de repos ;
  - déplacement absolu (m) moyen des extrémités, et normalisé par la distance entre hanches ;
  - triangles retournés (LBS, SQ, nouveaux) ;
  - déformation surfacique : écart moyen |log(aire SQ / aire repos)| pondéré par l'aire de repos ;
  - répartition des régressions : arête mixte directe / arête à poids purs proche d'une zone mixte (propagation,
    distance de graphe 1 à 3) / arête à poids purs éloignée (> 3 anneaux).
Volume : fermeture (arêtes frontière, non-variétés), cohérence d'orientation (arêtes parcourues dans le même sens
par deux faces), composantes connexes, volume signé calculé avec la même origine pour LBS et SQ. Un volume est marqué
non fiable si la surface n'est pas fermée ou si l'orientation n'est pas cohérente.
"""
import importlib.util
import json
import os

import numpy as np
import scipy.sparse as sp
from scipy.sparse.csgraph import connected_components


def distance_multi(G, src, N):
    """Distance en arêtes à l'ensemble src (BFS multi-sources, indépendant de la version de scipy)."""
    d = np.full(N, np.inf)
    d[src] = 0
    front = np.asarray(src)
    k = 0
    while front.size:
        k += 1
        nb = np.unique(G[front].indices)
        new = nb[np.isinf(d[nb])]
        d[new] = k
        front = new
    return d

HERE = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
SORTIE = os.path.join(RACINE, "docs", "rapports", "skinning", "regionale")


def charger(nom):
    spec = importlib.util.spec_from_file_location(nom, os.path.join(HERE, nom + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


DEC = charger("investigation_decomposition")
CMP = charger("investigation_comparaison")
MORPHS = ["masculin", "feminin", "maria"]


def quantile_pondere(x, w, q):
    o = np.argsort(x)
    x, w = x[o], w[o]
    cw = np.cumsum(w)
    cw = cw / cw[-1]
    return float(np.interp(q, cw, x))


def pcts(x, w=None):
    if len(x) == 0:
        return None
    if w is None:
        return {f"p{p}": float(np.quantile(x, p / 100)) for p in (50, 90, 95, 99)}
    return {f"p{p}": quantile_pondere(x, w, p / 100) for p in (50, 90, 95, 99)}


def topologie(M):
    """Arêtes frontière, non-variétés, cohérence d'orientation, composantes, depuis les polygones d'origine."""
    b, tot = M["b"], M["tot"]
    debut = np.concatenate([[0], np.cumsum(tot)[:-1]])
    cnt = {}
    dirs = {}
    for d0, n in zip(debut, tot):
        p = b[d0:d0 + n]
        for k in range(n):
            u, v = int(p[k]), int(p[(k + 1) % n])
            key = (min(u, v), max(u, v))
            cnt[key] = cnt.get(key, 0) + 1
            dirs.setdefault(key, []).append((u, v))
    frontiere = sum(1 for k, n in cnt.items() if n == 1)
    non_var = sum(1 for k, n in cnt.items() if n > 2)
    incoh = 0
    for k, lst in dirs.items():
        if len(lst) == 2 and lst[0] == lst[1]:
            incoh += 1
    N = M["N"]
    rows = [k[0] for k in cnt]
    cols = [k[1] for k in cnt]
    G = sp.coo_matrix((np.ones(len(rows)), (rows, cols)), shape=(N, N))
    ncomp, etiq = connected_components(G, directed=False)
    tailles = np.bincount(etiq)
    return {"aretes": len(cnt), "aretes_frontiere": int(frontiere), "aretes_non_variete": int(non_var),
            "aretes_orientation_incoherente": int(incoh), "surface_fermee": bool(frontiere == 0 and non_var == 0),
            "orientation_coherente": bool(incoh == 0), "composantes": int(ncomp),
            "tailles_composantes_top5": sorted(tailles.tolist(), reverse=True)[:5]}


def volume_signe(p, b, tot, origine):
    debut = np.concatenate([[0], np.cumsum(tot)[:-1]])
    v = 0.0
    for d0, n in zip(debut, tot):
        q = p[b[d0:d0 + n]] - origine
        for k in range(1, n - 1):
            v += np.dot(q[0], np.cross(q[k], q[k + 1])) / 6.0
    return float(v)


if __name__ == "__main__":
    os.makedirs(SORTIE, exist_ok=True)
    out = {"protocole": {"poses": CMP.POSES, "lambda": CMP.LAM, "normalisation": "distance entre hanches",
                         "regions": "comparaison.regions", "arete_ge5mm": True},
           "phase3": {}, "phase4_volume": {}}
    for m in MORPHS:
        M = CMP.charger_morph(m)
        rest, A, tris, W, b, tot = M["rest"], M["A"], M["tris"], M["W"], M["b"], M["tot"]
        a, c = A[:, 0], A[:, 1]
        N = M["N"]
        labs = CMP.regions(M)
        pur = W.max(1) > 1 - 1e-6
        # distance de graphe (en arêtes) à la zone mixte la plus proche
        Gr = sp.coo_matrix((np.ones(len(A)), (a, c)), shape=(N, N)).tocsr()
        Gr = Gr + Gr.T
        src = np.where(~pur)[0]
        dist_mixte = distance_multi(Gr, src, N)
        lr = np.linalg.norm(rest[a] - rest[c], axis=1)
        ok5 = lr >= 0.005
        # arête « directe mixte » : au moins une extrémité à poids mixtes
        mixte = (~pur[a]) | (~pur[c])
        dmin = np.minimum(dist_mixte[a], dist_mixte[c])
        classe = np.where(mixte, "directe_mixte",
                          np.where(dmin <= 3, "propagee_pure_anneau1_3", "pure_eloignee"))
        er = np.where(labs[a] == labs[c], labs[a], "frontiere")
        tf = np.array([labs[t[0]] if labs[t[0]] == labs[t[1]] == labs[t[2]] else "frontiere" for t in tris], dtype=object)
        aire0 = 0.5 * np.linalg.norm(np.cross(rest[tris[:, 1]] - rest[tris[:, 0]], rest[tris[:, 2]] - rest[tris[:, 0]]), axis=1)
        hd = M["hipd"]
        # accumulateurs par région (sur les 29 poses)
        acc = {}
        topo = topologie(M)
        origine = rest.mean(0)
        vol = {"topologie": topo, "origine_m": origine.round(4).tolist(), "par_pose": {}}
        vol["volume_repos"] = volume_signe(rest, b, tot, origine)
        for nom in CMP.POSES:
            pm = CMP.pose_de(M, nom)
            lbs, sq, Mv, R, t = CMP.evaluer(M, pm)
            exc = np.linalg.norm(sq[a] - sq[c], axis=1) / np.maximum(lr, 1e-12) - np.linalg.norm(lbs[a] - lbs[c], axis=1) / np.maximum(lr, 1e-12)
            dep = np.linalg.norm(sq - lbs, axis=1)
            depe = 0.5 * (dep[a] + dep[c])
            # triangles : retournements et déformation surfacique
            n0 = np.cross(rest[tris[:, 1]] - rest[tris[:, 0]], rest[tris[:, 2]] - rest[tris[:, 0]])
            nL = np.cross(lbs[tris[:, 1]] - lbs[tris[:, 0]], lbs[tris[:, 2]] - lbs[tris[:, 0]])
            nS = np.cross(sq[tris[:, 1]] - sq[tris[:, 0]], sq[tris[:, 2]] - sq[tris[:, 0]])
            Mt = Mv[tris].mean(1)
            ref = np.einsum("tij,tj->ti", DEC.polaire_gen(Mt), n0 / np.maximum(np.linalg.norm(n0, axis=1, keepdims=True), 1e-300))
            fL = np.einsum("ti,ti->t", nL, ref) < 0
            fS = np.einsum("ti,ti->t", nS, ref) < 0
            aS = 0.5 * np.linalg.norm(nS, axis=1)
            dS = np.abs(np.log(np.maximum(aS, 1e-300) / np.maximum(aire0, 1e-300)))
            for reg in sorted(set(er)) + ["__tous__"]:
                me = (er == reg) if reg != "__tous__" else np.ones(len(er), bool)
                me = me & ok5
                mt = (tf == reg) if reg != "__tous__" else np.ones(len(tf), bool)
                if reg == "__tous__":
                    pass
                key = reg
                d = acc.setdefault(key, {"exc": [], "lr": [], "dep": [], "depn": [], "classe": [], "fL": 0, "fS": 0,
                                         "nouv": 0, "dS": [], "w_aire": [], "tri_n": 0})
                d["exc"].append(exc[me]); d["lr"].append(lr[me]); d["classe"].append(classe[me])
                d["dep"].append(depe[me]); d["depn"].append(depe[me] / hd)
                d["fL"] += int((fL & mt).sum()); d["fS"] += int((fS & mt).sum())
                d["nouv"] += int(((fS & ~fL) & mt).sum())
                d["dS"].append(dS[mt]); d["w_aire"].append(aire0[mt]); d["tri_n"] += int(mt.sum())
            vol["par_pose"][nom] = {
                "volume_LBS": volume_signe(lbs, b, tot, origine),
                "volume_SQ": volume_signe(sq, b, tot, origine),
            }
        res_m = {}
        for reg, d in acc.items():
            exc = np.concatenate(d["exc"]); lrr = np.concatenate(d["lr"]); cl = np.concatenate(d["classe"])
            dep = np.concatenate(d["dep"]); depn = np.concatenate(d["depn"])
            dS = np.concatenate(d["dS"]); wa = np.concatenate(d["w_aire"])
            n = len(exc)
            reg_ = exc > 0.05
            ame = exc < -0.02
            res_m[reg] = {
                "aretes": int(n),
                "aretes_regressees": int(reg_.sum()),
                "pourcentage_amelioration": float(ame.mean()) if n else None,
                "pourcentage_regression": float(reg_.mean()) if n else None,
                "pourcentage_regression_ponderee_longueur": float((lrr * reg_).sum() / max(lrr.sum(), 1e-300)) if n else None,
                "pourcentage_amelioration_ponderee_longueur": float((lrr * ame).sum() / max(lrr.sum(), 1e-300)) if n else None,
                "exc_percentiles_non_ponderes": pcts(exc),
                "exc_percentiles_ponderes_longueur": pcts(exc, lrr),
                "deplacement_absolu_m_moyen": float(dep.mean()) if n else None,
                "deplacement_absolu_m_p99": float(np.quantile(dep, 0.99)) if n else None,
                "deplacement_normalise_hanche_p99": float(np.quantile(depn, 0.99)) if n else None,
                "triangles": int(d["tri_n"]),
                "retournements_LBS": int(d["fL"]), "retournements_SQ": int(d["fS"]), "retournements_nouveaux_SQ": int(d["nouv"]),
                "deformation_surfacique_ponderee_aire": float((dS * wa).sum() / max(wa.sum(), 1e-300)) if len(dS) else None,
                "regressions_par_classe": {k: int((reg_ & (cl == k)).sum()) for k in
                                           ["directe_mixte", "propagee_pure_anneau1_3", "pure_eloignee"]},
                "aretes_par_classe": {k: int((cl == k).sum()) for k in
                                      ["directe_mixte", "propagee_pure_anneau1_3", "pure_eloignee"]},
            }
        out["phase3"][m] = res_m
        # volume : comparaison à même méthode
        vL = np.array([vol["par_pose"][p]["volume_LBS"] for p in CMP.POSES])
        vS = np.array([vol["par_pose"][p]["volume_SQ"] for p in CMP.POSES])
        rel = lambda v: (v - vol["volume_repos"]) / abs(vol["volume_repos"])
        vol["fiable"] = bool(topo["surface_fermee"] and topo["orientation_coherente"])
        vol["variation_relative_moyenne_LBS"] = float(rel(vL).mean())
        vol["variation_relative_moyenne_SQ"] = float(rel(vS).mean())
        vol["avertissement"] = ("volume non fiable : surface non fermée ou orientation incohérente"
                                if not vol["fiable"] else "volume signé sur surface fermée orientée")
        out["phase4_volume"][m] = vol
        print(m, "topologie", topo, "fiable", vol["fiable"], flush=True)
        for reg in ["entrejambe", "hanche_G", "hanche_D", "genou_G", "genou_D", "cuisse_G", "cuisse_D", "bassin", "frontiere", "autre"]:
            if reg in res_m:
                r = res_m[reg]
                print(f"  {reg:10s} n={r['aretes']:7d} reg={r['aretes_regressees']:5d} amél={r['pourcentage_amelioration']:.3f} "
                      f"aggr={r['pourcentage_regression']:.3f} aggr_pond={r['pourcentage_regression_ponderee_longueur']:.4f} "
                      f"nouv={r['retournements_nouveaux_SQ']} classes={r['regressions_par_classe']}", flush=True)
    with open(os.path.join(SORTIE, "regionale.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    print("ECRIT", flush=True)

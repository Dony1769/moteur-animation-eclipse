"""Phase 1 (complément) et phase 5 : mécanisme des 32 retournements SQ nouveaux de Maria.

1. Pour chaque retournement nouveau : produit scalaire normale SQ / normale LBS (retournement relatif à la forme LBS
   ou seulement relatif au repère de référence), angles de rotation des deux os dominants, mélange des poids.
2. Corrélations (AUC de Mann-Whitney) entre retournement et caractéristiques, sur les triangles de la même zone
   (entrejambe) pendant les poses où un retournement nouveau apparaît : observations, pas mécanisme.
3. Expérience contrôlée : on remplace, dans une pose donnée, les poids mixtes des sommets des triangles concernés par
   leur os dominant (affectation dure), et on recompte les retournements nouveaux sur les mêmes triangles. Un contrôle
   applique la même opération à un ensemble de sommets de même taille choisi hors de la zone.
Aucun seuil n'est modifié ; l'algorithme SQ n'est pas changé.
"""
import importlib.util
import json
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
SORTIE = os.path.join(RACINE, "docs", "rapports", "skinning", "maria_retournements")


def charger(nom):
    import importlib.util as iu
    spec = iu.spec_from_file_location(nom, os.path.join(HERE, nom + ".py"))
    m = iu.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


DEC = charger("investigation_decomposition")
CMP = charger("investigation_comparaison")


def normales(p, tris):
    return np.cross(p[tris[:, 1]] - p[tris[:, 0]], p[tris[:, 2]] - p[tris[:, 0]])


def unit(v):
    return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-300)


def angle_rot(R):
    c = np.clip((np.trace(R, axis1=-2, axis2=-1) - 1) / 2, -1, 1)
    return np.degrees(np.arccos(c))


def auc(pos, neg):
    """AUC de Mann-Whitney : probabilité qu'un positif dépasse un négatif (0,5 = pas de séparation)."""
    if len(pos) == 0 or len(neg) == 0:
        return None
    x = np.concatenate([pos, neg])
    r = np.argsort(np.argsort(x)) + 1.0
    # rangs moyens pour les ex aequo
    _, inv, cnt = np.unique(x, return_inverse=True, return_counts=True)
    somme = np.bincount(inv, weights=r)
    rang = somme[inv] / cnt[inv]
    return float((rang[:len(pos)].sum() - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg)))


if __name__ == "__main__":
    os.makedirs(SORTIE, exist_ok=True)
    M = CMP.charger_morph("maria")
    rest, tris, W, A = M["rest"], M["tris"], M["W"], M["A"]
    labs = CMP.regions(M)
    ent = np.array([labs[t[0]] == "entrejambe" and labs[t[1]] == "entrejambe" and labs[t[2]] == "entrejambe" for t in tris])
    n0 = normales(rest, tris)
    dom = W.argmax(1)

    # distances de graphe pour la propagation : sommets adjacents
    pose_info = []
    nouveaux_detail = []
    features_pos, features_neg = {}, {}
    poses_avec = []
    for nom in CMP.POSES:
        pm = CMP.pose_de(M, nom)
        lbs, sq, Mv, R, t = CMP.evaluer(M, pm)
        nL, nS = normales(lbs, tris), normales(sq, tris)
        Mt = Mv[tris].mean(1)
        ref = np.einsum("tij,tj->ti", DEC.polaire_gen(Mt), unit(n0))
        fL = np.einsum("ti,ti->t", nL, ref) < 0
        fS = np.einsum("ti,ti->t", nS, ref) < 0
        nouv = fS & ~fL
        if nouv.sum() == 0:
            continue
        poses_avec.append(nom)
        dotLS = np.einsum("ti,ti->t", unit(nS), unit(nL))
        aS = 0.5 * np.linalg.norm(nS, axis=1)
        aL = 0.5 * np.linalg.norm(nL, axis=1)
        a0 = 0.5 * np.linalg.norm(n0, axis=1)
        sv = np.linalg.svd(Mt, compute_uv=False)
        # caractéristiques par triangle
        mix = 1 - W.max(1)
        mixt = mix[tris].mean(1)
        angles = angle_rot(R)  # (K,)
        ang_dom = angles[dom[tris]]  # (T,3)
        ang_dom_max = ang_dom.max(1)
        # angle relatif entre os dominants des sommets
        rel = np.zeros(len(tris))
        for k, tr in enumerate(tris):
            d = dom[tr]
            Rr = np.einsum("ji,kjl->kil", R[d[0]], R[d[1:]])  # R_d0^T R_dk
            rel[k] = np.max(angle_rot(Rr)) if len(d) else 0
        # ratio d'aire : SQ / repos et LBS / repos
        rS = aS / np.maximum(a0, 1e-300)
        rL = aL / np.maximum(a0, 1e-300)
        cote = np.linalg.norm(rest[tris[:, 1]] - rest[tris[:, 0]], axis=1)
        aspect = np.min([np.linalg.norm(rest[tris[:, 1]] - rest[tris[:, 0]], axis=1),
                         np.linalg.norm(rest[tris[:, 2]] - rest[tris[:, 1]], axis=1),
                         np.linalg.norm(rest[tris[:, 0]] - rest[tris[:, 2]], axis=1)], axis=0) / np.maximum(
            np.max([np.linalg.norm(rest[tris[:, 1]] - rest[tris[:, 0]], axis=1),
                    np.linalg.norm(rest[tris[:, 2]] - rest[tris[:, 1]], axis=1),
                    np.linalg.norm(rest[tris[:, 0]] - rest[tris[:, 2]], axis=1)], axis=0), 1e-300)
        sv_min = np.linalg.svd(Mt, compute_uv=False)[:, -1]
        sv_max = np.linalg.svd(Mt, compute_uv=False)[:, 0]
        # détail des nouveaux retournements
        for ti in np.where(nouv)[0]:
            i, j, k = tris[ti]
            nouveaux_detail.append({
                "pose": nom, "triangle": [int(i), int(j), int(k)],
                "dot_SQ_LBS": round(float(dotLS[ti]), 4),
                "retournement_relatif_LBS": bool(dotLS[ti] < 0),
                "retournement_seulement_repere": bool(dotLS[ti] >= 0),
                "mixage_moyen": round(float(mixt[ti]), 4),
                "angle_dominant_max_deg": round(float(ang_dom_max[ti]), 2),
                "angle_relatif_os_deg": round(float(rel[ti]), 2),
                "ratio_aire_SQ": round(float(rS[ti]), 4),
                "ratio_aire_LBS": round(float(rL[ti]), 4),
                "sv_min_Mv": round(float(sv_min[ti]), 4),
                "sv_max_Mv": round(float(sv_max[ti]), 4),
                "rapport_aspect_repos": round(float(aspect[ti]), 4),
            })
        # corrélations : triangles de l'entrejambe de cette pose
        sel = ent
        for nm, val in {"mixage_moyen": mixt, "angle_dominant_max_deg": ang_dom_max, "angle_relatif_os_deg": rel,
                        "ratio_aire_SQ": rS, "ratio_aire_LBS": rL, "sv_min_Mv": sv_min,
                        "rapport_aspect_repos": aspect}.items():
            features_pos.setdefault(nm, []).append(val[sel & nouv])
            features_neg.setdefault(nm, []).append(val[sel & ~fS])

    # AUC par caractéristique (positifs = nouveaux retournements, négatifs = triangles entrejambe sans retournement SQ)
    corr = {}
    for nm in features_pos:
        p = np.concatenate(features_pos[nm]) if features_pos[nm] else np.array([])
        q = np.concatenate(features_neg[nm]) if features_neg[nm] else np.array([])
        corr[nm] = {"AUC": auc(p, q), "median_positifs": float(np.median(p)) if len(p) else None,
                    "median_negatifs": float(np.median(q)) if len(q) else None,
                    "n_positifs": int(len(p)), "n_negatifs": int(len(q))}

    # expérience contrôlée : affectation dure des poids mixtes des sommets concernés
    sommets_concernes = sorted({v for d in nouveaux_detail for v in d["triangle"]})
    ensemble_controle = np.array([v for v in range(M["N"]) if labs[v] == "entrejambe" and v not in set(sommets_concernes)])
    rng = np.random.default_rng(0)
    ctrl = rng.choice(ensemble_controle, size=min(len(sommets_concernes), len(ensemble_controle)), replace=False)
    exp = {"n_sommets_concernes": len(sommets_concernes), "n_controle": int(len(ctrl)), "poses": {}}
    for nom in poses_avec:
        pm = CMP.pose_de(M, nom)
        lbs0, sq0, Mv0, _, _ = CMP.evaluer(M, pm)
        nL0, nS0 = normales(lbs0, tris), normales(sq0, tris)
        Mt0 = Mv0[tris].mean(1)
        ref0 = np.einsum("tij,tj->ti", DEC.polaire_gen(Mt0), unit(n0))
        nouv0 = (np.einsum("ti,ti->t", nS0, ref0) < 0) & ~(np.einsum("ti,ti->t", nL0, ref0) < 0)
        base = int(nouv0.sum())

        def comptage(vs):
            Wh = M["W"].copy()
            for v in vs:
                Wh[v] = 0
                Wh[v, dom[v]] = 1
            l2, s2, M2, _, _ = CMP.evaluer(M, pm, W=Wh)
            nL2, nS2 = normales(l2, tris), normales(s2, tris)
            Mt2 = M2[tris].mean(1)
            r2 = np.einsum("tij,tj->ti", DEC.polaire_gen(Mt2), unit(n0))
            fL2 = np.einsum("ti,ti->t", nL2, r2) < 0
            fS2 = np.einsum("ti,ti->t", nS2, r2) < 0
            return int((fS2 & ~fL2).sum()), int((fS2 & ~fL2)[nouv0].sum())

        n_hard, rest_hard = comptage(sommets_concernes)
        n_ctrl, _ = comptage(ctrl)
        exp["poses"][nom] = {"nouveaux_base": base, "nouveaux_apres_affectation_dure_sommets_concernes": n_hard,
                             "nouveaux_apres_affectation_dure_controle": n_ctrl}
        print(nom, exp["poses"][nom], flush=True)

    res = {
        "convention": "retournement : normale déformée opposée à la normale de référence polaire(Mv_moyen) appliquée à la normale de repos",
        "poses_avec_nouveaux": poses_avec,
        "nombre_nouveaux_detail": len(nouveaux_detail),
        "retournements_relatifs_LBS": int(sum(d["retournement_relatif_LBS"] for d in nouveaux_detail)),
        "retournements_seulement_repere": int(sum(d["retournement_seulement_repere"] for d in nouveaux_detail)),
        "sommets_concernes": sommets_concernes,
        "triangles": nouveaux_detail,
        "correlations_entrejambe_AUC": corr,
        "experience_affectation_dure": exp,
    }
    with open(os.path.join(SORTIE, "mecanisme_retournements.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1, ensure_ascii=False, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    print("relatifs LBS", res["retournements_relatifs_LBS"], "seulement repère", res["retournements_seulement_repere"])
    for k, v in corr.items():
        print(k, v)
    print("ECRIT", flush=True)

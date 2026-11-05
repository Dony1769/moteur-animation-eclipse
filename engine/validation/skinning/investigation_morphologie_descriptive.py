"""Comparaison descriptive, sur les maillages NATIFS, de l'entrejambe masculin et féminin.

Aucune correspondance entre les deux maillages n'est utilisée (leur plus proche voisin a une erreur médiane de 2 cm,
supérieure à une arête : voir RAPPORT_factorielle.md). Chaque morphologie est décrite par ses propres indices.

Région R : sommets à deux influences de cuisse (poids G et D > 0), élargie d'un voisinage (1 anneau).
Mesures : densité, longueurs et orientations d'arêtes, formes des quads, courbure (1 − cos entre normales de
polygones adjacentes), valence, distances aux centres articulaires réels, disposition spatiale des sommets mixtes,
histogramme des poids G, gradients de poids sur les arêtes mixtes.
"""
import importlib.util
import json
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
SORTIE = os.path.join(RACINE, "docs", "rapports", "skinning", "factorielle")
DONNEES = os.environ.get("ANATOMIE_DONNEES", "/tmp/claude-0/-home-claude/9ce8e1e5-f7cf-5619-8a75-3c6d9a11ab1c/scratchpad")


def charger(nom):
    spec = importlib.util.spec_from_file_location(nom, os.path.join(HERE, nom + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


P = charger("poses_articulaires")
EXP = charger("experience_corrections_articulaires")
Ms = charger("mesures")


def polygones(b, tot):
    debut = np.concatenate([[0], np.cumsum(tot)[:-1]])
    return [b[d0:d0 + n] for d0, n in zip(debut, tot)]


def decrire(nom, npz, js_rel):
    z = np.load(os.path.join(DONNEES, npz))
    noms = [str(n) for n in z["noms_os"]]
    rest, Wi, Ww = z["rest_monde"], z["W_idx"], z["W_w"]
    b, tot = z["b_boucle"], z["b_tot"]
    N = len(rest)
    gG, gD = noms.index("mixamorig:LeftUpLeg"), noms.index("mixamorig:RightUpLeg")
    wG = np.where(Wi == gG, Ww, 0).sum(1)
    wD = np.where(Wi == gD, Ww, 0).sum(1)
    mixte = (wG > 1e-6) & (wD > 1e-6)
    A = Ms.aretes(b, tot, N)
    a, c = A[:, 0], A[:, 1]
    voisin = np.zeros(N, bool)
    voisin[mixte] = True
    voisin[a[mixte[a]]] = True
    voisin[c[mixte[c]]] = True
    voisin[c[voisin[a]]] = True
    voisin[a[voisin[c]]] = True
    R = voisin
    er = np.linalg.norm(rest[a] - rest[c], axis=1)
    arR = R[a] & R[c]
    polys = polygones(b, tot)
    # normales de polygones et courbure
    normales = []
    for p_ in polys:
        v = rest[p_]
        n_ = np.cross(v[1] - v[0], v[2] - v[0])
        normales.append(n_ / max(np.linalg.norm(n_), 1e-12))
    normales = np.array(normales)
    som_normales = [[] for _ in range(N)]
    for k, p_ in enumerate(polys):
        for v_ in p_:
            som_normales[v_].append(k)
    courbure = np.zeros(N)
    for v_ in range(N):
        ks = som_normales[v_]
        if len(ks) > 1:
            n_ = normales[ks]
            courbure[v_] = float(np.mean(1 - (n_ @ n_.T)[np.triu_indices(len(ks), 1)]))
    valence = np.bincount(np.concatenate([a, c]), minlength=N)
    # forme des polygones : rapport max/min des arêtes
    rap = []
    for p_ in polys:
        if p_.shape[0] >= 3:
            l_ = [np.linalg.norm(rest[p_[k]] - rest[p_[(k + 1) % len(p_)]]) for k in range(len(p_))]
            rap.append(max(l_) / max(min(l_), 1e-12))
    rap = np.array(rap)
    # centres articulaires réels de cette morphologie
    js = os.path.join(RACINE, js_rel)
    cG, _, _ = P.articulation(js, EXP.prefixe(noms) + "LeftUpLeg")
    cD, _, _ = P.articulation(js, EXP.prefixe(noms) + "RightUpLeg")
    dG = np.linalg.norm(rest - cG, axis=1)
    dD = np.linalg.norm(rest - cD, axis=1)
    dmin = np.minimum(dG, dD)
    m_ = mixte
    centre_mix = rest[m_].mean(0)
    ecart_mix = rest[m_].std(0)
    milieu = (cG + cD) / 2
    dist_milieu = np.linalg.norm(rest[m_] - milieu, axis=1)
    mixA = m_[a] & m_[c]
    gradient = np.abs(wG[a] - wG[c]) / np.maximum(er, 1e-12)
    histo, _ = np.histogram(wG[m_], bins=10, range=(0, 1))
    return {
        "nom": nom, "N": int(N), "polygones": int(len(polys)),
        "quads": int(np.sum(tot == 4)), "triangles": int(np.sum(tot == 3)),
        "bbox_min": rest.min(0).round(4).tolist(), "bbox_max": rest.max(0).round(4).tolist(),
        "centres_hanche_G": cG.round(4).tolist(), "centres_hanche_D": cD.round(4).tolist(),
        "region_R_sommets": int(R.sum()), "region_R_mixtes": int(m_.sum()),
        "mixtes_equilibres_0.4_0.6": int((m_ & (wG >= 0.4) & (wG <= 0.6)).sum()),
        "region_R_aretes": int(arR.sum()),
        "aretes_mediane_m": float(np.median(er[arR])), "aretes_p10_m": float(np.quantile(er[arR], 0.1)),
        "aretes_p90_m": float(np.quantile(er[arR], 0.9)),
        "aretes_direction_mixte_axe_x_moyenne": float(np.mean(np.abs((rest[a[arR]] - rest[c[arR]])[:, 0]) / np.maximum(er[arR], 1e-12))),
        "polygone_rapport_max_min_mediane_R": float(np.median(rap[np.array([R[p_].all() for p_ in polys])])) if any(R[p_].all() for p_ in polys) else None,
        "courbure_mediane_R": float(np.median(courbure[R])),
        "courbure_mediane_global": float(np.median(courbure)),
        "valence_mediane_R": float(np.median(valence[R])),
        "valence_repartition_global": np.bincount(valence).tolist()[:9],
        "mixtes_centroide": centre_mix.round(4).tolist(),
        "mixtes_etendue_std": ecart_mix.round(4).tolist(),
        "mixtes_distance_milieu_hanches_mediane": float(np.median(dist_milieu)),
        "mixtes_distance_min_centre_mediane": float(np.median(dmin[m_])),
        "mixtes_aretes_nb": int(mixA.sum()),
        "mixtes_gradient_poids_mediane_par_m": float(np.median(gradient[mixA])),
        "mixtes_gradient_poids_p90_par_m": float(np.quantile(gradient[mixA], 0.9)),
        "histogramme_wG_mixtes_10_classes": histo.tolist(),
    }


if __name__ == "__main__":
    os.makedirs(SORTIE, exist_ok=True)
    res = {
        "masculin": decrire("masculin", "skin/poses2.npz", "docs/rapports/skinning/anatomie/squelette_masc.json"),
        "feminin": decrire("feminin", "morpho/femme.npz", "docs/rapports/skinning/anatomie/squelette_fem.json"),
    }
    with open(os.path.join(SORTIE, "descriptif_morphologies.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1, ensure_ascii=False)
    for k, v in res.items():
        print(k, {kk: vv for kk, vv in v.items() if kk not in ("bbox_min", "bbox_max")}, flush=True)
    print("ECRIT", flush=True)

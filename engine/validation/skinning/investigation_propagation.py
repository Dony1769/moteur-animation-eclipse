"""Test de propagation : SQ étire-t-il les sommets défectueux à cause de leurs voisins ?

Pour chaque arête incidente aux défauts, classe chaque extrémité selon ses poids de cuisse :
  G : cuisse gauche seule ; D : cuisse droite seule ; mixte : les deux ; autre.
Mesure, à poids originaux (base) puis à poids synthétiques (t = 0, cuisse droite seule pour les sommets mixtes) :
  - l'amplification SQ − LBS par classe d'arête,
  - le déplacement SQ − LBS de chaque extrémité défectueuse, par classe.
Aucun critère, aucune méthode de référence modifiée.
"""
import importlib.util
import json
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
SORTIE = os.path.join(RACINE, "docs", "rapports", "skinning", "decomposition_hanche_masc")


def charger(nom):
    spec = importlib.util.spec_from_file_location(nom, os.path.join(HERE, nom + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


DEC = charger("investigation_decomposition")
INV = DEC.INV
ARAP = INV.ARAP


def med(x):
    return float(np.median(x)) if len(x) else None


if __name__ == "__main__":
    os.makedirs(SORTIE, exist_ok=True)
    z, noms, rest, Wi, Ww, B, b, tot, A, sortie = INV.tous_les_defauts()
    N = len(rest)
    D = np.array(sortie["defauts_union"], int)
    pm, _, _, _ = INV.pose_test(z, noms, INV.JSON_SQ, "hanche_G", 120)
    a, c = A[:, 0], A[:, 1]
    gG, gD = noms.index("mixamorig:LeftUpLeg"), noms.index("mixamorig:RightUpLeg")
    wG = np.where(Wi == gG, Ww, 0).sum(1)
    wD = np.where(Wi == gD, Ww, 0).sum(1)
    eps = 1e-9
    classe = np.where((wG > eps) & (wD > eps), "mixte",
                      np.where(wG > eps, "G", np.where(wD > eps, "D", "autre")))
    inc = np.isin(a, D) | np.isin(c, D)
    ie = np.where(inc)[0]

    def analyse(Wt, etiquette):
        wG_t = np.where(Wi == gG, Wt, 0).sum(1)
        wD_t = np.where(Wi == gD, Wt, 0).sum(1)
        classe = np.where((wG_t > eps) & (wD_t > eps), "mixte",
                          np.where(wG_t > eps, "G", np.where(wD_t > eps, "D", "autre")))
        lbs, Mv, Rsq = DEC.pipeline(Wi, Wt, B, pm, rest)
        sq = ARAP.solve_fixe(lbs, rest, A, Rsq, 0.1)
        L = lambda p: np.linalg.norm(p[a] - p[c], axis=1)
        lr, ll, ls = L(rest), L(lbs), L(sq)
        amp = (ls - ll) / lr
        groupes = {}
        for e in ie:
            cle = " - ".join(sorted([classe[a[e]], classe[c[e]]]))
            groupes.setdefault(cle, []).append(e)
        resume = {}
        for cle, es in sorted(groupes.items()):
            es = np.array(es)
            resume[cle] = {"n_aretes": int(len(es)), "amplification_mediane": med(amp[es]),
                           "amplification_max": float(amp[es].max())}
        # déplacement SQ − LBS des sommets défectueux, par classe
        dep = np.linalg.norm(sq - lbs, axis=1)
        par_classe = {}
        for k in ["G", "D", "mixte", "autre"]:
            m_ = np.isin(np.arange(N), D) & (classe == k)
            par_classe[k] = {"n": int(m_.sum()), "deplacement_SQ_LBS_mediane_m": med(dep[m_])}
        print(f"== {etiquette}", flush=True)
        for cle, v in resume.items():
            print(f"   {cle:12s} n={v['n_aretes']:3d} amp_med={v['amplification_mediane']:+.4f} amp_max={v['amplification_max']:+.4f}", flush=True)
        print("   défauts par classe :", par_classe, flush=True)
        return {"par_classe_d_aretes": resume, "defauts_par_classe": par_classe,
                "stretch_LBS_D_max": float((ll[ie]).max()), "stretch_SQ_D_max": float(ls[ie].max())}

    res = {"base": analyse(Ww, "poids originaux")}

    # t = 0 : les sommets mixtes du patch reçoivent tout le poids de la cuisse droite
    Wt = Ww.copy()
    slotG = (Wi == gG)
    slotD = (Wi == gD)
    voisin = np.unique(np.concatenate([D, a[np.isin(c, D)], c[np.isin(a, D)]]))
    S = np.where((slotG.any(1) & slotD.any(1)) & np.isin(np.arange(N), voisin))[0]
    for v in S:
        kG = np.where(slotG[v])[0][0]
        kD = np.where(slotD[v])[0][0]
        s_ = Ww[v, kG] + Ww[v, kD]
        Wt[v, kG] = 0.0
        Wt[v, kD] = s_
    res["t0_droite"] = analyse(Wt, "t = 0 (mixtes -> cuisse droite)")

    with open(os.path.join(SORTIE, "propagation.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1, ensure_ascii=False)
    print("ECRIT", os.path.join(SORTIE, "propagation.json"), flush=True)

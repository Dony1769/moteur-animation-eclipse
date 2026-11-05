"""Hypothèse H3 : le défaut apparaît là où le poids des deux cuisses change très vite, sur les arêtes courtes.
Mesure, par arête : gradient de poids g = |Δ w_cuisse_G − Δ w_cuisse_D| / longueur de repos, et gradient de
déplacement LBS. Corrélation avec la variation d'étirement SQ − LBS, sur masculin hanche G 120°."""
import importlib.util
import json
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
SORTIE = os.path.join(RACINE, "docs", "rapports", "skinning", "investigation_hanche_masc")


def charger(nom):
    spec = importlib.util.spec_from_file_location(nom, os.path.join(HERE, nom + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


INV = charger("investigation_hanche_masc")
M, ARAP = INV.M, INV.ARAP

if __name__ == "__main__":
    z, noms, rest, Wi, Ww, B, b, tot, A, _ = INV.tous_les_defauts()
    pm, centre, chaine, sens = INV.pose_test(z, noms, INV.JSON_SQ, "hanche_G", 120)
    lbs = M.calculer_toutes(rest, Wi, Ww, B, pm)[0]["LBS"]
    Rsq = ARAP.polaire(M.repere_rigide(Wi, Ww, B, pm))
    sq = ARAP.solve_fixe(lbs, rest, A, Rsq, 0.1)
    N = len(rest)
    gG, gD = noms.index("mixamorig:LeftUpLeg"), noms.index("mixamorig:RightUpLeg")
    wG = np.zeros(N); wD = np.zeros(N)
    for c in range(Wi.shape[1]):
        wG += np.where(Wi[:, c] == gG, Ww[:, c], 0)
        wD += np.where(Wi[:, c] == gD, Ww[:, c], 0)
    a, c_ = A[:, 0], A[:, 1]
    lr = np.linalg.norm(rest[a] - rest[c_], axis=1)
    ok = lr > 1e-9
    grad_w = np.abs((wG[a] - wD[a]) - (wG[c_] - wD[c_])) / np.maximum(lr, 1e-12)
    dl = np.linalg.norm(lbs[a] - lbs[c_], axis=1) - lr
    rl = np.linalg.norm(lbs[a] - lbs[c_], axis=1) / np.maximum(lr, 1e-12)
    rs = np.linalg.norm(sq[a] - sq[c_], axis=1) / np.maximum(lr, 1e-12)
    dS = (rs - rl)
    r = np.corrcoef(grad_w[ok], np.abs(dS[ok]))[0, 1]
    r2 = np.corrcoef(grad_w[ok], rl[ok])[0, 1]
    top = np.argsort(-grad_w * ok)[:50]
    top_ok = top[ok[top]]
    print(f"top50 : médiane (SQ − LBS) = {np.median(dS[top_ok]):+.3f} ; part où SQ > LBS = {np.mean(dS[top_ok] > 0):.2f}")
    print(f"toutes arêtes : médiane (SQ − LBS) = {np.median(dS[ok]):+.4f} ; part où SQ > LBS = {np.mean(dS[ok] > 1e-9):.3f}")
    deg = ok & (dS > 0.05)
    print(f"arêtes où SQ dépasse LBS de plus de 0,05 : {int(deg.sum())} ; gradient de poids médian {np.median(grad_w[deg]):.2f} "
          f"contre {np.median(grad_w[ok]):.2f} pour toutes")
    print(f"arêtes {ok.sum()} ; corrélation |gradient de poids| / |variation d'étirement SQ−LBS| = {r:.3f}")
    print(f"corrélation |gradient de poids| / étirement LBS = {r2:.3f}")
    top = np.argsort(-grad_w * ok)[:50]
    print(f"50 arêtes au gradient de poids le plus fort : longueur médiane {np.median(lr[top])*100:.2f} cm ; "
          f"étirement LBS médian {np.median(rl[top]):.3f} ; étirement SQ médian {np.median(rs[top]):.3f}")
    print(f"toutes arêtes : longueur médiane {np.median(lr[ok])*100:.2f} cm ; étirement LBS médian {np.median(rl[ok]):.3f}")
    json.dump({"correlation_gradient_poids_variation": float(r), "correlation_gradient_poids_etirement_LBS": float(r2),
               "top50_longueur_med_cm": float(np.median(lr[top]) * 100), "top50_etirement_LBS_med": float(np.median(rl[top])),
               "top50_etirement_SQ_med": float(np.median(rs[top])), "toutes_etirement_LBS_med": float(np.median(rl[ok]))},
              open(os.path.join(SORTIE, "H3_gradient_poids.json"), "w"), indent=1)

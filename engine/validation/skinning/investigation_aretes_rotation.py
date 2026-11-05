"""Hypothèse H2 : l'amplification de SQ se produit sur les arêtes dont les deux extrémités ont des rotations
moyennées très différentes. Test : corrélation, sur toutes les arêtes, entre l'angle R_a^T R_b (rotations SQ) et
la variation d'étirement SQ − LBS. Même pose, mêmes géométries (hanche G 120°, masculin)."""
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
M, ARAP, Ms = INV.M, INV.ARAP, INV.Ms

if __name__ == "__main__":
    z, noms, rest, Wi, Ww, B, b, tot, A, sortie = INV.tous_les_defauts()
    pm, centre, chaine, sens = INV.pose_test(z, noms, INV.JSON_SQ, "hanche_G", 120)
    lbs = M.calculer_toutes(rest, Wi, Ww, B, pm)[0]["LBS"]
    Rsq = ARAP.polaire(M.repere_rigide(Wi, Ww, B, pm))
    sq = ARAP.solve_fixe(lbs, rest, A, Rsq, 0.1)
    a, c = A[:, 0], A[:, 1]
    lr = np.linalg.norm(rest[a] - rest[c], axis=1)
    rl = np.linalg.norm(lbs[a] - lbs[c], axis=1) / np.maximum(lr, 1e-12)
    rs = np.linalg.norm(sq[a] - sq[c], axis=1) / np.maximum(lr, 1e-12)
    ok = lr > 1e-9
    # angle entre les rotations moyennées des deux extrémités
    rel = np.einsum("eji,ejk->eik", Rsq[a], Rsq[c])
    tr = np.clip((np.trace(rel, axis1=1, axis2=2) - 1) / 2, -1, 1)
    ang = np.degrees(np.arccos(tr))
    d_stretch = (rs - rl)[ok]
    ang_ok = ang[ok]
    r = np.corrcoef(ang_ok, d_stretch)[0, 1]
    print(f"arêtes : {ok.sum()} ; corrélation (angle des rotations moyennées, variation d'étirement SQ−LBS) = {r:.3f}")
    # tranches d'angle
    for lo, hi in [(0, 5), (5, 15), (15, 30), (30, 60), (60, 180)]:
        m = (ang_ok >= lo) & (ang_ok < hi)
        if m.any():
            print(f"  angle [{lo:3d},{hi:3d}) deg : n={m.sum():5d}  variation moyenne {d_stretch[m].mean():+.4f}  "
                  f"part où SQ > LBS+0,05 : {np.mean(d_stretch[m] > 0.05):.3f}")
    # arêtes à défaut SQ
    defauts_arete = (rs[ok] > 1.5) & (d_stretch > 0.05)
    print(f"arêtes dégradées (SQ > 1,5 et hausse > 0,05) : {defauts_arete.sum()} ; angle médian {np.median(ang_ok[defauts_arete]):.1f}° "
          f"contre {np.median(ang_ok):.1f}° pour toutes")
    out = {"correlation_angle_variation": float(r), "n_aretes": int(ok.sum()),
           "angle_median_aretes_degradees_deg": float(np.median(ang_ok[defauts_arete])) if defauts_arete.any() else None,
           "angle_median_toutes_deg": float(np.median(ang_ok))}
    json.dump(out, open(os.path.join(SORTIE, "H2_angle_aretes.json"), "w"), indent=1)

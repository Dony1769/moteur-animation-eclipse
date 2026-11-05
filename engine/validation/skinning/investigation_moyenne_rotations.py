"""Test : la moyenne arithmétique R_ab = (R_a + R_b)/2 explique-t-elle les retournements à grand angle ?
Même géométrie, mêmes poids (brutal, cuisse droite fixe), même λ = 0,1 ; seul R_ab change :
  - moyenne arithmétique (SQ actuel) ;
  - polaire de la moyenne (diagnostic : retire le rétrécissement, n'est pas un candidat).
Balayage d'angle 30°, 60°, 90°, 120°, maillages 21 et 41."""
import importlib.util
import json
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
SORTIE = os.path.join(RACINE, "docs", "rapports", "skinning", "propagation_synthetique")


def charger(nom):
    spec = importlib.util.spec_from_file_location(nom, os.path.join(HERE, nom + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


S = charger("investigation_synthetique")
DEC = S.DEC


def solve_variante(lbs, rest, A, Rsq, lam, polaire):
    Rab = 0.5 * (Rsq[A[:, 0]] + Rsq[A[:, 1]])
    if polaire:
        Rab = DEC.polaire_gen(Rab)
    return DEC.solve_R(lbs, rest, A, Rab, lam)


if __name__ == "__main__":
    out = {}
    for n in (21, 41):
        for deg in (30, 60, 90, 120):
            rest, tris, A, wG, lbs, Mv, Rsq = S.construire(S.xs_uniforme(n), S.xs_uniforme(n), "brutal",
                                                           np.radians(deg), 0.0)
            N = len(rest)
            cle = f"n{n}_angle{deg}"
            row = {}
            for nom, pol in (("moyenne_arithmetique", False), ("polaire_de_la_moyenne", True)):
                sq = solve_variante(lbs, rest, A, Rsq, 0.1, pol)
                st = S.stats(rest, lbs, sq, tris, A, Mv)
                disp = np.linalg.norm(sq - lbs, axis=1)
                h = float(np.mean(np.linalg.norm(rest[A[:, 0]] - rest[A[:, 1]], axis=1)))
                PD = wG <= 1e-12
                prof = S.profil(N, A, np.round(wG, 9), wG >= 1 - 1e-12, PD, disp, h, dmax=5)
                row[nom] = {"profil_pur_D_sur_h": {k: round(v["deplacement_SQ_LBS_sur_h_mediane"], 4) for k, v in prof["pur_D"].items()},
                            "retournements": st["SQ"]["retournements"], "etirement_max": st["SQ"]["etirement_max"],
                            "aire_min": st["triangles"]["aire_min_SQ"],
                            "moyenne_SQ_moins_LBS": float(np.linalg.norm((sq - lbs).mean(0)))}
            row["LBS"] = {"retournements": S.stats(rest, lbs, lbs, tris, A, Mv)["LBS"]["retournements"]}
            out[cle] = row
            print(cle, row, flush=True)
    with open(os.path.join(SORTIE, "moyenne_rotations.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print("ECRIT", flush=True)

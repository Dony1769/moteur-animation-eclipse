"""Complément : configuration proche du cas réel (rotation 120°, cuisse droite fixe) et dépendance en densité
exprimée en absolu et en longueurs d'arête. Mêmes fonctions que investigation_synthetique (aucun paramètre ajusté)."""
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

if __name__ == "__main__":
    out = {"angle_120_cuisse_droite_fixe": {}, "densite": {}}
    for wk in ("brutal", "progressif"):
        for n in (21, 41):
            r = S.evaluer(f"{wk}_120_n{n}", S.xs_uniforme(n), S.xs_uniforme(n), wk, np.radians(120), 0.0, lam=0.1)
            p = r["profil_propagation"]["pur_D"]
            out["angle_120_cuisse_droite_fixe"][f"{wk}_n{n}"] = {
                "h": r["h_moyen"],
                "pur_D_profil_sur_h": {k: round(v["deplacement_SQ_LBS_sur_h_mediane"], 4) for k, v in p.items()},
                "pur_D_profil_absolu_m": {k: round(v["deplacement_SQ_LBS_sur_h_mediane"] * r["h_moyen"], 5) for k, v in p.items()},
                "etirement_SQ_max": r["stats"]["SQ"]["etirement_max"], "etirement_LBS_max": r["stats"]["LBS"]["etirement_max"],
                "retournements_SQ": r["stats"]["SQ"]["retournements"], "aire_min_SQ": r["stats"]["triangles"]["aire_min_SQ"]}
            print(wk, n, out["angle_120_cuisse_droite_fixe"][f"{wk}_n{n}"], flush=True)
    for n in (11, 21, 41):
        r = S.evaluer(f"densite_{n}", S.xs_uniforme(n), S.xs_uniforme(n), "progressif", np.radians(30), np.radians(-30), lam=0.1)
        p = r["profil_propagation"]["pur_D"]["0"]["deplacement_SQ_LBS_sur_h_mediane"]
        out["densite"][str(n)] = {"h": r["h_moyen"], "depl_pur_d0_sur_h": p, "depl_pur_d0_absolu_m": p * r["h_moyen"]}
        print("densite", n, out["densite"][str(n)], flush=True)
    with open(os.path.join(SORTIE, "complement.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print("ECRIT", flush=True)

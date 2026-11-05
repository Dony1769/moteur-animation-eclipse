"""Test de symétrie gauche-droite par réflexion géométrique (phase 4, axe 2).

Pour chaque mouvement X (flexion, abduction, rotation, genou, combinaisons) :
  1. la pose gauche L_X est déformée (LBS, méthode de référence) ;
  2. ses positions sont réfléchies par rapport au plan médian du corps ;
  3. chaque sommet réfléchi est associé à son sommet droit le plus proche au repos (correspondance de symétrie) ;
  4. on compare la position réfléchie gauche à la position droite R_X associée.

Ce qui est mesuré : écart de déformation = écart posé − écart au repos. L'écart au repos (maillage non parfaitement
symétrique, 4 mm au plus) est retiré pour ne garder que l'asymétrie de la déformation.

Critères fixés AVANT la mesure (ne pas modifier pour faire passer le test) :
  - écart de déformation p99 < 2 mm ;
  - étirement max gauche/droite : écart relatif < 5 % ;
  - volume : écart absolu de la variation relative < 0,5 point ;
  - retournements : égaux.
Un échec est une asymétrie réelle à expliquer, pas un seuil à relâcher.

Usage : python3 engine/validation/skinning/test_symetrie.py POSES.npz [SORTIE.json]
"""
import json
import os
import sys

import numpy as np
from scipy.spatial import cKDTree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import methodes as M  # noqa: E402
import mesures as Ms  # noqa: E402

CRITERES = {"deformation_p99_m": 0.002, "etirement_relatif": 0.05, "volume_point": 0.005}
MOUVEMENTS = ["flex30", "flex60", "flex90", "flex120", "abd30", "add20", "ext30", "int30",
              "genou30", "genou60", "genou90", "combo_flex90_abd30_ext30", "combo_flex120_genou90",
              "combo_flex60_abd20_int20_genou60"]


def main():
    npz = sys.argv[1]
    sortie = sys.argv[2] if len(sys.argv) > 2 else None
    d = np.load(npz)
    rest, Wi, Ww, B = d["rest_monde"], d["W_idx"], d["W_w"], d["bones_rest_monde"]
    b, tot = d["b_boucle"], d["b_tot"]
    A = Ms.aretes(b, tot, len(rest))
    xc = float(d["rest_monde"][:, 0].mean()) if "plan_median_x" not in d.files else float(d["plan_median_x"])
    meta = json.load(open(npz.replace(".npz", ".json")))
    xc = float(meta.get("plan_median_x", xc))
    refl = rest.copy()
    refl[:, 0] = 2 * xc - rest[:, 0]
    # correspondance : sommet réfléchi i (côté gauche) -> sommet le plus proche au repos
    dist_rep, assoc = cKDTree(rest).query(refl)
    rep_p99 = float(np.percentile(dist_rep, 99))
    # le repos est lui-même non parfaitement symétrique : son écart sert de référence
    resultats = {"plan_median_x": xc, "ecart_repos_p99_m": rep_p99, "criteres": CRITERES, "mouvements": {}}
    echecs = []
    for mv in MOUVEMENTS:
        gauche, droite = "L_" + mv, "R_" + mv
        if gauche + "__os" not in d.files or droite + "__os" not in d.files:
            continue
        pg = M.calculer_toutes(rest, Wi, Ww, B, d[gauche + "__os"])[0]["LBS"]
        pd = M.calculer_toutes(rest, Wi, Ww, B, d[droite + "__os"])[0]["LBS"]
        pg_refl = pg.copy()
        pg_refl[:, 0] = 2 * xc - pg[:, 0]
        # écart posé, comparé à l'écart au repos pour les mêmes sommets
        ecart_pose = np.linalg.norm(pg_refl - pd[assoc], axis=1)
        ecart_def = np.abs(ecart_pose - dist_rep)
        p99 = float(np.percentile(ecart_def, 99))
        mg = Ms.mesurer(pg, rest, b, tot, A, Mv=M.repere_rigide(Wi, Ww, B, d[gauche + "__os"]))
        md = Ms.mesurer(pd, rest, b, tot, A, Mv=M.repere_rigide(Wi, Ww, B, d[droite + "__os"]))
        # étirement sur arêtes >= 5 mm (entrée 151)
        rel = abs(mg["etirement_max_ge5mm"] - md["etirement_max_ge5mm"]) / max(md["etirement_max_ge5mm"], 1e-9)
        dvol = abs(mg["variation_volume_relative"] - md["variation_volume_relative"])
        flips_ok = mg["polygones_retournes"] == md["polygones_retournes"]
        ok = (p99 < CRITERES["deformation_p99_m"] and rel < CRITERES["etirement_relatif"]
              and dvol < CRITERES["volume_point"] and flips_ok)
        if not ok:
            echecs.append(mv)
        resultats["mouvements"][mv] = {
            "deformation_asymetrie_p99_m": p99, "etirement_gauche": mg["etirement_max_ge5mm"],
            "etirement_droite": md["etirement_max_ge5mm"], "etirement_relatif": rel,
            "volume_gauche": mg["variation_volume_relative"], "volume_droite": md["variation_volume_relative"],
            "retournements_gauche": mg["polygones_retournes"], "retournements_droite": md["polygones_retournes"],
            "OK": ok,
        }
        print(("OK   " if ok else "ECHEC") + f" {mv}: asymétrie p99 {p99*1000:.2f} mm ; étirement G {mg['etirement_max']:.3f} "
              f"D {md['etirement_max_ge5mm']:.3f} (écart {rel*100:.1f} %) ; volume G {mg['variation_volume_relative']:+.4f} "
              f"D {md['variation_volume_relative']:+.4f} ; retournements G {mg['polygones_retournes']} D {md['polygones_retournes']}",
              flush=True)
    resultats["echecs"] = echecs
    if sortie:
        with open(sortie, "w") as f:
            json.dump(resultats, f, indent=2, ensure_ascii=False)
    print("SYMETRIE", "OK" if not echecs else "ECHEC " + ",".join(echecs))
    return 0 if not echecs else 1


if __name__ == "__main__":
    sys.exit(main())

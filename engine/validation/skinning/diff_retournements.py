"""Différences de retournements gauche/droite, polygone par polygone (phase 4, priorité 1).

Pour chaque mouvement, les polygones du côté gauche sont appariés à leur image miroir du côté droit (par les sommets
appariés au repos). Pour chaque paire où le statut « retourné » diffère, on donne la position au repos, l'os dominant,
et le cosinus entre normale posée et normale de référence (un cosinus proche de 0 = polygone au seuil, donc sensible
au moindre arrondi).

Usage : python3 engine/validation/skinning/diff_retournements.py POSES.npz [MOUVEMENT ...]
"""
import json
import os
import sys

import numpy as np
from scipy.spatial import cKDTree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import methodes as M  # noqa: E402
import mesures as Ms  # noqa: E402


def cosinus_retournement(pos, rest, b, tot, Mv):
    debut = Ms._debuts(tot)
    poly = np.repeat(np.arange(len(tot)), tot)
    local = np.arange(len(b)) - debut[poly]
    nxt = debut[poly] + (local + 1) % tot[poly]
    n_pos = Ms._newell(pos, b, tot, nxt)
    n_rest = Ms._newell(rest, b, tot, nxt)
    Mp = np.add.reduceat(Mv[b], debut, axis=0) / tot[:, None, None]
    ref = np.einsum("pab,pb->pa", Mp, n_rest)
    nn = np.linalg.norm(n_pos, axis=1) * np.linalg.norm(ref, axis=1)
    cos = np.einsum("nc,nc->n", n_pos, ref) / np.maximum(nn, 1e-12)
    return cos


def main():
    npz = sys.argv[1]
    mvs = sys.argv[2:] or ["flex120", "combo_flex120_genou90", "genou60", "combo_flex90_abd30_ext30",
                           "combo_flex60_abd20_int20_genou60"]
    d = np.load(npz)
    meta = json.load(open(npz.replace(".npz", ".json")))
    rest, Wi, Ww, B = d["rest_monde"], d["W_idx"], d["W_w"], d["bones_rest_monde"]
    b, tot = d["b_boucle"], d["b_tot"]
    noms = [str(n) for n in d["noms_os"]] if "noms_os" in d.files else None
    xc = float(meta["plan_median_x"])
    refl = rest.copy(); refl[:, 0] = 2 * xc - rest[:, 0]
    _, assoc = cKDTree(rest).query(refl)
    debut = Ms._debuts(tot)
    centres = np.add.reduceat(rest[b], debut, axis=0) / tot[:, None]
    # clé de polygone = ensemble des sommets
    cle_droite = {}
    for p in range(len(tot)):
        cle_droite[frozenset(b[debut[p]:debut[p] + tot[p]].tolist())] = p
    rapport = {}
    for mv in mvs:
        pg, pd = d["L_" + mv + "__os"], d["R_" + mv + "__os"]
        Lg = M.calculer_toutes(rest, Wi, Ww, B, pg)[0]["LBS"]
        Ld = M.calculer_toutes(rest, Wi, Ww, B, pd)[0]["LBS"]
        Mg = M.repere_rigide(Wi, Ww, B, pg)
        Md = M.repere_rigide(Wi, Ww, B, pd)
        fg, _ = Ms.masque_retournes(Lg, rest, b, tot, Mg)
        fd, _ = Ms.masque_retournes(Ld, rest, b, tot, Md)
        cg = cosinus_retournement(Lg, rest, b, tot, Mg)
        cd = cosinus_retournement(Ld, rest, b, tot, Md)
        # appariement : polygone gauche p -> polygone droit dont les sommets sont les images miroir
        app = []
        for p in range(len(tot)):
            img = frozenset(int(assoc[v]) for v in b[debut[p]:debut[p] + tot[p]])
            q = cle_droite.get(img)
            if q is None:
                continue
            app.append((p, q))
        app = np.array(app)
        p, q = app[:, 0], app[:, 1]
        diff = np.where(fg[p] != fd[q])[0]
        lignes = []
        for k in diff:
            pg_i, pd_i = p[k], q[k]
            x, y, z = centres[pg_i]
            vs = b[debut[pg_i]:debut[pg_i] + tot[pg_i]]
            poids = Wi[vs]
            ww = Ww[vs]
            os_dom = None
            if noms is not None:
                acc = {}
                for vi, row_i, row_w in zip(vs, poids, ww):
                    for j, w in zip(row_i, row_w):
                        if w > 0:
                            acc[j] = acc.get(j, 0) + w
                os_dom = noms[max(acc, key=acc.get)] if acc else None
            lignes.append({
                "polygone_gauche": int(pg_i), "polygone_droit": int(pd_i),
                "repos_xyz_m": [round(float(x), 4), round(float(y), 4), round(float(z), 4)],
                "os_dominant": os_dom,
                "retourne_gauche": bool(fg[pg_i]), "retourne_droit": bool(fd[pd_i]),
                "cos_gauche": round(float(cg[pg_i]), 5), "cos_droit": round(float(cd[pd_i]), 5),
            })
        rapport[mv] = {"flips_G": int(fg.sum()), "flips_D": int(fd.sum()),
                       "paires_appariees": int(len(app)), "differences": lignes}
        print(f"{mv}: retournements G {int(fg.sum())} D {int(fd.sum())} ; paires {len(app)} ; "
              f"différences {len(lignes)}", flush=True)
        for l in lignes:
            print("   ", l, flush=True)
    sortie = os.environ.get("SORTIE")
    if sortie:
        json.dump(rapport, open(sortie, "w"), indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()

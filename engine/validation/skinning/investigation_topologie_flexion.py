"""Phase 4 : interaction topologie et flexion sur Maria, avec la même topologie pour toutes les poses.

- Balayage de la flexion de hanche gauche et droite (0 à 120° par pas de 15°), mêmes poids et même maillage.
- Les 29 poses de référence (réelles et génératives) pour situer les sept triangles dans l'ensemble.
- Pour chaque pose : nombre de retournements nouveaux (mesure A) sur tout le maillage, par composante, et par distance
  en anneaux aux frontières (distance de graphe au sommet de frontière le plus proche).
- Seuil d'apparition, évolution avec l'angle, comparaison gauche/droite.
"""
import importlib.util
import json
import os
from collections import deque

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
SORTIE = os.path.join(RACINE, "docs", "rapports", "skinning", "topologie")


def charger(nom):
    spec = importlib.util.spec_from_file_location(nom, os.path.join(HERE, nom + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


CMP = charger("investigation_comparaison")
G = charger("investigation_maria_geometrie")
TD = charger("investigation_topologie_detail")
LM = charger("investigation_lambda_morphos")
EXP = LM.EXP
P = LM.P


def pose_hanche_D(z, noms, js, th):
    cle = [k for k in z.keys() if k.startswith("R_flex") and k.endswith("__os")]
    ref = sorted(cle)[0][:-4]
    sens = EXP.signe_depuis_pose_reelle(z, noms, js, "RightUpLeg", ref)[0]
    c, ax, ch = P.articulation(js, EXP.prefixe(noms) + "RightUpLeg")
    T = P.transformation_articulation(c, ax, np.radians(th), sens)
    return P.matrices_pose(z["bones_rest_monde"], noms, ch, T), ref


def distance_bord(N, A, bord_v):
    voisins = [[] for _ in range(N)]
    for a, c in A:
        voisins[a].append(c)
        voisins[c].append(a)
    d = np.full(N, -1)
    f = deque()
    for v in bord_v:
        d[v] = 0
        f.append(v)
    while f:
        u = f.popleft()
        for v in voisins[u]:
            if d[v] < 0:
                d[v] = d[u] + 1
                f.append(v)
    return d


if __name__ == "__main__":
    os.makedirs(SORTIE, exist_ok=True)
    M = CMP.charger_morph("maria")
    rest, tris, A, N = M["rest"], M["tris"], M["A"], M["N"]
    nc, comp = TD.composantes(N, A)
    fr, cnt = TD.frontieres(tris)[0], TD.frontieres(tris)[1]
    bord_v = np.unique(fr[cnt == 1])
    dist_b = distance_bord(N, A, bord_v)
    # distance de chaque triangle : minimum des trois sommets
    dtri = dist_b[tris].min(1)
    ctri = comp[tris[:, 0]]
    z, noms, js = M["z"], M["noms"], M["js"]

    poses = {}
    for th in range(0, 121, 15):
        poses[f"gauche_{th}"] = LM.pose_hanche_G(z, noms, js, th)
    for th in range(0, 121, 15):
        pm, ref = pose_hanche_D(z, noms, js, th)
        poses[f"droite_{th}"] = pm
    for nom in CMP.POSES:
        poses[f"reelle_{nom}"] = CMP.pose_de(M, nom)

    res = {"reference_poses_droite": ref, "frontiere_sommets": int(len(bord_v)), "resultats": {}}
    for nom, pm in poses.items():
        lbs, sq, Mv, R, t = CMP.evaluer(M, pm)
        f = G.flags(rest, tris, lbs, sq, Mv)
        nv = f["nouveau_A"]
        par_comp = {}
        for c in np.unique(ctri[nv]):
            par_comp[str(int(c))] = int((nv & (ctri == c)).sum())
        par_dist = {}
        for dval in range(0, int(dtri.max()) + 1):
            m = dtri == dval
            par_dist[str(dval)] = {"triangles": int(m.sum()), "nouveaux": int((nv & m).sum())}
        res["resultats"][nom] = {"nouveaux_total": int(nv.sum()), "LBS_total": int(f["A_LBS"].sum()),
                                 "SQ_total": int(f["A_SQ"].sum()), "par_composante": par_comp,
                                 "par_distance_frontiere_anneaux": par_dist}
        print(nom, int(nv.sum()), par_comp, flush=True)

    # seuil et évolution avec l'angle
    def courbe(prefixe):
        return [(th, res["resultats"][f"{prefixe}_{th}"]["nouveaux_total"]) for th in range(0, 121, 15)]
    res["courbe_gauche"] = courbe("gauche")
    res["courbe_droite"] = courbe("droite")
    seuil = {}
    for cote in ["gauche", "droite"]:
        c = dict(res["courbe_" + ("gauche" if cote == "gauche" else "droite")])
        seuil[cote] = next((th for th, n in sorted(c.items()) if n > 0), None)
    res["seuil_apparition_deg"] = seuil

    with open(os.path.join(SORTIE, "flexion_topologie.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1, ensure_ascii=False, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    print("seuils", seuil, "gauche", res["courbe_gauche"], "droite", res["courbe_droite"], flush=True)
    print("ECRIT", flush=True)

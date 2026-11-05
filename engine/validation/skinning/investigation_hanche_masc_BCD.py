"""Étapes B, C, D de l'investigation de la hanche masculine (sommets défectueux de l'étape A).

B : fiche par sommet (repos, positions LBS/SQ/SQV1, déplacements, étirements, poids, distances aux articulations
    et aux segments osseux réels, arêtes et polygones incidents).
C : carte spatiale des défauts (plans x-z et y-z au repos), coloriée par étirement SQV1 à hanche gauche 120°.
D : conventions et transformations : vérification de lbs (somme pondérée), rotation moyennée SQ, rotations des os
    dominant et voisins, angle entre ces rotations, effet de la correction de volume.
"""
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
M = INV.M
P = INV.P
ARAP = INV.ARAP
CV = INV.CV
np_ = np


def distance_segment(p, A_, B_, point):
    if point:
        return float(np.linalg.norm(p - A_))
    AB = B_ - A_
    t = np.clip(np.dot(p - A_, AB) / max(np.dot(AB, AB), 1e-12), 0.0, 1.0)
    return float(np.linalg.norm(p - (A_ + t * AB)))


def segments_reels(js, noms):
    d = json.load(open(js, encoding="utf-8"))
    par = {o["nom"]: o for o in d["os"]}
    out = []
    for n in noms:
        o = par[n]
        if o["longueur_fiable"]:
            out.append((n, np.array(o["tete"]), np.array(o["queue"]), False, o["longueur"]))
        else:
            out.append((n, np.array(o["tete"]), np.array(o["tete"]), True, None))
    return out


def polygones_par_sommet(b, tot, N):
    debut = np.concatenate([[0], np.cumsum(tot)[:-1]])
    cnt = np.zeros(N, int)
    for d0, n in zip(debut, tot):
        for v in b[d0:d0 + n]:
            cnt[v] += 1
    return cnt


if __name__ == "__main__":
    os.makedirs(SORTIE, exist_ok=True)
    z, noms, rest, Wi, Ww, B, b, tot, A, sortie = INV.tous_les_defauts()
    N = len(rest)
    defauts = np.array(sortie["defauts_union"], int)
    segs = segments_reels(INV.JSON_SQ, noms)
    cent_G = np.array(json.load(open(INV.JSON_SQ))["os"][0]["tete"])
    polys = polygones_par_sommet(b, tot, N)
    voisins = [set() for _ in range(N)]
    for a_, b_ in A:
        voisins[a_].add(int(b_))
        voisins[b_].add(int(a_))

    # Pose de référence pour la fiche détaillée : hanche gauche 120°.
    pm, centre, chaine, sens = INV.pose_test(z, noms, INV.JSON_SQ, "hanche_G", 120)
    ref = M.calculer_toutes(rest, Wi, Ww, B, pm)[0]
    lbs = ref["LBS"]
    Rsq = ARAP.polaire(M.repere_rigide(Wi, Ww, B, pm))
    sq = ARAP.solve_fixe(lbs, rest, A, Rsq, 0.1)
    sqv1, _ = CV.corriger(sq, rest, Wi, Ww, b, tot, T=CV._triangles(b, tot), M=1)
    s_lbs, _ = INV.ratio_par_sommet(lbs, rest, A, N)
    s_sq, _ = INV.ratio_par_sommet(sq, rest, A, N)
    s_v1, _ = INV.ratio_par_sommet(sqv1, rest, A, N)

    Tk = pm @ np.linalg.inv(B)
    fiches = []
    for i in defauts:
        ws = [(noms[k], float(Ww[i, c])) for c, k in enumerate(Wi[i]) if Ww[i, c] > 0]
        ws.sort(key=lambda t: -t[1])
        dist_segs = sorted(((distance_segment(rest[i], s[1], s[2], s[3]) if not s[3] else distance_segment(rest[i], s[1], s[1], True), s[0]) for s in segs))
        fiches.append({
            "sommet": int(i),
            "repos_m": rest[i].round(5).tolist(),
            "stretch_LBS_120G": round(float(s_lbs[i]), 4),
            "stretch_SQ_120G": round(float(s_sq[i]), 4),
            "stretch_SQV1_120G": round(float(s_v1[i]), 4),
            "deplacement_LBS_m": round(float(np.linalg.norm(lbs[i] - rest[i])), 5),
            "deplacement_SQ_m": round(float(np.linalg.norm(sq[i] - rest[i])), 5),
            "correction_volume_m": round(float(np.linalg.norm(sqv1[i] - sq[i])), 6),
            "poids": ws,
            "distance_centre_hanche_G_m": round(float(np.linalg.norm(rest[i] - cent_G)), 4),
            "distance_segment_plus_proche": {"os": dist_segs[0][1], "m": round(float(dist_segs[0][0]), 4)},
            "aretes_incidentes": len(voisins[i]),
            "polygones_incidents": int(polys[i]),
        })
    with open(os.path.join(SORTIE, "etape_B_fiches.json"), "w", encoding="utf-8") as f:
        json.dump(fiches, f, indent=1, ensure_ascii=False)

    # Étape C : carte spatiale
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(1, 2, figsize=(11, 5))
    for k, (axe_x, axe_y, titre) in enumerate([(0, 2, "vue de face (x, z)"), (1, 2, "vue de profil (y, z)")]):
        ax[k].scatter(rest[:, axe_x], rest[:, axe_y], s=2, c="0.85", label="tous les sommets")
        sc = ax[k].scatter(rest[defauts, axe_x], rest[defauts, axe_y], s=28, c=s_v1[defauts], cmap="inferno",
                           vmin=1.0, vmax=max(1.6, float(s_v1[defauts].max())), label="défauts (SQV1, hanche G 120°)")
        ax[k].scatter([cent_G[axe_x]], [cent_G[axe_y]], marker="x", c="cyan", s=80, label="centre hanche G")
        ax[k].set_title(titre)
        ax[k].set_aspect("equal")
        ax[k].set_xlabel("xyz"[axe_x] + " (m)")
        ax[k].set_ylabel("z (m)")
    plt.colorbar(sc, ax=ax, label="étirement max incident")
    ax[0].legend(loc="upper left", fontsize=7)
    fig.savefig(os.path.join(SORTIE, "carte_defauts_masculin_hanche_G120.png"), dpi=110)
    print("carte écrite", flush=True)

    # Étape D : conventions et transformations
    manuel = np.zeros_like(rest)
    for c in range(Wi.shape[1]):
        k = Wi[:, c]
        manuel += Ww[:, c, None] * (np.einsum("nab,nb->na", Tk[k, :3, :3], rest) + Tk[k, :3, 3])
    err_lbs = float(np.abs(manuel - lbs).max())
    Mv = M.repere_rigide(Wi, Ww, B, pm)
    def angle(Ra):
        c_ = np.clip((np.trace(Ra) - 1) / 2, -1, 1)
        return float(np.degrees(np.arccos(c_)))
    dom_idx = Wi[np.arange(N), np.argmax(Ww, axis=1)]
    rotdom = ARAP.polaire(Tk[dom_idx, :3, :3])
    rows = []
    for i in defauts:
        rows.append({
            "sommet": int(i),
            "LBS_vs_somme_manuelle_m": round(float(np.abs(manuel[i] - lbs[i]).max()), 9),
            "det_Mv": round(float(np.linalg.det(Mv[i])), 4),
            "angle_rotation_moyennee_deg": round(angle(Rsq[i]), 2),
            "angle_rotation_os_dominant_deg": round(angle(rotdom[i]), 2),
            "ecart_moyenne_vs_dominant_deg": round(angle(Rsq[i].T @ rotdom[i]), 2),
            "ecart_polaire_Mv_m": round(float(np.linalg.norm(Mv[i] - Rsq[i])), 4),
        })
    with open(os.path.join(SORTIE, "etape_D_transformations.json"), "w", encoding="utf-8") as f:
        json.dump({"erreur_LBS_manuel_global_m": err_lbs, "lignes": rows}, f, indent=1, ensure_ascii=False)
    print("erreur LBS (somme manuelle) max :", err_lbs, flush=True)
    print("ECRITS etapes B, C, D", flush=True)

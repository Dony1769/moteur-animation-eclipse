"""Étape A (phase 4) : diagnostic de la zone hanche / bas-ventre, sans rien modifier.

Entrée : POSES.npz (sortie extraire_poses), pose de référence (défaut L_flex120).
Ensemble D des sommets problématiques : sommets dont l'étirement maximal (LBS, arêtes >= 5 mm) dépasse 1,25 dans la
pose de référence. Zone Z : sommets à moins de 0,20 m de la tête de l'os UpLeg gauche.
Mesures (chacune séparée) :
  1. poids par os (Hips, Spine, Spine1, LeftUpLeg, RightUpLeg) sur D, Z et le reste du corps ;
  2. transitions : variation maximale de poids entre sommets voisins (arêtes) pour chaque os ;
  3. distances de D aux têtes des os qui les influencent ;
  4. déplacement |posé - repos| par pose, LBS et DQS, sur D ;
  5. volume et étirement dans Z (LBS et DQS) ;
  6. différence LBS - DQS par sommet sur D.
Sorties : JSON et figures (poids par os, carte thermique des déformations) dans le dossier donné.

Usage : python3 engine/validation/skinning/diagnostic_hanche.py POSES.npz SORTIE_DOSSIER [POSE]
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import methodes as M  # noqa: E402
import mesures as Ms  # noqa: E402
import metriques_locales as ML  # noqa: E402

OS_ETUDIES = ["mixamorig:Hips", "mixamorig:Spine", "mixamorig:Spine1", "mixamorig:LeftUpLeg", "mixamorig:RightUpLeg"]
RAYON = 0.20
SEUIL = 1.25


def poids_dense(Wi, Ww, J):
    P = np.zeros((len(Wi), J))
    for k in range(Wi.shape[1]):
        m = Wi[:, k] >= 0
        np.add.at(P, (np.where(m)[0], Wi[m, k]), Ww[m, k])
    return P


def main():
    npz, sortie = sys.argv[1], sys.argv[2]
    pose_ref = sys.argv[3] if len(sys.argv) > 3 else "L_flex120"
    os.makedirs(sortie, exist_ok=True)
    d = np.load(npz)
    rest, Wi, Ww, B = d["rest_monde"], d["W_idx"], d["W_w"], d["bones_rest_monde"]
    b, tot = d["b_boucle"], d["b_tot"]
    noms = [str(n) for n in d["noms_os"]]
    J = len(noms)
    A = Ms.aretes(b, tot, len(rest))
    T_ref = d[pose_ref + "__os"] @ np.linalg.inv(B)
    heads = {n: B[noms.index(n)][:3, 3] for n in noms}
    P = poids_dense(Wi, Ww, J)
    # ---- posé de référence ----
    lbs_ref = M.calculer_toutes(rest, Wi, Ww, B, d[pose_ref + "__os"])[0]
    pos_L, pos_D = lbs_ref["LBS"], lbs_ref["DQS"]
    dfx = ML.defauts(pos_L, rest, b, tot, A, seuils_etirement=(1.1, 1.25, 1.5))
    vmax_L = dfx["_vertex_etirement"]
    D = np.where(np.nan_to_num(vmax_L, nan=0) > SEUIL)[0]
    dist_hanche = np.linalg.norm(rest - heads["mixamorig:LeftUpLeg"], axis=1)
    Z = np.where(dist_hanche < RAYON)[0]
    masque_D = np.zeros(len(rest), bool); masque_D[D] = True
    masque_Z = np.zeros(len(rest), bool); masque_Z[Z] = True
    reste = ~(masque_Z | masque_D)
    R = {"pose": pose_ref, "nb_D": int(len(D)), "nb_Z": int(len(Z)), "rayon_m": RAYON, "seuil": SEUIL}

    # 1. poids par os
    def resume_poids(idx):
        out = {}
        for n in OS_ETUDIES:
            w = P[idx, noms.index(n)]
            out[n.replace("mixamorig:", "")] = {"moyen": float(w.mean()), "p10": float(np.percentile(w, 10)),
                                                  "p90": float(np.percentile(w, 90))} if len(idx) else None
        return out
    R["1_poids_par_os"] = {"D": resume_poids(D), "Z": resume_poids(Z), "reste": resume_poids(np.where(reste)[0])}
    dom = np.argmax(P, axis=1)
    R["1b_os_dominant_D"] = {noms[j].replace("mixamorig:", ""): int((dom[D] == j).sum()) for j in np.unique(dom[D])}

    # 2. transitions : variation de poids entre voisins, par os
    a, bb = A[:, 0], A[:, 1]
    transitions = {}
    for n in OS_ETUDIES:
        j = noms.index(n)
        dw = np.abs(P[a, j] - P[bb, j])
        # pour chaque sommet, plus forte variation sur une arête incidente
        vmaxw = np.zeros(len(rest))
        np.maximum.at(vmaxw, a, dw); np.maximum.at(vmaxw, bb, dw)
        transitions[n.replace("mixamorig:", "")] = {"variation_max_arete_D": float(vmaxw[D].max()) if len(D) else 0.0,
                                                     "variation_moy_arete_D": float(vmaxw[D].mean()) if len(D) else 0.0,
                                                     "variation_max_arete_reste": float(vmaxw[reste].max())}
    R["2_transitions"] = transitions

    # 3. distances aux têtes des os influents (sommets D)
    dist = {}
    for n in ["mixamorig:Hips", "mixamorig:Spine", "mixamorig:Spine1", "mixamorig:LeftUpLeg"]:
        dist[n.replace("mixamorig:", "")] = {"moy_m": float(np.linalg.norm(rest[D] - heads[n], axis=1).mean()) if len(D) else None}
    R["3_distances_aux_tetes_os_m"] = dist

    # 4. déplacements par pose (LBS, DQS) sur D et Z
    poses_test = ["L_flex30", "L_flex60", "L_flex90", "L_flex120", "L_abd30"]
    dep = {}
    for pose in poses_test:
        if pose + "__os" not in d.files:
            continue
        r = M.calculer_toutes(rest, Wi, Ww, B, d[pose + "__os"])[0]
        for m in ["LBS", "DQS"]:
            dd = np.linalg.norm(r[m] - rest, axis=1)
            dep.setdefault(pose, {})[m] = {"D_moy_mm": float(dd[D].mean() * 1e3) if len(D) else None,
                                            "D_max_mm": float(dd[D].max() * 1e3) if len(D) else None,
                                            "Z_max_mm": float(dd[Z].max() * 1e3)}
    R["4_deplacements"] = dep

    # 5. volume et étirement dans Z, LBS et DQS
    zone_poly = np.zeros(len(tot), bool)
    debut = np.concatenate([[0], np.cumsum(tot)[:-1]]).astype(np.int64)
    for p_i in range(len(tot)):
        if masque_Z[b[debut[p_i]:debut[p_i] + tot[p_i]]].mean() > 0.5:
            zone_poly[p_i] = True
    vol = {}
    for m, p in [("LBS", pos_L), ("DQS", pos_D)]:
        v = ML.volume_local(p, rest, b, tot, zone_polygone=zone_poly)
        e = ML.defauts(p, rest, b, tot, A)
        vol[m] = {"volume_zone_variation": v["variation_volume_zone"],
                  "volume_total_variation": v["variation_volume_total"],
                  "etirement_max_zone": float(np.nanmax(np.where(masque_Z[A[:, 0]] | masque_Z[A[:, 1]],
                                                                  np.linalg.norm(p[A[:, 0]] - p[A[:, 1]], axis=1) /
                                                                  np.maximum(np.linalg.norm(rest[A[:, 0]] - rest[A[:, 1]], axis=1), 1e-12), np.nan)))}
    R["5_volume_etirement_zone"] = vol

    # 6. LBS - DQS sur D
    diff = np.linalg.norm(pos_L - pos_D, axis=1)
    R["6_LBS_moins_DQS"] = {"D_moy_mm": float(diff[D].mean() * 1e3) if len(D) else None,
                             "D_max_mm": float(diff[D].max() * 1e3) if len(D) else None,
                             "reste_max_mm": float(diff[reste].max() * 1e3)}
    vmax_D = np.nan_to_num(ML.defauts(pos_D, rest, b, tot, A)["_vertex_etirement"], nan=0)
    R["6b_DQS_sur_D"] = {"etirement_max_LBS_sur_D": float(np.nan_to_num(vmax_L, nan=0)[D].max()) if len(D) else None,
                         "etirement_max_DQS_sur_D": float(vmax_D[D].max()) if len(D) else None,
                         "sommets_D_plus_etires_en_DQS": int((vmax_D[D] > np.nan_to_num(vmax_L, nan=0)[D]).sum())}
    json.dump(R, open(os.path.join(sortie, f"diagnostic_hanche_{pose_ref}.json"), "w"), indent=2, ensure_ascii=False)

    # figures
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(1, len(OS_ETUDIES), figsize=(3.2 * len(OS_ETUDIES), 3.6))
    for i, n in enumerate(OS_ETUDIES):
        sc = ax[i].scatter(rest[:, 1], rest[:, 2], s=0.8, c=P[:, noms.index(n)], cmap="magma", vmin=0, vmax=1)
        ax[i].set_title(n.replace("mixamorig:", "") + " (poids)", fontsize=8)
        ax[i].set_xlim(-0.35, 0.35); ax[i].set_ylim(0.6, 1.3); ax[i].set_aspect("equal"); ax[i].tick_params(labelsize=6)
    fig.colorbar(sc, ax=ax, shrink=0.8)
    fig.savefig(os.path.join(sortie, "poids_par_os_zone_hanche.png"), dpi=110)
    plt.close(fig)
    fig, ax = plt.subplots(1, 3, figsize=(10, 4))
    for i, (titre, v) in enumerate([("LBS (étirement par sommet)", vmax_L), ("DQS", vmax_D)]):
        sc = ax[i].scatter(rest[:, 1], rest[:, 2], s=0.8, c=np.clip(np.nan_to_num(v, nan=1.0), 1.0, 2.5),
                           cmap="inferno", vmin=1.0, vmax=2.5)
        ax[i].set_title(titre, fontsize=8)
        ax[i].set_xlim(-0.35, 0.35); ax[i].set_ylim(0.6, 1.3); ax[i].set_aspect("equal"); ax[i].tick_params(labelsize=6)
    dd = np.where(masque_D, diff, 0)
    sc2 = ax[2].scatter(rest[:, 1], rest[:, 2], s=0.8, c=dd * 1e3, cmap="viridis", vmin=0, vmax=max(1.0, float(dd.max() * 1e3)))
    ax[2].set_title("|LBS - DQS| sur D (mm)", fontsize=8)
    ax[2].set_xlim(-0.35, 0.35); ax[2].set_ylim(0.6, 1.3); ax[2].set_aspect("equal"); ax[2].tick_params(labelsize=6)
    fig.colorbar(sc, ax=ax[:2], shrink=0.8)
    fig.colorbar(sc2, ax=ax[2], shrink=0.8)
    fig.savefig(os.path.join(sortie, "carte_thermique_deformations.png"), dpi=110)
    plt.close(fig)
    print("DIAG_OK", sortie, "nb_D", len(D), "nb_Z", len(Z))


if __name__ == "__main__":
    main()

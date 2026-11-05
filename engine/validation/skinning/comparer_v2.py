"""Comparatif v2 (phase 4, priorité 3) : LBS, DQS et hybrides sur UN personnage, mêmes poses, mêmes matrices,
même maillage de base, mêmes mesures. Chaque personnage est traité séparément (un rapport par personnage).

Mesures par méthode et par pose :
  - métriques existantes (mesures.mesurer) : retournements, volume, étirement p99 et max ;
  - défauts locaux (metriques_locales.defauts) : maximum, comptages à plusieurs seuils, localisation, surface ;
  - déformation locale (metriques_locales.residu_os_dominant) : écart au mouvement rigide de l'os dominant (max, p99) ;
  - localisation anatomique : part des sommets touchés (>1,25 et >1,5) dans la zone hanche et la zone genou.
Une défaillance n'est jamais masquée : le maximum et les comptages sont toujours écrits avec le p99.

Usage : python3 engine/validation/skinning/comparer_v2.py POSES.npz NOM SORTIE_DOSSIER
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import methodes as M  # noqa: E402
import mesures as Ms  # noqa: E402
import metriques_locales as ML  # noqa: E402

METHODES = ["LBS", "DQS", "HYBRIDE_global", "HYBRIDE_angle"]
SEUILS_ETIR = (1.1, 1.25, 1.5)
SEUILS_COMP = (0.9, 0.8)
RAYON_ZONE = 0.20  # m : rayon des zones anatomiques autour de l'articulation (hanche, genou), fixé à l'avance
CAPTURE = ["L_flex120", "L_genou90", "L_abd30"]


def zones_articulaires(rest, B, noms):
    """Zones : sphères de rayon RAYON_ZONE autour de la tête des os cuisse et jambe (côtés gauche et droit)."""
    def t(n):
        return B[noms.index(n)][:3, 3]
    return {
        "hanche_G": t("mixamorig:LeftUpLeg"), "hanche_D": t("mixamorig:RightUpLeg"),
        "genou_G": t("mixamorig:LeftLeg"), "genou_D": t("mixamorig:RightLeg"),
    }


def sommets_par_zone(rest, zones):
    out = {}
    for nom, c in zones.items():
        out[nom] = np.linalg.norm(rest - c, axis=1) < RAYON_ZONE
    return out


def stats_zones(vmax, masques):
    """vmax : étirement maximal par sommet ; retourne comptages par zone (part des sommets de la zone)."""
    res = {}
    for nom, m in masques.items():
        v = vmax[m]
        v = v[np.isfinite(v)]
        if len(v) == 0:
            res[nom] = None
            continue
        res[nom] = {"sommets": int(len(v)),
                    "max": float(v.max()),
                    "part_>1.25": float((v > 1.25).mean()),
                    "part_>1.5": float((v > 1.5).mean())}
    return res


def main():
    npz, nom_perso, sortie = sys.argv[1], sys.argv[2], sys.argv[3]
    os.makedirs(sortie, exist_ok=True)
    d = np.load(npz)
    meta = json.load(open(npz.replace(".npz", ".json")))
    rest, Wi, Ww, B = d["rest_monde"], d["W_idx"], d["W_w"], d["bones_rest_monde"]
    b, tot = d["b_boucle"], d["b_tot"]
    noms = [str(n) for n in d["noms_os"]]
    A = Ms.aretes(b, tot, len(rest))
    poses = sorted({k[: -len("__os")] for k in d.files if k.endswith("__os")})
    zones = zones_articulaires(rest, B, noms)
    masques = sommets_par_zone(rest, zones)
    resultat = {"personnage": nom_perso, "fichier": os.path.basename(npz), "nb_sommets": int(len(rest)),
                "nb_polygones": int(len(tot)), "rayon_zone_m": RAYON_ZONE, "seuils_etirement": SEUILS_ETIR,
                "seuils_compression": SEUILS_COMP, "poses": {}}
    captures = {}
    for pose in poses:
        pm = d[pose + "__os"]
        pos_m, diag = M.calculer_toutes(rest, Wi, Ww, B, pm)
        Mv = M.repere_rigide(Wi, Ww, B, pm)
        T = pm @ np.linalg.inv(B)  # transformations d'os (même convention que calculer_toutes)
        entree = {"ctrl_LBS_vs_Blender_m": None}
        if pose + "__ctrl" in d.files:
            entree["ctrl_LBS_vs_Blender_m"] = float(np.abs(pos_m["LBS"] - d[pose + "__ctrl"]).max())
        entree["methodes"] = {}
        for m in METHODES:
            p = pos_m[m]
            mes = Ms.mesurer(p, rest, b, tot, A, Mv=Mv)
            dfx = ML.defauts(p, rest, b, tot, A, seuils_etirement=SEUILS_ETIR, seuils_compression=SEUILS_COMP)
            resid = ML.residu_os_dominant(p, rest, Wi, Ww, T)
            vol = ML.volume_local(p, rest, b, tot)["variation_volume_total"]
            vmax = dfx.pop("_vertex_etirement")
            dfx.pop("_vertex_compression")
            entree["methodes"][m] = {
                "retournements": mes["polygones_retournes"],
                "volume_variation": vol,
                "etirement_p99": mes["etirement_p99"],
                "etirement_max": dfx["etirement_max"],
                "etirement_ge5mm_max": mes["etirement_max_ge5mm"],
                "residu_os_dominant_max_m": float(resid.max()),
                "residu_os_dominant_p99_m": float(np.percentile(resid, 99)),
                "defauts": dfx,
                "zones": stats_zones(vmax, masques),
            }
            if pose in CAPTURE:
                captures.setdefault(pose, {})[m] = (p, vmax)
        resultat["poses"][pose] = entree
        print(nom_perso, pose, {m: entree["methodes"][m]["retournements"] for m in METHODES}, flush=True)
    with open(os.path.join(sortie, f"comparatif_{nom_perso}.json"), "w") as f:
        json.dump(resultat, f, indent=2, ensure_ascii=False)
    # captures : profil, couleur = étirement maximal du sommet ; défauts > 1,25 en rouge
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(len(METHODES), len(CAPTURE), figsize=(4.2 * len(CAPTURE), 3.4 * len(METHODES)))
    for i, m in enumerate(METHODES):
        for j, pose in enumerate(CAPTURE):
            ax = axes[i][j]
            p, vmax = captures[pose][m]
            c = np.clip(np.nan_to_num(vmax, nan=1.0), 1.0, 1.6)
            ax.scatter(p[:, 1], p[:, 2], s=0.6, c=c, cmap="viridis", vmin=1.0, vmax=1.6)
            bad = vmax > 1.25
            ax.scatter(p[bad, 1], p[bad, 2], s=2.0, c="red")
            ax.set_title(f"{nom_perso} {m} {pose}\nrouge : étirement > 1,25 ({int(bad.sum())} sommets)", fontsize=7)
            ax.set_aspect("equal")
            ax.set_xlim(-0.7, 0.7)
            ax.set_ylim(-0.1, 2.0)
            ax.tick_params(labelsize=6)
    fig.tight_layout()
    fig.savefig(os.path.join(sortie, f"captures_{nom_perso}.png"), dpi=110)
    plt.close(fig)
    print("COMPARATIF_V2_OK", nom_perso, sortie)


if __name__ == "__main__":
    main()

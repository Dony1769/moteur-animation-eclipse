"""Étape A/B (phase 4) : expériences contrôlées sur les POIDS seuls dans la zone hanche.

Protocole : mêmes poses, mêmes matrices d'os, même maillage, même méthode (LBS ou DQS) ; seules les lignes de poids
des sommets de la zone Z (rayon 0,20 m autour de la tête de LeftUpLeg) sont modifiées. Les poids sont renormalisés
comme Blender (entrée 152). Le modèle n'est jamais écrit : les variantes vivent en mémoire.

Référence : E0 (poids reconstruits à l'identique) doit donner exactement les mêmes mesures que le système actuel.
Variantes :
  E1 « nette »      : chaque sommet de Z ne garde que son os dominant (transition supprimée) ;
  E2 « lissée »     : moyenne des poids sur le voisinage (5 itérations), déjà testée (entrée 118) : reprise ici ;
  E3 « sans cuisse » : poids de LeftUpLeg retirés dans Z (le reste renormalisé) ;
  E4 « sans bassin » : poids de Hips et Spine retirés dans Z (le reste renormalisé).
Mesures : étirement max et p99 (globaux et dans Z), comptages > 1,1 / 1,25 / 1,5, volume de la zone, retournements.

Usage : python3 engine/validation/skinning/experience_poids_controlee.py POSES.npz SORTIE.json [POSE]
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import methodes as M  # noqa: E402
import mesures as Ms  # noqa: E402
import metriques_locales as ML  # noqa: E402
from diagnostic_hanche import poids_dense  # noqa: E402

RAYON = 0.20


def vers_sparse(P):
    N, J = P.shape
    K = int((P > 0).sum(axis=1).max())
    Wi = -np.ones((N, K), dtype=np.int64)
    Ww = np.zeros((N, K))
    for i in range(N):
        idx = np.where(P[i] > 0)[0]
        idx = idx[np.argsort(-P[i, idx])]
        Wi[i, :len(idx)] = idx
        Ww[i, :len(idx)] = P[i, idx]
    return Wi, Ww


def lisser(P, A, N, iters=5):
    Q = P.copy()
    a, b = A[:, 0], A[:, 1]
    deg = np.bincount(np.concatenate([a, b]), minlength=N).astype(float)
    for _ in range(iters):
        S = np.zeros_like(Q)
        np.add.at(S, a, Q[b]); np.add.at(S, b, Q[a])
        Q = (S + Q) / (deg[:, None] + 1)
    return Q


PERCENTILE_GRADIENT = 95  # fixé avant mesure : seuil = percentile 95 des gradients de poids hors zone, même corps


def limiter_gradient(P, A, rest, mZ, iters=30, s=0.25):
    """E5 : limite automatique du gradient de poids par arête. Seuil T = percentile PERCENTILE_GRADIENT des gradients
    (max_j |w_a,j - w_b,j| / longueur de repos) sur les arêtes qui ne touchent pas la zone, donc propre à chaque corps.
    Les arêtes au-dessus de T et touchant la zone sont relaxées (mélange partiel des poids des deux extrémités)."""
    a, b = A[:, 0], A[:, 1]
    l = np.maximum(np.linalg.norm(rest[a] - rest[b], axis=1), 1e-9)
    hors = ~(mZ[a] | mZ[b])
    def gradient(Q):
        return np.abs(Q[a] - Q[b]).max(axis=1) / l
    T = float(np.percentile(gradient(P)[hors], PERCENTILE_GRADIENT))
    Q = P.copy()
    touche = mZ[a] | mZ[b]
    modifies = np.zeros(len(P), bool)
    for it in range(iters):
        g = gradient(Q)
        viol = (g > T) & touche
        if not viol.any():
            break
        ia, ib = a[viol], b[viol]
        delta = np.zeros_like(Q)
        cnt = np.zeros(len(Q))
        np.add.at(delta, ia, s * (Q[ib] - Q[ia])); np.add.at(cnt, ia, 1)
        np.add.at(delta, ib, s * (Q[ia] - Q[ib])); np.add.at(cnt, ib, 1)
        m = cnt > 0
        Q[m] += delta[m] / cnt[m, None]
        modifies |= m
    return Q, {"seuil_gradient_T": T, "iterations": it + 1, "sommets_modifies": int(modifies.sum()),
               "gradient_max_apres": float(gradient(Q)[touche].max()), "gradient_max_avant": float(gradient(P)[touche].max())}


def mesurer_variante(P, rest, Wi_ref_B, B, d, b, tot, A, Z, pose, methode):
    Wi, Ww = vers_sparse(P)
    pm = d[pose + "__os"]
    res = M.calculer_toutes(rest, Wi, Ww, B, pm)[0][methode]
    Mv = M.repere_rigide(Wi, Ww, B, pm)
    mes = Ms.mesurer(res, rest, b, tot, A, Mv=Mv)
    dfx = ML.defauts(res, rest, b, tot, A)
    vmax = np.nan_to_num(dfx.pop("_vertex_etirement"), nan=1.0)
    zone_poly = np.zeros(len(tot), bool)
    debut = np.concatenate([[0], np.cumsum(tot)[:-1]]).astype(np.int64)
    masque_Z = np.zeros(len(rest), bool); masque_Z[Z] = True
    for p_i in range(len(tot)):
        if masque_Z[b[debut[p_i]:debut[p_i] + tot[p_i]]].mean() > 0.5:
            zone_poly[p_i] = True
    vol = ML.volume_local(res, rest, b, tot, zone_polygone=zone_poly)
    return {
        "etirement_max": dfx["etirement_max"], "etirement_p99": mes["etirement_p99"],
        "etirement_max_zone": float(vmax[Z].max()), "etirement_p99_zone": float(np.percentile(vmax[Z], 99)),
        "n_sommets_>1.1": dfx["sommets_etires_>1.1"], "n_sommets_>1.25": dfx["sommets_etires_>1.25"],
        "n_sommets_>1.5": dfx["sommets_etires_>1.5"], "volume_zone": vol["variation_volume_zone"],
        "volume_total": vol["variation_volume_total"], "retournements": mes["polygones_retournes"],
    }


def main():
    npz, sortie = sys.argv[1], sys.argv[2]
    pose = sys.argv[3] if len(sys.argv) > 3 else "L_flex120"
    d = np.load(npz)
    rest, Wi0, Ww0, B = d["rest_monde"], d["W_idx"], d["W_w"], d["bones_rest_monde"]
    b, tot = d["b_boucle"], d["b_tot"]
    noms = [str(n) for n in d["noms_os"]]
    N, J = len(rest), len(noms)
    A = Ms.aretes(b, tot, N)
    P0 = poids_dense(Wi0, Ww0, J)
    jUL = noms.index("mixamorig:LeftUpLeg"); jH = noms.index("mixamorig:Hips"); jS = noms.index("mixamorig:Spine")
    head = B[jUL][:3, 3]
    Z = np.where(np.linalg.norm(rest - head, axis=1) < RAYON)[0]
    mZ = np.zeros(N, bool); mZ[Z] = True
    variantes = {}
    variantes["E0_reference"] = P0.copy()
    P5, info5 = limiter_gradient(P0, A, rest, mZ)
    variantes["E5_gradient_limite"] = P5
    P1 = P0.copy(); am = np.argmax(P0, axis=1)
    P1[mZ] = 0; P1[np.where(mZ)[0], am[mZ]] = 1.0
    variantes["E1_nette"] = P1
    P2 = P0.copy(); L2 = lisser(P0, A, N)
    P2[mZ] = L2[mZ]
    variantes["E2_lissee"] = P2
    # retrait d'un os : si un sommet n'a plus aucun poids, il reçoit 1 sur Hips (repli déclaré, compté)
    def retirer(P, jlist):
        Q = P.copy()
        Q[np.ix_(np.where(mZ)[0], jlist)] = 0
        vides = np.where(mZ & (Q.sum(axis=1) <= 1e-12))[0]
        Q[vides, jH] = 1.0
        return Q, int(len(vides))
    P3, n3 = retirer(P0, [jUL])
    variantes["E3_sans_cuisse"] = P3
    P4, n4 = retirer(P0, [jH, jS])
    variantes["E4_sans_bassin"] = P4
    repli = {"E3_sans_cuisse": n3, "E4_sans_bassin": n4}
    # renormalisation de chaque variante (même règle que Blender et que _valides)
    for k in variantes:
        s = variantes[k].sum(axis=1, keepdims=True)
        variantes[k] = np.where(s > 1e-12, variantes[k] / np.maximum(s, 1e-12), variantes[k])
    out = {"pose": pose, "rayon_m": RAYON, "nb_Z": int(len(Z)), "variantes": {}, "sommets_repli_sur_Hips": repli,
           "E5_info": info5, "percentile_gradient": PERCENTILE_GRADIENT}
    for nom, P in variantes.items():
        out["variantes"][nom] = {}
        for methode in ["LBS", "DQS"]:
            out["variantes"][nom][methode] = mesurer_variante(P, rest, None, B, d, b, tot, A, Z, pose, methode)
        r = out["variantes"][nom]["LBS"]
        print(nom, "LBS max %.3f p99 %.3f zone_max %.3f >1.25 %d vol_zone %+.3f flips %d" % (
            r["etirement_max"], r["etirement_p99"], r["etirement_max_zone"], r["n_sommets_>1.25"],
            r["volume_zone"], r["retournements"]), flush=True)
    # contrôle : E0 doit reproduire la référence du système actuel
    ref = M.calculer_toutes(rest, Wi0, Ww0, B, d[pose + "__os"])[0]["LBS"]
    Wi_c, Ww_c = vers_sparse(variantes["E0_reference"])
    chk = M.calculer_toutes(rest, Wi_c, Ww_c, B, d[pose + "__os"])[0]["LBS"]
    out["controle_E0_ecart_m"] = float(np.abs(chk - ref).max())
    print("controle E0 ecart max m", out["controle_E0_ecart_m"], "repli", repli)
    json.dump(out, open(sortie, "w"), indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()

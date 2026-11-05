"""Centres de rotation par sommet (idée de Le & Hodgins 2016), réimplémentation maison.

Ce fichier ne copie aucun code du dépôt AvatarWorld/OptimisedCentresOfRotationSkinning (non officiel) : la méthode a été
lue (src/CoRCalculator.cpp, src/WeightsPerBone.cpp), puis réécrite à partir de la formule :

  centre_i = Σ_t aire_t · sim(w_i, w̄_t) · c_t  /  Σ_t aire_t · sim(w_i, w̄_t)

  - c_t : centroïde du triangle t au repos ; w̄_t : moyenne des poids de peau des sommets de t ;
  - sim(p, v) = Σ_{j≠k} exp( −(p_j v_k − p_k v_j)² / σ² ) : similarité de deux distributions de poids (deux sommets
    « pivotent » autour des mêmes os dans le même rapport). σ = 0,1 (valeur par défaut du dépôt non officiel).

Idée utilisée : le centre d'un sommet est là où ses voisins de même influence se rejoignent, c'est-à-dire près du
centre anatomique de l'articulation, et non sur la tête géométrique de l'os. Déformation : chaque sommet tourne autour de
son centre p_i selon l'angle θ·f_i de son os (f_i = poids de l'os articulé). Les distances au centre sont conservées.

Mesures : mêmes critères que les autres tests de phase 4 (étirement p99 hors et dans la bande, plis par plis_locaux,
inversions). Aucune évaluation n'est faite sans comparaison à la chaîne de nœuds actuelle.
"""
import sys, json
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_chaine_hanche as t
from correctif_arap import _rotations
from mesures_pose import plis_locaux
from scipy.spatial.transform import Rotation as Rot

SIGMA = 0.1


def centroides_et_aires(rest, faces):
    p0, p1, p2 = rest[faces[:, 0]], rest[faces[:, 1]], rest[faces[:, 2]]
    centre = (p0 + p1 + p2) / 3.0
    aire = 0.5 * np.linalg.norm(np.cross(p1 - p0, p2 - p0), axis=1)
    return centre, aire


def similarite(wv, Wt, sigma=SIGMA):
    """sim(wv, Wt[t]) pour tous les triangles t. wv : (K,), Wt : (T, K). Somme sur j≠k."""
    K = wv.shape[0]
    s = np.zeros(Wt.shape[0])
    s2 = sigma * sigma
    for j in range(K):
        for k in range(K):
            if j == k:
                continue
            a = wv[j] * Wt[:, k] - wv[k] * Wt[:, j]
            s += np.exp(-(a * a) / s2)
    return s


def centres_de_rotation(rest, faces, Wbones, sommets, sigma=SIGMA):
    """Centre de rotation de chaque sommet listé dans `sommets`.

    Wbones : (N, K) poids restreints aux K os retenus (les autres poids sont ignorés, justifié ci-dessous).
    Retourne (len(sommets), 3) et un indicateur de validité (dénominateur non nul).
    """
    centre, aire = centroides_et_aires(rest, faces)
    Wt = Wbones[faces].mean(axis=1)                    # poids moyens par triangle
    out = np.zeros((len(sommets), 3))
    ok = np.zeros(len(sommets), dtype=bool)
    for n, i in enumerate(sommets):
        sim = similarite(Wbones[i], Wt, sigma)
        poids = aire * sim
        den = poids.sum()
        if den > 0:
            out[n] = (poids[:, None] * centre).sum(axis=0) / den
            ok[n] = True
    return out, ok


if __name__ == "__main__":
    W = t.W
    # os retenus pour la hanche : hanche et ses enfants immédiats (les autres poids sont négligeables ici)
    os_hanche = [t.ix["mixamorig:Hips"], t.ix["mixamorig:LeftUpLeg"], t.ix["mixamorig:RightUpLeg"],
                 t.ix["mixamorig:Spine"], t.ix["mixamorig:LeftLeg"]]
    Wk = W[:, os_hanche]
    part_restante = 1.0 - Wk.sum(axis=1)
    print("masse de poids hors des 5 os retenus : max", float(part_restante.max()), flush=True)
    s = (t.rest - t.h[t.ix["mixamorig:LeftUpLeg"]]) @ (t.h[t.ix["mixamorig:LeftLeg"]] - t.h[t.ix["mixamorig:LeftUpLeg"]])
    sommets = np.where(np.abs(s) < 0.15)[0][:300]      # échantillon de la bande (test d'abord, pas tout le maillage)
    C, ok = centres_de_rotation(t.rest, t.faces, Wk, sommets)
    pivot = t.h[t.ix["mixamorig:LeftUpLeg"]]
    ecart = np.linalg.norm(C[ok] - pivot, axis=1)
    rapport = dict(
        sommets_testes=int(len(sommets)), centres_valides=int(ok.sum()),
        ecart_au_pivot_geometrique_m_mediane=round(float(np.median(ecart)), 4),
        ecart_au_pivot_geometrique_m_max=round(float(ecart.max()), 4),
        masse_hors_os_retenus_max=round(float(part_restante.max()), 5),
        sigma=SIGMA, statut="MESURE_EN_COURS")
    print(json.dumps(rapport, indent=2), flush=True)
    out = Path(__file__).resolve().parents[2] / "docs" / "rapports" / "phase4_centres_rotation_hanche.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rapport, indent=2, ensure_ascii=False))

"""Expériences d'isolation sur la hanche masculine : un facteur à la fois, mêmes géométries, poids et repères.

Facteurs (chacun modifie UN seul élément par rapport à SQ de base) :
  F0  SQ de base : rotation moyennée = polaire de Mv ; ancrage λ = 0,1 ; appliqué à tous les sommets.
  F1  SQV1 : SQ suivi d'une étape de correction de volume.
  F2  SQV3 : SQ suivi de trois étapes de correction de volume.
  F3  rotations interpolées autrement : moyenne de quaternions pondérée (signe aligné) au lieu de la polaire de Mv.
  F4  zone d'application : SQ seulement là où la distance au centre de l'articulation est < α × longueur réelle
      de l'os articulé, LBS ailleurs. α ∈ {0,5 ; 1,0 ; 1,5}.
  F5  ancrage λ ∈ {0,01 ; 0,1 ; 1,0}.
  F6  DIAGNOSTIC DE POIDS (pas un candidat) : poids des deux cuisses transférés au bassin pour les sommets dont les
      deux cuisses ont un poids ≥ 0,2. Compare LBS et SQ avec les mêmes nouveaux poids.

Jeux de poses :
  - calibration (choix de α et λ seulement) : hanche gauche 60° et 90°, synthétiques ;
  - investigation (poses où le défaut a été observé) : hanche G 75/105/120, hanche D 75/120, synthétiques ;
  - indépendantes (JAMAIS utilisées pour choisir ni pour diagnostiquer) : poses réelles de poses2.npz non examinées
    (abduction, adduction, rotations, combinaisons, flexions 30/60°, genoux 30/60/90°).
Mesures : étirement max, p99, retournements (repère Mv de référence), |volume| (mesurer), par pose.
"""
import importlib.util
import json
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
DONNEES = os.environ.get("ANATOMIE_DONNEES", "/tmp/claude-0/-home-claude/9ce8e1e5-f7cf-5619-8a75-3c6d9a11ab1c/scratchpad")
SORTIE = os.path.join(RACINE, "docs", "rapports", "skinning", "isolation_hanche_masc")
NPZ = os.path.join(DONNEES, "skin", "poses2.npz")
JS = os.path.join(RACINE, "docs", "rapports", "skinning", "anatomie", "squelette_masc.json")


def charger(nom):
    spec = importlib.util.spec_from_file_location(nom, os.path.join(HERE, nom + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


INV = charger("investigation_hanche_masc")
P, M, Ms, ARAP, CV = INV.P, INV.M, INV.Ms, INV.ARAP, INV.CV
EXP = INV.EXP

ARTS = {"hanche_G": "LeftUpLeg", "hanche_D": "RightUpLeg"}
CALIB = [("hanche_G", 60), ("hanche_G", 90)]
INVEST = [("hanche_G", 75), ("hanche_G", 105), ("hanche_G", 120), ("hanche_D", 75), ("hanche_D", 120)]
REELLES = ["L_abd30", "L_add20", "L_ext30", "L_int30", "R_abd30", "R_add20", "L_flex30", "L_flex60",
           "L_genou30", "L_genou60", "R_flex30", "R_flex60", "R_flex90", "R_flex120", "R_genou90",
           "L_combo_flex60_abd20_int20_genou60", "L_combo_flex90_abd30_ext30", "R_combo_flex90_abd30_ext30",
           "R_combo_flex60_abd20_int20_genou60", "L_combo_flex120_genou90", "R_combo_flex120_genou90"]


def quaternion_depuis_R(R):
    """R (...,3,3) -> q (...,4) (w,x,y,z), Shepperd, vectorisé."""
    tr = R[..., 0, 0] + R[..., 1, 1] + R[..., 2, 2]
    q = np.zeros(R.shape[:-2] + (4,))
    t = np.sqrt(np.maximum(tr + 1, 1e-12)) * 0.5
    q[..., 0] = t
    q[..., 1] = (R[..., 2, 1] - R[..., 1, 2]) / (4 * t + 1e-12)
    q[..., 2] = (R[..., 0, 2] - R[..., 2, 0]) / (4 * t + 1e-12)
    q[..., 3] = (R[..., 1, 0] - R[..., 0, 1]) / (4 * t + 1e-12)
    return q


def R_depuis_quaternion(q):
    q = q / np.linalg.norm(q, axis=-1, keepdims=True)
    w, x, y, z = q[..., 0], q[..., 1], q[..., 2], q[..., 3]
    R = np.empty(q.shape[:-1] + (3, 3))
    R[..., 0, 0] = 1 - 2 * (y * y + z * z)
    R[..., 0, 1] = 2 * (x * y - z * w)
    R[..., 0, 2] = 2 * (x * z + y * w)
    R[..., 1, 0] = 2 * (x * y + z * w)
    R[..., 1, 1] = 1 - 2 * (x * x + z * z)
    R[..., 1, 2] = 2 * (y * z - x * w)
    R[..., 2, 0] = 2 * (x * z - y * w)
    R[..., 2, 1] = 2 * (y * z + x * w)
    R[..., 2, 2] = 1 - 2 * (x * x + y * y)
    return R


def rotation_quaternion_moyennee(Wi, Ww, Tk):
    """Moyenne pondérée de quaternions (signe aligné sur l'os de plus fort poids), puis matrice."""
    Rk = Tk[:, :3, :3]
    qk = quaternion_depuis_R(Rk)  # (J,4)
    qi = qk[Wi]  # (N,4,4)
    dom = np.argmax(Ww, axis=1)
    ref = qi[np.arange(len(Wi)), dom]  # (N,4)
    signe = np.sign(np.einsum("nkd,nd->nk", qi, ref))
    signe[signe == 0] = 1
    q = np.einsum("nk,nkd->nd", Ww * signe, qi)
    return R_depuis_quaternion(q)


def stretch_lbs_sq(pos_lbs, rest, A, Rfix, lam):
    return ARAP.solve_fixe(pos_lbs, rest, A, Rfix, lam)


def mesures(pos, rest, b, tot, A, Wi, Ww, B, pm):
    Mv = M.repere_rigide(Wi, Ww, B, pm)
    m = Ms.mesurer(pos, rest, b, tot, A, Mv=Mv)
    return {"etirement_max": float(m["etirement_max"]), "etirement_p99": float(m["etirement_p99"]),
            "retournements": int(m["polygones_retournes"]), "volume_variation": float(m["variation_volume_relative"])}


def contexte():
    z = np.load(NPZ)
    noms = [str(n) for n in z["noms_os"]]
    rest, Wi, Ww, B = z["rest_monde"], z["W_idx"], z["W_w"], z["bones_rest_monde"]
    b, tot = z["b_boucle"], z["b_tot"]
    A = Ms.aretes(b, tot, len(rest))
    TRI = CV._triangles(b, tot)
    return z, noms, rest, Wi, Ww, B, b, tot, A, TRI


def poses_synthetiques(z, noms, art, th):
    pm, centre, chaine, sens = INV.pose_test(z, noms, JS, art, th)
    return pm, centre, ARTS[art]


def poses_reelles(z, noms, nom):
    return z[nom + "__os"]


def variantes(z, noms, rest, Wi, Ww, B, b, tot, A, TRI, pm, centre, longueur, lbs, facteur, arg=None):
    """Positions pour un facteur. Retourne (pos, Wi_utilisé, Ww_utilisé)."""
    Mv_ref = M.repere_rigide(Wi, Ww, B, pm)
    Tk = pm @ np.linalg.inv(B)
    if facteur == "F0":
        return ARAP.solve_fixe(lbs, rest, A, ARAP.polaire(Mv_ref), 0.1), Wi, Ww
    if facteur == "F1":
        p = ARAP.solve_fixe(lbs, rest, A, ARAP.polaire(Mv_ref), 0.1)
        return CV.corriger(p, rest, Wi, Ww, b, tot, T=TRI, M=1)[0], Wi, Ww
    if facteur == "F2":
        p = ARAP.solve_fixe(lbs, rest, A, ARAP.polaire(Mv_ref), 0.1)
        return CV.corriger(p, rest, Wi, Ww, b, tot, T=TRI, M=3)[0], Wi, Ww
    if facteur == "F3":
        Rq = rotation_quaternion_moyennee(Wi, Ww, Tk)
        return ARAP.solve_fixe(lbs, rest, A, Rq, 0.1), Wi, Ww
    if facteur == "F4":
        p = ARAP.solve_fixe(lbs, rest, A, ARAP.polaire(Mv_ref), 0.1)
        rayon = arg * longueur
        zone = np.linalg.norm(rest - centre, axis=1) < rayon
        return np.where(zone[:, None], p, lbs), Wi, Ww
    if facteur == "F5":
        return ARAP.solve_fixe(lbs, rest, A, ARAP.polaire(Mv_ref), arg), Wi, Ww
    if facteur == "F6":
        # diagnostic : pour les sommets dont les deux cuisses pèsent ≥ 0,2, le poids de la cuisse gauche est transféré
        # au bassin (même somme de poids, pas de renormalisation), la cuisse droite est mise à zéro.
        idx_h = noms.index("mixamorig:Hips")
        gauche, droite = noms.index("mixamorig:LeftUpLeg"), noms.index("mixamorig:RightUpLeg")
        Wi2, Ww2 = Wi.copy(), Ww.copy()
        for i in range(len(Wi2)):
            sg = [c for c in range(Wi2.shape[1]) if Wi2[i, c] == gauche]
            sd = [c for c in range(Wi2.shape[1]) if Wi2[i, c] == droite]
            if not sg or not sd:
                continue
            wg, wd = Ww2[i, sg[0]], Ww2[i, sd[0]]
            if wg >= 0.2 and wd >= 0.2:
                Wi2[i, sg[0]] = idx_h
                Ww2[i, sg[0]] = wg + wd
                Ww2[i, sd[0]] = 0.0
        lbs2 = M.calculer_toutes(rest, Wi2, Ww2, B, pm)[0]["LBS"]
        p = ARAP.solve_fixe(lbs2, rest, A, ARAP.polaire(M.repere_rigide(Wi2, Ww2, B, pm)), 0.1)
        return p, Wi2, Ww2
    raise ValueError(facteur)


if __name__ == "__main__":
    os.makedirs(SORTIE, exist_ok=True)
    z, noms, rest, Wi, Ww, B, b, tot, A, TRI = contexte()
    resultats = {"calibration": {}, "investigation": {}, "independantes": {}}
    alphas = [0.5, 1.0, 1.5]
    lambdas = [0.01, 0.1, 1.0]
    configs = [("F0", None), ("F1", None), ("F2", None), ("F3", None)] + \
              [("F4", a) for a in alphas] + [("F5", l) for l in lambdas] + [("F6", None)]

    def evaluer(jeu, poses):
        sortie = {}
        for nom_pose, (pm, centre, os_nom) in poses.items():
            ref = M.calculer_toutes(rest, Wi, Ww, B, pm)[0]
            lbs = ref["LBS"]
            longueur = [o for o in json_os if o["nom"] == "mixamorig:" + os_nom][0]["longueur"]
            ligne = {"LBS": mesures(lbs, rest, b, tot, A, Wi, Ww, B, pm)}
            for f, arg in configs:
                cle = f + ("" if arg is None else f"_{arg}")
                pos, Wu, Wwu = variantes(z, noms, rest, Wi, Ww, B, b, tot, A, TRI, pm, centre, longueur, lbs, f, arg)
                if f == "F6":
                    lbs_mod = M.calculer_toutes(rest, Wu, Wwu, B, pm)[0]["LBS"]
                    ligne["F6_LBS_poids_modifies"] = mesures(lbs_mod, rest, b, tot, A, Wi, Ww, B, pm)
                ligne[cle] = mesures(pos, rest, b, tot, A, Wi, Ww, B, pm)
            sortie[nom_pose] = ligne
        return sortie

    json_os = json.load(open(JS, encoding="utf-8"))["os"]
    # 1) calibration (synthétique)
    cal_poses = {f"{a}_{t}": poses_synthetiques(z, noms, a, t) for a, t in CALIB}
    resultats["calibration"] = evaluer("calibration", cal_poses)
    # 2) investigation (synthétique, poses où le défaut a été observé)
    inv_poses = {f"{a}_{t}": poses_synthetiques(z, noms, a, t) for a, t in INVEST}
    resultats["investigation"] = evaluer("investigation", inv_poses)
    # 3) indépendantes (réelles, jamais examinées)
    ind_poses = {n: (z[n + "__os"], None, None) for n in REELLES}
    # le centre et l'os articulé sont déduits du nom de la pose
    for n in REELLES:
        art = "hanche_G" if n.startswith("L_") else "hanche_D"
        os_nom = "LeftUpLeg" if art == "hanche_G" else "RightUpLeg"
        centre = np.array([o for o in json_os if o["nom"] == "mixamorig:" + os_nom][0]["tete"])
        ind_poses[n] = (z[n + "__os"], centre, os_nom)
    resultats["independantes"] = evaluer("independantes", ind_poses)
    with open(os.path.join(SORTIE, "resultats_isolation.json"), "w", encoding="utf-8") as f:
        json.dump(resultats, f, indent=1, ensure_ascii=False, default=float)
    print("ECRIT", os.path.join(SORTIE, "resultats_isolation.json"), flush=True)

"""Étape 3c (suite) : correction ARAP locale-globale, sans cible (phase 4).

Méthode (Sorkine & Alexa 2007, « As-Rigid-As-Possible Surface Modeling », formulation locale-globale) :
- état initial : positions LBS p (référence du projet) ;
- étape locale : pour chaque sommet i, rotation R_i = polaire de S_i = Σ_j w_ij (r_i − r_j)(p_i − p_j)^T,
  avec r = repos, p = courant ; déterminant forcé à +1 ;
- étape globale : pour chaque arête (a,b), R_ab = (R_a + R_b)/2 ; on minimise
  Σ w_ab |(p_a − p_b) − R_ab (r_a − r_b)|² + λ Σ_i |p_i − p_LBS,i|² (résolution linéaire, matrice constante) ;
- K itérations locale-globale. Poids w_ab = 1 (arêtes du maillage). Paramètres GLOBAUX : K ∈ {5 ; 20}, λ ∈ {0,1 ; 1,0} (λ > 0 obligatoire, voir entrée 180).

Protocole identique à l'étape 3c (arêtes) et 3b : calibration masculin hanche 60°/90° ; critère sur chaque pose :
p99 ≤ LBS, retournements ≤ LBS, |volume| ≤ LBS. Aucun critère relâché. Test sur les autres poses, trois morphologies.
"""
import importlib.util
import json
import os

import numpy as np
import scipy.sparse as sp
from scipy.sparse.linalg import factorized

HERE = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
DONNEES = os.environ.get("ANATOMIE_DONNEES", "/tmp/claude-0/-home-claude/9ce8e1e5-f7cf-5619-8a75-3c6d9a11ab1c/scratchpad")
SORTIE = os.path.join(RACINE, "docs", "rapports", "skinning", "arap")


def charger(nom):
    spec = importlib.util.spec_from_file_location(nom, os.path.join(HERE, nom + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


P = charger("poses_articulaires")
M = charger("methodes")
Ms = charger("mesures")
EXP = charger("experience_corrections_articulaires")
CV = charger("correction_volume")

KS = [5, 20]
LAMBDAS = [0.1, 1.0]  # λ > 0 obligatoire : λ = 0 rend le système singulier (translation libre, voir entrée 180)


def arap(pos_lbs, rest, A, K, lam):
    """ARAP locale-globale. Retourne les positions finales (N,3)."""
    a, b = A[:, 0], A[:, 1]
    N = len(rest)
    d0 = rest[a] - rest[b]  # arêtes au repos (E,3)
    deg = np.bincount(np.concatenate([a, b]), minlength=N).astype(float)
    # matrice constante : (deg + λ) I − Adj
    diag = deg + lam
    M_mat = sp.coo_matrix(
        (np.concatenate([diag, -np.ones(2 * len(a))]),
         (np.concatenate([np.arange(N), a, b]), np.concatenate([np.arange(N), b, a]))),
        shape=(N, N)).tocsc()
    solve = factorized(M_mat)
    p = pos_lbs.copy()
    for _ in range(K):
        # étape locale : covariance par sommet
        d = p[a] - p[b]
        Pab = d0[:, :, None] * d[:, None, :]  # (E,3,3) : (r_a−r_b)(p_a−p_b)^T
        S = np.zeros((N, 3, 3))
        np.add.at(S, a, Pab)
        np.add.at(S, b, Pab)
        U, _, Vt = np.linalg.svd(S)
        R = np.matmul(np.transpose(Vt, (0, 2, 1)), np.transpose(U, (0, 2, 1)))
        det = np.linalg.det(R)
        # correction de déterminant : inverser la dernière colonne de V si det < 0
        Vt2 = Vt.copy()
        Vt2[det < 0, 2, :] *= -1
        R = np.matmul(np.transpose(Vt2, (0, 2, 1)), np.transpose(U, (0, 2, 1)))
        # étape globale : second membre
        Rab = 0.5 * (R[a] + R[b])  # (E,3,3)
        rhs_edge = np.einsum("eij,ej->ei", Rab, d0)  # R_ab (r_a − r_b)
        rhs = np.zeros((N, 3))
        np.add.at(rhs, a, rhs_edge)
        np.add.at(rhs, b, -rhs_edge)
        rhs += lam * pos_lbs
        p = np.column_stack([solve(rhs[:, c]) for c in range(3)])
    return p


def mesurer_pose(pos_pose, rest, b, tot, A, Wi, Ww, B, pm):
    Mv = M.repere_rigide(Wi, Ww, B, pm)
    mes = Ms.mesurer(pos_pose, rest, b, tot, A, Mv=Mv)
    return {"etirement_max": float(mes["etirement_max"]), "etirement_p99": float(mes["etirement_p99"]),
            "retournements": int(mes["polygones_retournes"]),
            "volume_variation": float(mes["variation_volume_relative"])}


def main():
    os.makedirs(SORTIE, exist_ok=True)
    resultats = {"ks": KS, "lambdas": LAMBDAS, "morphos": {}, "calibration": {}, "choix": None}
    contextes = {}
    for morph, (npz, js) in EXP.MORPHOS.items():
        z = np.load(os.path.join(DONNEES, npz))
        noms = [str(n) for n in z["noms_os"]]
        sens = {art: EXP.signe_depuis_pose_reelle(z, noms, os.path.join(RACINE, js), os_nom, pose_ref)[0]
                for art, (os_nom, pose_ref) in EXP.ARTICULATIONS.items()}
        contextes[morph] = {"z": z, "noms": noms, "js": os.path.join(RACINE, js), "sens": sens}

    cles = [f"ARAP_K{k}_l{l}" for k in KS for l in LAMBDAS] + [f"SQ_l{l}" for l in LAMBDAS] + \
        [f"SQV{e}_l{l}" for e in (1, 3) for l in LAMBDAS] + [f"SD_l{l}" for l in LAMBDAS] + [f"SDV1_l{l}" for l in LAMBDAS]
    for morph, c in contextes.items():
        z, noms, js = c["z"], c["noms"], c["js"]
        rest, Wi, Ww, B = z["rest_monde"], z["W_idx"], z["W_w"], z["bones_rest_monde"]
        b, tot = z["b_boucle"], z["b_tot"]
        A = Ms.aretes(b, tot, len(rest))
        TRI = CV._triangles(b, tot)
        lignes = []
        for art, (os_nom, _) in EXP.ARTICULATIONS.items():
            if art not in EXP.TEST:
                continue
            sens = c["sens"][art]
            for th in sorted(set(EXP.CALIB.get(art, []) + EXP.TEST[art])):
                theta = np.radians(th)
                centre, axe, chaine = P.articulation(js, EXP.prefixe(noms) + os_nom)
                T = P.transformation_articulation(centre, axe, theta, sens)
                pm = P.matrices_pose(B, noms, chaine, T)
                ref = M.calculer_toutes(rest, Wi, Ww, B, pm)[0]
                lbs = ref["LBS"]
                ligne = {"articulation": art, "angle_deg": th,
                         "phase": "calibration" if th in EXP.CALIB.get(art, []) else "test",
                         "LBS": mesurer_pose(lbs, rest, b, tot, A, Wi, Ww, B, pm),
                         "DQS": mesurer_pose(ref["DQS"], rest, b, tot, A, Wi, Ww, B, pm)}
                for K in KS:
                    for lam in LAMBDAS:
                        pos = arap(lbs, rest, A, K, lam)
                        ligne[f"ARAP_K{K}_l{lam}"] = mesurer_pose(pos, rest, b, tot, A, Wi, Ww, B, pm)
                Rsq = polaire(M.repere_rigide(Wi, Ww, B, pm))
                # variante « os dominant » : rotation du seul os de plus fort poids (pas de moyenne)
                Tk = pm @ np.linalg.inv(B)
                dom = Wi[np.arange(len(Wi)), np.argmax(Ww, axis=1)]
                Rdom = polaire(Tk[dom, :3, :3])
                for lam in LAMBDAS:
                    pos_d = solve_fixe(lbs, rest, A, Rdom, lam)
                    ligne[f"SD_l{lam}"] = mesurer_pose(pos_d, rest, b, tot, A, Wi, Ww, B, pm)
                    pvd, _ = CV.corriger(pos_d, rest, Wi, Ww, b, tot, T=TRI, M=1)
                    ligne[f"SDV1_l{lam}"] = mesurer_pose(pvd, rest, b, tot, A, Wi, Ww, B, pm)
                for lam in LAMBDAS:
                    pos = solve_fixe(lbs, rest, A, Rsq, lam)
                    ligne[f"SQ_l{lam}"] = mesurer_pose(pos, rest, b, tot, A, Wi, Ww, B, pm)
                    # chaîne : SQ puis correction de volume (étape 2 de la phase, méthode Rohmer, dérivée et testée)
                    for etapes in (1, 3):
                        pv, _ = CV.corriger(pos, rest, Wi, Ww, b, tot, T=TRI, M=etapes)
                        ligne[f"SQV{etapes}_l{lam}"] = mesurer_pose(pv, rest, b, tot, A, Wi, Ww, B, pm)
                lignes.append(ligne)
                print(morph, art, th, flush=True)
        resultats["morphos"][morph] = {"lignes": lignes}

    cal = [l for l in resultats["morphos"]["masculin"]["lignes"] if l["phase"] == "calibration"]
    acceptes = []
    for cl in cles:
        ok = all(l[cl]["etirement_p99"] <= l["LBS"]["etirement_p99"] + 1e-12 and
                 l[cl]["retournements"] <= l["LBS"]["retournements"] and
                 abs(l[cl]["volume_variation"]) <= abs(l["LBS"]["volume_variation"]) + 1e-12 for l in cal)
        resultats["calibration"][cl] = {"accepte": bool(ok),
                                        "max_pire": float(max(l[cl]["etirement_max"] for l in cal)),
                                        "p99_pire": float(max(l[cl]["etirement_p99"] for l in cal)),
                                        "retournements_pires": int(max(l[cl]["retournements"] for l in cal))}
        if ok:
            acceptes.append(cl)
    resultats["choix"] = min(acceptes, key=lambda k: resultats["calibration"][k]["max_pire"]) if acceptes else None
    print("acceptés en calibration :", acceptes, flush=True)
    with open(os.path.join(SORTIE, "resume.json"), "w", encoding="utf-8") as f:
        json.dump(resultats, f, indent=1, ensure_ascii=False, default=float)
    print("ECRIT", flush=True)




def solve_fixe(pos_lbs, rest, A, Rfix, lam):
    """Variante « rotations du squelette » : R_i fournis (polaire de Mv = Σ w_k R_k), pas d'étape locale.
    Résout min Σ_ab |(p_a−p_b) − R_ab(r_a−r_b)|² + λ|p − p_LBS|², une seule fois (pas d'itération)."""
    a, b = A[:, 0], A[:, 1]
    N = len(rest)
    d0 = rest[a] - rest[b]
    deg = np.bincount(np.concatenate([a, b]), minlength=N).astype(float)
    M_mat = sp.coo_matrix(
        (np.concatenate([deg + lam, -np.ones(2 * len(a))]),
         (np.concatenate([np.arange(N), a, b]), np.concatenate([np.arange(N), b, a]))),
        shape=(N, N)).tocsc()
    solve = factorized(M_mat)
    Rab = 0.5 * (Rfix[a] + Rfix[b])
    rhs_edge = np.einsum("eij,ej->ei", Rab, d0)
    rhs = np.zeros((N, 3))
    np.add.at(rhs, a, rhs_edge)
    np.add.at(rhs, b, -rhs_edge)
    rhs += lam * pos_lbs
    return np.column_stack([solve(rhs[:, c]) for c in range(3)])


def polaire(Mv):
    U, _, Vt = np.linalg.svd(Mv)
    R = np.matmul(U, Vt)
    det = np.linalg.det(R)
    U2 = U.copy()
    U2[det < 0, :, 2] *= -1
    return np.matmul(U2, Vt)


if __name__ == "__main__":
    main()

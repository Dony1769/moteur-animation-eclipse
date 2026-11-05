"""Étape 3c : correction par contraintes d'arêtes (position-based dynamics), sans cible (phase 4).

Principe : partir de la position LBS (référence du projet) et ramener chaque arête vers sa longueur de repos,
avec un ancrage à la position LBS. Aucune forme sculptée, aucune cible HR (voir étape 3a).

Itération de Jacobi (par arête (i,j), C = |p_i − p_j| − L_ij) :
  Δ_i += −½ β C n_ij ; Δ_j += +½ β C n_ij, où n_ij = (p_i − p_j)/|p_i − p_j| ;
  Δ moyenné par degré du sommet ; puis p ← p + Δ + λ (p_LBS − p).
Paramètres GLOBAUX : β ∈ {0,5 ; 1,0}, K ∈ {5 ; 20} itérations, λ ∈ {0 ; 0,3}. Aucun réglage par personnage.

Protocole (identique à l'étape 3b) :
  - calibration : masculin, hanche gauche 60° et 90°. Critère : sur chaque pose, p99 ≤ LBS, retournements ≤ LBS,
    |volume| ≤ LBS ; le maximum d'étirement n'est PAS suffisant seul ;
  - test : poses de l'étape 3b (hanche G 75/105/120, hanche D 75/120, genou G 60/90/105), trois morphologies ;
  - référence : LBS et DQS ; mêmes métriques (mesurer, repère rigide commun).
"""
import importlib.util
import json
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
DONNEES = os.environ.get("ANATOMIE_DONNEES", "/tmp/claude-0/-home-claude/9ce8e1e5-f7cf-5619-8a75-3c6d9a11ab1c/scratchpad")
SORTIE = os.path.join(RACINE, "docs", "rapports", "skinning", "contraintes_aretes")


def charger(nom):
    spec = importlib.util.spec_from_file_location(nom, os.path.join(HERE, nom + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


P = charger("poses_articulaires")
M = charger("methodes")
Ms = charger("mesures")
EXP = charger("experience_corrections_articulaires")  # réutilise MORPHOS, signes, protocole de test

BETAS = [0.5, 1.0]
ITERS = [5, 20]
LAMBDAS = [0.0, 0.3]


def contraindre_aretes(pos_init, rest, A, beta, K, lam):
    """Ramène les arêtes vers leur longueur de repos, ancrage λ vers pos_init. Retourne positions finales."""
    a, b = A[:, 0], A[:, 1]
    L = np.linalg.norm(rest[a] - rest[b], axis=1)
    N = len(rest)
    deg = np.bincount(np.concatenate([a, b]), minlength=N).astype(float)
    deg = np.maximum(deg, 1.0)[:, None]
    p = pos_init.copy()
    for _ in range(K):
        d = p[a] - p[b]
        l = np.linalg.norm(d, axis=1)
        l_safe = np.maximum(l, 1e-12)
        C = l - L
        n = d / l_safe[:, None]
        corr = (-0.5 * beta * C)[:, None] * n  # déplacement de a ; b reçoit l'opposé
        D = np.zeros((N, 3))
        np.add.at(D, a, corr)
        np.add.at(D, b, -corr)
        p = p + D / deg + lam * (pos_init - p)
    return p


def mesurer_pose(pos_pose, rest, b, tot, A, Wi, Ww, B, pm):
    Mv = M.repere_rigide(Wi, Ww, B, pm)
    mes = Ms.mesurer(pos_pose, rest, b, tot, A, Mv=Mv)
    return {"etirement_max": float(mes["etirement_max"]), "etirement_p99": float(mes["etirement_p99"]),
            "retournements": int(mes["polygones_retournes"]),
            "volume_variation": float(mes["variation_volume_relative"])}


def main():
    os.makedirs(SORTIE, exist_ok=True)
    resultats = {"betas": BETAS, "iters": ITERS, "lambdas": LAMBDAS, "morphos": {}, "calibration": {}, "choix": None}
    contextes = {}
    for morph, (npz, js) in EXP.MORPHOS.items():
        z = np.load(os.path.join(DONNEES, npz))
        noms = [str(n) for n in z["noms_os"]]
        sens = {}
        for art, (os_nom, pose_ref) in EXP.ARTICULATIONS.items():
            sens[art] = EXP.signe_depuis_pose_reelle(z, noms, os.path.join(RACINE, js), os_nom, pose_ref)[0]
        contextes[morph] = {"z": z, "noms": noms, "js": os.path.join(RACINE, js), "sens": sens}

    cles = [f"AR_b{b}_K{k}_l{l}" for b in BETAS for k in ITERS for l in LAMBDAS]
    for morph, c in contextes.items():
        z, noms, js = c["z"], c["noms"], c["js"]
        rest, Wi, Ww, B = z["rest_monde"], z["W_idx"], z["W_w"], z["bones_rest_monde"]
        b, tot = z["b_boucle"], z["b_tot"]
        A = Ms.aretes(b, tot, len(rest))
        lignes = []
        for art, (os_nom, _) in EXP.ARTICULATIONS.items():
            if art not in EXP.TEST:
                continue
            sens = c["sens"][art]
            EXP.ART_OS[art] = os_nom
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
                for be in BETAS:
                    for K in ITERS:
                        for lam in LAMBDAS:
                            pos = contraindre_aretes(lbs, rest, A, be, K, lam)
                            ligne[f"AR_b{be}_K{K}_l{lam}"] = mesurer_pose(pos, rest, b, tot, A, Wi, Ww, B, pm)
                lignes.append(ligne)
                print(morph, art, th, flush=True)
        resultats["morphos"][morph] = {"lignes": lignes}

    # Choix sur la calibration masculine uniquement, critère multiple, sans seuil relâché.
    cal = [l for l in resultats["morphos"]["masculin"]["lignes"] if l["phase"] == "calibration"]
    acceptes = []
    for cl in cles:
        ok = all(l[cl]["etirement_p99"] <= l["LBS"]["etirement_p99"] + 1e-12 and
                 l[cl]["retournements"] <= l["LBS"]["retournements"] and
                 abs(l[cl]["volume_variation"]) <= abs(l["LBS"]["volume_variation"]) + 1e-12 for l in cal)
        resultats["calibration"][cl] = {"accepte": bool(ok),
                                        "max_pire": float(max(l[cl]["etirement_max"] for l in cal)),
                                        "p99_pire": float(max(l[cl]["etirement_p99"] for l in cal))}
        if ok:
            acceptes.append(cl)
    resultats["choix"] = min(acceptes, key=lambda k: resultats["calibration"][k]["max_pire"]) if acceptes else None
    print("candidats acceptés en calibration :", acceptes, flush=True)
    print("choix :", resultats["choix"], flush=True)
    with open(os.path.join(SORTIE, "resume.json"), "w", encoding="utf-8") as f:
        json.dump(resultats, f, indent=1, ensure_ascii=False, default=float)
    print("ECRIT", os.path.join(SORTIE, "resume.json"), flush=True)


if __name__ == "__main__":
    main()

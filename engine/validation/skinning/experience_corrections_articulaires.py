"""Étape 3b : correction procédurale d'articulation, interpolation et généralisation (phase 4).

Candidat C1 « blend rigide articulaire » (aucune cible sculptée, aucune cible HR) :
  x_LBS(v)  : position LBS du projet (référence) ;
  x_rig(v)  : position du sommet par la transformation rigide de la chaîne de l'articulation (centre et axe réels) ;
  s(v)      : clamp(1 − d(v, centre)/(α L_os), 0, 1), L_os = longueur réelle de l'os articulé ;
  x'(v)     = (1 − s) x_LBS + s x_rig.

Protocole (fixé avant les calculs) :
  - calibration : hanche gauche 60° et 90° (poses réelles) ; choix de α sur ce seul ensemble ;
  - test : hanche gauche 75°, 105°, 120° ; hanche droite 75°, 120° ; genou gauche 60°, 90°, 105° ;
  - généralisation : α choisi sur le masculin, appliqué sans changement au féminin et à Maria.
  - référence : LBS et DQS sur les mêmes poses, mêmes métriques (étirement max, p99, retournements, volume).
  - PSD : écart entre la pose directe à 75° et l'interpolation linéaire entre 60° et 90° (sommet max).
Le signe de rotation de chaque articulation est mesuré sur les poses réelles de chaque morphologie (R_flex90, R_genou90).
"""
import importlib.util
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
DONNEES = os.environ.get("ANATOMIE_DONNEES", "/tmp/claude-0/-home-claude/9ce8e1e5-f7cf-5619-8a75-3c6d9a11ab1c/scratchpad")
SORTIE = os.path.join(RACINE, "docs", "rapports", "skinning", "corrections_articulaires")


def charger(nom):
    spec = importlib.util.spec_from_file_location(nom, os.path.join(HERE, nom + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


P = charger("poses_articulaires")
M = charger("methodes")
Ms = charger("mesures")

MORPHOS = {
    "masculin": ("skin/poses2.npz", "docs/rapports/skinning/anatomie/squelette_masc.json"),
    "feminin": ("morpho/femme.npz", "docs/rapports/skinning/anatomie/squelette_fem.json"),
    "maria": ("morpho/maria.npz", "docs/rapports/skinning/anatomie/squelette_maria.json"),
}
ALPHAS = [0.25, 0.5, 0.75, 1.0]
ARTICULATIONS = {  # nom : (os, pose de référence pour le signe)
    "hanche_G": ("LeftUpLeg", "L_flex90"),
    "hanche_D": ("RightUpLeg", "R_flex90"),
    "genou_G": ("LeftLeg", "L_genou90"),
}
TEST = {"hanche_G": [75, 105, 120], "hanche_D": [75, 120], "genou_G": [60, 90, 105]}
CALIB = {"hanche_G": [60, 90]}


def prefixe(noms):
    return "mixamorig:" if any(n.startswith("mixamorig:") for n in noms) else ""


def signe_depuis_pose_reelle(z, noms, js, os_nom, pose_ref):
    """Mesure le signe : +1 si la rotation réelle est autour de +axe_X, −1 sinon. Refuse si ambigu."""
    k = noms.index(prefixe(noms) + os_nom)
    pm, B = z[pose_ref + "__os"], z["bones_rest_monde"]
    R = (pm[k] @ np.linalg.inv(B[k]))[:3, :3]
    ang, ax = P.angle_et_axe(R)
    _, axe, _ = P.articulation(js, prefixe(noms) + os_nom)
    dot = float(ax @ (axe / np.linalg.norm(axe)))
    if ang < 1e-3 or abs(abs(dot) - 1) > 1e-3:
        raise ValueError(f"signe ambigu pour {os_nom} dans {pose_ref} (angle {ang}, dot {dot})")
    return int(np.sign(dot)), float(np.degrees(ang))


def longueur_os(js, nom):
    d = json.load(open(js, encoding="utf-8"))
    o = [x for x in d["os"] if x["nom"] == nom][0]
    if not o["longueur_fiable"]:
        raise ValueError(f"longueur non fiable pour {nom}")
    return o["longueur"]


def position_articulee(rest, Wi, Ww, B, noms, js, art, theta, alpha, sens, ref_lbs):
    """Positions du candidat C1 pour une articulation et un angle."""
    nom_full = prefixe(noms) + ART_OS[art]
    centre, axe, chaine = P.articulation(js, nom_full)
    T = P.transformation_articulation(centre, axe, theta, sens)
    x_rig = rest @ T[:3, :3].T + T[:3, 3]
    L = longueur_os(js, nom_full)
    d = np.linalg.norm(rest - centre, axis=1)
    s = np.clip(1.0 - d / (alpha * L), 0.0, 1.0)[:, None]
    return (1 - s) * ref_lbs + s * x_rig, T, chaine


ART_OS = {}


def mesurer_pose(pos_pose, rest, b, tot, A, Wi, Ww, B, pm):
    Mv = M.repere_rigide(Wi, Ww, B, pm)
    mes = Ms.mesurer(pos_pose, rest, b, tot, A, Mv=Mv)
    return {"etirement_max": float(mes["etirement_max"]), "etirement_p99": float(mes["etirement_p99"]),
            "retournements": int(mes["polygones_retournes"]),
            "volume_variation": float(mes["variation_volume_relative"])}


def main():
    os.makedirs(SORTIE, exist_ok=True)
    resultats = {"alphas": ALPHAS, "morphos": {}, "calibration": {}, "choix_alpha": None}
    # 1) signes et longueurs par morphologie (mesurés, pas supposés)
    contexte = {}
    for morph, (npz, js) in MORPHOS.items():
        z = np.load(os.path.join(DONNEES, npz))
        noms = [str(n) for n in z["noms_os"]]
        sens = {}
        for art, (os_nom, pose_ref) in ARTICULATIONS.items():
            if os_nom and pose_ref + "__os" in z.files:
                sens[art] = signe_depuis_pose_reelle(z, noms, os.path.join(RACINE, js), os_nom, pose_ref)
        contexte[morph] = {"z": z, "noms": noms, "js": os.path.join(RACINE, js), "sens": sens}
        resultats["morphos"][morph] = {"signes_mesures": {a: {"sens": v[0], "angle_ref_deg": round(v[1], 3)} for a, v in sens.items()}}
        print(morph, "signes mesurés:", {a: v[0] for a, v in sens.items()}, flush=True)

    # 2) évaluation
    for morph, c in contexte.items():
        z, noms, js = c["z"], c["noms"], c["js"]
        rest, Wi, Ww, B = z["rest_monde"], z["W_idx"], z["W_w"], z["bones_rest_monde"]
        b, tot = z["b_boucle"], z["b_tot"]
        A = Ms.aretes(b, tot, len(rest))
        lignes = []
        for art, (os_nom, _) in ARTICULATIONS.items():
            if art not in c["sens"]:
                continue
            sens = c["sens"][art][0]
            ART_OS[art] = os_nom
            for th_deg in sorted(set(CALIB.get(art, []) + TEST.get(art, []))):
                theta = np.radians(th_deg)
                nom_full = prefixe(noms) + os_nom
                centre, axe, chaine = P.articulation(js, nom_full)
                T = P.transformation_articulation(centre, axe, theta, sens)
                pm = P.matrices_pose(B, noms, chaine, T)
                ref = M.calculer_toutes(rest, Wi, Ww, B, pm)[0]
                lbs, dqs = ref["LBS"], ref["DQS"]
                ligne = {"articulation": art, "angle_deg": th_deg,
                         "phase": "calibration" if th_deg in CALIB.get(art, []) else "test",
                         "LBS": mesurer_pose(lbs, rest, b, tot, A, Wi, Ww, B, pm),
                         "DQS": mesurer_pose(dqs, rest, b, tot, A, Wi, Ww, B, pm)}
                for alpha in ALPHAS:
                    pos, _, _ = position_articulee(rest, Wi, Ww, B, noms, js, art, theta, alpha, sens, lbs)
                    ligne[f"C1_a{alpha}"] = mesurer_pose(pos, rest, b, tot, A, Wi, Ww, B, pm)
                lignes.append(ligne)
                print(morph, art, th_deg, flush=True)
        resultats["morphos"][morph]["lignes"] = lignes

    # 3) choix de α : calibration masculin uniquement, critère multiple, pas de seuil assoupli
    lignes_cal = [l for l in resultats["morphos"]["masculin"]["lignes"] if l["phase"] == "calibration"]
    choix = {}
    for alpha in ALPHAS:
        cl = f"C1_a{alpha}"
        ok = all(l[cl]["etirement_p99"] <= l["LBS"]["etirement_p99"] + 1e-9 and
                 l[cl]["retournements"] <= l["LBS"]["retournements"] for l in lignes_cal)
        choix[str(alpha)] = {"accepte_calibration": bool(ok),
                             "max_pire": float(max(l[cl]["etirement_max"] for l in lignes_cal)),
                             "p99_pire": float(max(l[cl]["etirement_p99"] for l in lignes_cal))}
    acceptes = [a for a in ALPHAS if choix[str(a)]["accepte_calibration"]]
    resultats["choix_alpha"] = (min(acceptes, key=lambda a: choix[str(a)]["max_pire"]) if acceptes else None)
    resultats["calibration"] = choix
    print("choix α (calibration) :", resultats["choix_alpha"], choix, flush=True)

    # 4) PSD : la CORRECTION δ = méthode − LBS doit s'interpoler proprement. Erreur = |δ(75) − (δ(60)+δ(90))/2|.
    #    Mesurer la position brute serait dominé par la courbure des trajectoires rigides (identique pour toutes les
    #    méthodes) ; la correction isole l'effet de la méthode.
    c = contexte["masculin"]
    z, noms, js = c["z"], c["noms"], c["js"]
    rest, Wi, Ww, B = z["rest_monde"], z["W_idx"], z["W_w"], z["bones_rest_monde"]
    sens = c["sens"]["hanche_G"][0]
    ART_OS["hanche_G"] = "LeftUpLeg"
    psd = {}
    deltas = {}
    for th in [60, 75, 90]:
        theta = np.radians(th)
        centre, axe, chaine = P.articulation(js, prefixe(noms) + "LeftUpLeg")
        T = P.transformation_articulation(centre, axe, theta, sens)
        pm = P.matrices_pose(B, noms, chaine, T)
        ref = M.calculer_toutes(rest, Wi, Ww, B, pm)[0]
        lbs = ref["LBS"]
        deltas.setdefault("DQS", {})[th] = ref["DQS"] - lbs
        for alpha in ALPHAS:
            pos, _, _ = position_articulee(rest, Wi, Ww, B, noms, js, "hanche_G", theta, alpha, sens, lbs)
            deltas.setdefault(f"C1_a{alpha}", {})[th] = pos - lbs
    for nom, dd in deltas.items():
        err = np.linalg.norm(dd[75] - 0.5 * (dd[60] + dd[90]), axis=1)
        amp = np.linalg.norm(dd[90], axis=1).max()
        psd[nom] = {"erreur_interpolation_max_m": float(err.max()), "erreur_interpolation_p99_m": float(np.percentile(err, 99)),
                    "amplitude_correction_90_max_m": float(amp)}
    resultats["psd_correction_75_entre_60_90"] = psd
    print("PSD (correction) :", {k: round(v["erreur_interpolation_max_m"], 5) for k, v in psd.items()}, flush=True)

    with open(os.path.join(SORTIE, "resume.json"), "w", encoding="utf-8") as f:
        json.dump(resultats, f, indent=1, ensure_ascii=False, default=float)
    print("ECRIT", os.path.join(SORTIE, "resume.json"))


if __name__ == "__main__":
    main()

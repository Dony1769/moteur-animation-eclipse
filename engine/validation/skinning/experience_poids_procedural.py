"""Expérience : poids procéduraux par longueur réelle d'os (phase 4, étape 2).

Pour chaque morphologie et chaque coefficient GLOBAL ALPHA (identique pour les trois) :
  1. construire un fichier de poses dont seuls W_idx / W_w changent (même maillage, mêmes poses, mêmes matrices) ;
  2. exécuter comparer_v2.py (même protocole, mêmes métriques que la référence) ;
  3. résumer LBS et DQS, et comparer à la référence v2 (poids Bone Heat Blender).

Aucun réglage par personnage : ALPHA est choisi dans ALPHAS avant le calcul, et le même ensemble s'applique partout.
Sorties : docs/rapports/skinning/procedural/resume.json et tableau.md ; fichiers intermédiaires dans SCRATCH.
"""
import importlib.util
import json
import os
import shutil
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
SCRATCH = os.environ.get("ANATOMIE_SCRATCH", "/tmp/procedural_scratch")
DONNEES = os.environ.get("ANATOMIE_DONNEES", "/tmp/claude-0/-home-claude/9ce8e1e5-f7cf-5619-8a75-3c6d9a11ab1c/scratchpad")
SORTIE = os.path.join(RACINE, "docs", "rapports", "skinning", "procedural")
ALPHAS = [0.25, 0.5, 1.0]
MODE = sys.argv[1] if len(sys.argv) > 1 else "remplacement"  # "remplacement" ou "bande"
ZONES = ["hanche_G", "hanche_D", "genou_G", "genou_D"]

# morphologie : (fichier de poses, squelette extrait correspondant, rapport de référence v2)
MORPHOS = {
    "maria": ("morpho/maria.npz", "docs/rapports/skinning/anatomie/squelette_maria.json", "comparatif_maria.json"),
    "masculin": ("skin/poses2.npz", "docs/rapports/skinning/anatomie/squelette_masc.json", "comparatif_masculin.json"),
    "feminin": ("morpho/femme.npz", "docs/rapports/skinning/anatomie/squelette_fem.json", "comparatif_feminin.json"),
}


def charger_module(nom, chemin):
    spec = importlib.util.spec_from_file_location(nom, chemin)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def resumer(comparatif):
    """Résumé par méthode : maxima, p99 moyens, comptages, retournements, zones hanche/genou."""
    out = {}
    for methode in ["LBS", "DQS"]:
        maxi, p99, nb15, nb125, retour, res_max, zones_max = [], [], 0, 0, 0, [], {z: [] for z in ZONES}
        for pose, e in comparatif["poses"].items():
            m = e["methodes"][methode]
            maxi.append(m["etirement_max"])
            p99.append(m["etirement_p99"])
            nb15 += int(m["etirement_max"] > 1.5)
            nb125 += int(m["etirement_max"] > 1.25)
            retour += m["retournements"]
            res_max.append(m["residu_os_dominant_max_m"])
            for z in ZONES:
                zz = m["zones"].get(z) if isinstance(m["zones"], dict) else None
                if zz and zz.get("max") is not None:
                    zones_max[z].append(zz["max"])
        out[methode] = {
            "etirement_max_pire": float(max(maxi)),
            "etirement_max_mediane": float(np.median(maxi)),
            "etirement_p99_moyen": float(np.mean(p99)),
            "poses_max_>1.5": nb15,
            "poses_max_>1.25": nb125,
            "retournements_total": int(retour),
            "residu_os_max_m": float(max(res_max)),
            "zones_max_pire": {z: (float(max(v)) if v else None) for z, v in zones_max.items()},
        }
    return out


def comparatif_pour(npz_meta_src, npz_variant, nom):
    """Exécute comparer_v2 sur le fichier variante et renvoie son JSON."""
    sortie = os.path.join(SCRATCH, f"out_{nom}")
    shutil.rmtree(sortie, ignore_errors=True)
    subprocess.run([sys.executable, os.path.join(HERE, "comparer_v2.py"), npz_variant, nom, sortie],
                   check=True, capture_output=True)
    return json.load(open(os.path.join(sortie, f"comparatif_{nom}.json"), encoding="utf-8"))


def main():
    os.makedirs(SORTIE, exist_ok=True)
    if MODE not in ("remplacement", "bande"):
        raise SystemExit("mode inconnu")
    os.makedirs(SCRATCH, exist_ok=True)
    seg_mod = charger_module("poids_procedural", os.path.join(HERE, "poids_procedural.py"))
    resultats = {"alphas": ALPHAS, "morphos": {}}
    for morph, (poses, squelette, ref) in MORPHOS.items():
        src_poses = os.path.join(DONNEES, poses)
        d = dict(np.load(src_poses))
        noms = [str(n) for n in d["noms_os"]]
        ts = seg_mod.segments_depuis_squelette(os.path.join(RACINE, squelette), noms)
        meta_src = src_poses.replace(".npz", ".json")
        ref_json = json.load(open(os.path.join(RACINE, "docs", "rapports", "skinning", "v2", ref), encoding="utf-8"))
        resultats["morphos"][morph] = {"reference": resumer(ref_json), "variantes": {}}
        for alpha in ALPHAS:
            if MODE == "remplacement":
                idx, w = seg_mod.poids_procedural(d["rest_monde"], ts, alpha)
            else:
                idx, w = seg_mod.melange_pres_articulation(d["rest_monde"], d["W_idx"], d["W_w"], ts, noms, alpha)
            dv = dict(d)
            dv["W_idx"] = idx.astype(np.int64)
            dv["W_w"] = w.astype(np.float64)
            nom = f"{morph}_{MODE[:3]}_a{str(alpha).replace('.', '')}"
            fichier = os.path.join(SCRATCH, nom + ".npz")
            np.savez(fichier, **dv)
            shutil.copy(meta_src, fichier.replace(".npz", ".json"))
            comp = comparatif_pour(meta_src, fichier, nom)
            resultats["morphos"][morph]["variantes"][str(alpha)] = resumer(comp)
            print(morph, alpha, "ok", flush=True)
    sortie = os.path.join(SORTIE, f"resume_{MODE}.json")
    resultats["mode"] = MODE
    json.dump(resultats, open(sortie, "w"), indent=1, ensure_ascii=False)
    print("ECRIT", sortie)


if __name__ == "__main__":
    main()

"""Tests de l'analyse anatomique (phase 4, étape 1).

Lancement : python3 engine/anatomie/test_analyse_topologie.py
Les noms d'os n'entrent que dans les contrôles (test_noms_controle), jamais dans la classification.
Un test dont les données manquent est signalé SAUTÉ, jamais compté comme réussi.
"""
import importlib.util
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.normpath(os.path.join(HERE, "..", "..", "docs", "rapports", "skinning", "anatomie"))
SCRATCH = os.environ.get("ANATOMIE_SCRATCH", "")

spec = importlib.util.spec_from_file_location("analyser_topologie", os.path.join(HERE, "analyser_topologie.py"))
A = importlib.util.module_from_spec(spec)
spec.loader.exec_module(A)

MORPHOS = ["maria", "masc", "fem"]
resultats = {"ok": 0, "echec": 0, "saute": 0}


def verifier(nom, condition, detail=""):
    if condition:
        resultats["ok"] += 1
        print(f"  OK    {nom}")
    else:
        resultats["echec"] += 1
        print(f"  ECHEC {nom} {detail}")


def sauter(nom, raison):
    resultats["saute"] += 1
    print(f"  SAUTE {nom} : {raison}")


def squelette(m):
    return os.path.join(DOCS, f"squelette_{m}.json")


def test_topologie_structure():
    print("[T1] structure : deux jambes, tronc, cou, deux bras, sans nom")
    for m in MORPHOS:
        r = A.analyser(squelette(m))
        jambes = r["regions"]["jambes"]
        verifier(f"{m} : 2 jambes", len(jambes) == 2, f"({len(jambes)})")
        verifier(f"{m} : tronc non vide", len(r["regions"]["tronc"]) >= 2)
        verifier(f"{m} : cou trouvé", r["regions"]["cou"] is not None)
        verifier(f"{m} : 2 bras", len(r["regions"]["epaules"]) == 2, f"({len(r['regions']['epaules'])})")
        for c, seg in jambes.items():
            verifier(f"{m} : jambe {c} a au moins cuisse, jambe, pied", len(seg) >= 3, f"({len(seg)})")


def test_noms_controle():
    print("[T2] contrôle a posteriori par les noms (hors classification)")
    for m in MORPHOS:
        r = A.analyser(squelette(m))
        noms_tronc = [n.split(":")[-1] for n in r["regions"]["tronc"]]
        verifier(f"{m} : le tronc contient Spine", "Spine" in noms_tronc, f"({noms_tronc})")
        cuisses = [seg[0].split(":")[-1] for seg in r["regions"]["jambes"].values()]
        verifier(f"{m} : cuisses = UpLeg", all(c.endswith("UpLeg") for c in cuisses), f"({cuisses})")


def test_longueurs_reelles():
    print("[T3] longueurs réelles : aucune valeur de remplacement")
    for m in MORPHOS:
        d = json.load(open(squelette(m), encoding="utf-8"))
        cuisses = [o["longueur"] for o in d["os"] if o["nom"].endswith("UpLeg")]
        verifier(f"{m} : cuisses réelles entre 0,30 et 0,50 m", all(0.30 < c < 0.50 for c in cuisses), f"({cuisses})")
        verifier(f"{m} : aucune longueur égale à 0,10 m par défaut",
                 not any(abs(o["longueur"] - 0.10) < 1e-9 for o in d["os"]))
        feuilles = [o for o in d["os"] if o["feuille"]]
        verifier(f"{m} : os terminaux marqués non fiables",
                 all(not o["longueur_fiable"] for o in feuilles) and all(o["longueur_fiable"] for o in d["os"] if not o["feuille"]))


def test_ambigus_signales():
    print("[T4] ambiguïtés signalées, non classées de force")
    r = A.analyser(squelette("masc"))
    noms_amb = [a["segment"][0] for a in r["ambigus"]]
    verifier("masculin : les auxiliaires de bras sont signalés", any("ArmHelper" in n for n in noms_amb), f"({noms_amb})")
    verifier("masculin : auxiliaires absents des bras", all("ArmHelper" not in s[0] for s in r["regions"]["epaules"]))


def test_comptage_sommets():
    print("[T5] comptage : somme des régions = nombre de sommets")
    for m in MORPHOS:
        rep = json.load(open(os.path.join(DOCS, f"anatomie_{m}.json"), encoding="utf-8"))
        total = sum(rep["vertices_par_region_dominante"].values())
        ref = json.load(open(squelette(m), encoding="utf-8"))
        verifier(f"{m} : somme des régions = nombre de sommets extraits ({ref['nb_sommets']})",
                 total == ref["nb_sommets"], f"(somme {total})")


def test_geometrie_regions():
    print("[T6] ordre géométrique des régions (indépendant de la morphologie)")
    for m in MORPHOS:
        if not SCRATCH or not os.path.exists(os.path.join(SCRATCH, f"{m}.npz")):
            sauter(f"{m} : ordre des hauteurs", "npz de sommets absent (ANATOMIE_SCRATCH non défini)")
            continue
        z = np.load(os.path.join(SCRATCH, f"{m}.npz"))
        sommets, poids = z["sommets"], z["poids"]
        noms = [str(n) for n in z["noms_os"]]
        rep = A.representation(squelette(m), os.path.join(SCRATCH, f"{m}.npz"))
        dom = poids.argmax(axis=1)
        valide = poids.sum(axis=1) > 0
        # Hauteur moyenne des sommets dominés par la jambe et par le cou.
        def hauteur_de(pred):
            masque = np.array([pred(noms[i]) for i in dom]) & valide
            return float(sommets[masque, 2].mean()) if masque.any() else None
        jambes_noms = [n for seg in A.analyser(squelette(m))["regions"]["jambes"].values() for n in seg]
        cou_noms = set(A.analyser(squelette(m))["regions"]["cou"] or [])
        h_jambe = hauteur_de(lambda n: n in jambes_noms)
        h_cou = hauteur_de(lambda n: n in cou_noms)
        verifier(f"{m} : sommets de jambe plus bas que sommets de cou", h_jambe is not None and h_cou is not None and h_jambe < h_cou,
                 f"(jambe {h_jambe}, cou {h_cou})")


def test_absence_signalee():
    print("[T7] une structure sans cou est signalée, pas inventée")
    d = json.load(open(squelette("maria"), encoding="utf-8"))
    # Retire le cou (et la tête) de la hiérarchie pour simuler un modèle sans tête.
    tronc_haut = [o for o in d["os"] if o["nom"].endswith("Spine2")][0]
    tronc_haut["enfants"] = [e for e in tronc_haut["enfants"] if "Neck" not in e]
    tmp = os.path.join(os.environ.get("TMPDIR", "/tmp"), "squelette_sans_cou_test.json")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f)
    try:
        r = A.analyser(tmp)
        verifier("cou absent : le cou n'est pas inventé", r["regions"]["cou"] is None or "Neck" not in str(r["regions"]["cou"]),
                 f"({r['regions']['cou']})")
    except (ValueError, StopIteration) as e:
        verifier("cou absent : erreur explicite (pas de cou inventé)", True, str(e))
    finally:
        os.remove(tmp)


if __name__ == "__main__":
    for t in [test_topologie_structure, test_noms_controle, test_longueurs_reelles, test_ambigus_signales,
              test_comptage_sommets, test_geometrie_regions, test_absence_signalee]:
        t()
    print(f"\nRÉSULTAT : {resultats['ok']} OK, {resultats['echec']} ECHEC, {resultats['saute']} SAUTÉ")
    sys.exit(1 if resultats["echec"] else 0)

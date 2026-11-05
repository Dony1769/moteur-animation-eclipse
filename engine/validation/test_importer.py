"""Phase 2 : tests de l'importeur de diagnostic sur des variantes contrôlées.

Vérifie que le diagnostic reconnaît le type de personnage, signale les anomalies attendues et propose
les opérations nécessaires, sur : Maria d'origine, Maria sans armature, Maria à poids partiels,
Maria sans poids, et le corps HBM sans armature.

Usage : python3 engine/validation/test_importer.py DOSSIER_SCRATCH
  DOSSIER_SCRATCH doit contenir maria.fbx (copie) et corps_hbm.blend (copie).
Blender : BLENDER=/chemin/blender (défaut : /home/claude/moteur3d/tools/blender-4.5.15-linux-x64/blender)
"""
import glob
import json
import os
import subprocess
import sys

RACINE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
BLENDER = os.environ.get("BLENDER", "/home/claude/moteur3d/tools/blender-4.5.15-linux-x64/blender")


def blender(script, *args):
    cmd = [BLENDER, "-b", "--factory-startup", "--disable-autoexec", "-P", script, "--", *args]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=900)


def main():
    scratch = os.path.abspath(sys.argv[1])
    var = os.path.join(scratch, "variantes")
    diag = os.path.join(scratch, "diag_test")
    os.makedirs(diag, exist_ok=True)
    r = blender(os.path.join(RACINE, "engine/importer/variantes.py"), os.path.join(scratch, "maria.fbx"), var)
    assert "VARIANTES_OK" in r.stdout, r.stderr[-800:]
    entrees = {
        "maria_origine": os.path.join(scratch, "maria.fbx"),
        "A_sans_armature": os.path.join(var, "A_sans_armature.blend"),
        "B_poids_partiels": os.path.join(var, "B_poids_partiels.blend"),
        "C_sans_poids": os.path.join(var, "C_sans_poids.blend"),
        "hbm_sans_armature": os.path.join(scratch, "corps_hbm.blend"),
    }
    rapports = {}
    # Le bundle HBM contient toutes les variantes : on choisit un corps explicitement (entrée 142).
    options = {"hbm_sans_armature": ["--corps", "GEO-body_female_realistic"]}
    for nom, f in entrees.items():
        sortie = os.path.join(diag, nom + ".json")
        r = blender(os.path.join(RACINE, "engine/importer/diagnostic.py"), f, sortie, *options.get(nom, []))
        assert "DIAGNOSTIC_OK" in r.stdout, (nom, r.stderr[-800:])
        rapports[nom] = json.load(open(sortie))

    resultats = []

    def verifier(nom, cond, detail=""):
        resultats.append((nom, bool(cond), detail))

    m = rapports["maria_origine"]
    verifier("maria_type", m["type"] == "armature_et_poids", m["type"])
    verifier("maria_pas_d_anomalie", m["anomalies"] == [], str(m["anomalies"]))
    verifier("maria_pas_d_operation", m["operations_recommandees"] == [], str(m["operations_recommandees"]))
    verifier("maria_hauteur_plausible", 1.4 <= m["hauteur_m"] <= 2.0, str(m["hauteur_m"]))
    verifier("maria_parties_du_corps", {"tete", "tronc", "bras_gauche"} <= set(m["parties_du_corps"]["parties"]),
             str(m["parties_du_corps"]["parties"]))

    a = rapports["A_sans_armature"]
    verifier("A_type", a["type"] == "sans_armature", a["type"])
    verifier("A_echelle_detectee", any("échelle suspecte" in x for x in a["anomalies"]), str(a["anomalies"]))
    verifier("A_operation_echelle", any(o.startswith("normaliser_echelle_x0.01") for o in a["operations_recommandees"]),
             str(a["operations_recommandees"]))
    verifier("A_operations_auto_rig", {"generer_armature", "calculer_poids"} <= set(a["operations_recommandees"]),
             str(a["operations_recommandees"]))

    b = rapports["B_poids_partiels"]
    verifier("B_type", b["type"] == "armature_et_poids", b["type"])
    verifier("B_anomalie_poids_partiels", any("sommets sans poids" in x for x in b["anomalies"]), str(b["anomalies"]))
    verifier("B_operation_completer", "completer_poids_sommets_orphelins" in b["operations_recommandees"],
             str(b["operations_recommandees"]))

    c = rapports["C_sans_poids"]
    verifier("C_type", c["type"] == "armature_sans_poids", c["type"])
    verifier("C_anomalie_armature_sans_poids", any("aucun groupe de poids" in x for x in c["anomalies"]),
             str(c["anomalies"]))
    verifier("C_operation_calculer", "calculer_poids" in c["operations_recommandees"], str(c["operations_recommandees"]))

    h = rapports["hbm_sans_armature"]
    verifier("hbm_type", h["type"] == "sans_armature", h["type"])
    verifier("hbm_dimensions_humaines", 1.4 <= h["dimensions_m"]["z"] <= 2.0 and h["dimensions_m"]["x"] < 1.2,
             str(h["dimensions_m"]))
    verifier("hbm_pas_de_parties_inventees", h["parties_du_corps"]["parties"] == [],
             str(h["parties_du_corps"]))

    # boucle complète : le diagnostic propose le facteur et l'axe, la normalisation les applique,
    # et le résultat doit retrouver les dimensions de Maria d'origine (référence mesurée)
    norm_dir = os.path.join(scratch, "norm_test")
    os.makedirs(norm_dir, exist_ok=True)
    sortie_norm = os.path.join(norm_dir, "A_normalise.blend")
    import hashlib
    empreinte = lambda f: hashlib.sha256(open(f, "rb").read()).hexdigest()
    avant = empreinte(entrees["A_sans_armature"])
    r = blender(os.path.join(RACINE, "engine/importer/normaliser.py"), entrees["A_sans_armature"], sortie_norm,
                str(a["facteur_echelle_suggere"]), a["axe_vertical_suggere"])
    assert "NORMALISE_OK" in r.stdout, r.stderr[-800:]
    verifier("source_intacte_apres_normalisation", empreinte(entrees["A_sans_armature"]) == avant,
             "la source n'est jamais modifiée")
    sortie_json = os.path.join(norm_dir, "A_normalise.json")
    r = blender(os.path.join(RACINE, "engine/importer/diagnostic.py"), sortie_norm, sortie_json)
    assert "DIAGNOSTIC_OK" in r.stdout, r.stderr[-800:]
    n = json.load(open(sortie_json))
    ref = m["dimensions_m"]
    ecart = max(abs(n["dimensions_m"][k] - ref[k]) for k in ("x", "y", "z"))
    verifier("A_normalisee_egale_original", ecart < 1e-3,
             f"ecart max {ecart:.6f} m ; normalisee {n['dimensions_m']} ; original {ref}")
    verifier("A_normalisee_sans_echelle_suspecte", not any("échelle suspecte" in x for x in n["anomalies"]),
             str(n["anomalies"]))

    echecs = [n for n, ok, _ in resultats if not ok]
    for n, ok, d in resultats:
        print(("OK   " if ok else "ECHEC") + " " + n + " : " + d)
    print("RESULTAT", "OK" if not echecs else "ECHEC " + ",".join(echecs))
    return 0 if not echecs else 1


if __name__ == "__main__":
    sys.exit(main())

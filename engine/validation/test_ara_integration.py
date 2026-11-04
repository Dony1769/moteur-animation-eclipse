"""Intégration Ara : le FBX produit par engine/generation/ara_adapter.py passe-t-il notre importeur ?

Traite le FBX Ara comme un personnage EXTERNE : diagnostic.analyser (import, type, os, poids, taille, anomalies)
puis contrôles de compatibilité avec nos conventions. Ne modifie pas le FBX.
Usage : blender -b --factory-startup --disable-autoexec -P engine/validation/test_ara_integration.py -- FBX SORTIE.json SCRATCH
"""
import sys, json, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "importer"))
import diagnostic as d  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:]
fbx, sortie = argv[0], argv[1]
rap = d.analyser(fbx)
res = {"fichier": fbx, "tests": {}, "rapport_diagnostic_resume": {}}
T = res["tests"]
def ok(n, c, det="", statut=None):
    T[n] = {"ok": bool(c), "detail": det, "statut": statut or ("ok" if c else "echec")}

arms = rap["armatures"]; meshes = rap["meshes"]
ok("type_reconnu", rap["type"] == "armature_et_poids", f"type {rap['type']}")
ok("armature_mixamo", len(arms) == 1 and arms[0]["convention"] == "mixamo",
   f"{len(arms)} armature(s), {arms[0]['os'] if arms else 0} os, convention {arms[0]['convention'] if arms else None}")
peau = max(meshes, key=lambda m: m["sommets"]) if meshes else None
ok("poids_normalises", peau and peau["poids"]["sommets_poids_non_normalises"] == 0,
   f"sommets non normalisés {peau['poids']['sommets_poids_non_normalises'] if peau else '-'}")
ok("influences_max_4", peau and peau["poids"]["max_influences_par_sommet"] <= 4,
   f"influences max {peau['poids']['max_influences_par_sommet'] if peau else '-'}")
ok("sans_sommet_orphelin", peau and peau["poids"]["sommets_sans_poids"] == 0,
   f"sommets sans poids {peau['poids']['sommets_sans_poids'] if peau else '-'}")
ok("materiaux", peau and len(peau["materiaux"]) > 0, f"matériaux {peau['materiaux'] if peau else []}")
ok("taille_humaine", rap["hauteur_m"] is not None and 1.4 <= rap["hauteur_m"] <= 2.0,
   f"hauteur {rap['hauteur_m']} m (preset 169 cm)")
ok("anomalies", len(rap["anomalies"]) == 0, f"anomalies {rap['anomalies']}", statut="ok" if not rap["anomalies"] else "avertissement")
res["rapport_diagnostic_resume"] = {"type": rap["type"], "os": arms[0]["os"] if arms else 0, "sommets": peau["sommets"] if peau else 0,
                                    "hauteur_m": rap["hauteur_m"], "anomalies": rap["anomalies"]}
json.dump(res, open(sortie, "w"), indent=2, ensure_ascii=False)
print("RESULTAT", "OK" if all(v["ok"] for v in T.values()) else "ECHEC " + ",".join(k for k, v in T.items() if not v["ok"]))
for k, v in T.items(): print("TEST", k, v)

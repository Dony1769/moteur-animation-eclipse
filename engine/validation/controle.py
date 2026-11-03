"""Contrôle qualité d'un personnage à partir de son rapport de diagnostic (engine/importer/diagnostic.py).

Règle de la mission : un personnage n'est déclaré READY FOR ANIMATION que si les tests fondamentaux passent.
Ce module lit seulement un rapport JSON ; il ne modifie aucun fichier.
"""

MAX_INFLUENCES = 4          # limite courante pour le temps réel ; configurable par profil CPU plus tard


def valider(rapport):
    """Renvoie un dictionnaire : statut ('READY' ou 'NON PRÊT'), score (0 à 100), tests et erreurs."""
    tests = []

    def test(nom, ok, detail):
        tests.append({"test": nom, "ok": bool(ok), "detail": detail})

    meshes = rapport.get("meshes", [])
    armatures = rapport.get("armatures", [])

    test("import : au moins un maillage", len(meshes) > 0, f"{len(meshes)} maillage(s)")
    test("armature présente", len(armatures) > 0, f"{len(armatures)} armature(s)")

    if armatures:
        a = armatures[0]
        test("hiérarchie : une seule racine", len(a.get("racine", [])) == 1,
             f"racines : {a.get('racine')}")
        test("nombre d'os raisonnable (10 à 200)", 10 <= a.get("os", 0) <= 200, f"{a.get('os')} os")

    for m in meshes:
        nom = m["nom"]
        test(f"{nom} : sommets présents", m["sommets"] > 0, f"{m['sommets']} sommets")
        test(f"{nom} : UV présentes", len(m.get("uv_calques", [])) > 0, str(m.get("uv_calques")))
        p = m.get("poids")
        if p is None:
            test(f"{nom} : skinning présent", False, "aucun groupe de sommets")
            continue
        test(f"{nom} : aucun sommet sans poids", p["sommets_sans_poids"] == 0,
             f"{p['sommets_sans_poids']} sommet(s) sans poids")
        test(f"{nom} : poids normalisés", p["sommets_poids_non_normalises"] == 0,
             f"{p['sommets_poids_non_normalises']} sommet(s) hors norme")
        test(f"{nom} : au plus {MAX_INFLUENCES} influences par sommet",
             p["max_influences_par_sommet"] <= MAX_INFLUENCES,
             f"maximum observé : {p['max_influences_par_sommet']}")

    total = len(tests)
    reussis = sum(1 for t in tests if t["ok"])
    score = round(100 * reussis / total) if total else 0
    echecs = [t for t in tests if not t["ok"]]
    statut = "READY" if not echecs and total else "NON PRÊT"
    return {
        "statut": "READY FOR ANIMATION" if statut == "READY" else "NON PRÊT",
        "score": score,
        "tests": tests,
        "echecs": [t["test"] + " : " + t["detail"] for t in echecs],
        "anomalies_du_diagnostic": rapport.get("anomalies", []),
    }

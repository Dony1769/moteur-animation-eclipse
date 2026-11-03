"""Non-régression de l'étape 3 : le corps HBM skinné doit rester READY et ses tests de déformation passer.

Lit les rapports committés (générés par engine/skinning/auto_skin.py puis engine/importer/diagnostic.py).
"""
import json, pathlib, sys

RACINE = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE / "engine" / "validation"))
import controle  # noqa: E402

RAPPORTS = RACINE / "docs" / "rapports"


def charger(nom):
    return json.loads((RAPPORTS / nom).read_text(encoding="utf-8"))


def test_corps_skinne_est_ready():
    r = controle.valider(charger("hbm_corps_skinne.json"))
    assert r["statut"] == "READY FOR ANIMATION", r["echecs"]
    assert r["score"] == 100


def test_tests_de_deformation_passent():
    s = charger("hbm_skinning_tests.json")
    echecs = [t for t in s["tests_deformation"] if not t["ok"]]
    assert not echecs, echecs


def test_pose_de_repos_inchangee():
    s = charger("hbm_skinning_tests.json")
    repos = [t for t in s["tests_deformation"] if t["test"].startswith("pose de repos")]
    assert repos and repos[0]["ok"], repos


def test_limite_influences_respectee():
    s = charger("hbm_skinning_tests.json")
    assert s["poids"]["max_influences_par_sommet"] <= controle.MAX_INFLUENCES
    assert s["poids"]["sommets_sans_poids"] == 0
    assert s["poids"]["sommets_poids_non_normalises"] == 0

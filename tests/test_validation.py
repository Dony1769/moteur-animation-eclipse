"""Tests du contrôle qualité sur les rapports réels de diagnostic.

Lancer : python3 tests/test_validation.py   (ou python3 -m pytest tests/test_validation.py -q)
"""
import json
import os
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RACINE, "engine", "validation"))
from controle import valider  # noqa: E402

RAPPORTS = os.path.join(RACINE, "docs", "rapports")


def charger(nom):
    with open(os.path.join(RAPPORTS, nom)) as f:
        return json.load(f)


def test_maria_est_prete():
    r = valider(charger("maria.json"))
    assert r["statut"] == "READY FOR ANIMATION", r["echecs"]
    assert r["score"] == 100


def test_bot_x_est_pret():
    r = valider(charger("x_bot.json"))
    assert r["statut"] == "READY FOR ANIMATION", r["echecs"]


def test_animation_seule_non_prete():
    r = valider(charger("standing_briefcase_idle.json"))
    assert r["statut"] == "NON PRÊT"
    assert any("maillage" in e for e in r["echecs"])


def test_bundle_hbm_non_pret():
    r = valider(charger("hbm_bundle.json"))
    assert r["statut"] == "NON PRÊT"
    assert any("armature" in e for e in r["echecs"])


if __name__ == "__main__":
    for nom in ("maria.json", "x_bot.json", "standing_briefcase_idle.json", "hbm_bundle.json"):
        r = valider(charger(nom))
        print(f"{nom:34s} {r['statut']:22s} score {r['score']:3d}  échecs {len(r['echecs'])}")
    print("OK")

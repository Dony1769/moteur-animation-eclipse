"""Non-régression du contrôle de gonflement (engine/skinning/controle_gonflement.py).

Vérifie : le témoin à 0 degré (volume conservé, arêtes inchangées) sur les rapports committés,
et la présence des indicateurs. Les valeurs de pliage et d'étirement sont mesurées et documentées
dans docs/skinning.md ; elles ne sont pas figées ici (ce sont des défauts connus, pas des objectifs).
"""
import json, pathlib, pytest

RAPPORTS = pathlib.Path(__file__).resolve().parent.parent / "docs" / "rapports"
FICHIERS = ["gonflement_avec_cles.json", "gonflement_sans_cles.json", "gonflement_lissage1_200it.json"]


@pytest.mark.parametrize("fichier", FICHIERS)
def test_temoin_zero_degre(fichier):
    r = json.load(open(RAPPORTS / fichier))
    for mode, os_par_nom in r["modes"].items():
        for os_nom, par_angle in os_par_nom.items():
            v = par_angle["0"]
            assert v["ratio_volume"] == pytest.approx(1.0, abs=1e-6), (mode, os_nom)
            # plancher de précision mesuré : 1,3 um d'écart au repos (résidu 1e-6 de pose, flottants)
            # sur des arêtes d'environ 1 mm => ratio à 1e-3 près. Tolérance 1,5e-3, justifiée par cette mesure.
            assert abs(v["etirement_max"] - 1.0) <= 1.5e-3 and abs(v["etirement_min"] - 1.0) <= 1.5e-3, (mode, os_nom)


@pytest.mark.parametrize("fichier", FICHIERS)
def test_indicateurs_presents(fichier):
    r = json.load(open(RAPPORTS / fichier))
    for mode in ("LBS", "DQS"):
        for os_nom in ("LeftArm", "LeftForeArm", "LeftLeg"):
            for angle in ("60", "90", "105", "120"):
                v = r["modes"][mode][os_nom][angle]
                assert set(v) == {"ratio_volume", "etirement_max", "etirement_min", "ecart_p99"}

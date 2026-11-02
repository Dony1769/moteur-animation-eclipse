"""Tests M3 : validation des manifests de personnage."""
import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "engine", "personnages"))
import valider  # noqa: E402


class TestManifestKael(unittest.TestCase):
    def test_kael_passe(self):
        with open(os.path.join(valider.RACINE, "personnages", "kael_vareth.json"), encoding="utf-8") as f:
            self.assertEqual(valider.valider(json.load(f)), [])

    def test_fichier_manquant_est_une_erreur(self):
        with open(os.path.join(valider.RACINE, "personnages", "kael_vareth.json"), encoding="utf-8") as f:
            m = json.load(f)
        m["bouche"]["A"] = "universes/inexistant/bouche_A.png"
        erreurs = valider.valider(m)
        self.assertTrue(any("fichier manquant" in e and "A" in e for e in erreurs))


class TestManifestsCompletsDesPlanches(unittest.TestCase):
    """Aiko, Darius, Alaric, Vorthaz : manifestes construits à partir des planches de base."""

    def test_chaque_personnage_passe(self):
        for nom in ("aiko_soryu", "darius_valen", "alaric", "vorthaz"):
            with self.subTest(personnage=nom):
                with open(os.path.join(valider.RACINE, "personnages", nom + ".json"), encoding="utf-8") as f:
                    self.assertEqual(valider.valider(json.load(f)), [])


if __name__ == "__main__":
    unittest.main()

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from moteur import config  # noqa: E402


class TestRendu(unittest.TestCase):
    def test_defauts_coherents(self):
        r = config.Rendu()
        self.assertEqual(r.nb_images, 96)            # 4 s à 24 i/s

    def test_resolution_impaire_refusee(self):
        with self.assertRaises(ValueError):
            config.Rendu(largeur=961)

    def test_fps_non_supporte_refuse(self):
        with self.assertRaises(ValueError):
            config.Rendu(fps=50)

    def test_duree_nulle_refusee(self):
        with self.assertRaises(ValueError):
            config.Rendu(duree_s=0)


if __name__ == "__main__":
    unittest.main()

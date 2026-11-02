"""Tests du moteur de déformation 2D : seuls les pixels des dessins sont visibles, la grille n'ajoute rien."""
import sys
import unittest
from pathlib import Path

import cv2
import numpy as np

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

from moteur2d import action as A  # noqa: E402
from moteur2d import personnage as P  # noqa: E402
from moteur2d.grille import Grille  # noqa: E402
from moteur2d.rendu import Rendu  # noqa: E402
from moteur2d.segmentation import garder_composante, premier_plan  # noqa: E402

KAEL = RACINE / "characters" / "kael"


class TestSegmentation(unittest.TestCase):
    def test_fragment_etranger_exclu_de_la_vue_34(self):
        bgr = cv2.imread(str(KAEL / "vues" / "trois_quarts_g.png"))
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB).astype(np.float32) / 255
        fg = premier_plan(rgb)
        garde = garder_composante(fg, (174, 170))
        self.assertGreater(fg.sum() - garde.sum(), 0)             # le fragment du bord existe et est écarté
        self.assertFalse(garde[:, 800:].any())                    # plus rien dans le bord droit

    def test_fond_blanc_n_est_pas_du_premier_plan(self):
        blanc = np.ones((10, 10, 3), np.float32)
        self.assertFalse(premier_plan(blanc).any())


class TestGrille(unittest.TestCase):
    def test_champ_nul_ne_deplace_rien(self):
        g = Grille(120, 100, pas=16)
        X, Y = g.positions_identite()
        img = np.random.RandomState(0).rand(120, 100, 4).astype(np.float32)
        self.assertTrue(np.allclose(g.deformer(img, X, Y), img))


class TestPersonnage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p = P.charger(KAEL)

    def test_vues_chargees_et_recalage(self):
        self.assertEqual(set(self.p.vues), {"face", "trois_quarts"})
        self.assertEqual(self.p.translation_34, (116.0, 33.0))

    def test_vue_absente_refusee(self):
        import json, shutil, tempfile
        with tempfile.TemporaryDirectory() as d:
            shutil.copytree(KAEL, Path(d) / "kael")
            rig_p = Path(d) / "kael" / "rig.json"
            rig = json.loads(rig_p.read_text(encoding="utf-8"))
            rig["vues"]["trois_quarts"]["disponible"] = False
            rig_p.write_text(json.dumps(rig), encoding="utf-8")
            with self.assertRaises(ValueError):
                P.charger(Path(d) / "kael")


class TestAction(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.act = A.charger(KAEL / "actions" / "idle.json")
        cls.s = A.series(cls.act)

    def test_yaw_de_0_a_45_et_retour(self):
        self.assertAlmostEqual(float(self.s["yaw"][0]), 0.0)
        self.assertAlmostEqual(float(self.s["yaw"].max()), 45.0)
        self.assertAlmostEqual(A.cle_valeur(self.act["pistes"][0]["cles"], 96), 0.0)   # boucle fermée à la frame 96
        self.assertLess(float(self.s["yaw"][-1]), 1.0)                                # dernier dessin proche de 0

    def test_cadence_tenue_par_dessin(self):
        self.assertEqual(self.s["tenue"], 3)
        self.assertEqual(len(self.s["yaw"]), self.act["duree_frames"] // 3)

    def test_ressort_retour_au_repos(self):
        x = A.ressort([1.0] + [0.0] * 200, raideur=60, amortissement=0.25, gain_px=1.0)
        self.assertLess(abs(x[-1]), 1e-3)
        self.assertLess(np.abs(x).max(), 10.0)

    def test_retard_du_ressort(self):
        x = A.ressort([1.0] + [0.0] * 20, raideur=60, amortissement=0.25, gain_px=1.0, retard_pas=2)
        self.assertEqual(x[0], 0.0)
        self.assertEqual(x[1], 0.0)


class TestRendu(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p = P.charger(KAEL)
        cls.R = Rendu(cls.p, pas=24)

    def test_sans_deformation_l_image_est_le_dessin_de_face(self):
        out = self.R.image(t=0.0)
        attendu = (self.p.vues["face"].rgb * 255 + 0.5).astype(np.uint8)
        attendu[~self.p.vues["face"].fg] = 255
        diff = np.abs(out.astype(int) - attendu.astype(int)).max(axis=2)
        self.assertLess(np.mean(diff > 6), 0.005)               # seul l'antialiasing des bords peut différer

    def test_pixels_visibles_viennent_des_dessins(self):
        zone = self.p.vues["face"].fg | self.p.vues["trois_quarts"].fg
        zone = cv2.dilate(zone.astype(np.uint8), np.ones((31, 31), np.uint8)).astype(bool)
        out = self.R.image(t=0.5, respiration=0.02, cape_px=8, cheveux_px=3)
        non_blanc = out.min(axis=2) < 245
        self.assertLess((non_blanc & ~zone).sum(), 50)

    def test_fondu_change_la_tete(self):
        a = self.R.image(t=0.0)
        b = self.R.image(t=1.0)
        self.assertGreater(np.abs(a.astype(int) - b.astype(int)).mean(), 0.5)

    def test_fantome_mesure(self):
        self.assertTrue(0.0 < self.R.fantome(0.5) <= 1.0)


if __name__ == "__main__":
    unittest.main()

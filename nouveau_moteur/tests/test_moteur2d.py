"""Tests du moteur 2D : seuls les pixels des dessins sont visibles ; effets et séquenceur vérifiés."""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

from moteur2d import effets as E  # noqa: E402
from moteur2d import personnage as P  # noqa: E402
from moteur2d import sequenceur as S  # noqa: E402
from moteur2d.segmentation import garder_composante, premier_plan  # noqa: E402

KAEL = RACINE / "characters" / "kael"
SCENE = RACINE / "scenes" / "demo_6s.json"


class TestSegmentation(unittest.TestCase):
    def test_fragment_etranger_exclu_de_la_vue_34(self):
        bgr = cv2.imread(str(KAEL / "vues" / "trois_quarts_g.png"))
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB).astype(np.float32) / 255
        fg = premier_plan(rgb)
        garde = garder_composante(fg, (174, 170))
        self.assertGreater(fg.sum() - garde.sum(), 0)
        self.assertFalse(garde[:, 800:].any())

    def test_fond_blanc_n_est_pas_du_premier_plan(self):
        self.assertFalse(premier_plan(np.ones((10, 10, 3), np.float32)).any())


class TestPersonnage(unittest.TestCase):
    def test_vues_chargees(self):
        p = P.charger(KAEL)
        self.assertEqual(set(p.vues), {"face", "trois_quarts"})
        self.assertGreater(p.vues["face"].fg.sum(), 0)

    def test_vue_absente_refusee(self):
        with tempfile.TemporaryDirectory() as d:
            shutil.copytree(KAEL, Path(d) / "kael")
            rig_p = Path(d) / "kael" / "rig.json"
            rig = json.loads(rig_p.read_text(encoding="utf-8"))
            rig["vues"]["trois_quarts"]["disponible"] = False
            rig_p.write_text(json.dumps(rig), encoding="utf-8")
            with self.assertRaises(ValueError):
                P.charger(Path(d) / "kael")


class TestEffets(unittest.TestCase):
    def test_secousse_s_amortit(self):
        amps = [abs(E.secousse(n, 14, 0.6)[0]) for n in range(25)]
        self.assertGreater(amps[0], amps[-1])
        self.assertLess(amps[-1], 1.0)

    def test_quantifier_garde_le_blanc_et_limite_les_tons(self):
        img = np.full((20, 20, 3), 255, np.uint8)
        img[:10] = (30, 40, 90)
        img[10:] = (200, 180, 120)
        img[:, 19] = 255                                        # une colonne de fond blanc
        centres = E.ajuster_palette([img], tons=2)
        q = E.quantifier(img, centres)
        self.assertTrue((q[:, 19] == 255).all())                # blanc inchangé
        self.assertLessEqual(len(np.unique(q[:10, :19].reshape(-1, 3), axis=0)), 1)

    def test_smear_ne_cree_que_du_contenu_existant(self):
        calque = np.zeros((30, 30, 4), np.float32)
        calque[10:20, 10:20] = 1.0
        out = E.smear(calque, (1, 0), 8)
        self.assertFalse(((out[..., 3] > 0) & (calque[..., 3] == 0) & (np.arange(30)[None, :] > 20)).any())


class TestSequenceur(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p = P.charger(KAEL)
        cls.scene = S.charger_scene(SCENE)

    def test_duree_et_flash_blanc(self):
        images, masques = S.Sequenceur(self.p, self.scene).rendre()
        self.assertEqual(len(images), 144)                      # 6 s à 24 i/s
        self.assertEqual(int(sum(m.sum() == 0 for m in masques)), 1)   # une seule frame de flash
        flash = [i for i, m in enumerate(masques) if m.sum() == 0][0]
        self.assertTrue((images[flash] == 255).all())

    def test_contenu_seulement_des_dessins(self):
        images, masques = S.Sequenceur(self.p, self.scene).rendre()
        for im, ma in zip(images, masques):
            if ma.sum() == 0:
                continue
            zone = cv2.dilate(ma.astype(np.uint8), np.ones((9, 9), np.uint8)).astype(bool)
            non_blanc = im.min(axis=2) < 200
            self.assertFalse((non_blanc & ~zone).any())

    def test_duree_incoherente_refusee(self):
        with tempfile.TemporaryDirectory() as d:
            s = json.loads(SCENE.read_text(encoding="utf-8"))
            s["plans"][0]["duree_s"] = 3.0
            p = Path(d) / "s.json"
            p.write_text(json.dumps(s), encoding="utf-8")
            with self.assertRaises(ValueError):
                S.charger_scene(p)

    def test_effet_inconnu_refuse(self):
        with tempfile.TemporaryDirectory() as d:
            s = json.loads(SCENE.read_text(encoding="utf-8"))
            s["plans"][0]["effets"] = [{"type": "forme_dessinee", "frames": [0, 1]}]
            p = Path(d) / "s.json"
            p.write_text(json.dumps(s), encoding="utf-8")
            with self.assertRaises(ValueError):
                S.charger_scene(p)


if __name__ == "__main__":
    unittest.main()

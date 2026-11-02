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

    def test_palette_prise_dans_les_dessins(self):
        couleurs = np.array([[30, 40, 90], [200, 180, 120], [250, 250, 250], [10, 10, 10]], np.uint8)
        pal = E.ajuster_palette(couleurs, tons=2)
        self.assertTrue(all(tuple(c) in {tuple(x) for x in couleurs} for c in pal))

    def test_quantifier_garde_le_blanc(self):
        img = np.full((20, 20, 3), 255, np.uint8)
        img[:, :10] = (30, 40, 90)
        q = E.quantifier(img, np.array([[30, 40, 90], [200, 180, 120]], np.uint8))
        self.assertTrue((q[:, 15] == 255).all())
        self.assertTrue((q[:, :10] == (30, 40, 90)).all())

    def test_smear_garde_alpha_et_ne_melange_pas_le_blanc(self):
        calque = np.zeros((30, 30, 4), np.float32)
        calque[10:20, 10:20, :3] = np.array([0.1, 0.2, 0.4])
        calque[10:20, 10:20, 3] = 1.0
        out = E.smear(calque, (1, 0), 8)
        self.assertTrue(np.allclose(out[..., 3], calque[..., 3]))           # alpha d'origine
        self.assertEqual(float(out[..., :3][calque[..., 3] == 0].sum()), 0.0)  # rien hors silhouette
        couleur = out[10:20, 10:20, :3] / np.maximum(out[10:20, 10:20, 3:4], 1e-6)
        self.assertTrue(np.allclose(couleur, [0.1, 0.2, 0.4], atol=1e-4))   # couleur du personnage seulement


class TestSequenceur(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p = P.charger(KAEL)
        cls.scene = S.charger_scene(SCENE)
        cls.seq = S.Sequenceur(cls.p, cls.scene, RACINE)
        cls.images, cls.masques, cls.flashs = cls.seq.rendre()

    def test_duree_et_flash_silhouette(self):
        self.assertEqual(len(self.images), 144)                     # 6 s à 24 i/s
        self.assertEqual(sum(self.flashs), 1)                       # une seule frame de flash
        k = self.flashs.index(True)
        self.assertGreater(self.masques[k].sum(), 0)                # la silhouette existe (vient du calque)
        self.assertTrue((self.images[k] == 255).all())              # et elle est blanche

    def test_aucune_couleur_hors_des_dessins(self):
        """Contrôle à chaque commit : toute couleur visible vient d'un dessin fourni, ou est le blanc."""
        self.assertEqual(S.couleurs_hors(self.images, self.seq.sources), set())

    def test_aucun_pixel_hors_silhouette(self):
        for im, ma in zip(self.images, self.masques):
            zone = cv2.dilate(ma.astype(np.uint8), np.ones((9, 9), np.uint8)).astype(bool)
            non_blanc = im.min(axis=2) < 200
            self.assertFalse((non_blanc & ~zone).any())

    def test_calque_trait_vide_sans_effet(self):
        rgb, alpha = S._charger_png(RACINE / "effets_calques" / "traits_vitesse.png")
        self.assertEqual(float(alpha.sum()), 0.0)

    def test_plan_d_attaque_marque_placeholder(self):
        self.assertTrue(self.scene["plans"][1]["placeholder"])

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

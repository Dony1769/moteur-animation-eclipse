"""Tests du rendu NPR (M7) : rampe, formules, contour, et équivalence GPU / référence numpy.

Les tests GL sont ignorés (SkipTest) s'il n'existe pas de contexte OpenGL 3.3
(EGL headless). Dans ce dépôt, llvmpipe via EGL est disponible.
"""
import os
import sys
import unittest

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "engine"))

from npr import reference as R  # noqa: E402
from npr import tete_test as T  # noqa: E402
from npr.parametres import ParamsContour, ParamsOmbrage  # noqa: E402
from npr.rampe import COULEURS_TOON, rampe, rampe_par_defaut, vers_flottant  # noqa: E402
from npr.rendu import RenduNPR, creer_contexte  # noqa: E402


class TestRampe(unittest.TestCase):
    def test_forme_et_bandes(self):
        r = rampe_par_defaut()
        self.assertEqual(r.shape, (256, 3))
        self.assertEqual(r.dtype, np.uint8)
        c = [np.round(np.array(x) * 255).astype(np.uint8) for x in COULEURS_TOON]
        # Bords alignés sur 1/256 : 0,35 -> texel 90 ; 0,70 -> texel 180.
        np.testing.assert_array_equal(r[89], c[0])
        np.testing.assert_array_equal(r[90], c[1])
        np.testing.assert_array_equal(r[179], c[1])
        np.testing.assert_array_equal(r[180], c[2])
        np.testing.assert_array_equal(r[255], c[2])

    def test_nombre_de_couleurs_invalide(self):
        with self.assertRaises(ValueError):
            rampe((0.5,), COULEURS_TOON)


class TestFormules(unittest.TestCase):
    def test_demi_lambert_bornes_et_cas_limites(self):
        rng = np.random.default_rng(0)
        n = R.normaliser(rng.normal(size=(1000, 3)))
        l = R.normaliser(np.array([0.3, -0.4, 0.8]))
        d = R.demi_lambert(n, l)
        self.assertTrue(np.all(d >= 0.0) and np.all(d <= 1.0))
        self.assertAlmostEqual(float(R.demi_lambert(l, l)), 1.0, places=6)
        self.assertAlmostEqual(float(R.demi_lambert(-l, l)), 0.0, places=6)

    def test_indice_rampe(self):
        self.assertEqual(int(R.indice_rampe(np.float64(0.0), 256)), 0)
        self.assertEqual(int(R.indice_rampe(np.float64(0.5), 256)), 128)
        self.assertEqual(int(R.indice_rampe(np.float64(1.0), 256)), 255)

    def test_spec_binaire(self):
        s = R.step(0.95, np.linspace(0.0, 1.0, 1001))
        self.assertEqual(set(np.unique(s).tolist()), {0.0, 1.0})

    def test_smoothstep_centre(self):
        self.assertAlmostEqual(float(R.smoothstep(0.4, 0.6, np.float64(0.5))), 0.5, places=6)

    def test_plan_face_camera_eclaire_de_face(self):
        """Plan face caméra, lumière dans l'axe : u = 1, donc la couleur la plus claire de la rampe."""
        H = W = 8
        albedo = np.ones((H, W, 4), np.float32)
        normale = np.zeros((H, W, 3), np.float32)
        normale[..., 2] = 1.0
        prof = np.full((H, W), 2.0, np.float32)
        uv = np.zeros((H, W, 2), np.float32)
        rf = vers_flottant(rampe_par_defaut())
        # poids_sphere = 0 : on teste la rampe seule ; spéculaire et rim désactivés.
        p = ParamsOmbrage(poids_sphere=0.0, spec_seuil=1.5, rim_seuil=1.5)
        out = R.ombrage(albedo, normale, prof, uv, rf, p, (1.0, 1.0),
                        np.array([0.0, 0.0, -2.0], np.float32),
                        np.array([0.0, 0.0, 1.0], np.float32),
                        np.array([0.0, 0.0, 1.0], np.float32))
        np.testing.assert_allclose(out[..., :3], np.broadcast_to(rf[-1], (H, W, 3)), atol=1e-6)

    def test_fond_reste_vide(self):
        H = W = 4
        out = R.ombrage(np.ones((H, W, 4), np.float32), np.zeros((H, W, 3), np.float32),
                        np.zeros((H, W), np.float32), np.zeros((H, W, 2), np.float32),
                        vers_flottant(rampe_par_defaut()), ParamsOmbrage(), (1.0, 1.0),
                        np.array([0.0, 0.0, -2.0]), np.array([0.0, 0.0, 1.0]),
                        np.array([0.0, 0.0, 1.0]))
        self.assertTrue(np.all(out == 0.0))


class TestContour(unittest.TestCase):
    def _scene(self):
        H = W = 20
        prof = np.full((H, W), 2.0, np.float32)
        prof[:, 10:] = 5.0
        normale = np.zeros((H, W, 3), np.float32)
        normale[..., 2] = 1.0
        couleur = np.full((H, W, 4), 0.5, np.float32)
        return couleur, normale, prof

    def test_trait_sur_saut_de_profondeur(self):
        c, n, p = self._scene()
        out = R.contour(c, n, p, ParamsContour(epaisseur=1))
        trait = np.all(out[..., :3] == 0.0, axis=-1)
        colonnes = np.where(trait[5:15].any(axis=0))[0]
        self.assertEqual(set(colonnes.tolist()), {9, 10})

    def test_silhouette_contre_le_fond(self):
        c, n, p = self._scene()
        p[:, 10:] = 0.0
        n[:, 10:] = 0.0
        out = R.contour(c, n, p, ParamsContour())
        np.testing.assert_allclose(out[0, 15, :3], ParamsContour().couleur_fond, atol=1e-6)
        self.assertTrue(np.all(out[5, 9, :3] == 0.0))


_CTX = None
_CTX_CHERCHE = False


def _contexte():
    global _CTX, _CTX_CHERCHE
    if not _CTX_CHERCHE:
        _CTX = creer_contexte()
        _CTX_CHERCHE = True
    return _CTX


class TestGL(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ctx = _contexte()
        if ctx is None:
            raise unittest.SkipTest("pas de contexte OpenGL 3.3 disponible")
        cls.ctx = ctx
        cls.W = cls.H = 192
        cls.rendu = RenduNPR(ctx, cls.W, cls.H)          # compile les trois programmes
        cls.maillage = T.charger(ctx, cls.rendu.prog_geo)
        cls.ms, cls.mo = T.masques(512, 512)
        cls.rendu.definir_masques(cls.ms, cls.mo)
        cls.tan = T.tan_fov(cls.W, cls.H)
        cls.rf = vers_flottant(rampe_par_defaut())

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "rendu"):
            cls.rendu.liberer()

    def _rendre(self, p_ombrage, p_contour=None):
        self.rendu.p_ombrage = p_ombrage
        self.rendu.p_contour = p_contour or ParamsContour()
        self.rendu.dessiner(self.maillage,
                            modele_vue=T.modele_vue(),
                            projection=T.projection(self.W, self.H),
                            centre_tete_vue=T.CENTRE_VUE,
                            lumiere_vue=T.LUMIERE_VUE,
                            avant_tete_vue=T.AVANT_VUE,
                            tan_fov=self.tan)
        return self.rendu.lire_gbuffer(), self.rendu.lire_ombrage()

    def test_ombrage_gpu_egal_reference(self):
        cas = [ParamsOmbrage(poids_sphere=0.0, spec_seuil=0.985),
               ParamsOmbrage(poids_sphere=1.0, masque_visage=True, spec_seuil=0.985)]
        for p in cas:
            with self.subTest(poids=p.poids_sphere, visage=p.masque_visage):
                g, gl = self._rendre(p)
                ref = R.ombrage(g["albedo"], g["normale"], g["profondeur"], g["uv"], self.rf, p,
                                self.tan, T.CENTRE_VUE, T.LUMIERE_VUE, T.AVANT_VUE,
                                self.ms, self.mo)
                self.assertLess(float(np.abs(ref - gl).max()), 1e-3)

    def test_contour_gpu_egal_reference(self):
        p = ParamsOmbrage(poids_sphere=1.0, masque_visage=True, spec_seuil=0.985)
        g, gl = self._rendre(p, ParamsContour())
        ref = R.contour(gl, g["normale"], g["profondeur"], ParamsContour())
        gpu = self.rendu.image_finale()[::-1].astype(np.int32)   # remis en ordre OpenGL
        attendu = np.round(ref * 255.0).astype(np.int32)
        ecart = np.abs(gpu - attendu)[..., :3]
        self.assertLess(float((ecart > 1).mean()), 0.001)
        self.assertGreater(int(np.all(gpu[..., :3] == 0, axis=-1).sum()), 50)  # traits présents

    def test_contour_gpu_isole_chaque_terme(self):
        """Saut de profondeur seul, puis saut de normale seul : GPU = référence, colonnes attendues."""
        H, W = self.H, self.W
        couleur = np.full((H, W, 3), 0.5, np.float32)
        profondeur_uniforme = np.full((H, W), 2.0, np.float32)
        normale_uniforme = np.zeros((H, W, 3), np.float32)
        normale_uniforme[..., 2] = 1.0

        prof_saut = profondeur_uniforme.copy()
        prof_saut[:, W // 2:] = 5.0
        normale_saut = normale_uniforme.copy()
        normale_saut[:, W // 2:] = (0.6, 0.0, 0.8)

        prof_saut_h = profondeur_uniforme.copy()
        prof_saut_h[H // 2:, :] = 5.0
        normale_saut_h = normale_uniforme.copy()
        normale_saut_h[H // 2:, :] = (0.6, 0.0, 0.8)

        # (nom, normales, profondeur, axe du saut) : 'x' = saut vertical (colonnes), 'y' = horizontal.
        cas = [
            ("profondeur_x", normale_uniforme, prof_saut, "x"),
            ("normale_x", normale_saut, profondeur_uniforme, "x"),
            ("profondeur_y", normale_uniforme, prof_saut_h, "y"),
            ("normale_y", normale_saut_h, profondeur_uniforme, "y"),
        ]
        for nom, n, d, axe in cas:
            with self.subTest(terme=nom):
                gpu = self.rendu.contour_sur(couleur, n, d, ParamsContour())
                ref = R.contour(couleur, n, d, ParamsContour())
                self.assertLess(float(np.abs(gpu[..., :3] - ref[..., :3]).max()), 1e-5)
                trait = np.all(gpu[..., :3] == 0.0, axis=-1)
                if axe == "x":
                    lignes = trait[H // 4: 3 * H // 4]
                    attendu = {W // 2 - 1, W // 2}
                    trouve = set(np.where(lignes.any(axis=0))[0].tolist())
                else:
                    colonnes = trait[:, W // 4: 3 * W // 4]
                    attendu = {H // 2 - 1, H // 2}
                    trouve = set(np.where(colonnes.any(axis=1))[0].tolist())
                self.assertEqual(trouve, attendu)


if __name__ == "__main__":
    unittest.main()

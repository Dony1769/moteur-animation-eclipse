"""Maillage 3D : importeur OBJ, squelette et skinning linéaire, poids d'os, et rendu NPR GPU d'un buste skinné."""
import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "engine"))

from npr import buste as B  # noqa: E402
from npr import maillage3d as M  # noqa: E402

MODELE_OBJ = Path(__file__).resolve().parent.parent / "engine" / "npr" / "modeles" / "buste_proxy.obj"

CARRE_OBJ = """\
# commentaire ignoré
v 0 0 0
v 1 0 0
v 1 1 0
v 0 1 0
vt 0 0
vt 1 0
vt 1 1
vt 0 1
vn 0 0 1
f 1/1/1 2/2/1 3/3/1 4/4/1
"""


def _triangles_geometriques(m):
    """Ensemble des triangles par coordonnées (indépendant de l'ordre des sommets)."""
    return {tuple(sorted(tuple(np.round(m.sommets[i], 6)) for i in tri)) for tri in m.triangles}


class TestImportOBJ(unittest.TestCase):
    def test_quad_triangule_en_eventail(self):
        m = M.lire_obj(CARRE_OBJ, "carre")
        self.assertEqual(len(m.sommets), 4)
        self.assertEqual(len(m.triangles), 2)
        self.assertEqual(m.uv.shape, (4, 2))
        self.assertEqual(m.uv_origine, "fichier")

    def test_indices_negatifs(self):
        texte = "v 0 0 0\nv 1 0 0\nv 0 1 0\nf -3 -2 -1\n"
        m = M.lire_obj(texte, "neg")
        self.assertEqual(len(m.triangles), 1)
        self.assertEqual(len(m.sommets), 3)

    def test_indice_hors_plage_refuse(self):
        with self.assertRaises(ValueError):
            M.lire_obj("v 0 0 0\nv 1 0 0\nf 1 2 9\n", "bad")

    def test_sans_face_refuse(self):
        with self.assertRaises(ValueError):
            M.lire_obj("v 0 0 0\nv 1 0 0\n", "vide")

    def test_face_incomplete_refusee(self):
        with self.assertRaises(ValueError):
            M.lire_obj("v 0 0 0\nv 1 0 0\nf 1 2\n", "incomplet")

    def test_normales_unitaires_et_tangentes_orthogonales(self):
        m = M.lire_obj(CARRE_OBJ, "carre")
        self.assertTrue(np.allclose(np.linalg.norm(m.normales, axis=1), 1.0, atol=1e-6))
        dot = np.einsum("ni,ni->n", m.normales, m.tangentes[:, :3])
        self.assertTrue(np.allclose(dot, 0.0, atol=1e-5))

    def test_proxy_charge_avec_uv_dans_le_carre_unite(self):
        m = M.charger_obj(MODELE_OBJ)
        self.assertGreater(len(m.sommets), 100)
        self.assertTrue(np.all(m.uv >= -1e-6) and np.all(m.uv <= 1.0 + 1e-6))

    def test_aller_retour_ecriture_lecture(self):
        """Compare la géométrie des triangles (pas l'ordre des sommets, que l'importeur renumérote)."""
        original = B.buste_proxy()
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            chemin = Path(d) / "buste.obj"
            M.ecrire_obj(original, chemin)
            relu = M.charger_obj(chemin)
        self.assertEqual(_triangles_geometriques(original), _triangles_geometriques(relu))


class TestSquelette(unittest.TestCase):
    def setUp(self):
        self.sq = B.squelette_buste()

    def test_repos_identite(self):
        """Sans pose, la transformation de skinning de chaque os est l'identité."""
        S = self.sq.matrices_skinning(None)
        for k in range(len(S)):
            self.assertTrue(np.allclose(S[k], np.eye(4), atol=1e-9))

    def test_rotation_de_tete_conserve_les_distances_au_pivot(self):
        """La tête tourne autour de l'articulation du cou : les points de la tête gardent leur distance au pivot."""
        pivot = np.asarray(self.sq.joints[2], float)
        pose = {"tete": (np.array([0.0, 0.0, 1.0]), 0.4)}
        S = self.sq.matrices_skinning(pose)
        p = np.array([0.05, 0.35, 0.0, 1.0])
        q = S[2] @ p
        self.assertAlmostEqual(np.linalg.norm(p[:3] - pivot), np.linalg.norm(q[:3] - pivot), places=6)

    def test_os_inconnu_refuse(self):
        with self.assertRaises(ValueError):
            self.sq.matrices_skinning({"inconnu": (np.array([0.0, 0.0, 1.0]), 0.1)})

    def test_parent_avant_enfant(self):
        for k, o in enumerate(self.sq.os):
            self.assertLess(o.parent, k)


class TestPoids(unittest.TestCase):
    def test_poids_somment_a_un_et_au_plus_k_non_nuls(self):
        m = B.buste_proxy()
        sq = B.squelette_buste()
        w = M.poids_proximite(m.sommets, sq, sigma=0.08, k=2)
        self.assertTrue(np.allclose(w.sum(axis=1), 1.0, atol=1e-6))
        self.assertTrue(np.all((w > 0).sum(axis=1) <= 2))


class TestRenduNPR(unittest.TestCase):
    """Rendu GPU réel : le chemin 3D doit produire une image non vide, réagir au yaw et à la pose,
    et conserver la couleur d'albédo de la texture."""

    @classmethod
    def setUpClass(cls):
        from npr import demo_buste3d as DB
        from npr import rendu3d as R
        from npr.rendu import creer_contexte
        cls.ctx = creer_contexte()
        if cls.ctx is None:
            raise unittest.SkipTest("contexte OpenGL indisponible")
        modele, sq = DB.charger_buste()
        tex = np.zeros((8, 8, 4), np.float32)
        tex[..., 0], tex[..., 1], tex[..., 2], tex[..., 3] = 0.9, 0.2, 0.2, 1.0   # rouge franc
        cls.av = R.Avatar3D(cls.ctx, modele, sq, 160, 200, texture_rgba=tex)

    @classmethod
    def tearDownClass(cls):
        if getattr(cls, "av", None) is not None:
            cls.av.liberer()

    def test_image_non_vide_et_forme(self):
        img = self.av.rendre(None, 0.0)
        self.assertEqual(img.shape, (200, 160, 3))
        self.assertEqual(img.dtype, np.uint8)
        self.assertGreater(int(img.max()), 40)

    def test_yaw_change_l_image(self):
        a = self.av.rendre(None, 0.0).astype(int)
        b = self.av.rendre(None, 0.6).astype(int)
        self.assertGreater(np.abs(a - b).mean(), 1.0)

    def test_pose_change_l_image(self):
        a = self.av.rendre(None, 0.0).astype(int)
        b = self.av.rendre({"tete": (np.array([0.0, 0.0, 1.0]), 0.4)}, 0.0).astype(int)
        self.assertGreater(np.abs(a - b).mean(), 0.5)

    def test_albedo_rouge_present(self):
        img = self.av.rendre(None, 0.0).astype(int)
        rouge = (img[..., 0] > img[..., 1] + 30) & (img[..., 0] > img[..., 2] + 30)
        self.assertGreater(rouge.sum(), 200)


class TestMultivue(unittest.TestCase):
    """Sélection de vue, UV par vue et fondu : logique CPU, sans GPU."""

    def test_uv_de_face_egale_la_projection_planaire(self):
        from npr import demo_buste3d as DB
        m = B.buste_proxy()
        uv0 = DB.uv_vue(m, 0.0).uv
        self.assertTrue(np.allclose(uv0, M.uv_planaires(m.sommets), atol=1e-9))

    def test_uv_trois_quarts_different_de_la_face(self):
        from npr import demo_buste3d as DB
        m = B.buste_proxy()
        self.assertFalse(np.allclose(DB.uv_vue(m, DB.ANGLE_34).uv, DB.uv_vue(m, 0.0).uv))

    def test_recadrages_trois_quarts_dans_l_image(self):
        from npr import demo_buste3d as DB
        x0, y0, x1, y1 = DB.RECADRAGE_34
        self.assertTrue(0 <= x0 < x1 <= 900 and 0 <= y0 < y1 <= 856)

    def test_vue_la_plus_proche(self):
        from npr import rendu3d as R
        av = R.Avatar3D.__new__(R.Avatar3D)
        av.angles = [0.0, float(np.radians(45.0))]
        i, _ = R.Avatar3D.vue_pour(av, 0.1)
        self.assertEqual(i, 0)
        i, _ = R.Avatar3D.vue_pour(av, 0.7)
        self.assertEqual(i, 1)


if __name__ == "__main__":
    unittest.main()

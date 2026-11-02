"""Tests de l'encre fine (engine/npr/encre.py) : numpy pur, sans GPU.

Le disque sur fond et les marches de profondeur ou de normales servent de cas de référence.
"""
import os
import sys
import unittest

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "engine"))

from npr import encre as E  # noqa: E402


def _disque(H=64, W=64, rayon=18, valeur=5.0):
    yy, xx = np.mgrid[0:H, 0:W]
    masque = ((xx - W / 2) ** 2 + (yy - H / 2) ** 2) <= rayon ** 2
    d = np.where(masque, valeur, 0.0)
    n = np.zeros((H, W, 3))
    n[masque] = [0.0, 0.0, 1.0]
    return d, n, masque


def _encre(rgb_valeur, d, n, p=None):
    p = p or E.ParamsEncre()
    H, W = d.shape
    out = E.appliquer(np.full((H, W, 3), rgb_valeur), n, d, p)
    return np.all(np.isclose(out, p.couleur_trait, atol=1e-9), axis=2), out


class TestSilhouette(unittest.TestCase):
    def test_contour_mince_sur_face_eclairee(self):
        d, n, masque = _disque()
        ink, _ = _encre(0.9, d, n)
        # Sur la face éclairée, le trait reste fin : au plus 2 pixels par ligne (marche oblique).
        for y in range(20, 45):
            self.assertLessEqual(int(ink[y].sum()), 4, y)

    def test_contour_plus_epais_sur_face_ombree(self):
        d, n, masque = _disque()
        ink_clair, _ = _encre(0.9, d, n)
        ink_ombre, _ = _encre(0.15, d, n)
        self.assertGreater(ink_ombre.sum(), ink_clair.sum() * 1.5)

    def test_trait_ombre_a_trois_pixels(self):
        d, n, masque = _disque()
        ink, _ = _encre(0.15, d, n)
        gauche = np.nonzero(ink[32])[0]
        self.assertTrue(np.all(np.diff(gauche[gauche < 32]) == 1))   # trait continu
        self.assertEqual(int((gauche < 32).sum()), 3)

    def test_fond_inchange(self):
        d, n, masque = _disque()
        p = E.ParamsEncre()
        _, out = _encre(0.9, d, n, p)
        np.testing.assert_allclose(out[0, 0], p.couleur_fond, atol=1e-12)

    def test_silhouette_continue(self):
        """La frontière de la silhouette ne comporte pas de trou (aucun pixel du bord manquant)."""
        d, n, masque = _disque()
        ink, _ = _encre(0.9, d, n)
        bord = E.silhouette(d > 0)
        self.assertTrue(np.all(ink[bord]))

    def test_surface_plate_sans_trait(self):
        H = W = 32
        d = np.full((H, W), 5.0)
        n = np.zeros((H, W, 3))
        n[..., 2] = 1.0
        # Pas de silhouette si tout est valide : on ajoute un bord pour borner la surface.
        d[0, :] = 0.0
        ink, _ = _encre(0.9, d, n)
        self.assertFalse(ink[2:-2, 2:-2].any())


class TestAretesInternes(unittest.TestCase):
    def test_marche_de_normales_trait_fin(self):
        H = W = 40
        d = np.ones((H, W))
        n = np.zeros((H, W, 3))
        n[..., 2] = 1.0
        n[:, 20:, 0] = 0.8
        n[:, 20:, 2] = 0.6
        n /= np.linalg.norm(n, axis=2, keepdims=True)
        ink, _ = _encre(0.9, d, n, E.ParamsEncre(longueur_min=5))
        # Image entièrement valide : sa frontière (bords de l'image) n'est pas la marche. On mesure au centre.
        self.assertLessEqual(int(ink[20, 5:35].sum()), 2)
        self.assertTrue(ink[20, 5:35].any())

    def test_petits_fragments_retires(self):
        trait = np.zeros((20, 20), bool)
        trait[5, 5] = True
        trait[10:20, 10] = True
        gardes = E.retirer_petits(trait, 5)
        self.assertFalse(gardes[5, 5])
        self.assertTrue(gardes[12, 10])

    def test_hysteresis_garde_lie_au_fort(self):
        faible = np.zeros((10, 10), bool)
        faible[2, 2:8] = True
        faible[7, 7:9] = True
        forte = np.zeros_like(faible)
        forte[2, 4] = True
        h = E.hysteresis(faible, forte)
        self.assertTrue(h[2, 2:8].all())
        self.assertFalse(h[7, 7:9].any())

    def test_entree_invalide_acceptee_sans_erreur(self):
        d = np.zeros((8, 8))
        n = np.zeros((8, 8, 3))
        out = E.appliquer(np.zeros((8, 8, 3)), n, d)
        self.assertEqual(out.shape, (8, 8, 3))


if __name__ == "__main__":
    unittest.main()

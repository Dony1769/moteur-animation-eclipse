"""Métrique de scintillement (engine/npr/sequence_kael.py) sur des séquences synthétiques."""
import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "engine"))

from npr import demo_personnage as DP  # noqa: E402
from npr import sequence_kael as SQ  # noqa: E402


def _pile(valeurs_par_pixel):
    """Séquence (N, 1, P) : valeurs_par_pixel est une liste de N-listes, une par pixel."""
    arr = np.asarray(valeurs_par_pixel, np.float32)        # (P, N)
    return arr.T[:, None, :]                              # (N, 1, P)


class TestScintillement(unittest.TestCase):
    def test_balayage_continu_ne_scintille_pas(self):
        """Une variation lente et monotone (le trait traverse le pixel une fois) ne scintille pas."""
        lums = _pile([np.linspace(0.9, 0.1, 25)])
        self.assertFalse(SQ.scintillement(lums).any())

    def test_aller_retour_lent_ne_scintille_pas(self):
        """Un trait qui passe, repart, puis revient plus tard : inversions espacées, pas de scintillement."""
        bosse = np.concatenate([np.linspace(0.9, 0.1, 8), np.linspace(0.1, 0.9, 8),
                                np.full(5, 0.9), np.linspace(0.9, 0.1, 8), np.linspace(0.1, 0.9, 8)])
        lums = _pile([bosse[:25]])
        self.assertFalse(SQ.scintillement(lums).any())

    def test_clignotement_est_detecte(self):
        """Haut, bas, haut, bas en images consécutives : deux inversions rapides."""
        clignote = np.array([0.9, 0.1, 0.9, 0.1, 0.9, 0.1, 0.9, 0.9, 0.9, 0.9], np.float32)
        lums = _pile([clignote])
        self.assertTrue(SQ.scintillement(lums).all())

    def test_seul_le_pixel_qui_clignote_est_marque(self):
        stable = np.full(10, 0.5, np.float32)
        clignote = np.array([0.9, 0.1, 0.9, 0.1, 0.9, 0.1, 0.9, 0.5, 0.5, 0.5], np.float32)
        lums = _pile([stable, clignote])
        masque = SQ.scintillement(lums)[0]
        self.assertFalse(masque[0])
        self.assertTrue(masque[1])

    def test_variation_faible_ignoree(self):
        """Des variations sous le seuil ne comptent pas, même alternées."""
        petit = np.array([0.5, 0.52, 0.5, 0.52, 0.5, 0.52], np.float32)
        self.assertFalse(SQ.scintillement(_pile([petit])).any())

    def test_forme_invalide_refusee(self):
        with self.assertRaises(ValueError):
            SQ.scintillement(np.zeros((1, 4, 4)))

    def test_balayage_monotone_sans_demi_tour(self):
        t = SQ.inclinaisons(24)
        self.assertTrue(np.all(np.diff(t) < 0))                 # strictement décroissant : pas de demi-tour
        self.assertAlmostEqual(float(t[0]), SQ.AMPLITUDE, places=9)
        self.assertAlmostEqual(float(t[-1]), -SQ.AMPLITUDE, places=9)


class TestProfondeurCalques(unittest.TestCase):
    def test_ecart_de_plans_depasse_le_relief(self):
        """Un calque d'ordre supérieur doit rester devant le calque inférieur même à son bord, où le relief
        rapproche la surface de la caméra : l'écart entre plans doit dépasser relief_max."""
        for ordre in range(5):
            avant = DP.plan_de(ordre + 1)                    # calque avant, bord : relief nul, profondeur = plan
            arriere = DP.plan_de(ordre) - DP.RELIEF_KAEL     # calque arrière, intérieur : relief maximal
            self.assertLess(avant, arriere)


if __name__ == "__main__":
    unittest.main()

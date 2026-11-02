"""Spéculaire coupé sur les tissus sombres, et chaîne normale -> rampe (relief).

Référence numpy (reference.ombrage) et GPU (RenduNPR) doivent donner le même résultat.
"""
import sys
import unittest
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "engine"))

from npr import calques_anim as CA  # noqa: E402
from npr import reference as R  # noqa: E402
from npr import relief as RL  # noqa: E402
from npr import tete_test as T  # noqa: E402
from npr.parametres import ParamsOmbrage  # noqa: E402
from npr.rendu import RenduNPR, creer_contexte  # noqa: E402

CENTRE = np.array([0.0, 0.0, -100.0], np.float32)     # loin derrière le plan : pas de normale sphérique
LUMIERE = np.array([0.0, 0.0, 1.0], np.float32)       # dans l'axe de la vue : H = n sur un plan face caméra
AVANT = np.array([0.0, 0.0, 1.0], np.float32)
RAMPE = np.ones((256, 3), np.float32)                  # rampe constante : seul le spéculaire varie


def _plan_ombre(albedo_valeur, H=4, W=4, **kw):
    albedo = np.full((H, W, 3), albedo_valeur, np.float32)
    normale = np.zeros((H, W, 3), np.float32)
    normale[..., 2] = 1.0
    prof = np.full((H, W), 2.0, np.float32)
    uv = np.zeros((H, W, 2), np.float32)
    return R.ombrage(albedo, normale, prof, uv, RAMPE, ParamsOmbrage(poids_sphere=0.0, rim_seuil=1.5, **kw),
                     (1.0, 1.0), CENTRE, LUMIERE, AVANT)


class TestSpeculaireTissusSombres(unittest.TestCase):
    def test_albedo_sombre_sans_speculaire(self):
        """Albédo 0,2 (cuir, pantalon) : le spéculaire est coupé, comme s'il était désactivé."""
        avec = _plan_ombre(0.2, spec_seuil=0.95, spec_lum_min=0.35)
        sans = _plan_ombre(0.2, spec_seuil=1.5, spec_lum_min=0.35)
        np.testing.assert_allclose(avec, sans, atol=1e-6)

    def test_albedo_clair_garde_le_speculaire(self):
        """Albédo 0,8 : le spéculaire reste, il s'ajoute à la couleur de la rampe."""
        avec = _plan_ombre(0.8, spec_seuil=0.95, spec_lum_min=0.35)
        sans = _plan_ombre(0.8, spec_seuil=1.5, spec_lum_min=0.35)
        # Sortie écrêtée à 1 : sur albédo 0,8 le spéculaire ajoute 0,2 au centre.
        self.assertGreater(float(np.max(avec[..., :3] - sans[..., :3])), 0.1)

    def test_seuil_zero_ne_coupe_rien(self):
        """specLumMin = 0 : comportement d'avant (spéculaire partout), pour comparaison."""
        avec = _plan_ombre(0.2, spec_seuil=0.95, spec_lum_min=0.0)
        sans = _plan_ombre(0.2, spec_seuil=1.5, spec_lum_min=0.0)
        self.assertGreater(float(np.max(avec[..., :3] - sans[..., :3])), 0.5)

    def test_gpu_coupe_comme_la_reference(self):
        ctx = creer_contexte()
        if ctx is None:
            raise unittest.SkipTest("pas de contexte OpenGL 3.3 disponible")
        taille = 64
        rgba = np.zeros((taille, taille, 4), np.float32)
        yy, xx = np.mgrid[0:taille, 0:taille].astype(np.float32)
        disque = ((xx - 31.5) ** 2 + (yy - 31.5) ** 2) <= 22 ** 2
        rgba[..., :3] = 0.2
        rgba[..., 3] = disque
        calque = RL.Calque(rgba, plan=5.0, relief_max=0.0, rayon_biseau=10.0, flou=0.0)
        calques = [CA.construire("disque", calque, cellule=2.0)]
        mesures = {}
        for nom, params in (("coupe", ParamsOmbrage(poids_sphere=0.0, spec_seuil=0.95, spec_lum_min=0.35)),
                            ("sans", ParamsOmbrage(poids_sphere=0.0, spec_seuil=1.5, spec_lum_min=0.35))):
            rendu = RenduNPR(ctx, taille, taille, ombrage=params)
            try:
                rendu.dessiner_calques(calques, {}, projection=T.projection(taille, taille),
                                       tan_fov=T.tan_fov(taille, taille), centre_tete_vue=T.CENTRE_VUE,
                                       lumiere_vue=T.LUMIERE_VUE, avant_tete_vue=T.AVANT_VUE)
                mesures[nom] = rendu.image_finale()[..., :3].astype(float)
            finally:
                rendu.liberer()
        centre = (slice(20, 44), slice(20, 44))
        # Sur un albédo sombre, le spéculaire ne doit rien ajouter : écart nul à la quantification près.
        self.assertLessEqual(float(np.max(np.abs(mesures["coupe"][centre] - mesures["sans"][centre]))), 2 / 255)


class TestRelief(unittest.TestCase):
    def test_normales_unitaires(self):
        h = np.random.default_rng(0).random((32, 32)).astype(np.float32)
        n = RL.normales(h * 6.0, 1.0)
        np.testing.assert_allclose(np.linalg.norm(n, axis=-1), 1.0, atol=1e-5)

    def test_pente_zero_normales_plates(self):
        h = np.random.default_rng(1).random((16, 16)).astype(np.float32)
        n = RL.normales(h * 6.0, 0.0)
        np.testing.assert_allclose(n, np.broadcast_to([0.0, 0.0, 1.0], n.shape), atol=1e-6)

    def test_relief_max_ne_change_que_la_profondeur(self):
        """Contrat documenté : relief_max règle la profondeur des sommets, pas les normales de l'éclairage.
        L'éclairage du relief se règle par `pente` et `rayon_biseau`. Changer ce contrat changerait le rendu de Kaël."""
        rgba = np.zeros((40, 40, 4), np.float32)
        rgba[8:32, 8:32, :3] = 0.6
        rgba[8:32, 8:32, 3] = 1.0
        a = CA.construire("c", RL.Calque(rgba, relief_max=0.04, rayon_biseau=6.0, flou=2.0), cellule=2.0)
        b = CA.construire("c", RL.Calque(rgba, relief_max=0.25, rayon_biseau=6.0, flou=2.0), cellule=2.0)
        np.testing.assert_allclose(a.n_repos, b.n_repos, atol=1e-9)
        self.assertFalse(np.allclose(a.d_repos, b.d_repos))


class TestReliefGPU(unittest.TestCase):
    def test_pente_atteint_la_rampe_gpu(self):
        """La normale du biseau (pente > 0) change l'ombrage à l'écran : la chaîne normale -> rampe est active."""
        ctx = creer_contexte()
        if ctx is None:
            raise unittest.SkipTest("pas de contexte OpenGL 3.3 disponible")
        taille = 96
        rgba = np.zeros((taille, taille, 4), np.float32)
        yy, xx = np.mgrid[0:taille, 0:taille].astype(np.float32)
        disque = ((xx - 47.5) ** 2 + (yy - 47.5) ** 2) <= 34 ** 2
        rgba[..., :3] = 0.8
        rgba[..., 3] = disque
        images = {}
        for pente in (0.0, 1.0):
            calque = RL.Calque(rgba, plan=5.0, relief_max=0.3, rayon_biseau=12.0, pente=pente, flou=1.0)
            calques = [CA.construire("disque", calque, cellule=2.0)]
            rendu = RenduNPR(ctx, taille, taille, ombrage=ParamsOmbrage(poids_sphere=0.0, spec_seuil=1.5))
            try:
                rendu.dessiner_calques(calques, {}, projection=T.projection(taille, taille),
                                       tan_fov=T.tan_fov(taille, taille), centre_tete_vue=T.CENTRE_VUE,
                                       lumiere_vue=(0.6, 0.3, 0.74), avant_tete_vue=T.AVANT_VUE)
                images[pente] = rendu.image_finale()[..., :3].astype(float)
            finally:
                rendu.liberer()
        # Anneau du biseau : à l'intérieur du disque mais proche du bord.
        r = np.hypot(xx - 47.5, yy - 47.5)
        anneau = disque & (r > 26) & (r < 33)
        ecart = float(np.abs(images[1.0] - images[0.0])[anneau].mean())   # en niveaux 0..255
        self.assertGreater(ecart, 3.0)


if __name__ == "__main__":
    unittest.main()

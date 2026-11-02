"""Tests du rigging 2D et des calques articulés : rig (numpy), calques (numpy), rendu (GPU).

Les tests GPU sont ignorés (SkipTest) sans contexte OpenGL 3.3.
"""
import os
import sys
import unittest
from unittest import mock

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "engine"))

from npr import calques_anim as CA  # noqa: E402
from npr import relief as RL  # noqa: E402
from npr import tete_test as T  # noqa: E402
from npr.demo_articule import construire_personnage, timeline  # noqa: E402
from npr.parametres import ParamsOmbrage  # noqa: E402
from npr.rig import GrilleFFD, Os, Piste, Squelette, Timeline, decalage_clignement, poids_par_distance  # noqa: E402
from npr.rendu import Maillage, RenduNPR, creer_contexte  # noqa: E402


def _rot_image(v, theta):
    """Rotation d'un vecteur image (y vers le bas), sens horaire pour theta > 0."""
    c, s = np.cos(theta), np.sin(theta)
    return np.array([c * v[0] - s * v[1], s * v[0] + c * v[1]])


def _carre(taille=64, bord=16, couleur=(0.9, 0.5, 0.2), plan=5.0, relief_max=0.2):
    """Calque carré opaque (sans flou) : au centre, le relief vaut exactement 1."""
    rgba = np.zeros((taille, taille, 4), np.float32)
    rgba[bord:taille - bord, bord:taille - bord, :3] = couleur
    rgba[bord:taille - bord, bord:taille - bord, 3] = 1.0
    return RL.Calque(rgba, plan=plan, relief_max=relief_max, rayon_biseau=6.0, flou=0.0)


def _disque_calque(taille=64, r=20, plan=5.0, relief_max=0.2):
    yy, xx = np.mgrid[0:taille, 0:taille].astype(np.float32)
    c = (taille - 1) / 2
    rgba = np.zeros((taille, taille, 4), np.float32)
    rgba[..., :3] = (0.8, 0.6, 0.4)
    rgba[..., 3] = ((xx - c) ** 2 + (yy - c) ** 2) <= r * r
    return RL.Calque(rgba, plan=plan, relief_max=relief_max, rayon_biseau=8.0, flou=0.0)


class TestSquelette(unittest.TestCase):
    def test_repos_identite(self):
        sq = Squelette([Os("a", (10, 10)), Os("b", (20, 10), parent=0)])
        G = sq.matrices(None)
        np.testing.assert_allclose(G, np.broadcast_to(np.eye(3), G.shape), atol=1e-12)

    def test_rotation_autour_du_pivot(self):
        p = (100.0, 80.0)
        sq = Squelette([Os("a", p)])
        v = np.array([[130.0, 80.0], [100.0, 120.0]])
        theta = 0.7
        out = sq.skinner(v, np.ones((2, 1)), {"a": theta})
        for k in range(2):
            attendu = np.array(p) + _rot_image(v[k] - np.array(p), theta)
            np.testing.assert_allclose(out[k], attendu, atol=1e-9)

    def test_pivot_fixe(self):
        sq = Squelette([Os("a", (5.0, 7.0))])
        out = sq.skinner([[5.0, 7.0]], np.ones((1, 1)), {"a": 1.3})
        np.testing.assert_allclose(out, [[5.0, 7.0]], atol=1e-9)

    def test_enfant_suit_le_parent(self):
        sq = Squelette([Os("p", (0.0, 0.0)), Os("c", (10.0, 0.0), parent=0)])
        # Le pivot de l'enfant est au repos en (10, 0) ; le parent tourne de pi/2.
        out = sq.skinner([[10.0, 0.0]], np.array([[0.0, 1.0]]), {"p": np.pi / 2})
        np.testing.assert_allclose(out, [[0.0, 10.0]], atol=1e-9)

    def test_rotation_des_vecteurs_conserve_la_norme(self):
        sq = Squelette([Os("a", (0.0, 0.0))])
        v = np.array([[1.0, 0.0], [0.6, -0.8]])
        out = sq.tourner_vecteurs(v, np.ones((2, 1)), {"a": 0.9})
        np.testing.assert_allclose(np.linalg.norm(out, axis=1), np.linalg.norm(v, axis=1), atol=1e-12)
        np.testing.assert_allclose(out[0], _rot_image(v[0], 0.9), atol=1e-12)

    def test_parent_apres_enfant_refuse(self):
        with self.assertRaises(ValueError):
            Squelette([Os("a", (0, 0), parent=1), Os("b", (1, 1))])

    def test_noms_en_double_refuses(self):
        with self.assertRaises(ValueError):
            Squelette([Os("a", (0, 0)), Os("a", (1, 1))])


class TestPoids(unittest.TestCase):
    def setUp(self):
        self.sq = Squelette([Os("a", (0.0, 0.0), bout=(0.0, 100.0), sigma=20.0),
                             Os("b", (200.0, 0.0), bout=(200.0, 100.0), sigma=20.0)])

    def test_sommes_a_un_et_positifs(self):
        rng = np.random.default_rng(1)
        P = rng.uniform(-50, 250, size=(200, 2))
        w = poids_par_distance(P, self.sq)
        self.assertTrue(np.all(w >= 0))
        np.testing.assert_allclose(w.sum(axis=1), 1.0, atol=1e-12)

    def test_os_le_plus_proche_domine(self):
        w = poids_par_distance([[5.0, 50.0], [195.0, 50.0]], self.sq)
        self.assertGreater(w[0, 0], 0.99)
        self.assertGreater(w[1, 1], 0.99)

    def test_loin_de_tout_os_pas_de_ligne_nulle(self):
        w = poids_par_distance([[1e6, 1e6]], self.sq)
        self.assertTrue(np.all(np.isfinite(w)))
        np.testing.assert_allclose(w.sum(axis=1), 1.0, atol=1e-12)

    def test_os_actifs_annule_les_autres(self):
        P = np.array([[5.0, 50.0], [195.0, 50.0], [100.0, 50.0]])
        w = poids_par_distance(P, self.sq, actifs={"b"})
        np.testing.assert_allclose(w[:, 0], 0.0, atol=0.0)
        np.testing.assert_allclose(w[:, 1], 1.0, atol=1e-12)

    def test_os_actifs_inconnu_refuse(self):
        with self.assertRaises(ValueError):
            poids_par_distance([[0.0, 0.0]], self.sq, actifs={"zz"})

    def test_poids_one_hot_donne_l_os(self):
        P = np.array([[5.0, 50.0]])
        w = np.array([[1.0, 0.0]])
        out = self.sq.skinner(P, w, {"a": 0.5})
        np.testing.assert_allclose(out, [_rot_image(P[0] - [0, 0], 0.5)], atol=1e-9)


class TestFFD(unittest.TestCase):
    def setUp(self):
        self.g = GrilleFFD((0.0, 0.0, 100.0, 60.0), nx=3, ny=3)
        self.rng = np.random.default_rng(2)

    def test_identite_sans_decalage(self):
        P = self.rng.uniform(-20, 120, size=(50, 2))
        np.testing.assert_allclose(self.g.appliquer(P), P, atol=1e-12)

    def test_translation_uniforme_exacte(self):
        dec = np.zeros((3, 3, 2))
        dec[...] = (3.0, -2.0)
        P = self.rng.uniform(-20, 120, size=(50, 2))
        np.testing.assert_allclose(self.g.appliquer(P, dec), P + [3.0, -2.0], atol=1e-10)

    def test_clignement_lineaire_exact(self):
        """cligne = c : p'_y = (1 - c) y + c y_milieu, x inchangé (champ linéaire reproduit exactement)."""
        P = self.rng.uniform(-20, 120, size=(80, 2))
        c = 0.5
        out = self.g.appliquer(P, decalage_clignement(self.g, c))
        ym = 30.0
        np.testing.assert_allclose(out[:, 0], P[:, 0], atol=1e-10)
        np.testing.assert_allclose(out[:, 1], (1 - c) * P[:, 1] + c * ym, atol=1e-9)

    def test_clignement_ferme_ecrase_sur_la_ligne_mediane(self):
        out = self.g.appliquer(np.array([[50.0, 0.0], [50.0, 60.0]]), decalage_clignement(self.g, 1.0))
        np.testing.assert_allclose(out[:, 1], [30.0, 30.0], atol=1e-9)

    def test_grille_invalide_refusee(self):
        with self.assertRaises(ValueError):
            GrilleFFD((0, 0, 1, 1), nx=1, ny=3)
        with self.assertRaises(ValueError):
            GrilleFFD((1, 0, 0, 1), nx=2, ny=2)


class TestAnimation(unittest.TestCase):
    def test_passe_par_les_cles(self):
        cles = [(0.0, 0.3), (0.4, -1.0), (1.0, 2.0), (1.7, 0.5)]
        for mode in ("lineaire", "cubique"):
            with self.subTest(mode=mode):
                p = Piste(cles, mode)
                for t, v in cles:
                    self.assertAlmostEqual(p.valeur(t), v, places=12)

    def test_lineaire_milieu(self):
        p = Piste([(0.0, 0.0), (1.0, 2.0)], "lineaire")
        self.assertAlmostEqual(p.valeur(0.5), 1.0, places=12)

    def test_cubique_suit_une_droite(self):
        p = Piste([(0.0, 1.0), (0.5, 2.0), (1.0, 3.0), (2.0, 5.0)], "cubique")
        for t in np.linspace(0.0, 2.0, 41):
            self.assertAlmostEqual(p.valeur(t), 2.0 * t + 1.0, places=9)

    def test_cubique_continu_en_derivee(self):
        p = Piste([(0.0, 0.0), (0.5, 1.0), (1.0, 0.0)], "cubique")
        eps = 1e-6
        gauche = (p.valeur(0.5) - p.valeur(0.5 - eps)) / eps
        droite = (p.valeur(0.5 + eps) - p.valeur(0.5)) / eps
        self.assertLess(abs(gauche - droite), 1e-3)

    def test_hors_plage_clamp(self):
        p = Piste([(0.0, 1.0), (1.0, 4.0)], "cubique")
        self.assertEqual(p.valeur(-5.0), 1.0)
        self.assertEqual(p.valeur(99.0), 4.0)

    def test_erreurs(self):
        with self.assertRaises(ValueError):
            Piste([(0.0, 1.0), (0.0, 2.0)])
        with self.assertRaises(ValueError):
            Piste([(0.0, 1.0)], mode="spline")
        with self.assertRaises(ValueError):
            Piste([])

    def test_timeline_pose(self):
        tl = Timeline()
        tl.ajouter("a", [(0.0, 0.0), (1.0, 1.0)])
        tl.ajouter("b", [(0.0, 2.0), (2.0, 2.0)], mode="cubique")
        self.assertEqual(tl.duree(), 2.0)
        pose = tl.pose(0.5)
        self.assertAlmostEqual(pose["a"], 0.5)
        self.assertAlmostEqual(pose["b"], 2.0)


class TestCalques(unittest.TestCase):
    def test_vers_vue_convention(self):
        W = H = 100
        tx, ty = 0.5, 0.25
        pts = np.array([[50.0, 50.0], [0.0, 0.0], [0.0, 100.0]])
        v = CA.vers_vue(pts, np.array([4.0, 4.0, 4.0]), W, H, (tx, ty))
        np.testing.assert_allclose(v[0], [0.0, 0.0, -4.0], atol=1e-12)
        np.testing.assert_allclose(v[1], [-tx * 4, ty * 4, -4.0], atol=1e-12)   # haut-gauche : y vue > 0
        np.testing.assert_allclose(v[2], [-tx * 4, -ty * 4, -4.0], atol=1e-12)  # bas-gauche : y vue < 0

    def test_repos_inchange(self):
        _, sq = construire_personnage()
        c = CA.construire("carre", _carre(), squelette=sq, cellule=8.0)
        s = c.sommets({}, T.tan_fov(64, 64))
        np.testing.assert_allclose(s["px"], c.P, atol=1e-9)
        np.testing.assert_allclose(s["normales"], c.n_repos, atol=1e-9)

    def test_profondeur_du_plateau(self):
        c = CA.construire("carre", _carre(plan=5.0, relief_max=0.2), cellule=4.0)
        s = c.sommets({}, T.tan_fov(64, 64))
        interieur = (c.P[:, 0] > 26) & (c.P[:, 0] < 38) & (c.P[:, 1] > 26) & (c.P[:, 1] < 38)
        self.assertTrue(interieur.any())
        np.testing.assert_allclose(-s["vue"][interieur, 2], 5.0 - 0.2, atol=1e-9)

    def test_triangles_valides(self):
        c = CA.construire("disque", _disque_calque(), cellule=4.0)
        self.assertEqual(c.triangles.shape[1], 3)
        self.assertLess(int(c.triangles.max()), len(c.P))
        self.assertTrue(np.all(c.uv >= 0.0) and np.all(c.uv <= 1.0))
        self.assertTrue(np.all(np.linalg.norm(c.n_repos, axis=1) > 0.99))

    def test_calque_vide_refuse(self):
        rgba = np.zeros((16, 16, 4), np.float32)
        with self.assertRaises(ValueError):
            CA.construire("vide", RL.Calque(rgba))

    def test_normales_tournent_avec_l_os(self):
        """Un disque tourné autour de son centre : la normale de chaque sommet tourne comme ses positions."""
        sq = Squelette([Os("a", (31.5, 31.5), bout=(31.5, 31.5), sigma=1000.0)])
        c = CA.construire("disque", _disque_calque(), squelette=sq, cellule=4.0)
        theta = 0.6
        s = c.sommets({"a": theta}, T.tan_fov(64, 64))
        n0 = c.n_repos
        attendu_xy = np.stack([n0[:, 0], -n0[:, 1]], axis=1)
        attendu_xy = np.stack([np.cos(theta) * attendu_xy[:, 0] - np.sin(theta) * attendu_xy[:, 1],
                               np.sin(theta) * attendu_xy[:, 0] + np.cos(theta) * attendu_xy[:, 1]], axis=1)
        attendu = np.stack([attendu_xy[:, 0], -attendu_xy[:, 1], n0[:, 2]], axis=1)
        np.testing.assert_allclose(s["normales"], attendu, atol=1e-6)
        np.testing.assert_allclose(np.linalg.norm(s["normales"], axis=1), 1.0, atol=1e-9)

    def test_ffd_seule_sur_les_yeux(self):
        """Le clignement déforme la grille FFD ; sans cle_ffd dans la pose, la grille est sans effet."""
        g = GrilleFFD((0.0, 0.0, 64.0, 64.0), nx=3, ny=3)
        c = CA.construire("yeux", _carre(), ffd=g, cle_ffd="cligne", cellule=8.0)
        ouvert = c.sommets({"cligne": 0.0}, T.tan_fov(64, 64))["px"]
        ferme = c.sommets({"cligne": 1.0}, T.tan_fov(64, 64))["px"]
        np.testing.assert_allclose(ouvert, c.P, atol=1e-9)
        np.testing.assert_allclose(ferme[:, 1], 32.0, atol=1e-9)

    def test_tri_par_profondeur(self):
        proche = CA.construire("proche", _carre(plan=4.0), ordre=0, cellule=8.0)
        loin = CA.construire("loin", _carre(plan=6.0), ordre=1, cellule=8.0)
        sommets = {c.nom: c.sommets({}, T.tan_fov(64, 64)) for c in (proche, loin)}
        ordre = [c.nom for c in CA.trier_par_profondeur([proche, loin], sommets)]
        self.assertEqual(ordre, ["loin", "proche"])          # le plus loin dessiné en premier

    def test_tri_egalite_par_ordre(self):
        a = CA.construire("a", _carre(plan=5.0), ordre=2, cellule=8.0)
        b = CA.construire("b", _carre(plan=5.0), ordre=1, cellule=8.0)
        sommets = {c.nom: c.sommets({}, T.tan_fov(64, 64)) for c in (a, b)}
        ordre = [c.nom for c in CA.trier_par_profondeur([a, b], sommets)]
        self.assertEqual(ordre, ["b", "a"])

    def test_noms_en_double_refuses_au_tri(self):
        a = CA.construire("a", _carre(), cellule=8.0)
        with self.assertRaises(ValueError):
            CA.trier_par_profondeur([a, a], {"a": a.sommets({}, T.tan_fov(64, 64))})

    def test_corps_ne_suit_que_son_os(self):
        """Régression : incliner la tête ne doit pas déformer le corps (ses bords se courbaient)."""
        calques, _ = construire_personnage(cellule=8.0)
        corps = [c for c in calques if c.nom == "corps"][0]
        s = corps.sommets({"tete": 0.5, "meche": 0.3}, T.tan_fov(corps.largeur, corps.hauteur))
        np.testing.assert_allclose(s["px"], corps.P, atol=1e-9)

    def test_tete_bouge_le_visage_mais_pas_la_base_du_corps(self):
        calques, _ = construire_personnage(cellule=8.0)
        visage = [c for c in calques if c.nom == "visage"][0]
        s = visage.sommets({"tete": 0.3}, T.tan_fov(visage.largeur, visage.hauteur))
        self.assertGreater(float(np.abs(s["px"] - visage.P).max()), 5.0)

    def test_personnage_de_demo_pose_neutre_inchangee(self):
        calques, sq = construire_personnage(cellule=8.0)
        self.assertEqual(len(calques), 5)
        for c in calques:
            s = c.sommets({}, T.tan_fov(c.largeur, c.hauteur))
            np.testing.assert_allclose(s["px"], c.P, atol=1e-9, err_msg=c.nom)
        tl = timeline()
        for c in calques:
            s = c.sommets(tl.pose(0.46), T.tan_fov(c.largeur, c.hauteur))
            self.assertTrue(np.all(np.isfinite(s["vue"])), c.nom)


class TestMaillageDynamique(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ctx = creer_contexte()
        if cls.ctx is None:
            raise unittest.SkipTest("pas de contexte OpenGL 3.3 disponible")
        cls.rendu = RenduNPR(cls.ctx, 64, 64)

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "rendu"):
            cls.rendu.liberer()

    def _maillage(self, n=4):
        rng = np.random.default_rng(3)
        sommets = rng.normal(size=(n, 3)).astype(np.float32)
        normales = np.tile([0.0, 0.0, 1.0], (n, 1)).astype(np.float32)
        uv = rng.uniform(size=(n, 2)).astype(np.float32)
        tangentes = np.tile([1.0, 0.0, 0.0], (n, 1)).astype(np.float32)
        tri = np.array([[0, 1, 2], [1, 2, 3]], np.uint32)
        return Maillage(self.ctx, self.rendu.prog_geo, sommets, normales, uv, tangentes, tri), sommets

    def test_vbo_reecrit_sur_le_gpu(self):
        m, _ = self._maillage()
        nouveaux = np.arange(12, dtype=np.float32).reshape(4, 3)
        tangentes = np.tile([0.0, 1.0, 0.0], (4, 1)).astype(np.float32)
        avant = m.lire_sommets()
        m.mettre_a_jour(sommets=nouveaux, tangentes=tangentes)
        apres = m.lire_sommets()
        np.testing.assert_allclose(apres[:, 0:3], nouveaux)
        np.testing.assert_allclose(apres[:, 3:6], avant[:, 3:6])       # normales inchangées
        np.testing.assert_allclose(apres[:, 6:8], avant[:, 6:8])       # UV inchangés
        np.testing.assert_allclose(apres[:, 8:11], tangentes)
        m.vao.release()
        m.vbo.release()
        m.ibo.release()

    def test_forme_incorrecte_refusee(self):
        m, _ = self._maillage()
        with self.assertRaises(ValueError):
            m.mettre_a_jour(sommets=np.zeros((3, 3)))
        m.vao.release()
        m.vbo.release()
        m.ibo.release()


class TestCalquesGPU(unittest.TestCase):
    TAILLE = 64

    @classmethod
    def setUpClass(cls):
        cls.ctx = creer_contexte()
        if cls.ctx is None:
            raise unittest.SkipTest("pas de contexte OpenGL 3.3 disponible")

    def _rendu(self):
        return RenduNPR(self.ctx, self.TAILLE, self.TAILLE, ombrage=ParamsOmbrage(poids_sphere=0.0))

    def _dessiner(self, rendu, calques, pose=None):
        rendu.definir_masque_cheveux(np.ones((1, 1), np.float32))
        return rendu.dessiner_calques(calques, pose or {}, projection=T.projection(self.TAILLE, self.TAILLE),
                                      tan_fov=T.tan_fov(self.TAILLE, self.TAILLE),
                                      centre_tete_vue=T.CENTRE_VUE, lumiere_vue=T.LUMIERE_VUE,
                                      avant_tete_vue=T.AVANT_VUE)

    def test_profondeur_gpu_egale_au_compositeur(self):
        """Au plateau du relief, la profondeur du chemin articulé égale celle de relief.composer."""
        calque = _carre(self.TAILLE, bord=16, plan=5.0, relief_max=0.2)
        rendu = self._rendu()
        try:
            c = CA.construire("carre", calque, cellule=4.0)
            self._dessiner(rendu, [c])
            g = rendu.lire_gbuffer()
            ref = RL.composer([calque], self.TAILLE, self.TAILLE)
            plateau = ref["profondeur"] > 0
            interieur = np.zeros_like(plateau)
            interieur[24:-24, 24:-24] = True                 # loin du biseau (rayon 6 px)
            masque = plateau & interieur
            self.assertGreater(int(masque.sum()), 100)
            np.testing.assert_allclose(g["profondeur"][masque], ref["profondeur"][masque], atol=1e-4)
            np.testing.assert_allclose(g["normale"][masque], ref["normale"][masque], atol=1e-3)
        finally:
            rendu.liberer()
            rendu.liberer_calques()

    def test_couverture_gpu_egale_a_l_alpha(self):
        calque = _disque_calque(self.TAILLE, r=20)
        rendu = self._rendu()
        try:
            c = CA.construire("disque", calque, cellule=2.0)
            self._dessiner(rendu, [c])
            couverture = rendu.lire_gbuffer()["profondeur"][::-1] > 0       # ordre image
            alpha = calque.rgba[..., 3] >= RL.SEUIL_ALPHA
            desaccord = np.mean(couverture != alpha)
            self.assertLess(desaccord, 0.02)
        finally:
            rendu.liberer()
            rendu.liberer_calques()

    def test_rotation_gpu_coherente_avec_la_reference(self):
        """Un calque tourné d'un os : couverture GPU ≈ alpha tourné par cv2.warpAffine."""
        W = self.TAILLE
        calque = _disque_calque(W, r=18)
        alpha = calque.rgba[..., 3]
        centre = (W - 1) / 2
        sq = Squelette([Os("a", (centre, centre), bout=(centre, centre), sigma=1000.0)])
        theta = 0.5
        c_, s_ = np.cos(theta), np.sin(theta)
        M = np.array([[c_, -s_, centre - c_ * centre + s_ * centre],
                      [s_, c_, centre - s_ * centre - c_ * centre]], np.float32)
        attendu = cv2.warpAffine(alpha, M, (W, W), flags=cv2.INTER_NEAREST) >= RL.SEUIL_ALPHA
        rendu = self._rendu()
        try:
            c = CA.construire("disque", calque, squelette=sq, cellule=2.0)
            self._dessiner(rendu, [c], {"a": theta})
            couverture = rendu.lire_gbuffer()["profondeur"][::-1] > 0
            inter = np.logical_and(couverture, attendu).sum()
            union = np.logical_or(couverture, attendu).sum()
            self.assertGreater(inter / union, 0.9)
        finally:
            rendu.liberer()
            rendu.liberer_calques()

    def test_ordre_inverse_ne_change_pas_l_image(self):
        """Le z-buffer tranche : dessiner le premier plan d'abord donne le même G-buffer."""
        avant = CA.construire("avant", _carre(self.TAILLE, bord=8, plan=4.0, couleur=(1, 0, 0)), ordre=1, cellule=4.0)
        arriere = CA.construire("arriere", _carre(self.TAILLE, bord=4, plan=6.0, couleur=(0, 0, 1)), ordre=0, cellule=4.0)
        rendu = self._rendu()
        try:
            self._dessiner(rendu, [arriere, avant])
            normal = rendu.lire_gbuffer()
            with mock.patch("npr.rendu.trier_par_profondeur", side_effect=lambda cs, s: list(cs)[::-1]):
                self._dessiner(rendu, [arriere, avant])
            inverse = rendu.lire_gbuffer()
            np.testing.assert_allclose(inverse["profondeur"], normal["profondeur"], atol=1e-6)
            np.testing.assert_allclose(inverse["albedo"], normal["albedo"], atol=1e-6)
            # Au recouvrement, le premier plan (rouge) doit gagner.
            centre = self.TAILLE // 2
            np.testing.assert_allclose(normal["albedo"][centre, centre], [1, 0, 0], atol=1e-6)
        finally:
            rendu.liberer()
            rendu.liberer_calques()

    def test_tangente_nulle_hors_cheveux(self):
        """Le calque sans flux ne reçoit pas de tangente ; le calque de cheveux en reçoit (aucun NaN)."""
        W = self.TAILLE
        yy, xx = np.mgrid[0:W, 0:W].astype(np.float32)
        gauche = np.zeros((W, W, 4), np.float32)
        gauche[8:56, 4:28, :3] = (0.4, 0.2, 0.2)
        gauche[8:56, 4:28, 3] = 1.0
        droite = np.zeros((W, W, 4), np.float32)
        droite[8:56, 36:60, :3] = (0.2, 0.4, 0.2)
        droite[8:56, 36:60, 3] = 1.0
        flux = np.zeros((W, W, 2), np.float32)
        flux[..., 0] = 1.0                 # flux constant non nul : tangente (1, 0, 0) partout
        cheveux =CA.construire("cheveux", RL.Calque(gauche, plan=4.5, relief_max=0.1, rayon_biseau=5.0,
                                                     flux=flux, flou=0.0), cellule=2.0)
        corps = CA.construire("corps", RL.Calque(droite, plan=5.0, relief_max=0.1, rayon_biseau=5.0,
                                                 flou=0.0), cellule=2.0)
        rendu = self._rendu()
        try:
            self._dessiner(rendu, [cheveux, corps])
            g = rendu.lire_gbuffer()
            self.assertTrue(np.all(np.isfinite(g["tangente"])))
            norme = np.linalg.norm(g["tangente"], axis=-1)
            couvert_gauche = (g["profondeur"] > 0)[:, :32]
            couvert_droite = (g["profondeur"] > 0)[:, 32:]
            self.assertGreater(float(norme[:, :32][couvert_gauche].min()), 0.5)
            self.assertLess(float(norme[:, 32:][couvert_droite].max()), 1e-6)
        finally:
            rendu.liberer()
            rendu.liberer_calques()

    def test_cycles_creation_liberation_calques(self):
        personnage, _ = construire_personnage(cellule=16.0)
        tl = timeline()
        for _ in range(3):
            rendu = self._rendu()
            try:
                for t in (0.0, 0.46, 1.0):
                    rendu.definir_masque_cheveux(np.ones((1, 1), np.float32))
                    rendu.dessiner_calques(personnage, tl.pose(t), projection=T.projection(self.TAILLE, self.TAILLE),
                                           tan_fov=T.tan_fov(self.TAILLE, self.TAILLE),
                                           centre_tete_vue=T.CENTRE_VUE, lumiere_vue=T.LUMIERE_VUE,
                                           avant_tete_vue=T.AVANT_VUE)
                image = rendu.image_finale()
                self.assertEqual(image.shape, (self.TAILLE, self.TAILLE, 4))
            finally:
                rendu.liberer()
        self.assertEqual(len(personnage), 5)


if __name__ == "__main__":
    unittest.main()

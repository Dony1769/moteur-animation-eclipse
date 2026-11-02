"""Tests du personnage réel : chargeur de calques et atlas, normales sous FFD, cheveux Verlet, vues multiples.

Les données de référence sont celles de Kaël (universes/eclipse_royale/characters/kael).
Les tests GPU sont ignorés (SkipTest) sans contexte OpenGL 3.3.
"""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "engine"))

from npr import calques_anim as CA  # noqa: E402
from npr import relief as RL  # noqa: E402
from npr import tete_test as T  # noqa: E402
from npr.chargeur import FORMAT, charger_vue, construire_atlas, premier_plan, rgba_couche  # noqa: E402
from npr.multivue import bascule, fondre, poids_vues  # noqa: E402
from npr.parametres import ParamsOmbrage  # noqa: E402
from npr.physique import ChevelureSimulee, forces_fictives  # noqa: E402
from npr.rig import GrilleFFD, Os, Squelette  # noqa: E402
from npr.rendu import RenduNPR, creer_contexte  # noqa: E402

KAEL = Path(HERE).parent / "universes" / "eclipse_royale" / "characters" / "kael"
FACE = KAEL / "parts_v2_face_g.json"
TROIS_QUARTS = KAEL / "parts_v2_trois_quarts_g.json"


def _rotation2(theta):
    c, s = np.cos(theta), np.sin(theta)
    return np.array([[c, -s], [s, c]])


class TestFFDLocale(unittest.TestCase):
    def test_marge_arrete_la_deformation(self):
        """Avec une marge, les points au-delà de la boîte + marge ne bougent pas ; ceux de la boîte bougent."""
        g = GrilleFFD((100.0, 100.0, 200.0, 200.0), nx=3, ny=3, marge=20.0)
        g.decalages[..., 0] = 10.0
        dedans = np.array([[150.0, 150.0]])
        loin = np.array([[260.0, 150.0]])          # 60 px hors de la boîte, marge = 20 px
        np.testing.assert_allclose(g.appliquer(dedans)[0, 0] - 150.0, 10.0, atol=1e-9)
        np.testing.assert_allclose(g.appliquer(loin)[0, 0], 260.0, atol=1e-12)

    def test_marge_decroissance_douce(self):
        g = GrilleFFD((100.0, 100.0, 200.0, 200.0), nx=3, ny=3, marge=20.0)
        g.decalages[..., 0] = 10.0
        # Bord droit à x = 200, marge 20 : les points 205, 210, 215 sont dans la zone de décroissance.
        x = np.array([205.0, 210.0, 215.0])
        a = g.appliquer(np.stack([x, np.full(3, 150.0)], axis=1))[:, 0] - x
        self.assertTrue(10.0 > a[0] > a[1] > a[2] > 0.0)


class _Mouvement:
    """Mouvement scripté : pose(t) -> {nom: angle}."""

    def __init__(self, fonction):
        self.fonction = fonction

    def pose(self, t):
        return self.fonction(t)


class TestChargeur(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.face = charger_vue(FACE)
        cls.trois = charger_vue(TROIS_QUARTS)

    def test_couches_kael(self):
        self.assertEqual(self.face.nom, "face_g")
        self.assertEqual([c.id for c in self.face.couches],
                         ["cape_arriere", "jambe_g", "jambe_d", "tunique", "bras_g", "bras_d", "tete", "col_cape"])
        ordres = [c.ordre for c in self.face.couches]
        self.assertEqual(ordres, sorted(ordres))
        self.assertEqual((self.face.largeur, self.face.hauteur), (856, 900))
        for c in self.face.couches:
            self.assertTrue(c.masque.any(), c.id)

    def test_masque_exclut_le_fond(self):
        fond = ~premier_plan(self.face.reference)
        for c in self.face.couches:
            self.assertFalse((c.masque & fond).any(), c.id)

    def test_boites_dans_la_vue(self):
        """La boîte de chaque masque reste dans la vue ; la tête occupe le haut de l'image."""
        for c in self.face.couches:
            x0, y0, x1, y1 = c.boite
            self.assertTrue(0 <= x0 < x1 <= self.face.largeur and 0 <= y0 < y1 <= self.face.hauteur, c.id)
        x0, y0, x1, y1 = self.face.couche("tete").boite
        self.assertLess(y0, 60)         # le haut de la tête (sommet du crâne) est en haut de l'image
        self.assertTrue(150 < y1 < 200)  # le menton, au-dessus du col

    def test_points_du_squelette(self):
        for nom in ("bassin", "cou", "tete_haut"):
            self.assertIn(nom, self.face.points)

    def test_format_inconnu_refuse(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "v.json"
            p.write_text(json.dumps({"format": "autre/1"}), encoding="utf-8")
            with self.assertRaises(ValueError):
                charger_vue(p)

    def test_couche_hors_personnage_refusee(self):
        """Un polygone hors du personnage donne un masque vide : erreur explicite."""
        with tempfile.TemporaryDirectory() as d:
            dossier = Path(d)
            (dossier / "ref.png").write_bytes((KAEL / "vues" / "face_g.png").read_bytes())
            squelette = json.loads((KAEL / "squelette" / "face_g.json").read_text(encoding="utf-8"))
            (dossier / "sq.json").write_text(json.dumps(squelette), encoding="utf-8")
            donnees = {"format": FORMAT, "vue": "test", "reference": "ref.png", "squelette": "sq.json",
                       "couches": [{"id": "loin", "ordre": 0, "poly": [[-100, -100], [-50, -100], [-50, -50]]}]}
            (dossier / "v.json").write_text(json.dumps(donnees), encoding="utf-8")
            with self.assertRaises(ValueError):
                charger_vue(dossier / "v.json")

    def test_poly_et_polys_ensemble_refuses(self):
        with tempfile.TemporaryDirectory() as d:
            dossier = Path(d)
            (dossier / "ref.png").write_bytes((KAEL / "vues" / "face_g.png").read_bytes())
            (dossier / "sq.json").write_text(
                (KAEL / "squelette" / "face_g.json").read_text(encoding="utf-8"), encoding="utf-8")
            donnees = {"format": FORMAT, "reference": "ref.png", "squelette": "sq.json",
                       "couches": [{"id": "x", "ordre": 0, "poly": [[0, 0], [9, 0], [9, 9]],
                                    "polys": [[[0, 0], [9, 0], [9, 9]]]}]}
            (dossier / "v.json").write_text(json.dumps(donnees), encoding="utf-8")
            with self.assertRaises(ValueError):
                charger_vue(dossier / "v.json")

    def test_atlas_rectangles_disjoints_et_dans_la_texture(self):
        atlas = construire_atlas(self.face)
        rects = []
        for c in self.face.couches:
            u0, v0, u1, v1 = atlas.rectangle_uv(c.id)
            self.assertTrue(0.0 <= u0 < u1 <= 1.0 and 0.0 <= v0 < v1 <= 1.0, c.id)
            rects.append((atlas.emplacements[c.id].x, atlas.emplacements[c.id].y,
                          atlas.emplacements[c.id].x + atlas.emplacements[c.id].l,
                          atlas.emplacements[c.id].y + atlas.emplacements[c.id].h))
        for i, a in enumerate(rects):
            for b in rects[i + 1:]:
                disjoint = a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1]
                self.assertTrue(disjoint, (a, b))

    def test_echantillon_atlas_egal_au_sprite(self):
        """Pour des points intérieurs au masque, la texture à l'UV donne la couleur de la référence."""
        atlas = construire_atlas(self.face)
        rng = np.random.default_rng(0)
        for nom in ("tete", "tunique", "cape_arriere"):
            c = self.face.couche(nom)
            ys, xs = np.nonzero(c.masque)
            pick = rng.choice(len(xs), size=min(200, len(xs)), replace=False)
            P = np.stack([xs[pick] + 0.5, ys[pick] + 0.5], axis=1)
            uv = atlas.uv(nom, P)
            A_H, A_W = atlas.image.shape[:2]
            cols = np.floor(uv[:, 0] * A_W).astype(int)
            rows = np.floor(uv[:, 1] * A_H).astype(int)
            texel = atlas.image[rows, cols]
            ref = self.face.reference[P[:, 1].astype(int), P[:, 0].astype(int)]
            np.testing.assert_allclose(texel[:, :3], ref, atol=1e-6, err_msg=nom)
            np.testing.assert_allclose(texel[:, 3], 1.0, atol=1e-6, err_msg=nom)

    def test_alpha_atlas_egal_au_masque(self):
        """Un texel de l'atlas est opaque exactement là où le masque est vrai."""
        atlas = construire_atlas(self.face)
        c = self.face.couche("tete")
        e = atlas.emplacements["tete"]
        bloc = atlas.image[e.y:e.y + e.h, e.x:e.x + e.l, 3]
        np.testing.assert_array_equal(bloc > 0.5, c.masque[c.boite[1]:c.boite[3], c.boite[0]:c.boite[2]])

    def test_vue_trois_quarts_chargee(self):
        self.assertEqual(self.trois.nom, "trois_quarts_g")
        self.assertIn("tete", [c.id for c in self.trois.couches])

    def test_rgba_couche_alpha_masque(self):
        c = self.face.couche("tete")
        rgba = rgba_couche(self.face, c)
        np.testing.assert_array_equal(rgba[..., 3] > 0.5, c.masque)
        np.testing.assert_allclose(rgba[..., :3], self.face.reference, atol=1e-7)


class TestNormalesFFD(unittest.TestCase):
    def test_jacobienne_identite_au_repos(self):
        P = np.array([[0.0, 0.0], [4.0, 0.0], [0.0, 4.0], [4.0, 4.0]])
        tri = np.array([[0, 1, 2], [1, 3, 2]])
        J = CA.jacobiennes(P, P, tri)
        np.testing.assert_allclose(J, np.broadcast_to(np.eye(2), J.shape), atol=1e-12)

    def test_jacobienne_mise_a_l_echelle(self):
        P = np.array([[0.0, 0.0], [4.0, 0.0], [0.0, 4.0], [4.0, 4.0]])
        tri = np.array([[0, 1, 2], [1, 3, 2]])
        Q = P * np.array([2.0, 1.0])
        J = CA.jacobiennes(P, Q, tri)
        np.testing.assert_allclose(J, np.broadcast_to(np.diag([2.0, 1.0]), J.shape), atol=1e-12)

    def test_jacobienne_triangle_degenere_ignore(self):
        P = np.array([[0.0, 0.0], [4.0, 0.0], [8.0, 0.0], [0.0, 4.0]])   # trois points alignés
        tri = np.array([[0, 1, 2], [0, 1, 3]])
        Q = P * np.array([3.0, 1.0])
        J = CA.jacobiennes(P, Q, tri)
        self.assertTrue(np.all(np.isfinite(J)))
        np.testing.assert_allclose(J[3], np.diag([3.0, 1.0]), atol=1e-12)   # sommet 3 ne tient que du triangle sain

    def test_pente_lineaire_sous_mise_a_l_echelle(self):
        """h = a·x, étirée en x de s : la normale devient (-a/s, 0, 1) normalisée."""
        a, s = 0.5, 2.0
        n = np.array([[-a, 0.0, 1.0]]) / np.hypot(a, 1.0)
        t = np.zeros((1, 3))
        J = np.array([[[s, 0.0], [0.0, 1.0]]])
        out, _ = CA.pousser_normales(n, t, J)
        attendu = np.array([-a / s, 0.0, 1.0]) / np.hypot(a / s, 1.0)
        np.testing.assert_allclose(out[0], attendu, atol=1e-6)

    def test_normale_egale_a_la_derivee_numerique(self):
        """Surface h déformée par une application affine : la normale poussée égale celle de H' = h∘F^-1.

        Référence indépendante : gradient de H' par différences finies (pas de formule de pousse).
        """
        A = np.array([[1.3, 0.4], [-0.2, 0.8]])
        b = np.array([3.0, -2.0])
        Ainv = np.linalg.inv(A)

        def h(x, y):
            return 0.02 * x * x + 0.01 * x * y + 0.5 * y

        def H_def(xp, yp):
            p = Ainv @ (np.stack([xp, yp]) - b[:, None])      # (2, N), vectorisé
            return h(p[0], p[1])

        rng = np.random.default_rng(3)
        P = rng.uniform(-10, 10, size=(40, 2))
        # Normale au repos, convention relief.normales : n = (-∂h/∂x, +∂h/∂y_image, 1) normalisée.
        eps = 1e-6
        dhx = (h(P[:, 0] + eps, P[:, 1]) - h(P[:, 0] - eps, P[:, 1])) / (2 * eps)
        dhy = (h(P[:, 0], P[:, 1] + eps) - h(P[:, 0], P[:, 1] - eps)) / (2 * eps)
        n_rest = np.stack([-dhx, dhy, np.ones(len(P))], axis=1)
        n_rest /= np.linalg.norm(n_rest, axis=1, keepdims=True)
        t_rest = np.zeros((len(P), 3))
        J = np.broadcast_to(A, (len(P), 2, 2)).copy()
        out, _ = CA.pousser_normales(n_rest, t_rest, J)

        Q = P @ A.T + b
        dHx = (H_def(Q[:, 0] + eps, Q[:, 1]) - H_def(Q[:, 0] - eps, Q[:, 1])) / (2 * eps)
        dHy = (H_def(Q[:, 0], Q[:, 1] + eps) - H_def(Q[:, 0], Q[:, 1] - eps)) / (2 * eps)
        attendu = np.stack([-dHx, dHy, np.ones(len(P))], axis=1)
        attendu /= np.linalg.norm(attendu, axis=1, keepdims=True)
        np.testing.assert_allclose(out, attendu, atol=1e-5)

    def test_rotation_rigide_tourne_la_normale(self):
        """J = R(θ) : la normale image (nx, -ny, nz) tourne de R, retour en repère vue."""
        theta = 0.7
        n = np.array([[0.3, 0.4, 0.8660254]])
        n /= np.linalg.norm(n)
        R = _rotation2(theta)
        out, _ = CA.pousser_normales(n, np.zeros((1, 3)), R[None])
        img = np.array([n[0, 0], -n[0, 1]])
        tourne = R @ img
        attendu = np.array([tourne[0], -tourne[1], n[0, 2]])
        np.testing.assert_allclose(out[0], attendu / np.linalg.norm(attendu), atol=1e-6)

    def test_tangente_poussee_par_la_jacobienne(self):
        t = np.array([[0.6, 0.8, 0.0]])                     # vue ; repère image (0.6, -0.8)
        J = np.array([[[1.0, 0.0], [0.0, 2.0]]])
        _, tp = CA.pousser_normales(np.array([[0.0, 0.0, 1.0]]), t, J)
        # image : (0.6, -1.6) -> vue : (0.6, 1.6)
        attendu = np.array([0.6, 1.6, 0.0]) / np.hypot(0.6, 1.6)
        np.testing.assert_allclose(tp[0], attendu, atol=1e-6)

    def test_jacobienne_singuliere_repli_identite(self):
        n = np.array([[0.1, 0.2, 0.9746794]])
        out, _ = CA.pousser_normales(n, np.zeros((1, 3)), np.zeros((1, 2, 2)))
        np.testing.assert_allclose(out[0], n[0] / np.linalg.norm(n[0]), atol=1e-6)

    def test_ffd_clignement_change_les_normales_des_yeux(self):
        """Clignement FFD : les normales des paupières suivent le volume écrasé, sans recalcul au repos."""
        rgba = np.zeros((64, 64, 4), np.float32)
        yy, xx = np.mgrid[0:64, 0:64].astype(np.float32)
        rgba[..., :3] = (0.2, 0.2, 0.3)
        rgba[..., 3] = ((xx - 32) / 16) ** 2 + ((yy - 32) / 10) ** 2 <= 1.0
        calque = RL.Calque(rgba, plan=5.0, relief_max=0.4, rayon_biseau=8.0, flou=0.0)
        ffd = GrilleFFD((16, 22, 48, 42), nx=3, ny=3)
        c = CA.construire("yeux", calque, ffd=ffd, cle_ffd="cligne", cellule=2.0)
        repos = c.sommets({"cligne": 0.0}, T.tan_fov(64, 64))
        ferme = c.sommets({"cligne": 0.9}, T.tan_fov(64, 64))
        np.testing.assert_allclose(repos["normales"], c.n_repos, atol=1e-6)
        self.assertFalse(np.allclose(ferme["normales"], c.n_repos, atol=1e-3))
        np.testing.assert_allclose(np.linalg.norm(ferme["normales"], axis=1), 1.0, atol=1e-6)
        self.assertTrue(np.all(ferme["normales"][:, 2] > 0))
        # Vérifie l'écrasement réellement appliqué (sinon le test ne prouve rien).
        self.assertLess(np.ptp(ferme["px"][:, 1]), np.ptp(c.P[:, 1]))


class TestForcesFictives(unittest.TestCase):
    def test_centrifuge_vers_l_exterieur(self):
        f = forces_fictives(np.array([[10.0, 0.0]]), np.zeros((1, 2)), 1.0, 0.0)
        np.testing.assert_allclose(f[0], [10.0, 0.0], atol=1e-12)

    def test_euler_signe(self):
        f = forces_fictives(np.array([[0.0, 10.0]]), np.zeros((1, 2)), 0.0, 1.0)
        np.testing.assert_allclose(f[0], [10.0, 0.0], atol=1e-12)

    def test_coriolis(self):
        f = forces_fictives(np.zeros((1, 2)), np.array([[1.0, 0.0]]), 1.0, 0.0)
        np.testing.assert_allclose(f[0], [0.0, -2.0], atol=1e-12)


def _squelette_cheveux():
    """Os tête : pivot au-dessus de la grille, la chevelure pend vers le bas (y croissant)."""
    return Squelette([Os("tete", pivot=(250.0, 200.0), bout=(250.0, 300.0), sigma=60.0)])


class TestPhysique(unittest.TestCase):
    def _grille(self):
        return GrilleFFD((200.0, 300.0, 300.0, 400.0), nx=4, ny=5, marge=60.0)

    def test_racine_epinglee_reste_au_repos(self):
        g = self._grille()
        s = ChevelureSimulee(g, _squelette_cheveux(), "tete",
                             _Mouvement(lambda t: {"tete": 0.4 * np.sin(6 * t)}), epingle_ligne=0)
        s.avancer(0.6)
        np.testing.assert_array_equal(g.decalages[0], np.zeros((g.nx, 2)))

    def test_longueurs_conservees(self):
        g = self._grille()
        s = ChevelureSimulee(g, _squelette_cheveux(), "tete",
                             _Mouvement(lambda t: {"tete": 0.5 * np.sin(8 * t)}))
        s.avancer(1.0)
        self.assertLess(s.longueurs_relatives(), 0.01)

    def test_sans_mouvement_pas_de_glissement(self):
        """Chevelure pendante et inextensible : la gravité seule ne la déplace pas."""
        g = self._grille()
        s = ChevelureSimulee(g, _squelette_cheveux(), "tete", _Mouvement(lambda t: {}))
        s.avancer(1.0)
        self.assertLess(np.abs(g.decalages).max(), 0.05)

    def test_inertie_tete_decalage_oppose_au_mouvement(self):
        """Rotation accélérée de la tête (α > 0) : la rangée basse prend un retard en +x (sens opposé)."""
        g = self._grille()
        alpha = 20.0
        s = ChevelureSimulee(g, _squelette_cheveux(), "tete",
                             _Mouvement(lambda t: {"tete": 0.5 * alpha * t * t}))
        s.avancer(0.3)
        bas = g.decalages[-1]
        self.assertGreater(bas[:, 0].mean(), 0.5)          # retard en +x, mesuré en pixels

    def test_translation_du_pivot_par_un_parent(self):
        """Un parent qui tourne à vitesse constante fait accélérer le pivot : a = ω²·rayon, vers le centre."""
        sq = Squelette([Os("corps", pivot=(250.0, 0.0), sigma=60.0),
                        Os("tete", pivot=(250.0, 200.0), parent=0, sigma=60.0)])
        g = self._grille()
        omega = 2.0
        s = ChevelureSimulee(g, sq, "tete", _Mouvement(lambda t: {"corps": omega * t}))
        _, _, _, a_piv = s.mouvement_au(0.3)
        self.assertAlmostEqual(np.linalg.norm(a_piv), omega * omega * 200.0, delta=0.02 * omega * omega * 200.0)

    def test_decalages_alimentent_la_ffd(self):
        g = self._grille()
        s = ChevelureSimulee(g, _squelette_cheveux(), "tete",
                             _Mouvement(lambda t: {"tete": 0.3 * np.sin(5 * t)}))
        s.avancer(0.5)
        deplace = g.appliquer(g.repos.reshape(-1, 2))
        self.assertGreater(np.abs(deplace - g.repos.reshape(-1, 2)).max(), 0.1)
        np.testing.assert_allclose(g.decalages.reshape(-1, 2), s.P - s.repos, atol=1e-12)

    def test_retour_arriere_refuse(self):
        s = ChevelureSimulee(self._grille(), _squelette_cheveux(), "tete", _Mouvement(lambda t: {}))
        s.avancer(0.5)
        with self.assertRaises(ValueError):
            s.avancer(0.2)

    def test_parametres_refuses(self):
        g = self._grille()
        sq = _squelette_cheveux()
        m = _Mouvement(lambda t: {})
        with self.assertRaises(ValueError):
            ChevelureSimulee(g, sq, "absent", m)
        with self.assertRaises(ValueError):
            ChevelureSimulee(g, sq, "tete", m, epingle_ligne=9)
        with self.assertRaises(ValueError):
            ChevelureSimulee(g, sq, "tete", m, amortissement=0.0)


class TestMultivue(unittest.TestCase):
    VUES = {0.0: "face", 45.0: "trois_quarts"}

    def test_fondu_entre_deux_vues(self):
        poids, hors = poids_vues(22.5, self.VUES)
        self.assertFalse(hors)
        self.assertEqual(sorted(poids), sorted([("face", 0.5), ("trois_quarts", 0.5)]))

    def test_bornes_sans_fondu(self):
        self.assertEqual(poids_vues(-10.0, self.VUES), ([("face", 1.0)], False))
        self.assertEqual(poids_vues(45.0, self.VUES), ([("trois_quarts", 1.0)], False))

    def test_profil_hors_plage_signale(self):
        poids, hors = poids_vues(90.0, self.VUES)
        self.assertEqual(poids, [("trois_quarts", 1.0)])
        self.assertTrue(hors)

    def test_poids_sommes_a_un(self):
        for a in np.linspace(0, 60, 13):
            poids, _ = poids_vues(a, self.VUES)
            self.assertAlmostEqual(sum(w for _, w in poids), 1.0, places=12)

    def test_fondre_lineaire(self):
        images = {"a": np.zeros((2, 2, 3)), "b": np.ones((2, 2, 3))}
        out = fondre(images, [("a", 0.25), ("b", 0.75)])
        np.testing.assert_allclose(out, 0.75, atol=1e-6)

    def test_fondre_poids_non_normalises_refuses(self):
        with self.assertRaises(ValueError):
            fondre({"a": np.zeros((2, 2))}, [("a", 0.5)])

    def test_bascule_prend_le_poids_max(self):
        images = {"a": np.zeros((2, 2)), "b": np.ones((2, 2))}
        np.testing.assert_allclose(bascule(images, [("a", 0.2), ("b", 0.8)]), 1.0)


class TestPersonnageGPU(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ctx = creer_contexte()
        if cls.ctx is None:
            raise unittest.SkipTest("pas de contexte OpenGL 3.3 disponible")

    def test_atlas_partage_une_seule_texture(self):
        """Tous les calques d'un même atlas partagent une seule texture GPU."""
        import npr.demo_personnage as DP
        vue = charger_vue(FACE)
        calques, atlas = DP.construire_vue(vue, cellule=24.0)
        rendu = RenduNPR(self.ctx, vue.largeur, vue.hauteur, ombrage=ParamsOmbrage(poids_sphere=0.0))
        try:
            rendu.definir_masque_cheveux(np.ones((1, 1), np.float32))
            rendu.dessiner_calques(calques[:3], {}, projection=T.projection(vue.largeur, vue.hauteur),
                                   tan_fov=T.tan_fov(vue.largeur, vue.hauteur), centre_tete_vue=T.CENTRE_VUE,
                                   lumiere_vue=T.LUMIERE_VUE, avant_tete_vue=T.AVANT_VUE)
            textures = {id(rendu._calques_gpu[c.nom][1]) for c in calques[:3]}
            self.assertEqual(len(textures), 1)
            self.assertEqual(len(rendu._textures_partagees), 1)
        finally:
            rendu.liberer()
        self.assertEqual(rendu._calques_gpu, {})


if __name__ == "__main__":
    unittest.main()


class TestBasculeNette(unittest.TestCase):
    """Bascule de sprites au seuil d'angle, et transition FFD courte (multivue.py)."""
    VUES = {0.0: "face", 45.0: "trois_quarts"}

    def test_pas_de_fondu(self):
        from npr.multivue import vue_nette
        for a in np.linspace(0, 45, 19):
            nom, _ = vue_nette(a, self.VUES)
            self.assertIn(nom, ("face", "trois_quarts"))

    def test_seuil_au_point_median(self):
        from npr.multivue import vue_nette
        self.assertEqual(vue_nette(22.0, self.VUES), ("face", False))
        self.assertEqual(vue_nette(23.0, self.VUES), ("trois_quarts", False))

    def test_profil_hors_plage(self):
        from npr.multivue import vue_nette
        nom, hors = vue_nette(90.0, self.VUES)
        self.assertEqual(nom, "trois_quarts")
        self.assertTrue(hors)

    def test_transition_nulle_aux_bornes(self):
        from npr.multivue import decalage_transition
        self.assertAlmostEqual(decalage_transition(0.0, 6.0), 0.0, places=12)
        self.assertAlmostEqual(decalage_transition(1.0, 6.0), 0.0, places=12)
        self.assertAlmostEqual(decalage_transition(0.5, 6.0), 6.0, places=12)

    def test_transition_bornee_par_l_amplitude(self):
        from npr.multivue import appliquer_transition
        g = GrilleFFD((0.0, 0.0, 100.0, 200.0), nx=3, ny=4)
        for s in np.linspace(0, 1, 11):
            appliquer_transition([g], s, 5.0)
            self.assertLessEqual(np.abs(g.decalages).max(), 5.0 + 1e-9)

    def test_transition_cisaille_du_haut_vers_le_bas(self):
        from npr.multivue import appliquer_transition
        g = GrilleFFD((0.0, 0.0, 100.0, 200.0), nx=3, ny=4)
        appliquer_transition([g], 0.5, 5.0)
        self.assertAlmostEqual(g.decalages[0, 0, 0], -5.0, places=9)   # haut
        self.assertAlmostEqual(g.decalages[-1, 0, 0], 5.0, places=9)   # bas
        self.assertTrue(np.allclose(g.decalages[..., 1], 0.0))

    def test_transition_phase_invalide_refusee(self):
        from npr.multivue import decalage_transition
        with self.assertRaises(ValueError):
            decalage_transition(1.5, 5.0)


class TestRampesTeintees(unittest.TestCase):
    """Rampes toon chaude (peau) et froide (vêtements sombres), choisies par un masque matériau."""

    def test_rampes_extremes(self):
        from npr import rampe as R
        c = R.rampe_chaude()
        f = R.rampe_froide()
        self.assertEqual(c.shape, (256, 3))
        self.assertEqual(f.shape, (256, 3))
        np.testing.assert_array_equal(c[0], np.round(np.array(R.COULEURS_CHAUDES[0]) * 255).astype(np.uint8))
        np.testing.assert_array_equal(f[0], np.round(np.array(R.COULEURS_FROIDES[0]) * 255).astype(np.uint8))

    def test_ombre_chaude_et_froide(self):
        from npr import rampe as R
        c = R.rampe_chaude()[0].astype(int)
        f = R.rampe_froide()[0].astype(int)
        self.assertGreater(c[0] - c[2], 0)    # chaude : rouge > bleu dans l'ombre
        self.assertGreater(f[2] - f[0], 0)    # froide : bleu > rouge dans l'ombre

    def test_masque_materiau_change_la_teinte_gpu(self):
        ctx = creer_contexte()
        if ctx is None:
            raise unittest.SkipTest("pas de contexte OpenGL 3.3 disponible")
        from npr import rampe as R
        taille = 64
        rgba = np.zeros((taille, taille, 4), np.float32)
        yy, xx = np.mgrid[0:taille, 0:taille].astype(np.float32)
        disque = ((xx - 31.5) ** 2 + (yy - 31.5) ** 2) <= 22 ** 2
        rgba[..., :3] = 1.0                       # albédo blanc : la couleur vient de la rampe
        rgba[..., 3] = disque
        calque = RL.Calque(rgba, plan=5.0, relief_max=0.3, rayon_biseau=10.0, flou=0.0)
        calques = [CA.construire("disque", calque, cellule=2.0)]
        mesures = {}
        for nom, masque in (("chaud", np.zeros((taille, taille), np.float32)),
                            ("froid", np.ones((taille, taille), np.float32))):
            rendu = RenduNPR(ctx, taille, taille, ombrage=ParamsOmbrage(poids_sphere=0.0),
                             rampe_froide_u8=R.rampe_froide())
            try:
                rendu.definir_materiaux(masque)
                rendu.dessiner_calques(calques, {}, projection=T.projection(taille, taille),
                                       tan_fov=T.tan_fov(taille, taille), centre_tete_vue=T.CENTRE_VUE,
                                       lumiere_vue=T.LUMIERE_VUE, avant_tete_vue=T.AVANT_VUE)
                img = rendu.image_finale()[..., :3].astype(float)
            finally:
                rendu.liberer()
            centre = img[20:44, 20:44]           # intérieur du disque, loin du contour
            mesures[nom] = float(np.mean(centre[..., 2] - centre[..., 0]))
        self.assertGreater(mesures["froid"], mesures["chaud"] + 20.0)   # en valeurs 0..255

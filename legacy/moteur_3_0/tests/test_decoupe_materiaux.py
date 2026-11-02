"""Tests de la découpe par matériaux (engine/npr/decoupe_materiaux.py), sans GPU."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "engine"))

from npr import decoupe_materiaux as DM  # noqa: E402

BLANC = np.ones(3, np.float32)
PEAU = np.array([0.90, 0.70, 0.60], np.float32)
SOMBRE = np.array([0.05, 0.05, 0.05], np.float32)
GRIS = np.array([0.70, 0.70, 0.70], np.float32)


def _image(zones, taille=40):
    """Image blanche avec des rectangles (x0, y0, x1, y1, couleur)."""
    rgb = np.ones((taille, taille, 3), np.float32)
    for x0, y0, x1, y1, c in zones:
        rgb[y0:y1, x0:x1] = c
    return rgb


class TestNommer:
    def test_couleurs_types(self):
        assert DM.nommer(PEAU) == "peau"
        assert DM.nommer(SOMBRE) == "sombre"
        assert DM.nommer(GRIS) == "fourrure"

    def test_brun_rouge_est_cuir(self):
        assert DM.nommer((0.55, 0.30, 0.20)) == "cuir"


class TestCombler:
    def test_trou_rempli_par_voisin(self):
        carte = np.array([[1, 1, 1], [1, -1, 1], [1, 1, 1]], np.int32)
        masque = np.ones((3, 3), bool)
        out = DM._combler_trous(carte, masque)
        assert (out == 1).all()

    def test_hors_masque_reste_vide(self):
        carte = np.array([[1, -1, 2]], np.int32)
        masque = np.array([[True, False, True]])
        out = DM._combler_trous(carte, masque)
        assert out[0, 1] == -1

    def test_voisin_dans_bords_sans_repliement(self):
        a = np.arange(9, dtype=np.int32).reshape(3, 3)
        droite = DM._voisin_dans(a, 0, 1)
        assert (droite[:, -1] == -1).all()
        assert droite[0, 0] == a[0, 1]


class TestDecouper:
    def test_partition_sans_trou(self):
        # Damier de deux couleurs : l'ouverture 3x3 retire beaucoup de pixels ; la carte doit
        # pourtant couvrir tout le personnage, sans trou transparent.
        rgb = np.ones((40, 40, 3), np.float32)
        for y in range(8, 32):
            for x in range(8, 32):
                rgb[y, x] = PEAU if (x + y) % 2 == 0 else SOMBRE
        vue = DM.decouper(rgb, (0, 0, 40, 40), {}, k=2)
        masque = DM.premier_plan_region(rgb, (0, 0, 40, 40))
        union = np.zeros_like(masque)
        somme = np.zeros(masque.shape, int)
        for c in vue.couches:
            union |= c.masque
            somme += c.masque.astype(int)
        assert (union == masque).all()
        assert somme.max() <= 1

    def test_couches_nommees_et_triees(self):
        rgb = _image([(5, 5, 20, 20, PEAU), (22, 5, 35, 20, SOMBRE), (5, 22, 35, 35, GRIS)])
        vue = DM.decouper(rgb, (0, 0, 40, 40), {}, k=3)
        assert len(vue.couches) >= 3
        ordres = [c.ordre for c in vue.couches]
        assert ordres == sorted(ordres)
        noms = {DM.materiau_de(c).nom for c in vue.couches}
        assert {"peau", "sombre", "fourrure"} <= noms

    def test_materiau_froid_pour_vetement_sombre(self):
        rgb = _image([(5, 5, 35, 35, SOMBRE)])
        vue = DM.decouper(rgb, (0, 0, 40, 40), {}, k=2)
        froids = [DM.materiau_de(c).froid for c in vue.couches]
        assert any(froids)

    def test_petit_groupe_fusionne_sans_trou(self):
        # Un pixel isolé d'une autre couleur dans une zone peau : il ne doit pas créer de trou.
        rgb = _image([(5, 5, 35, 35, PEAU)])
        rgb[20, 20] = SOMBRE
        vue = DM.decouper(rgb, (0, 0, 40, 40), {}, k=2)
        masque = DM.premier_plan_region(rgb, (0, 0, 40, 40))
        union = np.zeros_like(masque)
        for c in vue.couches:
            union |= c.masque
        assert (union == masque).all()

    def test_reflet_clair_interne_reste_dans_le_personnage(self):
        # Un petit reflet blanc enfermé dans une zone sombre fait partie du personnage : il doit être
        # couvert par une couche (sinon le fond transparaît au rendu).
        rgb = _image([(5, 5, 35, 35, SOMBRE)])
        rgb[15:18, 15:18] = BLANC
        masque = DM.premier_plan_region(rgb, (0, 0, 40, 40))
        assert masque[16, 16]
        vue = DM.decouper(rgb, (0, 0, 40, 40), {}, k=2)
        union = np.zeros_like(masque)
        for c in vue.couches:
            union |= c.masque
        assert union[16, 16]

    def test_grande_zone_claire_enfermee_reste_du_fond(self):
        # Une zone claire de 64 px dans une boîte de 1600 px (4 %) n'est pas un reflet : elle reste du fond.
        rgb = _image([(5, 5, 35, 35, SOMBRE)])
        rgb[10:18, 10:18] = BLANC
        masque = DM.premier_plan_region(rgb, (0, 0, 40, 40))
        assert not masque[13, 13]

    def test_fond_relie_au_bord_non_rempli(self):
        rgb = _image([(10, 10, 30, 30, SOMBRE)])
        masque = DM.premier_plan_region(rgb, (0, 0, 40, 40))
        assert not masque[0, 0]
        assert not masque[5, 5]

    def test_trait_fin_separe_deux_zones_de_meme_couleur(self):
        # Deux zones de gris moyen, même couleur, séparées par un trait noir d'un pixel : aucune couche
        # ne doit couvrir les deux zones à la fois.
        gris = (0.25, 0.25, 0.25)
        rgb = _image([(5, 5, 19, 35, gris), (21, 5, 35, 35, gris), (19, 5, 21, 35, (0.02, 0.02, 0.02))])
        vue = DM.decouper(rgb, (0, 0, 40, 40), {}, k=2)
        gauche = np.zeros((40, 40), bool)
        gauche[5:35, 5:19] = True
        droite = np.zeros((40, 40), bool)
        droite[5:35, 21:35] = True
        assert not any((c.masque & gauche).any() and (c.masque & droite).any() for c in vue.couches)
        assert sum(bool((c.masque & gauche).any()) for c in vue.couches) >= 1
        assert sum(bool((c.masque & droite).any()) for c in vue.couches) >= 1

    def test_grande_zone_sombre_reste_une_couche(self):
        rgb = _image([(5, 5, 35, 35, SOMBRE)])
        vue = DM.decouper(rgb, (0, 0, 40, 40), {}, k=2)
        sombres = [c for c in vue.couches if DM.materiau_de(c).nom == "sombre"]
        assert len(sombres) == 1

    def test_lignes_encre_ne_retient_que_le_trait_fin(self):
        rgb = _image([(5, 5, 35, 35, (0.25, 0.25, 0.25))])
        rgb[:, 20] = 0.02                         # trait vertical d'un pixel
        masque = np.ones((40, 40), bool)
        traits = DM.lignes_encre(rgb, masque)
        assert traits[10:30, 20].all()
        assert not traits[10:30, 8:17].any()   # zone sombre large : pas de trait

    def test_image_sans_personnage_refusee(self):
        rgb = np.ones((10, 10, 3), np.float32)
        try:
            DM.decouper(rgb, (0, 0, 10, 10), {}, k=6)
        except ValueError:
            return
        raise AssertionError("une image vide doit être refusée")

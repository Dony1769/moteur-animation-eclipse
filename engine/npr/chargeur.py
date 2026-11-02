"""Chargeur de calques réels : un personnage découpé en couches -> calques RGBA et atlas de textures.

Lit le format « moteur-3.0/personnage-couches/2 » : un JSON par vue, à côté de l'illustration de
référence et du squelette à points-clés. Chaque couche porte un identifiant, un ordre de dessin,
un ou plusieurs polygones (pixels image), une chaîne d'os et un drapeau d'ombre.

- Masque d'une couche = polygone ∩ premier plan. Le premier plan exclut le fond presque blanc
  (canaux tous supérieurs ou égaux à SEUIL_FOND). Le fichier de données note que les contours
  peuvent déborder : le masque est donc une aide, pas une découpe parfaite.
- Les couleurs viennent de la référence : chaque calque garde les pixels d'origine.
- Atlas : les sprites utiles (boîte englobante du masque, marge transparente) sont rangés par
  rangées dans une seule texture. Chaque couche a un rectangle dans l'atlas et une correspondance
  coordonnées image -> UV, exacte au pixel près avec un échantillonnage NEAREST.

Pur numpy + cv2 (lecture PNG et remplissage de polygones), sans GPU.
"""
import json
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

FORMAT = "moteur-3.0/personnage-couches/2"
SEUIL_FOND = 245          # pixel de fond : tous les canaux >= 245 (fond blanc de l'illustration)
MARGE_ATLAS = 2           # pixels transparents autour de chaque sprite (évite les débordements)
LARGEUR_ATLAS = 1024      # largeur fixe de l'atlas, en pixels


@dataclass(frozen=True)
class Couche:
    id: str
    ordre: int
    masque: np.ndarray            # (H, W) bool, polygone ∩ premier plan
    chaine: tuple                 # os ou points-clés qui pilotent la couche
    ombre: bool

    @property
    def boite(self):
        """(x0, y0, x1, y1) entiers, x1 et y1 exclus : boîte englobante du masque."""
        ys, xs = np.nonzero(self.masque)
        return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1

    @property
    def dimensions(self):
        """(largeur, hauteur) du sprite utile, en pixels de la vue."""
        x0, y0, x1, y1 = self.boite
        return x1 - x0, y1 - y0


@dataclass
class Vue:
    nom: str
    reference: np.ndarray         # (H, W, 3) float 0..1
    couches: list                 # [Couche], triées par ordre de dessin croissant
    points: dict                  # {nom: (x, y)} : points-clés du squelette
    fiabilite: dict = field(default_factory=dict)

    @property
    def largeur(self):
        return self.reference.shape[1]

    @property
    def hauteur(self):
        return self.reference.shape[0]

    def couche(self, id_):
        for c in self.couches:
            if c.id == id_:
                return c
        raise KeyError(f"couche inconnue : {id_}")


def _masque_polygones(polygones, forme):
    m = np.zeros(forme, np.uint8)
    for poly in polygones:
        pts = np.round(np.asarray(poly, np.float64)).astype(np.int32)
        cv2.fillPoly(m, [pts], 1)
    return m.astype(bool)


def premier_plan(reference):
    """Masque (H, W) bool : vrai là où le pixel n'est pas le fond blanc."""
    fond = reference.min(axis=2) * 255.0 >= SEUIL_FOND
    return ~fond


def charger_vue(json_path):
    """Lit une vue au format couches/2. Erreur explicite si le format, les polygones ou l'image manquent."""
    json_path = Path(json_path)
    donnees = json.loads(json_path.read_text(encoding="utf-8"))
    if donnees.get("format") != FORMAT:
        raise ValueError(f"format inattendu : {donnees.get('format')!r} (attendu {FORMAT!r})")
    dossier = json_path.parent
    image = cv2.imread(str(dossier / donnees["reference"]), cv2.IMREAD_COLOR)
    if image is None:
        raise FileNotFoundError(dossier / donnees["reference"])
    reference = cv2.cvtColor(image, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    forme = reference.shape[:2]
    fond = premier_plan(reference)

    squelette = json.loads((dossier / donnees["squelette"]).read_text(encoding="utf-8"))
    points = {k: (float(v["x"]), float(v["y"])) for k, v in squelette.items()}
    fiabilite = {k: float(v.get("fiabilite", 1.0)) for k, v in squelette.items()}

    couches = []
    for c in donnees["couches"]:
        if "poly" in c and "polys" in c:
            raise ValueError(f"couche {c.get('id')} : « poly » et « polys » à la fois")
        polygones = [c["poly"]] if "poly" in c else c.get("polys")
        if not polygones:
            raise ValueError(f"couche {c.get('id')} sans polygone")
        masque = _masque_polygones(polygones, forme) & fond
        if not masque.any():
            raise ValueError(f"couche {c.get('id')} vide après découpe (polygone hors du personnage ?)")
        couches.append(Couche(id=c["id"], ordre=int(c["ordre"]), masque=masque,
                              chaine=tuple(c.get("chaine", ())), ombre=bool(c.get("ombre", False))))
    couches.sort(key=lambda c: c.ordre)
    ids = [c.id for c in couches]
    if len(set(ids)) != len(ids):
        raise ValueError("identifiants de couches en double")
    return Vue(nom=donnees.get("vue", json_path.stem), reference=reference, couches=couches,
               points=points, fiabilite=fiabilite)


def rgba_couche(vue, couche):
    """RGBA plein cadre (H, W, 4) float : couleurs de la référence, alpha = masque."""
    H, W = vue.hauteur, vue.largeur
    rgba = np.zeros((H, W, 4), np.float32)
    rgba[..., :3] = vue.reference
    rgba[..., 3] = couche.masque.astype(np.float32)
    return rgba


@dataclass(frozen=True)
class Emplacement:
    x: int                 # coin haut-gauche du sprite dans l'atlas (pixels, marge incluse)
    y: int
    l: int                 # dimensions du sprite utile
    h: int
    origine: tuple         # (bx0, by0) : coin du sprite dans la vue


class Atlas:
    """Texture RGBA unique, rangement en rangées, correspondance image -> UV par couche."""

    def __init__(self, image, emplacements):
        self.image = image                         # (A_H, A_W, 4) float32
        self.emplacements = dict(emplacements)     # {nom: Emplacement}

    @property
    def largeur(self):
        return self.image.shape[1]

    @property
    def hauteur(self):
        return self.image.shape[0]

    def dimensions(self, nom):
        e = self.emplacements[nom]
        return e.l, e.h

    def rectangle_uv(self, nom):
        """(u0, v0, u1, v1) du sprite utile, normalisés dans l'atlas."""
        e = self.emplacements[nom]
        return (e.x / self.largeur, e.y / self.hauteur,
                (e.x + e.l) / self.largeur, (e.y + e.h) / self.hauteur)

    def uv(self, nom, points):
        """Coordonnées UV (N, 2) des points image (N, 2) d'une couche. Linéaire, sans arrondi."""
        e = self.emplacements[nom]
        P = np.asarray(points, np.float64)
        u = (e.x + (P[:, 0] - e.origine[0])) / self.largeur
        v = (e.y + (P[:, 1] - e.origine[1])) / self.hauteur
        return np.stack([u, v], axis=1)


def construire_atlas(vue, couches=None):
    """Atlas de toutes les couches (ou d'une liste de couches) de la vue."""
    couches = list(vue.couches if couches is None else couches)
    if not couches:
        raise ValueError("atlas sans couche")
    tailles = {}
    for c in couches:
        l, h = c.dimensions
        if l + 2 * MARGE_ATLAS > LARGEUR_ATLAS:
            raise ValueError(f"couche {c.id} plus large que l'atlas ({l} px)")
        tailles[c.id] = (l + 2 * MARGE_ATLAS, h + 2 * MARGE_ATLAS)

    # Rangées : sprites les plus hauts d'abord, remplissage gauche -> droite.
    ordre = sorted(couches, key=lambda c: -tailles[c.id][1])
    emplacements = {}
    x = y = rangee_h = 0
    for c in ordre:
        w, h = tailles[c.id]
        if x + w > LARGEUR_ATLAS:
            y += rangee_h
            x = rangee_h = 0
        emplacements[c.id] = (x, y)
        x += w
        rangee_h = max(rangee_h, h)
    hauteur = y + rangee_h
    image = np.zeros((hauteur, LARGEUR_ATLAS, 4), np.float32)

    final = {}
    for c in couches:
        x0, y0, x1, y1 = c.boite
        ex, ey = emplacements[c.id]
        ox, oy = ex + MARGE_ATLAS, ey + MARGE_ATLAS
        ref_rgb = vue.reference[y0:y1, x0:x1]
        m = c.masque[y0:y1, x0:x1].astype(np.float32)
        image[oy:oy + (y1 - y0), ox:ox + (x1 - x0), :3] = ref_rgb
        image[oy:oy + (y1 - y0), ox:ox + (x1 - x0), 3] = m
        final[c.id] = Emplacement(x=ox, y=oy, l=x1 - x0, h=y1 - y0, origine=(x0, y0))
    return Atlas(image, final)

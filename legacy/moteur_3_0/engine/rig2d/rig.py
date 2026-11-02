"""Rig 2.5D v3 : couches de dessin déformées par des chaînes d'os, avec volume dessiné.

Principe :
- Chaque couche est un ou plusieurs polygones tracés sur une vue (jambe + botte ensemble, etc.).
- Une couche liée à une chaîne d'os (ex. hanche -> genou -> cheville -> orteil) se déforme ainsi :
  chaque articulation tourne le morceau situé après elle, avec un poids qui monte de 0 à son
  articulation jusqu'à 1 à l'articulation suivante. Le morceau ne se découpe pas, il se plie.
- Le volume est calculé sur le dessin lui-même : la distance au bord de chaque couche donne une
  forme gonflée (« gonflement »), la lumière d'en haut à gauche donne une zone éclairée et une
  zone d'ombre en deux tons (cel shading). Cette ombre est déformée avec la couche.
- Les couches sont dilatées de 1 px pour qu'aucun joint blanc n'apparaisse entre deux morceaux.

Usage : python3 engine/rig2d/rig.py <parts.json> <dossier_sortie> [repos|marche_3q|respiration]
"""
import json
import math
import os
import sys

import cv2
import numpy as np

MARGE = 48          # marge autour de la boîte d'une couche pour les déplacements
RAYON_VOLUME = 38.0  # épaisseur apparente (px) au-delà de laquelle une couche est « pleine »
LUMIERE = np.array([-0.45, -0.55, 0.70], np.float32)
LUMIERE /= np.linalg.norm(LUMIERE)


def _polygones(couche):
    if "polys" in couche:
        return couche["polys"]
    return [couche["poly"]]


class Rig:
    def __init__(self, chemin_parts, chemin_image=None, sans_volume=False):
        dossier = os.path.dirname(os.path.abspath(chemin_parts))
        cfg = json.load(open(chemin_parts, encoding="utf-8"))
        self.articulations = {}
        if "squelette" in cfg:
            sq = json.load(open(os.path.join(dossier, cfg["squelette"]), encoding="utf-8"))
            self.articulations = {k: (v["x"], v["y"]) for k, v in sq.items()}
        for k, v in cfg.get("articulations", {}).items():
            self.articulations.setdefault(k, tuple(v))
        image = chemin_image or os.path.join(dossier, cfg["reference"])
        bgr = cv2.imread(image)
        self.h, self.w = bgr.shape[:2]
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB).astype(np.float32)
        premier_plan = (bgr < 240).any(axis=2).astype(np.float32)
        self.couches = []
        for c in sorted(cfg["couches"], key=lambda c: c["ordre"]):
            masque = np.zeros((self.h, self.w), np.uint8)
            for poly in _polygones(c):
                cv2.fillPoly(masque, [np.array(poly, np.int32)], 255)
            masque = cv2.dilate(masque, np.ones((3, 3), np.uint8))  # pas de joint blanc entre morceaux
            alpha = cv2.GaussianBlur((masque / 255.0).astype(np.float32) * premier_plan, (3, 3), 0.7)
            ys, xs = np.where(alpha > 0.01)
            x0, x1 = max(xs.min() - MARGE, 0), min(xs.max() + MARGE + 1, self.w)
            y0, y1 = max(ys.min() - MARGE, 0), min(ys.max() + MARGE + 1, self.h)
            rgba = np.dstack([rgb[y0:y1, x0:x1], alpha[y0:y1, x0:x1] * 255.0]).astype(np.float32)
            gx, gy = np.meshgrid(np.arange(x0, x1, dtype=np.float32), np.arange(y0, y1, dtype=np.float32))
            ombre = np.ones(rgba.shape[:2], np.float32)
            if c.get("ombre", True) and not sans_volume:
                ombre = self._ombre(rgba[..., 3] / 255.0)
            self.couches.append({"id": c["id"], "rgba": rgba, "ombre": ombre, "box": (x0, y0, x1, y1),
                                 "gx": gx, "gy": gy, "chaine": c.get("chaine", [])})
        self._precalculer_poids()

    # ----- volume -----
    @staticmethod
    def _ombre(alpha):
        """Multiplicateur d'ombre en deux tons, déduit d'une forme gonflée de la silhouette."""
        masque = (alpha > 0.5).astype(np.uint8)
        dist = cv2.distanceTransform(masque, cv2.DIST_L2, 5).astype(np.float32)
        hauteur = np.sqrt(np.clip(dist / RAYON_VOLUME, 0, 1))
        hauteur = cv2.GaussianBlur(hauteur, (0, 0), 2.0)
        gx = cv2.Sobel(hauteur, cv2.CV_32F, 1, 0, ksize=3) / 8.0
        gy = cv2.Sobel(hauteur, cv2.CV_32F, 0, 1, ksize=3) / 8.0
        nx, ny, nz = -gx * 14.0, -gy * 14.0, np.ones_like(gx)
        norme = np.sqrt(nx * nx + ny * ny + nz * nz)
        lum = (nx * LUMIERE[0] + ny * LUMIERE[1] + nz * LUMIERE[2]) / norme
        # Deux tons : éclairé (1.0) / ombre (0.74), transition courte pour rester propre
        ombre = np.clip((lum - 0.30) / 0.08, 0, 1)
        return (0.60 + 0.40 * ombre).astype(np.float32)

    # ----- chaînes d'os -----
    def _rampe(self, couche, debut, fin):
        ux, uy = fin[0] - debut[0], fin[1] - debut[1]
        longueur = math.hypot(ux, uy)
        ux, uy = ux / longueur, uy / longueur
        t = ((couche["gx"] - debut[0]) * ux + (couche["gy"] - debut[1]) * uy) / longueur
        return np.clip(t, 0.0, 1.0).astype(np.float32)

    def _precalculer_poids(self):
        art = self.articulations
        for c in self.couches:
            liste = []
            ch = c["chaine"]
            for k in range(len(ch) - 1):
                joint, suivant = ch[k], ch[k + 1]
                liste.append((joint, art[joint], self._rampe(c, art[joint], art[suivant])))
            if c["id"] in ("tunique", "bras_d", "bras_g", "tete", "col_cape"):
                # Respiration : décalage vertical qui s'atténue vers le bas du tronc
                liste.append(("souffle", None, np.clip((490 - c["gy"]) / 40.0, 0, 1).astype(np.float32)))
            c["os"] = liste

    # ----- pose -----
    def pose(self, p):
        sortie = []
        for c in self.couches:
            dx = np.zeros(c["gx"].shape, np.float32)
            dy = np.zeros_like(dx)
            for nom, pivot, poids in c["os"]:
                if nom == "souffle":
                    dy += poids * p.get("souffle", 0.0)
                    continue
                ang = math.radians(p.get(nom, 0.0))
                if abs(ang) < 1e-9:
                    continue
                ca, sa = math.cos(ang) - 1.0, math.sin(ang)
                x = c["gx"] - pivot[0]
                y = c["gy"] - pivot[1]
                dx += poids * (ca * x - sa * y)
                dy += poids * (sa * x + ca * y)
            x0, y0 = c["box"][0], c["box"][1]
            mx = (c["gx"] - dx - x0).astype(np.float32)
            my = (c["gy"] - dy - y0).astype(np.float32)
            deforme = cv2.remap(c["rgba"], mx, my, cv2.INTER_LINEAR,
                                borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
            ombre = cv2.remap(c["ombre"], mx, my, cv2.INTER_LINEAR,
                              borderMode=cv2.BORDER_CONSTANT, borderValue=1.0)
            sortie.append({"id": c["id"], "rgba": deforme, "ombre": ombre, "box": c["box"]})
        return sortie

    # Ombre portée : la cape arrière projette une ombre vers le bas-droit sur le corps.
    OMBRE_SOURCE = "cape_arriere"
    OMBRE_RECEPTEURS = ("tunique", "bras_g", "bras_d", "jambe_g", "jambe_d", "col_cape")
    OMBRE_DECALAGE = (14.0, 18.0)
    OMBRE_FORCE = 0.30

    def _ombre_portee(self, couches_deformees):
        """Masque 0..1 (plein cadre) de l'ombre que la source projette, décalé et adouci."""
        src = next((c for c in couches_deformees if c["id"] == self.OMBRE_SOURCE), None)
        if src is None:
            return None
        plein = np.zeros((self.h, self.w), np.float32)
        x0, y0, x1, y1 = src["box"]
        plein[y0:y1, x0:x1] = src["rgba"][..., 3] / 255.0
        # La couche de cape contient aussi le corps : on ne garde que la cape visible hors du corps
        corps = np.zeros((self.h, self.w), np.float32)
        for c in couches_deformees:
            if c["id"] in self.OMBRE_RECEPTEURS:
                bx0, by0, bx1, by1 = c["box"]
                corps[by0:by1, bx0:bx1] = np.maximum(corps[by0:by1, bx0:bx1], c["rgba"][..., 3] / 255.0)
        plein = np.clip(plein - corps, 0.0, 1.0)
        dx, dy = self.OMBRE_DECALAGE
        m = np.float32([[1, 0, dx], [0, 1, dy]])
        decale = cv2.warpAffine(plein, m, (self.w, self.h), flags=cv2.INTER_LINEAR, borderValue=0)
        return cv2.GaussianBlur(decale, (0, 0), 5.0)

    def composer(self, couches_deformees, avec_ombre_portee=True):
        sortie = np.full((self.h, self.w, 3), 255.0, np.float32)
        ombre = self._ombre_portee(couches_deformees) if avec_ombre_portee else None
        for c in couches_deformees:
            x0, y0, x1, y1 = c["box"]
            zone = sortie[y0:y1, x0:x1]
            a = c["rgba"][..., 3:4] / 255.0
            couleur = c["rgba"][..., :3] * c["ombre"][..., None]
            if ombre is not None and c["id"] in self.OMBRE_RECEPTEURS:
                couleur = couleur * (1.0 - self.OMBRE_FORCE * ombre[y0:y1, x0:x1])[..., None]
            zone[:] = zone * (1 - a) + couleur * a
        return np.clip(sortie, 0, 255).astype(np.uint8)


def poses_repos(n=1):
    return [{} for _ in range(n)]


def poses_respiration(nb):
    poses = []
    for i in range(nb):
        th = 2 * math.pi * i / nb
        poses.append({"cape_haut": 1.6 * math.sin(th), "tete": 0.8 * math.sin(th), "souffle": -1.2 * math.sin(th)})
    return poses


def poses_marche_3q(nb, amplitude=12.0):
    """Cycle de marche de trois quarts (le personnage regarde vers la gauche de l'image).
    Angle positif = pied qui avance vers la gauche de l'écran."""
    poses = []
    for i in range(nb):
        th = 2 * math.pi * i / nb
        s = math.sin(th)
        poses.append({
            "cou": 0.5 * math.sin(2 * th), "tete": 0.5 * math.sin(2 * th), "souffle": -1.0 * math.sin(2 * th),
            "hanche_g": amplitude * s, "hanche_d": -amplitude * s,
            "genou_g": -9.0 * max(0.0, -s), "genou_d": -9.0 * max(0.0, s),
            "coude_g": -6.0 * max(0.0, s), "epaule_g": -0.5 * amplitude * s,
            "cape_haut": 2.5 * math.sin(th - 0.6) + 0.8 * math.sin(2 * th),
        })
    return poses


if __name__ == "__main__":
    parts, sortie = sys.argv[1], sys.argv[2]
    mode = sys.argv[3] if len(sys.argv) > 3 else "repos"
    os.makedirs(sortie, exist_ok=True)
    rig = Rig(parts)
    if mode == "repos":
        poses = poses_repos(1)
    elif mode == "respiration":
        poses = poses_respiration(48)
    else:
        poses = poses_marche_3q(48)
    for i, p in enumerate(poses):
        img = rig.composer(rig.pose(p))
        cv2.imwrite(os.path.join(sortie, "f%03d.png" % i), cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
    print(len(poses), "images ->", sortie)

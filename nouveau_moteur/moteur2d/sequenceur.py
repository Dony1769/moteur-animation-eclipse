"""Séquenceur et compositeur 2D.

Entrée : une scène JSON. Chaque plan est une suite de dessins tenus un nombre de frames donné, avec décalage,
zoom de caméra et effets. Sortie : une image RGB par frame, le masque du contenu et le drapeau de flash.

Toutes les couleurs de sortie sont des couleurs réelles des dessins fournis (palette prise dans ces dessins),
ou le blanc du fond. Les intermédiaires entre deux dessins ne sont jamais générés.
"""
import json
from pathlib import Path

import cv2
import numpy as np

from . import effets as E

FORMAT_SCENE = "moteur-animation/scene-2"
DESSINS = ("face", "trois_quarts")
EFFETS = ("flash_blanc", "secousse", "smear", "calque_trait")
BLANC = (255, 255, 255)


def charger_scene(chemin):
    s = json.loads(Path(chemin).read_text(encoding="utf-8"))
    if s.get("format") != FORMAT_SCENE:
        raise ValueError(f"format de scène inattendu : {s.get('format')!r}")
    fps = int(s["fps"])
    for plan in s["plans"]:
        total = sum(int(e["frames"]) for e in plan["sequence"])
        attendu = round(float(plan["duree_s"]) * fps)
        if total != attendu:
            raise ValueError(f"plan {plan['id']} : {total} frames, attendu {attendu}")
        for e in plan["sequence"]:
            if e["dessin"] not in DESSINS:
                raise ValueError(f"plan {plan['id']} : dessin inconnu {e['dessin']!r}")
            e.setdefault("decalage", [0, 0])
        for ef in plan.get("effets", []):
            if ef["type"] not in EFFETS:
                raise ValueError(f"effet inconnu : {ef['type']!r}")
            if ef["type"] == "calque_trait" and "fichier" not in ef:
                raise ValueError(f"plan {plan['id']} : calque_trait sans fichier")
        plan.setdefault("placeholder", False)
    return s


def _entree(plan, k):
    debut = 0
    for e in plan["sequence"]:
        if k < debut + int(e["frames"]):
            return e
        debut += int(e["frames"])
    raise IndexError(k)


def _actif(ef, k):
    if ef["type"] == "secousse":
        return ef["frame_debut"] <= k < ef["frame_debut"] + ef["duree"]
    a, b = ef["frames"]
    return a <= k <= b


def _charger_png(chemin):
    """PNG RGBA fourni par l'utilisateur : (rgb uint8 (H,W,3), alpha float (H,W))."""
    bgra = cv2.imread(str(chemin), cv2.IMREAD_UNCHANGED)
    if bgra is None:
        raise FileNotFoundError(chemin)
    if bgra.shape[2] != 4:
        raise ValueError(f"{chemin} : un PNG avec transparence est requis")
    rgb = cv2.cvtColor(bgra, cv2.COLOR_BGRA2RGB)
    alpha = bgra[..., 3].astype(np.float32) / 255.0
    return rgb, alpha


def couleurs_hors(images, sources):
    """Couleurs visibles qui ne viennent ni des dessins fournis ni du blanc. Doit être vide."""
    autorisees = {tuple(int(c) for c in s) for s in sources} | {BLANC}
    vues = set()
    for im in images:
        vues |= {tuple(int(c) for c in t) for t in np.unique(im.reshape(-1, 3), axis=0)}
    return vues - autorisees


class Sequenceur:
    def __init__(self, personnage, scene, racine):
        self.p = personnage
        self.s = scene
        self.racine = Path(racine)
        face = personnage.vues["face"]
        self.H, self.W = face.fg.shape
        self.tons = int(scene["palette"]["tons"]) if scene.get("palette", {}).get("actif") else 0
        self.traits = {}
        for plan in scene["plans"]:
            for ef in plan.get("effets", []):
                if ef["type"] == "calque_trait" and ef["fichier"] not in self.traits:
                    rgb, alpha = _charger_png(self.racine / ef["fichier"])
                    self.traits[ef["fichier"]] = (rgb, alpha)
        self.sources = self._couleurs_sources()
        self.palette = E.ajuster_palette(self._echantillon_pixels(), self.tons) if self.tons else None

    def _couleurs_sources(self):
        """Couleurs réelles des dessins : pixels du premier plan de chaque vue, et pixels des calques fournis."""
        morceaux = []
        for v in self.p.vues.values():
            rgb8 = np.round(v.rgb * 255).astype(np.uint8)
            morceaux.append(rgb8[v.fg])
        for rgb, alpha in self.traits.values():
            morceaux.append(rgb[alpha > 0])
        return E.couleurs_uniques(morceaux)

    def _echantillon_pixels(self, n=60000, graine=0):
        """Pixels réels des dessins, avec leur fréquence (pour que la palette suive ce qui se voit)."""
        morceaux = []
        for v in self.p.vues.values():
            morceaux.append(np.round(v.rgb * 255).astype(np.uint8)[v.fg])
        for rgb, alpha in self.traits.values():
            morceaux.append(rgb[alpha > 0])
        pile = np.concatenate(morceaux)
        rng = np.random.RandomState(graine)
        return pile[rng.choice(len(pile), size=min(n, len(pile)), replace=False)]

    def _ancre(self, plan):
        cam = plan.get("camera", {})
        if "centre_sur" in cam:
            return self.p.vues["face"].points[cam["centre_sur"]]
        return (self.W / 2.0, self.H / 2.0)

    def _plan(self, plan):
        cam = plan.get("camera", {})
        zoom = float(cam.get("zoom", 1.0))
        centre = self._ancre(plan)
        images, masques, flashs = [], [], []
        for k in range(int(round(float(plan["duree_s"]) * self.s["fps"]))):
            e = _entree(plan, k)
            calque = self.p.vues[e["dessin"]].premultiplie
            dx, dy = e["decalage"]
            calque = E.decalage(calque, dx, dy)
            if zoom != 1.0:
                calque = E.zoom(calque, zoom, centre)
            efs = plan.get("effets", [])
            for ef in efs:
                if ef["type"] == "smear" and _actif(ef, k):
                    calque = E.smear(calque, ef["direction"], ef["longueur_px"])
            flash = False
            for ef in efs:
                if ef["type"] == "flash_blanc" and _actif(ef, k):
                    calque[..., :3] = calque[..., 3:4]          # silhouette passée en blanc (alpha conservé)
                    flash = True
            fond = np.ones((self.H, self.W, 3), np.float32)
            sortie = calque[..., :3] + (1.0 - calque[..., 3:4]) * fond
            masque = calque[..., 3] > 0
            for ef in efs:
                if ef["type"] == "calque_trait" and _actif(ef, k):
                    rgb, alpha = self.traits[ef["fichier"]]
                    t = np.concatenate([rgb.astype(np.float32) / 255.0 * alpha[..., None], alpha[..., None]], axis=2)
                    sortie = t[..., :3] + (1.0 - t[..., 3:4]) * sortie
                    masque = masque | (alpha > 0)
            rgb8 = (np.clip(sortie, 0, 1) * 255 + 0.5).astype(np.uint8)
            for ef in efs:
                if ef["type"] == "secousse" and _actif(ef, k):
                    sx, sy = E.secousse(k - ef["frame_debut"], ef["amplitude_px"], ef["amortissement"])
                    rgb8 = E.decaler_image(rgb8, sx, sy)
                    masque = E.decalage(masque.astype(np.float32), sx, sy) > 0.5
            images.append(rgb8)
            masques.append(masque)
            flashs.append(flash)
        return images, masques, flashs

    def rendre(self):
        """(images, masques, flashs) pour toute la scène. Palette appliquée si demandée."""
        images, masques, flashs = [], [], []
        for plan in self.s["plans"]:
            im, ma, fl = self._plan(plan)
            images += im
            masques += ma
            flashs += fl
        if self.palette is not None:
            images = [E.quantifier(im, self.palette).astype(np.uint8) for im in images]
        return images, masques, flashs

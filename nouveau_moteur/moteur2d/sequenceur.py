"""Séquenceur et compositeur 2D.

Entrée : une scène JSON. Chaque plan est une suite de dessins, chacun tenu un nombre de frames donné,
avec décalage, zoom de caméra et effets. Sortie : une image RGB par frame, et le masque du contenu
(pour contrôler que rien d'autre que les dessins n'est visible).

Les intermédiaires entre deux dessins ne sont jamais générés : on passe d'un dessin au suivant.
"""
import json
from pathlib import Path

import numpy as np

from . import effets as E

FORMAT_SCENE = "moteur-animation/scene-2"
DESSINS = ("face", "trois_quarts")
EFFETS = ("flash_blanc", "secousse", "smear")


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
    return s


def _entree(plan, k):
    """(entrée de séquence, décalage) pour la frame k du plan."""
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


class Sequenceur:
    def __init__(self, personnage, scene):
        self.p = personnage
        self.s = scene
        face = personnage.vues["face"]
        self.H, self.W = face.fg.shape
        self.tons = int(scene["palette"]["tons"]) if scene.get("palette", {}).get("actif") else 0

    def _ancre(self, plan):
        cam = plan.get("camera", {})
        if "centre_sur" in cam:
            return self.p.vues["face"].points[cam["centre_sur"]]
        return (self.W / 2.0, self.H / 2.0)

    def _plan(self, plan):
        """Frames brutes (uint8) et masques de contenu (bool) d'un plan."""
        cam = plan.get("camera", {})
        zoom = float(cam.get("zoom", 1.0))
        centre = self._ancre(plan)
        images, masques = [], []
        for k in range(int(round(float(plan["duree_s"]) * self.s["fps"]))):
            e = _entree(plan, k)
            calque = self.p.vues[e["dessin"]].premultiplie
            dx, dy = e["decalage"]
            calque = E.decalage(calque, dx, dy)
            if zoom != 1.0:
                calque = E.zoom(calque, zoom, centre)
            for ef in plan.get("effets", []):
                if ef["type"] == "smear" and _actif(ef, k):
                    calque = E.smear(calque, ef["direction"], ef["longueur_px"])
            rgb = calque[..., :3] + (1.0 - calque[..., 3:4])     # composition sur fond blanc
            rgb = (np.clip(rgb, 0, 1) * 255 + 0.5).astype(np.uint8)
            masque = calque[..., 3] > 0.0
            flash = any(ef["type"] == "flash_blanc" and _actif(ef, k) for ef in plan.get("effets", []))
            for ef in plan.get("effets", []):
                if ef["type"] == "secousse" and _actif(ef, k):
                    sx, sy = E.secousse(k - ef["frame_debut"], ef["amplitude_px"], ef["amortissement"])
                    rgb = E.decaler_image(rgb, sx, sy)
                    masque = E.decalage(masque.astype(np.float32), sx, sy) > 0.5
            if flash:
                rgb = np.full_like(rgb, 255)
                masque = np.zeros_like(masque)                 # le flash n'est pas un dessin : exclu du contrôle
            images.append(rgb)
            masques.append(masque)
        return images, masques

    def rendre(self):
        """Renvoie (images, masques) pour toute la scène, palette appliquée si demandée."""
        images, masques = [], []
        for plan in self.s["plans"]:
            im, ma = self._plan(plan)
            images += im
            masques += ma
        if self.tons:
            centres = E.ajuster_palette(images[::max(1, len(images) // 12)], self.tons)
            images = [E.quantifier(im, centres) for im in images]
        return images, masques

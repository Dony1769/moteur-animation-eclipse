"""Chargement d'un personnage depuis characters/<nom>/ : rig.json, dessins, squelettes.

Chaque vue utilisée est un dessin fourni. Une vue déclarée absente (rig.json) ne peut pas être chargée.
La vue 3/4 est recalée sur la face par son articulation du cou (pivot tiré du rig).
"""
import json
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from .segmentation import garder_composante, premier_plan

FORMAT_RIG = "moteur-animation/rig-1"


@dataclass
class Vue:
    nom: str
    rgb: np.ndarray        # (H, W, 3) float 0..1, dessin tel quel
    fg: np.ndarray         # (H, W) bool, premier plan du dessin
    points: dict           # squelette {nom: (x, y)}
    pivot_tete: tuple      # articulation du cou dans ce dessin (x, y)

    @property
    def premultiplie(self):
        """(H, W, 4) float : couleurs multipliées par l'alpha (= le dessin, rien d'autre)."""
        a = self.fg.astype(np.float32)[..., None]
        return np.concatenate([self.rgb * a, a], axis=2)


@dataclass
class Personnage:
    nom: str
    vues: dict             # {'face': Vue, 'trois_quarts': Vue}
    translation_34: tuple  # décalage de recalage de la vue 3/4 sur la face (dx, dy)


def charger(dossier):
    d = Path(dossier)
    rig = json.loads((d / "rig.json").read_text(encoding="utf-8"))
    if rig.get("format") != FORMAT_RIG:
        raise ValueError(f"format de rig inattendu : {rig.get('format')!r}")
    pivots = rig["pivots"]["tete"]
    vues = {}
    for nom in ("face", "trois_quarts"):
        decl = rig["vues"][nom]
        if not decl["disponible"]:
            raise ValueError(f"vue {nom} déclarée absente dans rig.json")
        bgr = cv2.imread(str(d / decl["image"]), cv2.IMREAD_COLOR)
        if bgr is None:
            raise FileNotFoundError(d / decl["image"])
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        squelette = json.loads((d / decl["squelette"]).read_text(encoding="utf-8"))
        points = {k: (float(v["x"]), float(v["y"])) for k, v in squelette.items()}
        pivot = tuple(float(c) for c in pivots[nom])
        fg = garder_composante(premier_plan(rgb), pivot)
        vues[nom] = Vue(nom=nom, rgb=rgb, fg=fg, points=points, pivot_tete=pivot)
    f, t = vues["face"].pivot_tete, vues["trois_quarts"].pivot_tete
    translation = (f[0] - t[0], f[1] - t[1])
    return Personnage(nom=rig["personnage"], vues=vues, translation_34=translation)

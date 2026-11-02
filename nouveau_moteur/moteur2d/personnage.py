"""Chargement d'un personnage depuis characters/<nom>/ : rig.json, dessins fournis, squelettes.

Chaque vue utilisée est un dessin fourni. Une vue déclarée absente dans rig.json ne peut pas être chargée.
"""
import json
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from .segmentation import garder_composante, premier_plan

FORMAT_RIG = "moteur-animation/rig-2"


@dataclass
class Vue:
    nom: str
    rgb: np.ndarray        # (H, W, 3) float 0..1 : le dessin tel que fourni
    fg: np.ndarray         # (H, W) bool : premier plan du dessin
    points: dict           # squelette {nom: (x, y)}

    @property
    def premultiplie(self):
        """(H, W, 4) float : couleurs du dessin multipliées par l'alpha. Aucun pixel n'est ajouté."""
        a = self.fg.astype(np.float32)[..., None]
        return np.concatenate([self.rgb * a, a], axis=2)


@dataclass
class Personnage:
    nom: str
    vues: dict             # {'face': Vue, 'trois_quarts': Vue}


def charger(dossier):
    d = Path(dossier)
    rig = json.loads((d / "rig.json").read_text(encoding="utf-8"))
    if rig.get("format") != FORMAT_RIG:
        raise ValueError(f"format de rig inattendu : {rig.get('format')!r}")
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
        fg = garder_composante(premier_plan(rgb), points["cou"])
        vues[nom] = Vue(nom=nom, rgb=rgb, fg=fg, points=points)
    return Personnage(nom=rig["personnage"], vues=vues)

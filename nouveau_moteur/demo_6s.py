"""Démo 6 s : plan immobile, attaque (anticipation, impact, flash, secousse, traînée), plan de titre.

Usage : python3 demo_6s.py <dossier_sortie>
Sorties : frames PNG, demo_6s.mp4 (24 i/s), planche de contrôle des frames clés, metriques.json.
"""
import json
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from moteur2d import personnage as P  # noqa: E402
from moteur2d import sequenceur as S  # noqa: E402


def planche(images, indices, sortie, colonnes=4):
    lignes = []
    for i in range(0, len(indices), colonnes):
        rangee = [images[j] for j in indices[i:i + colonnes]]
        while len(rangee) < colonnes:
            rangee.append(np.full_like(images[0], 255))
        lignes.append(np.hstack(rangee))
    cv2.imwrite(str(sortie), cv2.cvtColor(np.vstack(lignes), cv2.COLOR_RGB2BGR))


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 1
    sortie = Path(argv[1])
    sortie.mkdir(parents=True, exist_ok=True)
    perso = P.charger(HERE / "characters" / "kael")
    scene = S.charger_scene(HERE / "scenes" / "demo_6s.json")
    images, masques = S.Sequenceur(perso, scene).rendre()

    for i, im in enumerate(images):
        cv2.imwrite(str(sortie / f"{i:03d}.png"), cv2.cvtColor(im, cv2.COLOR_RGB2BGR))
    video = sortie / "demo_6s.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(scene["fps"]),
                    "-i", str(sortie / "%03d.png"), "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    str(video)], check=True)
    planche(images, [0, 47, 48, 50, 51, 52, 53, 54, 60, 95, 120, 143], sortie / "planche_cles.png")

    # contrôle : hors des frames flash, le non-blanc ne doit pas dépasser le contenu des dessins
    hors = []
    for im, ma in zip(images, masques):
        if ma.sum() == 0:
            continue                                  # frame de flash
        zone = cv2.dilate(ma.astype(np.uint8), np.ones((9, 9), np.uint8)).astype(bool)
        non_blanc = im.min(axis=2) < 200
        if non_blanc.sum():
            hors.append(float((non_blanc & ~zone).sum() / non_blanc.sum()))
    tons = [len(np.unique(im.reshape(-1, 3), axis=0)) for im in images]
    metriques = {
        "frames": len(images),
        "duree_s": round(len(images) / scene["fps"], 3),
        "frames_flash": int(sum(1 for m in masques if m.sum() == 0)),
        "fraction_non_blanc_hors_dessins_max": round(max(hors), 5) if hors else 0.0,
        "tons_max_par_frame": int(max(tons)),
        "palette_tons": scene["palette"]["tons"],
    }
    (sortie / "metriques.json").write_text(json.dumps(metriques, indent=2), encoding="utf-8")
    print(json.dumps(metriques, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

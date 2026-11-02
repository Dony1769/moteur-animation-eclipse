"""Démo : rendu de l'action idle de Kaël (yaw de la tête 0 -> +45 -> 0, respiration, cape et cheveux).

Usage : python3 demo_idle.py <dossier_sortie>
Sorties : frames PNG, idle.mp4 (24 i/s, un dessin tenu 3 images), planche de contrôle, métriques.json.
"""
import json
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from moteur2d import action as A  # noqa: E402
from moteur2d import personnage as P  # noqa: E402
from moteur2d.rendu import Rendu  # noqa: E402


def controle(images, sortie):
    """Planche : 8 frames de l'idle, pour inspection visuelle."""
    choix = [0, 12, 24, 36, 48, 60, 72, 84]
    ligne1 = np.hstack([images[i] for i in choix[:4]])
    ligne2 = np.hstack([images[i] for i in choix[4:]])
    planche = np.vstack([ligne1, ligne2])
    cv2.imwrite(str(sortie), cv2.cvtColor(planche, cv2.COLOR_RGB2BGR))


def hors_dessins(image, zone_autorisee):
    """Fraction des pixels non blancs de l'image situés hors de la zone autorisée (dessins + marge)."""
    non_blanc = image.min(axis=2) < 245
    if non_blanc.sum() == 0:
        return 0.0
    return float((non_blanc & ~zone_autorisee).sum() / non_blanc.sum())


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 1
    sortie = Path(argv[1])
    sortie.mkdir(parents=True, exist_ok=True)
    perso = P.charger(HERE / "characters" / "kael")
    act = A.charger(HERE / "characters" / "kael" / "actions" / "idle.json")
    s = A.series(act)
    R = Rendu(perso, pas=24)

    zone = np.zeros((R.H, R.W), bool)
    for v in perso.vues.values():
        zone |= v.fg
    zone = cv2.dilate(zone.astype(np.uint8), np.ones((31, 31), np.uint8)).astype(bool)

    images = []
    for f in range(act["duree_frames"]):
        n = f // s["tenue"]
        img = R.image(t=s["yaw"][n] / 45.0, respiration=s["respiration"][n],
                      cape_px=s["cape"][n], cheveux_px=s["cheveux"][n])
        images.append(img)
        cv2.imwrite(str(sortie / f"{f:03d}.png"), cv2.cvtColor(img, cv2.COLOR_RGB2BGR))

    video = sortie / "idle.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", "24",
                    "-i", str(sortie / "%03d.png"), "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    str(video)], check=True)
    controle(images, sortie / "controle.png")

    hors = max(hors_dessins(im, zone) for im in images)
    metriques = {
        "frames": len(images),
        "fps": act["cadence"]["fps"],
        "dessins_par_seconde": act["cadence"]["dessins_par_seconde"],
        "yaw_max_deg": float(s["yaw"].max()),
        "fantome_iou_t50": round(R.fantome(0.5), 3),
        "fraction_pixels_hors_dessins_max": round(hors, 5),
        "amplitude_cape_px": round(float(np.abs(s["cape"]).max()), 2),
        "amplitude_cheveux_px": round(float(np.abs(s["cheveux"]).max()), 2),
    }
    (sortie / "metriques.json").write_text(json.dumps(metriques, indent=2), encoding="utf-8")
    print(json.dumps(metriques, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

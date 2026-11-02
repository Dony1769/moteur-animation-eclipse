"""Séquences de rotation 3D du buste proxy : balayage du yaw (±45°) et de l'inclinaison de tête (±0,4 rad).

Chaque balayage est monotone (pas de demi-tour). Mesures :
- scintillement : pixels sombres dont la luminance fait deux inversions rapides (sequence_kael.scintillement) ;
- régularité du mouvement : rapport entre la plus grande variation d'une image à l'autre et la médiane
  (un mouvement uniforme donne un rapport proche de 1 ; les à-coups le font grimper) ;
- validité : aucune valeur non finie.

Usage : python3 engine/npr/sequence_3d.py <dossier_sortie> [nombre_d_images]
Sorties : <dossier>/yaw.mp4, <dossier>/tete.mp4, <dossier>/metriques.json, images PNG dans des sous-dossiers.
"""
import json
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from npr import demo_buste3d as DB  # noqa: E402
from npr import rendu3d as R  # noqa: E402
from npr import sequence_kael as SQ  # noqa: E402
from npr.chargeur import charger_vue  # noqa: E402
from npr import demo_personnage as DP  # noqa: E402
from npr.encre import ParamsEncre  # noqa: E402
from npr.rendu import creer_contexte  # noqa: E402

FPS = 12
YAW_MAX = np.pi / 4


def balayages(n):
    """(nom, [(yaw, pose)]) : yaw monotone de -45° à +45°, puis tête de +0,4 à -0,4 rad."""
    yaw = np.linspace(-YAW_MAX, YAW_MAX, n)
    tilt = np.linspace(0.4, -0.4, n)
    return [("yaw", [(float(y), None) for y in yaw]),
            ("tete", [(0.0, DB.pose_tete(float(t))) for t in tilt])]


def regularite(lums):
    """Plus grande variation d'une image à l'autre, rapportée à la médiane de ces variations."""
    var = np.abs(np.diff(lums, axis=0)).mean(axis=(1, 2))
    med = float(np.median(var))
    return float(var.max() / med) if med > 1e-9 else float("inf")


def encoder(dossier, sortie):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS),
                    "-i", str(dossier / "%03d.png"), "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    str(sortie)], check=True)


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 1
    sortie = Path(argv[1])
    n = int(argv[2]) if len(argv) > 2 else 25
    sortie.mkdir(parents=True, exist_ok=True)
    ctx = creer_contexte()
    if ctx is None:
        print("Aucun contexte OpenGL disponible.")
        return 1
    print("OpenGL :", ctx.info["GL_RENDERER"])
    vue = charger_vue(DP.KAEL / DP.FICHIERS[0.0])
    tex = DB.texture_kael(vue)
    modele, sq = DB.charger_buste()
    av = R.Avatar3D(ctx, modele, sq, 360, 480, texture_rgba=tex, encre=ParamsEncre())
    resultats = {}
    try:
        for nom, etapes in balayages(n):
            dossier = sortie / nom
            dossier.mkdir(parents=True, exist_ok=True)
            images = []
            for i, (yaw, pose) in enumerate(etapes):
                img = av.rendre(pose, yaw)
                cv2.imwrite(str(dossier / f"{i:03d}.png"), cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
                images.append(SQ.luminance(img))
            lums = np.stack(images)
            resultats[nom] = {
                "images": len(images),
                "valeurs_non_finies": int((~np.isfinite(lums)).sum()),
                "scintillement": SQ.mesurer(lums),
                "regularite": round(regularite(lums), 3),
            }
            encoder(dossier, sortie / f"{nom}.mp4")
            print(nom, resultats[nom])
    finally:
        av.liberer()
    (sortie / "metriques.json").write_text(json.dumps(resultats, indent=2, ensure_ascii=False))
    print("séquences :", sortie)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

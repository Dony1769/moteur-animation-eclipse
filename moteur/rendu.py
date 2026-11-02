"""Point d'entrée : rend une scène en MP4.

Usage (via tools/rendre.sh) :
    blender -b --factory-startup --disable-autoexec -P moteur/rendu.py -- SORTIE_DIR [--duree S]
Le script écrit les images PNG puis appelle FFmpeg pour le MP4.
"""
import argparse
import subprocess
import sys
from pathlib import Path

import bpy  # noqa: E402  (disponible uniquement dans Blender)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from moteur import config, scene  # noqa: E402


def _args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("sortie")
    p.add_argument("--duree", type=float, default=4.0)
    return p.parse_args(argv)


def main():
    a = _args()
    rendu = config.Rendu(duree_s=a.duree)
    sortie = Path(a.sortie)
    sortie.mkdir(parents=True, exist_ok=True)
    sc = scene.reinitialiser()
    scene.configurer(sc, rendu)
    scene.ajouter_camera(sc)
    sc.render.filepath = str(sortie / "img_")
    bpy.ops.render.render(animation=True)
    images = sorted(sortie.glob("img_*.png"))
    if len(images) != rendu.nb_images:
        raise RuntimeError(f"{len(images)} images rendues, {rendu.nb_images} attendues")
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-framerate", str(rendu.fps),
        "-i", str(sortie / "img_%04d.png"), "-c:v", "libx264", "-pix_fmt", "yuv420p",
        str(sortie / "scene.mp4"),
    ], check=True)
    print("MP4 :", sortie / "scene.mp4")


if __name__ == "__main__":
    main()

"""Rend la scène de 4 secondes en MP4 (exécuté dans Blender).

Usage : tools/rendre_4s.sh SORTIE [--image N] [--samples S] [--res LxH]
  --image N : rend seulement l'image N (test rapide)
"""
import argparse
import subprocess
import sys
import time
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from moteur import scene4s  # noqa: E402


def _args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("sortie")
    p.add_argument("--image", type=int, default=0)
    p.add_argument("--samples", type=int, default=4)
    p.add_argument("--res", default="960x540")
    return p.parse_args(argv)


def main():
    a = _args()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    lx, ly = (int(v) for v in a.res.split("x"))
    corps, arm, cam = scene4s.construire(sc)
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = a.samples
    sc.render.resolution_x, sc.render.resolution_y = lx, ly
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGB"
    sc.view_settings.view_transform = "Standard"
    sc.render.film_transparent = False
    monde = bpy.data.worlds.new("Monde")
    monde.use_nodes = True
    monde.node_tree.nodes["Background"].inputs[0].default_value = (1.0, 1.0, 1.0, 1.0)
    sc.world = monde
    sortie = Path(a.sortie)
    sortie.mkdir(parents=True, exist_ok=True)
    if a.image:
        sc.frame_set(a.image)
        sc.render.filepath = str(sortie / f"image_{a.image:03d}.png")
        t = time.time()
        bpy.ops.render.render(write_still=True)
        print("TEMPS_IMAGE_S", round(time.time() - t, 2))
        return
    sc.render.filepath = str(sortie / "img_")
    t = time.time()
    bpy.ops.render.render(animation=True)
    print("TEMPS_TOTAL_S", round(time.time() - t, 1))
    images = sorted(sortie.glob("img_*.png"))
    if len(images) != scene4s.NB_IMAGES:
        raise RuntimeError(f"{len(images)} images, {scene4s.NB_IMAGES} attendues")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(scene4s.FPS),
                    "-i", str(sortie / "img_%04d.png"), "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    str(sortie / "scene_4s.mp4")], check=True)
    print("MP4", sortie / "scene_4s.mp4")


if __name__ == "__main__":
    main()

"""Outils communs aux exercices M2 : écriture MP4 par tuyau vers ffmpeg."""
import os
import subprocess

import numpy as np

W, H, FPS = 1280, 720, 12
RACINE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SORTIE = os.path.join(RACINE, "renders", "exercices")


class Video:
    """Écrit des images BGR uint8 dans un MP4 H.264 yuv420p (lecture téléphone)."""

    def __init__(self, chemin, w=W, h=H, fps=FPS):
        os.makedirs(os.path.dirname(chemin), exist_ok=True)
        self.chemin, self.w, self.h = chemin, w, h
        self.nb = 0
        self.p = subprocess.Popen(
            ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgr24",
             "-s", f"{w}x{h}", "-r", str(fps), "-i", "-", "-c:v", "libx264",
             "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
             "-movflags", "+faststart", chemin],
            stdin=subprocess.PIPE)

    def ajouter(self, img):
        assert img.shape == (self.h, self.w, 3) and img.dtype == np.uint8, img.shape
        self.p.stdin.write(np.ascontiguousarray(img).tobytes())
        self.nb += 1

    def fermer(self):
        self.p.stdin.close()
        self.p.wait()
        assert self.p.returncode == 0, "ffmpeg a échoué"
        return self.chemin


def ajouter_audio(video, wav, sortie):
    """Mux une piste audio WAV dans un MP4 silencieux, coupé à la durée de la vidéo."""
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", video, "-i", wav,
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "128k", "-shortest",
                    "-movflags", "+faststart", sortie], check=True)
    return sortie

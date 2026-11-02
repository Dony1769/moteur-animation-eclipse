"""Exercice (c) : synchro labiale sur un dialogue de 5 secondes.

Voix : Piper (fr_FR-siwis-medium, licence CC BY 4.0), déjà présente en cache local.
Ouverture de bouche : enveloppe d'amplitude de la voix, une valeur par image
(12 images/s), lissée. C'est une synchro d'amplitude, pas de phonèmes : les
formes de bouche par phonème (Rhubarb) viennent en M4.
Visage dessiné de façon procédurale, uniquement pour tester la synchro.
"""
import os
import subprocess
import sys
import tempfile
import wave

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from commun import SORTIE, Video, W, H, FPS, ajouter_audio  # noqa: E402

VOIX = os.path.expanduser("/root/.cache/serie_voices/fr_FR-siwis-medium.onnx")
TEXTE = "Kaël, la grotte est plus profonde qu'on le pensait. Restons ensemble."
DUREE = 5.0
N = int(DUREE * FPS)
FOND = (236, 236, 236)
PEAU = (196, 218, 240)     # BGR
CHEVEUX = (70, 38, 30)
YEUX = (200, 120, 40)
LEVRES = (92, 96, 176)
INTERIEUR = (40, 30, 34)


def synthese(chemin_wav):
    subprocess.run(["piper", "-m", VOIX, "-f", chemin_wav], input=TEXTE.encode("utf-8"),
                   check=True, capture_output=True)


def lire_wav(chemin):
    with wave.open(chemin, "rb") as w:
        sr = w.getframerate()
        donnees = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32)
    return sr, donnees / 32768.0


def ajuster_duree(sr, son, duree):
    cible = int(duree * sr)
    if len(son) >= cible:
        return son[:cible]
    return np.concatenate([son, np.zeros(cible - len(son), np.float32)])


def enveloppe(son, sr):
    """Amplitude RMS par image, normalisée entre 0 et 1, puis lissée."""
    pas = sr // FPS
    rms = np.array([np.sqrt(np.mean(son[i * pas:(i + 1) * pas] ** 2) + 1e-12) for i in range(N)])
    ref = np.percentile(rms, 95) + 1e-9
    ouv = np.clip(rms / ref, 0, 1.0) ** 0.8
    ouv = np.convolve(ouv, np.array([0.25, 0.5, 0.25]), mode="same")
    return np.clip(ouv * 1.1, 0, 1)


def visage(img, ouverture):
    cx, cy = 640, 300
    cv2.circle(img, (cx, cy), 170, PEAU, -1, cv2.LINE_AA)
    cv2.ellipse(img, (cx, cy - 60), (182, 150), 0, 180, 360, CHEVEUX, -1, cv2.LINE_AA)
    for x in (560, 720):
        cv2.circle(img, (x, cy - 10), 17, (255, 255, 255), -1, cv2.LINE_AA)
        cv2.circle(img, (x, cy - 8), 11, YEUX, -1, cv2.LINE_AA)
    my = cy + 110
    if ouverture < 0.08:
        cv2.line(img, (cx - 36, my), (cx + 36, my), LEVRES, 7, cv2.LINE_AA)
    else:
        h = int(6 + ouverture * 46)
        cv2.ellipse(img, (cx, my), (36, h), 0, 0, 360, INTERIEUR, -1, cv2.LINE_AA)
        cv2.ellipse(img, (cx, my), (36, h), 0, 0, 360, LEVRES, 6, cv2.LINE_AA)


def main():
    with tempfile.TemporaryDirectory() as tmp:
        wav = os.path.join(tmp, "voix.wav")
        synthese(wav)
        sr, son = lire_wav(wav)
        duree_voix = len(son) / sr
        son = ajuster_duree(sr, son, DUREE)
        ouv = enveloppe(son, sr)
        silencieuse = os.path.join(tmp, "silencieuse.mp4")
        video = Video(silencieuse)
        for f in range(N):
            img = np.full((H, W, 3), FOND, np.uint8)
            visage(img, ouv[f])
            video.ajouter(img)
        video.fermer()
        wav5 = os.path.join(tmp, "voix5.wav")
        with wave.open(wav5, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(sr)
            w.writeframes((son * 32767).astype(np.int16).tobytes())
        sortie = os.path.join(SORTIE, "c_labiale.mp4")
        ajouter_audio(silencieuse, wav5, sortie)
    print("labiale :", sortie, "| voix synthétisée :", round(duree_voix, 2), "s | images :", N)
    print("ouverture (min, max, moyenne) :", round(float(ouv.min()), 2),
          round(float(ouv.max()), 2), round(float(ouv.mean()), 2))


if __name__ == "__main__":
    main()

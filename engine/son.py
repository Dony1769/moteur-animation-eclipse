"""Bruitages synthétisés (numpy) et piste WAV calée sur les images.

Aucun fichier son tiers : chaque bruit est calculé ici.
evenements = liste de (image, type) ; types : pas, sabre, impact, choc, chute.
"""
import wave
import numpy as np

RATE = 48000
FPS = 24


def _enveloppe(n, decroissance):
    t = np.arange(n) / RATE
    return np.exp(-t * decroissance)


def _bruit(n, seed):
    return np.random.default_rng(seed).standard_normal(n)


def pas(n=int(0.14 * RATE), seed=1):
    b = np.convolve(_bruit(n, seed), np.ones(40) / 40, mode="same")
    return 0.5 * b * _enveloppe(n, 30)


def sabre(n=int(0.22 * RATE), seed=2):
    b = _bruit(n, seed)
    b = np.diff(b, prepend=0.0)  # filtre passe-haut simple : son de lame
    return 0.35 * b * _enveloppe(n, 14)


def impact(n=int(0.45 * RATE), seed=3):
    t = np.arange(n) / RATE
    basse = np.sin(2 * np.pi * 95 * t * (1 - 0.3 * t)) * _enveloppe(n, 9)
    claquement = _bruit(n, seed) * _enveloppe(n, 60)
    return 0.8 * basse + 0.35 * claquement


def choc(n=int(0.7 * RATE)):
    t = np.arange(n) / RATE
    son = sum(np.sin(2 * np.pi * f * t) for f in (1830, 2740, 4120)) / 3
    return 0.3 * son * _enveloppe(n, 5)


def chute(n=int(0.9 * RATE), seed=5):
    t = np.arange(n) / RATE
    grave = np.sin(2 * np.pi * 55 * t) * _enveloppe(n, 6)
    return 0.7 * grave + 0.25 * _bruit(n, seed) * _enveloppe(n, 10)


BANQUE = {"pas": pas, "sabre": sabre, "impact": impact, "choc": choc, "chute": chute}


def piste(evenements, duree_images, sortie_wav):
    """Mixe les bruitages à leur image et écrit un WAV stéréo 48 kHz."""
    total = int(duree_images / FPS * RATE) + RATE
    mix = np.zeros(total)
    for image, type_ in evenements:
        son = BANQUE[type_]()
        debut = int((image - 1) / FPS * RATE)   # image Blender 1 = instant 0
        fin = min(total, debut + len(son))
        mix[debut:fin] += son[: fin - debut]
    mix = np.clip(mix * 0.8, -1, 1)
    stereo = np.stack([mix, mix], axis=1)
    data = (stereo * 32767).astype("<i2").tobytes()
    with wave.open(sortie_wav, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(data)
    return sortie_wav

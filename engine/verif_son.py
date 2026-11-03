"""Vérifie le calage du son sans l'écouter : débuts de bruitages mesurés contre instants attendus."""
import wave
import numpy as np

FPS = 24
TOLERANCE_S = 0.015


def debuts_mesures(chemin_wav, pas_s=0.01, seuil=0.25):
    with wave.open(chemin_wav, "rb") as w:
        rate = w.getframerate()
        data = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").reshape(-1, w.getnchannels())[:, 0]
    x = data.astype(float) / 32767.0
    pas = int(rate * pas_s)
    n = len(x) // pas
    env = np.sqrt((x[: n * pas].reshape(n, pas) ** 2).mean(axis=1))
    montee = np.diff(env, prepend=0.0)
    pic = env.max()
    debuts = []
    i = 0
    while i < n:
        if env[i] > seuil * pic and montee[i] > 0.4 * pic and (not debuts or (i * pas_s - debuts[-1]) > 0.1):
            debuts.append(i * pas_s)
        i += 1
    return debuts


def comparer(chemin_wav, evenements, fenetre=(-0.05, 0.25)):
    """Pour chaque instant attendu, mesure le début du bruit dans une petite fenêtre autour de cet instant.

    Méthode locale : chaque bruit est comparé à son propre niveau, donc les pas faibles sont vérifiés aussi.
    Renvoie (instant attendu, écart en ms ou None si rien n'est entendu dans la fenêtre).
    """
    with wave.open(chemin_wav, "rb") as w:
        rate = w.getframerate()
        data = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").reshape(-1, w.getnchannels())[:, 0]
    x = np.abs(data.astype(float) / 32767.0)
    pas = int(rate * 0.005)
    env = x[: (len(x) // pas) * pas].reshape(-1, pas).max(axis=1)     # enveloppe toutes les 5 ms
    rapport = []
    for image, _ in sorted(evenements):
        t = (image - 1) / FPS
        i0 = max(0, int((t + fenetre[0]) / 0.005))
        i1 = min(len(env), int((t + fenetre[1]) / 0.005))
        fen = env[i0:i1]
        if fen.size == 0 or fen.max() < 0.02:
            rapport.append((round(t, 3), None))
            continue
        seuil = 0.5 * fen.max()
        premier = int(np.argmax(fen >= seuil))
        debut = (i0 + premier) * 0.005
        rapport.append((round(t, 3), round((debut - t) * 1000, 1)))
    return rapport

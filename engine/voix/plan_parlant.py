"""M4 : plan parlant de 10 secondes.

Voix : Piper (fr_FR-siwis-medium, CC BY 4.0). Formes de bouche : Rhubarb Lip Sync 1.14.0
(formes A à F et X, mode par défaut). Dessins : bustes de Kaël, un par forme de bouche,
commutés image par image (animation « sur deux » : 1 dessin tenu 1 image sur 1 ou 2).

Table Rhubarb -> dessin disponible (les formes G et H ne sont pas dans les dessins) :
  A (M, B, P, bouche fermée) -> M
  B (consonnes, dents serrées) -> E
  C (E, I, bouche ouverte)    -> I
  D (A, grande ouverture)      -> A
  E (O, arrondie)              -> O
  F (U, W, lèvres pincées)     -> U
  X (repos)                    -> M

Usage : python3 engine/voix/plan_parlant.py <sortie.mp4>
"""
import json
import os
import subprocess
import sys
import tempfile
import wave

import cv2
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "exercices"))
sys.path.insert(0, os.path.dirname(__file__))
import aligner_bouches  # noqa: E402
from commun import Video, W, H, FPS, ajouter_audio  # noqa: E402

RACINE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
VOIX = "/root/.cache/serie_voices/fr_FR-siwis-medium.onnx"
RHUBARB = "/home/claude/outils/rhubarb/src/Rhubarb-Lip-Sync-1.14.0-Linux/rhubarb"
DESSINS = os.path.join(RACINE, "universes", "eclipse_royale", "characters", "kael", "dessins")
TABLE = {"A": "M", "B": "E", "C": "I", "D": "A", "E": "O", "F": "U", "X": "M"}
TEXTE = ("Kaël regarde la grotte. Elle est plus profonde qu'on le pensait, et l'air "
         "y sent la pierre humide. Restons ensemble, avance doucement, et ne touche à rien "
         "avant mon signal. Je veux voir ce qui brille au fond.")
DUREE = 10.0
HAUTEUR_IMAGE = 640   # le buste de 408 px est agrandi à 640 px de haut


def synthese(wav, texte, vitesse):
    subprocess.run(["piper", "-m", VOIX, "-f", wav, "--length-scale", str(vitesse)],
                   input=texte.encode("utf-8"), check=True, capture_output=True)


def duree_wav(chemin):
    with wave.open(chemin, "rb") as w:
        return w.getnframes() / w.getframerate()


def lire_wav(chemin):
    with wave.open(chemin, "rb") as w:
        sr = w.getframerate()
        son = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
    return sr, son


def ecrire_wav(chemin, sr, son):
    with wave.open(chemin, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(son.astype(np.int16).tobytes())


def rhubarb(wav, texte, tmp):
    fichier_texte = os.path.join(tmp, "dialogue.txt")
    with open(fichier_texte, "w", encoding="utf-8") as f:
        f.write(texte)
    sortie = os.path.join(tmp, "cues.json")
    subprocess.run([RHUBARB, "-f", "json", "-o", sortie, "--dialogFile", fichier_texte, wav],
                   check=True, capture_output=True)
    with open(sortie, encoding="utf-8") as f:
        return json.load(f)["mouthCues"]


def forme_a(cues, t):
    for c in cues:
        if c["start"] <= t < c["end"]:
            return c["value"]
    return "X"


def charger_dessins():
    """Bustes alignés sur les yeux (engine/voix/aligner_bouches.py)."""
    out, _ = aligner_bouches.aligner()
    return out


def cadrer(img):
    """Met le buste à l'échelle et le centre sur un canevas 720p."""
    h, w = img.shape[:2]
    s = HAUTEUR_IMAGE / h
    redim = cv2.resize(img, (int(round(w * s)), HAUTEUR_IMAGE), interpolation=cv2.INTER_CUBIC)
    canevas = np.full((H, W, 3), (236, 236, 236), np.uint8)
    x0 = (W - redim.shape[1]) // 2
    y0 = (H - HAUTEUR_IMAGE) // 2
    canevas[y0:y0 + HAUTEUR_IMAGE, x0:x0 + redim.shape[1]] = redim
    return canevas


def main(sortie):
    with tempfile.TemporaryDirectory() as tmp:
        brut = os.path.join(tmp, "brut.wav")
        # length-scale > 1 ralentit. Piper n'est pas linéaire : on cherche l'échelle
        # qui laisse la voix finir sous DUREE, sans couper la dernière phrase.
        vitesse = 1.0
        for _ in range(10):
            synthese(brut, TEXTE, round(vitesse, 3))
            d = duree_wav(brut)
            if d <= DUREE - 0.02:
                break
            vitesse *= (DUREE - 0.15) / d
        assert d <= DUREE, "la voix ne tient pas dans la durée"
        sr, son = lire_wav(brut)
        cible = int(DUREE * sr)
        son = np.concatenate([son, np.zeros(max(0, cible - len(son)), np.int16)])[:cible]
        wav10 = os.path.join(tmp, "voix10.wav")
        ecrire_wav(wav10, sr, son)
        cues = rhubarb(wav10, TEXTE, tmp)
        dessins = {k: cadrer(v) for k, v in charger_dessins().items()}
        silencieuse = os.path.join(tmp, "sans_son.mp4")
        video = Video(silencieuse)
        n = int(DUREE * FPS)
        formes = []
        for f in range(n):
            forme = TABLE.get(forme_a(cues, f / FPS), "M")
            formes.append(forme)
            video.ajouter(dessins[forme])
        video.fermer()
        os.makedirs(os.path.dirname(sortie), exist_ok=True)
        ajouter_audio(silencieuse, wav10, sortie)
    compte = {k: formes.count(k) for k in sorted(set(formes))}
    print("plan parlant :", sortie, "| durée voix :", round(d, 2), "s | échelle Piper :", round(vitesse, 3))
    print("formes utilisées (images) :", compte, "| signaux Rhubarb :", len(cues))


if __name__ == "__main__":
    main(sys.argv[1])

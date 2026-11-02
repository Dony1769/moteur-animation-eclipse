"""Gabarit de placement et contrôle des générations (Kaël, canevas 856x900).

1. creer_gabarit : PNG blanc 856x900 avec repères MAGENTA (#FF00FF) à donner au générateur
   avec la référence. Le générateur ne doit pas les recopier : on les retire ensuite.
2. nettoyer : supprime tout pixel magenta de l'image générée.
3. controler : mesure une image générée (DWPose) et la refuse si les yeux, le menton ou
   l'échelle dérivent de la référence.

Usage :
  python3 engine/gen/gabarit.py gabarit <sortie.png>
  python3 engine/gen/gabarit.py controler <image.png> [bouche|visage]
"""
import sys

import cv2
import numpy as np

sys.path.insert(0, "engine/rig2d")
REF = "universes/eclipse_royale/characters/kael/vues/face_g.png"
W, H = 856, 900
# Mesures de la référence (DWPose, 68 points) :
YEUX_G = np.array([269.3, 107.5]); YEUX_D = np.array([300.2, 106.9])
CENTRE = np.array([285.0, 107.0])              # milieu des yeux
ECART_YEUX = float(np.linalg.norm(YEUX_D - YEUX_G))  # ~31 px
LIGNES = {"haut_cheveux": 36, "sourcils": 97, "yeux": 107, "bouche": 137, "menton": 156, "pieds": 876}
MAGENTA = (255, 0, 255)  # BGR


def creer_gabarit(sortie):
    img = np.full((H, W, 3), 255, np.uint8)
    for nom, y in LIGNES.items():
        cv2.line(img, (0, y), (W - 1, y), MAGENTA, 1)
    cv2.line(img, (int(CENTRE[0]), 0), (int(CENTRE[0]), H - 1), MAGENTA, 1)
    # Cadre de la tête (boîte visage de la référence)
    cv2.rectangle(img, (251, 96), (317, 156), MAGENTA, 1)
    for p in (YEUX_G, YEUX_D):
        cv2.circle(img, (int(p[0]), int(p[1])), 3, MAGENTA, 1)
    cv2.imwrite(sortie, img)
    return sortie


def nettoyer(img_bgr):
    """Remplace les pixels magenta purs (et quasi) par du blanc."""
    proche = np.all(np.abs(img_bgr.astype(int) - np.array(MAGENTA)) < 60, axis=2)
    out = img_bgr.copy()
    out[proche] = (255, 255, 255)
    return out


def _points(img_bgr, session):
    import pose
    pts, sc = pose.detecter(cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB), session)
    return pts[23:91], sc[23:91]


def controler(chemin, mode="visage"):
    import onnxruntime as ort
    session = ort.InferenceSession("models/dw-ll_ucoco_384.onnx", providers=["CPUExecutionProvider"])
    img = cv2.imread(chemin)
    if img is None or img.shape[:2] != (H, W):
        return {"ok": False, "raison": "taille %s au lieu de %dx%d" % (None if img is None else img.shape[:2], W, H)}
    img = nettoyer(img)
    f, sc = _points(img, session)
    if sc.mean() < 0.5:
        return {"ok": False, "raison": "visage non détecté (fiabilité %.2f)" % sc.mean()}
    yeux = (f[36:42].mean(0) + f[42:48].mean(0)) / 2
    ecart = float(np.linalg.norm(f[42:48].mean(0) - f[36:42].mean(0)))
    echelle = ecart / ECART_YEUX
    dec = yeux - CENTRE
    rapport = {"decalage_x": round(float(dec[0]), 1), "decalage_y": round(float(dec[1]), 1),
               "echelle": round(echelle, 3)}
    ok = abs(dec[0]) <= 4 and abs(dec[1]) <= 4 and 0.92 <= echelle <= 1.08
    rapport["ok"] = bool(ok)
    if not ok:
        rapport["raison"] = "dérive : yeux à %+.1f/%+.1f px, échelle %.2f (tolérance 4 px, 0.92-1.08)" % (
            dec[0], dec[1], echelle)
    return rapport


if __name__ == "__main__":
    if sys.argv[1] == "gabarit":
        print(creer_gabarit(sys.argv[2]))
    elif sys.argv[1] == "controler":
        print(controler(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "visage"))

"""Recale les dessins de visage (bouches, expressions) sur le visage de référence.
Détection des 68 points du visage avec DWPose (engine/rig2d/pose.py), transformation de similitude
estimée par OpenCV (cv2.estimateAffinePartial2D) sur ces points, puis application au dessin détouré.
Usage : python3 engine/gen/recaler_visages.py
"""
import glob
import json
import os

import cv2
import numpy as np
import onnxruntime as ort
from PIL import Image

import sys
sys.path.insert(0, "engine/rig2d")
import pose  # noqa: E402

DOSSIER = "out/gemini/detoure"
SORTIE = "out/gemini/recales"
os.makedirs(SORTIE, exist_ok=True)
REF = "universes/eclipse_royale/characters/kael/vues/face_g.png"
session = ort.InferenceSession(pose.MODELE, providers=["CPUExecutionProvider"])


def visage(img_rgb):
    pts, score = pose.detecter(img_rgb, session)
    face = pts[23:91]
    return face, score[23:91]


def sur_blanc(png):
    fond = Image.new("RGBA", png.size, (255, 255, 255, 255))
    fond.alpha_composite(png.convert("RGBA"))
    return np.array(fond.convert("RGB"))


ref_bgr = cv2.imread(REF)
ref_rgb = cv2.cvtColor(ref_bgr, cv2.COLOR_BGR2RGB)
ref_pts, ref_score = visage(ref_rgb)
print("référence : score moyen visage %.2f" % float(ref_score.mean()))

fichiers = sorted([f for f in glob.glob(os.path.join(DOSSIER, "bouche_*.png")) + glob.glob(os.path.join(DOSSIER, "expr_*.png")) if "_brut" not in f])
rapport = {}
for f in fichiers:
    nom = os.path.splitext(os.path.basename(f))[0]
    png = Image.open(f).convert("RGBA")
    src_rgb = sur_blanc(png)
    src_pts, src_score = visage(src_rgb)
    if src_score.mean() < 0.3:
        rapport[nom] = "visage non détecté"
        print(nom, "visage non détecté")
        continue
    # Similitude estimée sur les points fiables du visage (yeux, nez, bouche)
    ok = (src_score > 0.3) & (ref_score > 0.3)
    m, inliers = cv2.estimateAffinePartial2D(src_pts[ok].astype(np.float32), ref_pts[ok].astype(np.float32), method=cv2.RANSAC)
    if m is None:
        rapport[nom] = "transformation impossible"
        continue
    H, W = ref_rgb.shape[:2]
    rgba = np.array(png)
    alpha_warp = cv2.warpAffine(rgba, m, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
    Image.fromarray(alpha_warp, "RGBA").save(os.path.join(SORTIE, nom + "_recale.png"))
    echelle = float(np.sqrt(m[0, 0] ** 2 + m[1, 0] ** 2))
    rapport[nom] = {"echelle": round(echelle, 3), "inliers": int(inliers.sum()), "points": int(ok.sum())}
    print(nom, rapport[nom])
json.dump(rapport, open(os.path.join(SORTIE, "rapport.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

# Superposition : chaque bouche et expression posée sur le visage de référence
apercus = []
for f in sorted(glob.glob(os.path.join(SORTIE, "*_recale.png"))):
    over = ref_rgb.copy()
    rec = np.array(Image.open(f).convert("RGBA")).astype(np.float32)
    a = rec[..., 3:4] / 255.0
    over = (over * (1 - a) + rec[..., :3] * a).astype(np.uint8)
    crop = over[0:520, 130:730]
    apercus.append(cv2.cvtColor(cv2.resize(crop, (240, 208)), cv2.COLOR_RGB2BGR))
if apercus:
    cv2.imwrite(os.path.join(SORTIE, "superposition.png"), np.hstack(apercus))
print("terminé :", len(apercus), "superpositions")

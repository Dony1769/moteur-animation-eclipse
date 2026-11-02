"""Plan 1 : Kaël est petit dans la grotte (plan large), puis un zoom avant révèle sa taille réelle.

Monde : grotte agrandie x4 cadrée à 2560×1440. Personnage : hauteur monde 467 px, pieds à (1280, 1280).
Caméra : zoom de 1.0 (plan large, personnage ~233 px) à 2.4 (personnage 560 px), pieds fixes à y=640.
Le personnage marche sur place (cycle de 4 poses, chaque pose tenue 4 images).
"""
import glob
import os
import subprocess

import cv2
import numpy as np

import integrer_grotte as g

W, H = 1280, 720
MONDE_W, MONDE_H = 2560, 1440
HAUTEUR_MONDE = 467.0
PIEDS_MONDE = (1280.0, 1280.0)
ZOOM0, ZOOM1 = 1.0, 2.4
CAM_Y0, CAM_Y1 = 720.0, 1047.0
CAM_X = 1280.0
FPS, TENUE = 12, 4
ATTENTE = 24          # images à zoom final (2 s)
ZOOM_IMAGES = 48      # images de zoom (4 s)
SORTIE = "out/rendu_plan_zoom"


def monde():
    x4 = cv2.imread("out/scene/grotte_x4.png")
    s = max(MONDE_W / x4.shape[1], MONDE_H / x4.shape[0])
    big = cv2.resize(x4, (int(round(x4.shape[1] * s)), int(round(x4.shape[0] * s))), interpolation=cv2.INTER_AREA)
    x0 = (big.shape[1] - MONDE_W) // 2
    plate = big[:, x0:x0 + MONDE_W]
    prof = np.load("out/rendu_grotte_v2/profondeur.npy")
    prof_m = cv2.resize(prof, (MONDE_W, MONDE_H), interpolation=cv2.INTER_LINEAR)
    # même cadrage pour la lumière : position dans le plateau 1280x720 -> monde
    lum_plateau = g.lumiere_ouverture(cv2.imread("out/rendu_grotte_v2/plateau.png"))
    lum_monde = (lum_plateau[0] * 2.0, lum_plateau[1] * 2.0)
    return plate, prof_m, lum_monde


def camera(i):
    t = min(1.0, i / ZOOM_IMAGES)
    e = t * t * (3 - 2 * t)           # ease in-out
    zoom = ZOOM0 + (ZOOM1 - ZOOM0) * e
    cam_y = CAM_Y0 + (CAM_Y1 - CAM_Y0) * e
    return zoom, cam_y


def vers_ecran(x, y, zoom, cam_y):
    s = zoom / 2.0                    # écran (1280) par px monde (2560)
    return (x - CAM_X) * s + 640.0, (y - cam_y) * s + 360.0, s


def image(plate, prof, lum_m, sprite, i):
    zoom, cam_y = camera(i)
    s2 = zoom                        # pour un rendu à 2x puis réduction (anti-crénelage)
    M = np.float32([[s2, 0, 1280 - CAM_X * s2], [0, s2, 720 - cam_y * s2]])
    grand = cv2.warpAffine(plate, M, (2560, 1440), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    fond = cv2.resize(grand, (W, H), interpolation=cv2.INTER_AREA)
    pm = cv2.warpAffine(prof, M, (2560, 1440), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    pm = cv2.resize(pm, (W, H), interpolation=cv2.INTER_AREA)
    fx, fy, s = vers_ecran(PIEDS_MONDE[0], PIEDS_MONDE[1], zoom, cam_y)
    lx, ly, _ = vers_ecran(lum_m[0], lum_m[1], zoom, cam_y)
    hauteur = HAUTEUR_MONDE * s
    return g.composer(fond, pm, sprite, fx, fy, hauteur, (lx, ly))


if __name__ == "__main__":
    os.makedirs(SORTIE, exist_ok=True)
    plate, prof_m, lum_m = monde()
    sprites = [cv2.imread(f, cv2.IMREAD_UNCHANGED).astype(np.float32)
               for f in ["out/cycle/hanche/cycle_1_contact_gauche.png", "out/cycle/hanche/cycle_2_passage.png",
                         "out/cycle/hanche/cycle_3_contact_droit.png", "out/cycle/hanche/cycle_4_passage.png"]]
    total = ZOOM_IMAGES + ATTENTE
    cadres = []
    for i in range(total):
        pose = (i // TENUE) % 4
        cadres.append(image(plate, prof_m, lum_m, sprites[pose], min(i, ZOOM_IMAGES)))
    for k, c in enumerate(cadres):
        cv2.imwrite(f"{SORTIE}/f{k:03d}.png", c)
    tmp = f"{SORTIE}/brut.mp4"
    vw = cv2.VideoWriter(tmp, cv2.VideoWriter_fourcc(*"mp4v"), FPS, (W, H))
    for c in cadres:
        vw.write(c)
    vw.release()
    final = f"{SORTIE}/plan_zoom.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", tmp, "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    "-crf", "20", final], check=True)
    os.remove(tmp)
    print(len(cadres), "images ->", final)

"""Plan 1 complet : zoom révélant la taille (plan_zoom), puis Kaël avance dans la grotte.

Phase B : zoom final (2.4), pieds qui remontent vers le fond de la grotte (monde 1280,1280 -> 1280,1170),
hauteur monde réduite de 15 % (éloignement), caméra qui suit à moitié le mouvement.
"""
import os
import subprocess

import cv2
import numpy as np

import plan_zoom as z
import integrer_grotte as g

W, H = 1280, 720
FIN_ZOOM = z.ZOOM1
DEBUT_FEET = np.array([1280.0, 1280.0])
FIN_FEET = np.array([1280.0, 1170.0])
RECUL = 0.15
MARCHE_IMAGES = 72
FPS, TENUE = 12, 4
SORTIE = "out/rendu_plan_1_opt"


def progression():
    """Avance des pieds par image : seulement pendant les passages (poses 1 et 3) pour limiter le glissement."""
    poses = [(k // TENUE) % 4 for k in range(MARCHE_IMAGES)]
    taux = np.array([1.0 if p in (1, 3) else 0.0 for p in poses])
    cum = np.cumsum(taux)
    return cum / cum[-1]


PROG = progression()


def image_marche(plate, prof_m, lum_m, sprite, k):
    t = float(PROG[k])
    feet = DEBUT_FEET + (FIN_FEET - DEBUT_FEET) * t
    h_monde = z.HAUTEUR_MONDE * (1 - RECUL * t)
    # balancement de caméra synchronisé sur les pas (2 oscillations par cycle de 4 poses)
    bob = 3.0 * np.sin(2 * np.pi * 2 * k / (4 * TENUE * 4))
    cam_y = z.CAM_Y1 + 0.5 * (feet[1] - DEBUT_FEET[1]) + bob
    zoom = FIN_ZOOM
    s2 = zoom
    M = np.float32([[s2, 0, 1280 - z.CAM_X * s2], [0, s2, 720 - cam_y * s2]])
    grand = cv2.warpAffine(plate, M, (2560, 1440), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    fond = cv2.resize(grand, (W, H), interpolation=cv2.INTER_AREA)
    pm = cv2.warpAffine(prof_m, M, (2560, 1440), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    pm = cv2.resize(pm, (W, H), interpolation=cv2.INTER_AREA)
    s = zoom / 2.0
    fx = (feet[0] - z.CAM_X) * s + 640.0
    fy = (feet[1] - cam_y) * s + 360.0
    lx = (lum_m[0] - z.CAM_X) * s + 640.0
    ly = (lum_m[1] - cam_y) * s + 360.0
    return g.composer(fond, pm, sprite, fx, fy, h_monde * s, (lx, ly))


if __name__ == "__main__":
    os.makedirs(SORTIE, exist_ok=True)
    plate, prof_m, lum_m = z.monde()
    flou = cv2.GaussianBlur(plate, (0, 0), 1.4)
    plate = cv2.addWeighted(plate, 1.5, flou, -0.5, 0)   # accentuation légère
    sprites = [cv2.imread(f, cv2.IMREAD_UNCHANGED).astype(np.float32)
               for f in ["out/cycle/hanche/cycle_1_contact_gauche.png", "out/cycle/hanche/cycle_2_passage.png",
                         "out/cycle/hanche/cycle_3_contact_droit.png", "out/cycle/hanche/cycle_4_passage.png"]]
    cadres = []
    # Phase A : zoom révélant la taille (même que plan_zoom)
    for i in range(z.ZOOM_IMAGES + z.ATTENTE):
        pose = (i // TENUE) % 4
        cadres.append(z.image(plate, prof_m, lum_m, sprites[pose], min(i, z.ZOOM_IMAGES)))
    # Phase B : Kaël avance vers le fond de la grotte
    # cycle de dos (cadres 3, 4, 5 de la planche de marche, puis 4 à nouveau)
    dos = [cv2.imread(f, cv2.IMREAD_UNCHANGED).astype(np.float32)
           for f in ["out/cycle/dos/dos_03.png", "out/cycle/dos/dos_04.png",
                     "out/cycle/dos/dos_05.png", "out/cycle/dos/dos_04.png"]]

    for k in range(MARCHE_IMAGES):
        pose = (k // TENUE) % 4
        cadres.append(image_marche(plate, prof_m, lum_m, dos[pose], k))
    for i, c in enumerate(cadres):
        cv2.imwrite(f"{SORTIE}/f{i:03d}.png", c)
    tmp = f"{SORTIE}/brut.mp4"
    vw = cv2.VideoWriter(tmp, cv2.VideoWriter_fourcc(*"mp4v"), FPS, (W, H))
    for c in cadres:
        vw.write(c)
    vw.release()
    final = f"{SORTIE}/plan_1.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", tmp, "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    "-crf", "20", final], check=True)
    os.remove(tmp)
    print(len(cadres), "images ->", final)

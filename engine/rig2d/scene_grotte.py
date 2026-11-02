"""Premier rendu : Kaël dans la grotte. Plans à images-clés tenues (2 à 4 images par dessin).

Plan A : tour du personnage (8 angles, tour_00..07), sur place.
Plan B : marche (marche_00..07), il s'éloigne dans la profondeur de la grotte (taille et sol qui remontent).
Chaque figure est posée sur le sol de la grotte avec une ombre de contact sous les pieds.
"""
import glob
import os
import subprocess

import cv2
import numpy as np

W, H = 1280, 720
FPS = 12
TENUE = 4
HAUTEUR_PERSO = 560       # hauteur du personnage à l'écran (px) au premier plan
SOL_DEPART = 640          # ligne des pieds au premier plan
SOL_FOND = 600            # ligne des pieds au fond
CX = 640
GROTTE = "/mnt/user-data/attachments/9ce8e1e5-f7cf-5619-8a75-3c6d9a11ab1c/28afa025-image.jpg"
SORTIE = "out/rendu_grotte"


def fond():
    img = cv2.imread(GROTTE)
    return cv2.resize(img, (W, H), interpolation=cv2.INTER_AREA).astype(np.float32)


def figure(chemin):
    """Retourne le RGBA recadré à la boîte du personnage (alpha > 0)."""
    im = cv2.imread(chemin, cv2.IMREAD_UNCHANGED)
    a = im[..., 3]
    ys, xs = np.where(a > 20)
    return im[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def poser(fond_bgr, rgba, cx, pieds_y, hauteur):
    h0, w0 = rgba.shape[:2]
    s = hauteur / h0
    nh, nw = int(round(h0 * s)), int(round(w0 * s))
    r = cv2.resize(rgba, (nw, nh), interpolation=cv2.INTER_AREA).astype(np.float32)
    out = fond_bgr.copy()
    # ombre de contact sous les pieds
    ombre = np.zeros((H, W), np.float32)
    cv2.ellipse(ombre, (int(cx), int(pieds_y)), (int(nw * 0.38), int(max(6, nh * 0.035))), 0, 0, 360, 1.0, -1)
    ombre = cv2.GaussianBlur(ombre, (0, 0), 6)
    out *= (1 - 0.45 * ombre)[..., None]
    x0 = int(round(cx - nw / 2)); y0 = int(round(pieds_y - nh))
    xa, ya = max(x0, 0), max(y0, 0)
    xb, yb = min(x0 + nw, W), min(y0 + nh, H)
    if xb <= xa or yb <= ya:
        return out
    bgr = r[ya - y0:yb - y0, xa - x0:xb - x0, :3]
    al = r[ya - y0:yb - y0, xa - x0:xb - x0, 3:4] / 255.0
    zone = out[ya:yb, xa:xb]
    out[ya:yb, xa:xb] = zone * (1 - al) + bgr * al
    return out


def images(prefixe):
    return sorted(glob.glob(f"out/sheets/{prefixe}_[0-9][0-9].png"))


if __name__ == "__main__":
    os.makedirs(SORTIE, exist_ok=True)
    F = fond()
    cadres = []
    # Plan A : tour sur place
    for f in images("tour"):
        rgba = figure(f)
        for _ in range(TENUE):
            cadres.append(poser(F, rgba, CX, SOL_DEPART, HAUTEUR_PERSO))
    # Plan B : il s'éloigne (marche)
    marche = images("marche")
    n = len(marche) * TENUE
    k = 0
    for f in marche:
        rgba = figure(f)
        for _ in range(TENUE):
            t = k / max(1, n - 1)
            hauteur = HAUTEUR_PERSO * (1 - 0.25 * t)
            pieds = SOL_DEPART + (SOL_FOND - SOL_DEPART) * t
            cadres.append(poser(F, rgba, CX, pieds, hauteur))
            k += 1
    for i, c in enumerate(cadres):
        cv2.imwrite(f"{SORTIE}/f{i:03d}.png", np.clip(c, 0, 255).astype(np.uint8))
    tmp = f"{SORTIE}/rendu_brut.mp4"
    vw = cv2.VideoWriter(tmp, cv2.VideoWriter_fourcc(*"mp4v"), FPS, (W, H))
    for c in cadres:
        vw.write(np.clip(c, 0, 255).astype(np.uint8))
    vw.release()
    final = f"{SORTIE}/kael_grotte.mp4"
    try:
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", tmp, "-c:v", "libx264", "-pix_fmt", "yuv420p",
                        "-crf", "20", final], check=True)
        os.remove(tmp)
    except Exception:
        os.replace(tmp, final)
    print(len(cadres), "images ->", final)

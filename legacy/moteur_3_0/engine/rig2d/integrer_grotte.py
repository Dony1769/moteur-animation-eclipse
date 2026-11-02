"""Intégration de Kaël dans la grotte (v2) : lumière de l'ouverture, ombre portée au sol,
ombre de contact, liseré de contre-jour, et masquage par les rochers plus proches (profondeur).

Entrées :
  - plateau : grotte sans bordure blanche, recadrée à 1280x720 (cover)
  - profondeur : Depth-Anything-V2 small sur le même plateau (plus haut = plus proche)
  - figures : out/sheets/tour_XX.png et marche_XX.png (canevas 856x900, pieds à y=876)
"""
import glob
import os
import subprocess

import cv2
import numpy as np

W, H = 1280, 720
FPS = 12
TENUE = 4
HAUTEUR_PERSO = 560
SOL_DEPART, SOL_FOND = 640, 600
CX = 640
SRC = "/mnt/user-data/attachments/9ce8e1e5-f7cf-5619-8a75-3c6d9a11ab1c/28afa025-image.jpg"
SORTIE = os.environ.get("SORTIE", "out/rendu_grotte_v2")
SPR = os.environ.get("SPR", "out/sheets")
RAYON = 38.0


def plateau_et_profondeur():
    import torch
    from PIL import Image
    from transformers import AutoImageProcessor, AutoModelForDepthEstimation
    if os.path.exists("out/scene/grotte_x4.png"):      # plateau agrandi x4 (Real-ESRGAN anime)
        crop = cv2.imread("out/scene/grotte_x4.png")
    else:
        img = cv2.imread(SRC)
        crop = img[71:697, 105:1271].copy()           # contenu sans bordure blanche
    # cover 1280x720
    s = max(W / crop.shape[1], H / crop.shape[0])
    big = cv2.resize(crop, (int(round(crop.shape[1] * s)), int(round(crop.shape[0] * s))), interpolation=cv2.INTER_CUBIC)
    x0 = (big.shape[1] - W) // 2
    plateau = big[:, x0:x0 + W]
    p = "models/depth_anything_v2_small"
    proc = AutoImageProcessor.from_pretrained(p)
    model = AutoModelForDepthEstimation.from_pretrained(p).eval()
    im = Image.fromarray(cv2.cvtColor(plateau, cv2.COLOR_BGR2RGB))
    with torch.no_grad():
        d = model(**proc(images=im, return_tensors="pt")).predicted_depth
    d = torch.nn.functional.interpolate(d[None], size=(H, W), mode="bicubic", align_corners=False)[0, 0].numpy()
    d = (d - d.min()) / (d.max() - d.min())
    return plateau, d


def lumiere_ouverture(plateau):
    """Position de la source (zone la plus lumineuse de la moitié haute)."""
    g = cv2.GaussianBlur(cv2.cvtColor(plateau, cv2.COLOR_BGR2GRAY).astype(np.float32), (0, 0), 25)
    haut = g[:H // 2]
    y, x = np.unravel_index(np.argmax(haut), haut.shape)
    return float(x), float(y)


def figure(chemin):
    im = cv2.imread(chemin, cv2.IMREAD_UNCHANGED)
    a = im[..., 3]
    ys, xs = np.where(a > 20)
    return im[ys.min():ys.max() + 1, xs.min():xs.max() + 1].astype(np.float32)


def hauteur_volume(alpha01):
    masque = (alpha01 > 0.5).astype(np.uint8)
    dist = cv2.distanceTransform(masque, cv2.DIST_L2, 5).astype(np.float32)
    h = np.sqrt(np.clip(dist / RAYON, 0, 1))
    return cv2.GaussianBlur(h, (0, 0), 2.0), dist


def eclairer(bgr, alpha01, lum_xy, centre_xy):
    """Deux tons (cel) selon la direction de la lumière, liseré de contre-jour, teinte chaude/froide."""
    h, dist = hauteur_volume(alpha01)
    gx = cv2.Sobel(h, cv2.CV_32F, 1, 0, ksize=3) / 8.0
    gy = cv2.Sobel(h, cv2.CV_32F, 0, 1, ksize=3) / 8.0
    vx, vy = lum_xy[0] - centre_xy[0], lum_xy[1] - centre_xy[1]
    n = max(1e-6, np.hypot(vx, vy))
    L = np.array([vx / n * 0.6, vy / n * 0.6, 0.8], np.float32)
    L /= np.linalg.norm(L)
    nx, ny, nz = -gx * 14.0, -gy * 14.0, np.ones_like(gx)
    nn = np.sqrt(nx * nx + ny * ny + nz * nz)
    lum = (nx * L[0] + ny * L[1] + nz * L[2]) / nn
    cel = np.clip((lum - 0.25) / 0.10, 0, 1)
    shade = 0.58 + 0.42 * cel
    # teinte : côté lumière chaud, côté ombre froid (lumière de l'ouverture)
    chaud = np.array([0.94, 1.00, 1.08], np.float32)   # BGR
    froid = np.array([1.06, 1.02, 0.90], np.float32)
    teinte = froid[None, None, :] * (1 - cel[..., None]) + chaud[None, None, :] * cel[..., None]
    out = bgr * shade[..., None] * teinte
    # liseré de contre-jour : bord dont la normale 2D pointe vers la source
    bord = np.clip(alpha01 - cv2.erode(alpha01, np.ones((3, 3), np.uint8)), 0, 1)
    ex, ey = -gx, -gy  # direction sortante approx.
    facing = np.clip((ex * L[0] + ey * L[1]) * 3.0, 0, 1)
    rim = bord * facing * 0.35
    out = out + rim[..., None] * np.array([150, 190, 230], np.float32)[None, None, :]
    return np.clip(out, 0, 255)


def ombre_portee(alpha01, lum_xy, centre_xy, hauteur_px):
    """Ombre projetée au sol, à l'opposé de la source (dans le sens de l'écran)."""
    vx, vy = centre_xy[0] - lum_xy[0], centre_xy[1] - lum_xy[1]
    n = max(1e-6, np.hypot(vx, vy))
    dx, dy = vx / n * hauteur_px * 0.35, abs(vy) / n * hauteur_px * 0.05
    m = np.float32([[1, 0, dx], [0, 1, dy]])
    return cv2.GaussianBlur(cv2.warpAffine(alpha01, m, (alpha01.shape[1], alpha01.shape[0])), (0, 0), 6)


def composer(plateau, profondeur, sprite, cx, pieds_y, hauteur, lum_xy):
    h0, w0 = sprite.shape[:2]
    s = hauteur / h0
    nh, nw = int(round(h0 * s)), int(round(w0 * s))
    r = cv2.resize(sprite, (nw, nh), interpolation=cv2.INTER_AREA)
    x0 = int(round(cx - nw / 2)); y0 = int(round(pieds_y - nh))
    A = np.zeros((H, W), np.float32); C = np.zeros((H, W, 3), np.float32)
    xa, ya, xb, yb = max(x0, 0), max(y0, 0), min(x0 + nw, W), min(y0 + nh, H)
    A[ya:yb, xa:xb] = r[ya - y0:yb - y0, xa - x0:xb - x0, 3] / 255.0
    bgr = r[..., :3]
    ombrage = eclairer(bgr, r[..., 3] / 255.0, lum_xy, (cx - x0, pieds_y - y0 - nh / 2))
    # exposition : le personnage suit la luminosité du décor qu'il occupe
    masque = r[..., 3] > 128
    lum_perso = float(ombrage[masque].mean()) if masque.any() else 1.0
    yy0, yy1, xx0, xx1 = max(ya, 0), min(yb, H), max(xa, 0), min(xb, W)
    lum_decor = float(cv2.cvtColor(plateau, cv2.COLOR_BGR2GRAY)[yy0:yy1, xx0:xx1].mean()) if yy1 > yy0 and xx1 > xx0 else lum_perso
    facteur = float(np.clip(1.10 * lum_decor / max(lum_perso, 1e-3), 0.55, 1.15))
    ombrage = ombrage * facteur
    C[ya:yb, xa:xb] = ombrage[ya - y0:yb - y0, xa - x0:xb - x0]
    out = plateau.astype(np.float32).copy()
    # ombre portée sur le sol (sous l'horizon du sol, zone basse)
    sol = np.zeros((H, W), np.float32); sol[int(pieds_y) - 40:, :] = 1
    cp = ombre_portee(A, lum_xy, (cx, pieds_y), hauteur) * sol
    out *= (1 - 0.6 * cp)[..., None]
    # ombre de contact sous les pieds
    contact = np.zeros((H, W), np.float32)
    cv2.ellipse(contact, (int(cx), int(pieds_y)), (int(nw * 0.36), max(5, int(nh * 0.03))), 0, 0, 360, 1.0, -1)
    contact = cv2.GaussianBlur(contact, (0, 0), 4)
    out *= (1 - 0.55 * contact)[..., None]
    # personnage par-dessus
    out = out * (1 - A[..., None]) + C * A[..., None]
    # masquage : rochers plus proches que le personnage (au-dessus des pieds)
    d_perso = float(profondeur[int(min(H - 1, pieds_y - 2)), int(np.clip(cx, 0, W - 1))])
    # Seuls les rochers devant les jambes (tiers bas de la silhouette) peuvent masquer le personnage :
    # la profondeur monoculaire ne suffit pas pour le haut du corps (les parois latérales sont
    # toujours « plus proches » que le centre de la grotte).
    proches = (profondeur > d_perso + 0.12).astype(np.float32)
    zone_jambes = np.zeros((H, W), np.float32)
    zone_jambes[max(0, int(pieds_y - 0.40 * nh)):int(pieds_y), :] = 1
    occ = cv2.GaussianBlur(proches * zone_jambes, (0, 0), 1.2)
    occ = np.clip(occ, 0, 1)
    out = out * (1 - occ[..., None]) + plateau.astype(np.float32) * occ[..., None]
    return np.clip(out, 0, 255).astype(np.uint8)


if __name__ == "__main__":
    os.makedirs(SORTIE, exist_ok=True)
    plateau, prof = plateau_et_profondeur()
    cv2.imwrite(f"{SORTIE}/plateau.png", plateau)
    np.save(f"{SORTIE}/profondeur.npy", prof)
    lum = lumiere_ouverture(plateau)
    print("source lumineuse ~", [round(v) for v in lum])
    cadres = []
    for f in sorted(glob.glob(SPR + "/tour_[0-9][0-9].png")):
        sp = figure(f)
        for _ in range(TENUE):
            cadres.append(composer(plateau, prof, sp, CX, SOL_DEPART, HAUTEUR_PERSO, lum))
    marche = sorted(glob.glob(SPR + "/marche_[0-9][0-9].png"))
    n = len(marche) * TENUE; k = 0
    for f in marche:
        sp = figure(f)
        for _ in range(TENUE):
            t = k / max(1, n - 1)
            cadres.append(composer(plateau, prof, sp, CX, SOL_DEPART + (SOL_FOND - SOL_DEPART) * t,
                                   HAUTEUR_PERSO * (1 - 0.25 * t), lum))
            k += 1
    for i, c in enumerate(cadres):
        cv2.imwrite(f"{SORTIE}/f{i:03d}.png", c)
    tmp = f"{SORTIE}/brut.mp4"
    vw = cv2.VideoWriter(tmp, cv2.VideoWriter_fourcc(*"mp4v"), FPS, (W, H))
    for c in cadres:
        vw.write(c)
    vw.release()
    final = f"{SORTIE}/kael_grotte_v2.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", tmp, "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    "-crf", "20", final], check=True)
    os.remove(tmp)
    print(len(cadres), "images ->", final)

"""Agrandissement local x4 pour dessins anime (Real-ESRGAN x4plus anime 6B, licence BSD-3).
Tourne sur le processeur, par tuiles pour limiter la mémoire.

Usage : python3 engine/gen/agrandir.py <entree.png> <sortie.png> [taille_tuile=192]
"""
import sys

import cv2
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

POIDS = "models/RealESRGAN_x4plus_anime_6B.pth"


class ResidualDenseBlock(nn.Module):
    def __init__(self, nf=64, gc=32):
        super().__init__()
        self.conv1 = nn.Conv2d(nf, gc, 3, 1, 1)
        self.conv2 = nn.Conv2d(nf + gc, gc, 3, 1, 1)
        self.conv3 = nn.Conv2d(nf + 2 * gc, gc, 3, 1, 1)
        self.conv4 = nn.Conv2d(nf + 3 * gc, gc, 3, 1, 1)
        self.conv5 = nn.Conv2d(nf + 4 * gc, nf, 3, 1, 1)
        self.lrelu = nn.LeakyReLU(0.2, inplace=True)

    def forward(self, x):
        x1 = self.lrelu(self.conv1(x))
        x2 = self.lrelu(self.conv2(torch.cat((x, x1), 1)))
        x3 = self.lrelu(self.conv3(torch.cat((x, x1, x2), 1)))
        x4 = self.lrelu(self.conv4(torch.cat((x, x1, x2, x3), 1)))
        x5 = self.conv5(torch.cat((x, x1, x2, x3, x4), 1))
        return x5 * 0.2 + x


class RRDB(nn.Module):
    def __init__(self, nf, gc):
        super().__init__()
        self.rdb1 = ResidualDenseBlock(nf, gc)
        self.rdb2 = ResidualDenseBlock(nf, gc)
        self.rdb3 = ResidualDenseBlock(nf, gc)

    def forward(self, x):
        return self.rdb3(self.rdb2(self.rdb1(x))) * 0.2 + x


class RRDBNet(nn.Module):
    def __init__(self, nf=64, nb=6, gc=32):
        super().__init__()
        self.conv_first = nn.Conv2d(3, nf, 3, 1, 1)
        self.body = nn.Sequential(*[RRDB(nf, gc) for _ in range(nb)])
        self.conv_body = nn.Conv2d(nf, nf, 3, 1, 1)
        self.conv_up1 = nn.Conv2d(nf, nf, 3, 1, 1)
        self.conv_up2 = nn.Conv2d(nf, nf, 3, 1, 1)
        self.conv_hr = nn.Conv2d(nf, nf, 3, 1, 1)
        self.conv_last = nn.Conv2d(nf, 3, 3, 1, 1)
        self.lrelu = nn.LeakyReLU(0.2, inplace=True)

    def forward(self, x):
        feat = self.conv_first(x)
        feat = feat + self.conv_body(self.body(feat))
        feat = self.lrelu(self.conv_up1(F.interpolate(feat, scale_factor=2, mode="nearest")))
        feat = self.lrelu(self.conv_up2(F.interpolate(feat, scale_factor=2, mode="nearest")))
        return self.conv_last(self.lrelu(self.conv_hr(feat)))


def charger():
    net = RRDBNet()
    etat = torch.load(POIDS, map_location="cpu", weights_only=True)
    for cle in ("params_ema", "params"):
        if cle in etat:
            etat = etat[cle]
            break
    net.load_state_dict(etat, strict=True)
    net.eval()
    return net


@torch.no_grad()
def agrandir(net, img_bgr, tuile=192, marge=16):
    """Agrandit x4 par tuiles avec une marge de recouvrement pour éviter les coutures."""
    h, w = img_bgr.shape[:2]
    rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    sortie = np.zeros((h * 4, w * 4, 3), np.float32)
    for y in range(0, h, tuile):
        for x in range(0, w, tuile):
            y0, x0 = max(y - marge, 0), max(x - marge, 0)
            y1, x1 = min(y + tuile + marge, h), min(x + tuile + marge, w)
            morceau = torch.from_numpy(rgb[y0:y1, x0:x1]).permute(2, 0, 1)[None]
            res = net(morceau)[0].permute(1, 2, 0).clamp(0, 1).numpy()
            dy, dx = (y - y0) * 4, (x - x0) * 4
            hh, ww = min(tuile, h - y) * 4, min(tuile, w - x) * 4
            sortie[y * 4:y * 4 + hh, x * 4:x * 4 + ww] = res[dy:dy + hh, dx:dx + ww]
    return cv2.cvtColor((sortie * 255).round().astype(np.uint8), cv2.COLOR_RGB2BGR)


if __name__ == "__main__":
    import time
    entree, sortie = sys.argv[1], sys.argv[2]
    tuile = int(sys.argv[3]) if len(sys.argv) > 3 else 192
    torch.set_num_threads(2)
    img = cv2.imread(entree)
    net = charger()
    debut = time.time()
    res = agrandir(net, img, tuile)
    cv2.imwrite(sortie, res)
    print("ok", res.shape[1], "x", res.shape[0], "en %.1f s" % (time.time() - debut))

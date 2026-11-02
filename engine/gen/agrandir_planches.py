"""Agrandit x4 chaque figure de out/sheets (RGBA) : couleurs par Real-ESRGAN anime, alpha par bicubique."""
import glob
import os
import sys

import cv2
import numpy as np
import torch

sys.path.insert(0, "engine/gen")
import agrandir  # noqa: E402

torch.set_num_threads(4)
net = agrandir.charger()
for f in sorted(glob.glob("out/sheets/*.png")):
    if f.endswith("_blanc.png"):
        continue
    nom = os.path.basename(f)
    sortie = os.path.join("out/sheets_x4", nom)
    if os.path.exists(sortie):
        continue
    im = cv2.imread(f, cv2.IMREAD_UNCHANGED)
    bgr = np.ascontiguousarray(im[..., :3])
    alpha = im[..., 3]
    grand = agrandir.agrandir(net, bgr, tuile=192)
    a4 = cv2.resize(alpha, (grand.shape[1], grand.shape[0]), interpolation=cv2.INTER_CUBIC)
    cv2.imwrite(sortie, np.dstack([grand, a4]))
    print("ok", nom, flush=True)
print("TERMINE", flush=True)

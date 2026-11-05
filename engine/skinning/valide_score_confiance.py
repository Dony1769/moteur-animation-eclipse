"""Validation du score de confiance : les sommets repliés à 120° (LBS) ont-ils une confiance plus basse ?
Usage : python3 valide_score_confiance.py DOSSIER/ FICHIER_POIDS.npz"""
import sys, os, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from score_confiance import confiance, par_zone
from plis_numpy import plis_masque
from correctif_arap import _lbs
from scipy.stats import mannwhitneyu

S = sys.argv[1].rstrip("/") + "/"
d = np.load(S + "donnees7.npz", allow_pickle=True)
rest, M, faces, etiq = d["rest"], d["M"], d["faces"], list(d["etiquettes"])
os_n = [str(o) for o in d["os"]]
W = np.load(sys.argv[2])["W"]; W = W / W.sum(1, keepdims=True)
conf = confiance(W)
dom = np.array([os_n[i] for i in W.argmax(1)])
print("confiance moyenne :", round(float(conf.mean()), 3))
for z, r in par_zone(conf, dom, {"bras": ["mixamorig:LeftArm", "mixamorig:LeftArmHelper", "mixamorig:LeftShoulder"],
                                 "avant-bras": ["mixamorig:LeftForeArm"], "jambe": ["mixamorig:LeftLeg", "mixamorig:LeftUpLeg"],
                                 "tronc": ["mixamorig:Hips", "mixamorig:Spine", "mixamorig:Spine1"]}).items():
    print(f"  {z:>10}: {r['n']:5d} sommets, confiance moyenne {r['confiance_moyenne']}")
p = etiq.index("LeftArm@120")
m = plis_masque(rest, _lbs(rest, W, M[p]), W, M[p], faces)
vs_plis = np.unique(np.concatenate([np.array(list(faces[k])) for k in np.where(m)[0]])) if m.any() else np.array([], int)
if len(vs_plis) > 0 and len(vs_plis) < len(conf):
    masque = np.zeros(len(conf), bool); masque[vs_plis] = True
    u, pval = mannwhitneyu(conf[masque], conf[~masque], alternative="less")
    print(f"sommets repliés à 120° (LBS) : {int(masque.sum())} ; confiance {conf[masque].mean():.3f} contre {conf[~masque].mean():.3f} ; Mann-Whitney p = {pval:.3g}")

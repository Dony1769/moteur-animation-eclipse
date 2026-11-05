"""Grille de transfert de poids autour d'une articulation (coude, genou), sélection sur l'entraînement.

Pour chaque combinaison (os source -> os cible, rayon, fraction) : transfert sur la base W, correctif ARAP
interpolé à partir des poses d'entraînement (chaîne), puis plis à la pose d'entraînement la plus extrême (120°).
Seul le résultat à 120° sert à choisir ; les poses de test ne sont pas affichées.
Usage : python3 grille_transfert_articulation.py DOSSIER/ BASE.npz CHAINE OS_SOURCE OS_CIBLE X Y Z
"""
import sys, os, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from correctif_arap import arap_cible, _lbs
from plis_numpy import plis_positions
from transfert_epaule import transferer

S, base, chaine, src, dst = sys.argv[1].rstrip("/") + "/", sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5]
articulation = np.array([float(sys.argv[6]), float(sys.argv[7]), float(sys.argv[8])])
d = np.load(S + "donnees7.npz", allow_pickle=True)
rest, M, ar, faces, etiq = d["rest"], d["M"], d["aretes"], d["faces"], list(d["etiquettes"])
os_n = [str(o) for o in d["os"]]
W0 = np.load(base)["W"]; W0 = W0 / W0.sum(1, keepdims=True)
tronc = [os_n.index(n) for n in ("mixamorig:Hips", "mixamorig:Spine", "mixamorig:Spine1", "mixamorig:Neck", "mixamorig:Head")]
def idx(a): return etiq.index(f"{chaine}@{a}")
for rayon in (0.10, 0.16):
    for frac in (0.5,):
        W, n = transferer(W0, rest, os_n, articulation, rayon, frac, os_bras=src, os_epaule=dst)
        ancre = W[:, tronc].sum(1) > 0.99
        p = idx(120)
        _, Pa = arap_cible(rest, W, M[p], ar, ancre, iters=40)
        print(f"{src} -> {dst} r={rayon} f={frac} (zone {n}) : plis à 120° (entraînement, après ARAP) = {plis_positions(rest, Pa, W, M[p], faces)}", flush=True)

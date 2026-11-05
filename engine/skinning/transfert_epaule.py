"""Transfert de poids à l'épaule (phase 4) : le haut du bras est partagé avec l'os de l'épaule.

Constat (erreur 69) : à 120°, les replis du bras (LBS puis ARAP) sont localisés sous le sommet de l'épaule,
dominés par l'os du bras. Un transfert d'une fraction du poids du bras vers l'épaule, dans un rayon
autour de l'articulation, supprime ces replis.
Sélection faite sur la pose d'entraînement (120°) uniquement (règle de l'erreur 59). Les tests (75°, 105°)
ne servent qu'à la vérification.

Usage : python3 transfert_epaule.py W_IN.npz W_OUT.npz DONNEES_REST_OS (rest et os via donnees7.npz) RAYON FRACTION
"""
import sys, numpy as np


def transferer(W, rest, os_n, articulation, rayon, fraction, os_bras="mixamorig:LeftArm",
               os_epaule="mixamorig:LeftShoulder"):
    """Retourne une copie de W, normalisée, avec fraction du poids du bras déplacée vers l'épaule
    pour les sommets à moins de rayon de l'articulation et où le bras a plus de 0,2."""
    W = W / W.sum(1, keepdims=True)
    ia, ie = os_n.index(os_bras), os_n.index(os_epaule)
    d = np.linalg.norm(rest - articulation, axis=1)
    zone = (d < rayon) & (W[:, ia] > 0.2)
    Wm = W.copy()
    t = Wm[zone, ia] * fraction
    Wm[zone, ia] -= t
    Wm[zone, ie] += t
    return Wm, int(zone.sum())


if __name__ == "__main__":
    import json
    entree, sortie, donnees, rayon, fraction = sys.argv[1], sys.argv[2], sys.argv[3], float(sys.argv[4]), float(sys.argv[5])
    d = np.load(donnees, allow_pickle=True)
    os_n = [str(o) for o in d["os"]]
    W = np.load(entree)["W"]
    articulation = np.array([-2.051, -0.001, 1.343])   # épaule gauche, repère armature (os_repos.json)
    Wm, n = transferer(W, d["rest"], os_n, articulation, rayon, fraction)
    np.savez(sortie, W=Wm)
    print("sommets déplacés :", n)

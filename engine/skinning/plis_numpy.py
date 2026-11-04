"""Faces repliées (plis) en numpy, calquée sur engine/skinning/mesure_lbs.faces_repliees.

Une face est repliée si sa normale de Newell en pose est opposée à sa normale de repos
tournée par la matrice 3x3 (colonnes normalisées) de l'os dominant de la face (vote des sommets).

Calibration (corps_haut.blend, Blender) : avant-bras identique sur 6 angles ; bras et jambe à
±4 faces près jusqu'à 120°. Ne pas utiliser sans cette calibration (erreur 51 : sans rotation
de la normale de repos, le compte était gonflé de deux ordres de grandeur).

Usage (module) : plis(rest, W, M, faces) -> nombre de faces repliées.
  rest  : (N,3) positions de repos dans l'espace de l'armature
  W     : (N,B) poids
  M     : (B,4,4) matrices de skinning de la pose (pose * repos^-1)
  faces : liste de boucles de sommets
"""
import numpy as np

def _newell(P, boucle):
    n = np.zeros(3)
    for k in range(len(boucle)):
        a = P[boucle[k]]; b = P[boucle[(k + 1) % len(boucle)]]
        n += np.cross(a, b)
    return n

def _lbs(rest, W, M):
    R4 = np.concatenate([rest, np.ones((len(rest), 1))], 1)
    return np.einsum("ib,bjk,ik->ij", W, M, R4)[:, :3]

def plis(rest, W, M, faces):
    pose = _lbs(rest, W, M)
    dom = W.argmax(1)
    n = 0
    for f in faces:
        boucle = list(f)
        os_ = np.bincount(dom[boucle], minlength=W.shape[1]).argmax()
        R = M[os_, :3, :3]
        R = R / np.linalg.norm(R, axis=0)
        nr = _newell(rest, boucle); npz = _newell(pose, boucle)
        if np.linalg.norm(nr) == 0 or np.linalg.norm(npz) == 0:
            continue
        if npz @ (R @ nr) < 0:
            n += 1
    return n

"""Mesures de pose (phase 4, erreur 92) : plis, étirement, déplacement.

- plis_retournes : FAUSSE MÉTRIQUE (erreur 108). Compare la normale monde au repos à la normale posée ; une
  rotation rigide de plus de 90° la fait basculer sans aucun repli. NE PAS UTILISER. Conservée uniquement pour
  mémoire des anciens chiffres, qui sont à remesurer avec plis_locaux.
- plis_locaux : métrique corrigée (erreur 108). La normale de repos est tournée par la rotation locale de
  peau de la face (Rf, (F,3,3)), puis comparée à la normale posée : un pli est un vrai retournement local.
- etirement_max : rapport maximal longueur posée / longueur au repos, sur toutes les arêtes.
- deplacement : distance max et médiane entre pose et repos (sommets déplacés).
Ces trois mesures sont secondaires à la pénétration, mais toutes trois doivent être rapportées.
"""
import numpy as np


def normales_faces(P, faces):
    N = np.zeros((len(faces), 3))
    for i, f in enumerate(faces):
        pts = P[list(f)]
        n = np.cross(pts[1] - pts[0], pts[2] - pts[0])
        N[i] = n / max(np.linalg.norm(n), 1e-12)
    return N


def plis_locaux(rest, P, faces, Rf):
    """Rf : (F,3,3) rotation locale de peau par face (ex. rotation de l'os de poids maximal, ou moyenne DQS).
    Un pli : n_pose · (Rf n_repos) < 0."""
    Nr = normales_faces(rest, faces)
    Nr_loc = np.einsum("fij,fj->fi", Rf, Nr)
    Np = normales_faces(P, faces)
    return int(np.sum(np.einsum("ij,ij->i", Nr_loc, Np) < 0))


def plis_retournes(rest, P, faces):
    """OBSOLÈTE (erreur 108) : voir plis_locaux."""
    Nr = normales_faces(rest, faces)
    Np = normales_faces(P, faces)
    return int(np.sum(np.einsum("ij,ij->i", Nr, Np) < 0))


def etirement_max(rest, P, aretes):
    i, j = aretes[:, 0], aretes[:, 1]
    L0 = np.linalg.norm(rest[i] - rest[j], axis=1)
    L1 = np.linalg.norm(P[i] - P[j], axis=1)
    return float(np.max(L1 / np.maximum(L0, 1e-9)))


def deplacement(rest, P):
    d = np.linalg.norm(P - rest, axis=1)
    m = d > 1e-9
    return float(d.max()), float(np.median(d[m])) if m.any() else 0.0

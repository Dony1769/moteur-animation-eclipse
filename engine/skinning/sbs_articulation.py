"""Skinning par mélange de rotations (Spherical Blend Skinning, Kavan et al., I3D 2005), pour une
articulation dont tous les os partagent un même pivot c (charnière ou sphère).

Au lieu de mélanger des matrices (LBS, cause des plis et des rétrécissements), on mélange le quaternion
de rotation : q(f) = normalise((1-f)·1 + f·q_θ), puis v' = R(q(f))·(v - c) + c.
Le paramètre f ∈ [0,1] vient de la bande (0 = os parent, 1 = os enfant). QLERP ≈ SLERP (erreur < 8,15°
d'après l'article). Référence : https://users.cs.utah.edu/~ladislav/kavan05spherical/kavan05spherical.pdf
"""
import numpy as np
from scipy.spatial.transform import Rotation as Rot


def qlerp_matrices(f, axe, phi):
    """Matrices (N,3,3) de la rotation q(f), pour f (N,), axe (3,), angle phi (rad)."""
    qf = np.array([np.cos(phi / 2), *(np.sin(phi / 2) * axe)])   # (w,x,y,z), w>0 si |phi|<π
    ident = np.array([1.0, 0, 0, 0])
    q = (1 - f)[:, None] * ident[None] + f[:, None] * qf[None]
    q = q / np.linalg.norm(q, axis=1, keepdims=True)
    # scipy : ordre (x,y,z,w)
    return Rot.from_quat(np.stack([q[:, 1], q[:, 2], q[:, 3], q[:, 0]], 1)).as_matrix()


def deformer_sbs(rest, f, c, axe, phi):
    """Positions déformées : chaque sommet tourne de f·phi (par QLERP) autour de c."""
    Rv = qlerp_matrices(f, axe, phi)
    return np.einsum("nij,nj->ni", Rv, rest - c) + c, Rv


def plis_sbs(rest, pts, faces, f, c, axe, phi):
    """Plis : une face est repliée si sa normale de Newell en pose est opposée à sa normale de repos
    tournée par la rotation moyenne de la face (f moyen sur les sommets de la face)."""
    def newell(P, b):
        v = np.zeros(3)
        for k in range(len(b)):
            v += np.cross(P[b[k]], P[b[(k + 1) % len(b)]])
        return v
    n = 0
    for fc in faces:
        b = list(fc)
        fm = float(f[b].mean())
        Rm = qlerp_matrices(np.array([fm]), axe, phi)[0]
        nr = newell(rest, b); npz = newell(pts, b)
        if np.linalg.norm(nr) == 0 or np.linalg.norm(npz) == 0:
            continue
        if npz @ (Rm @ nr) < 0:
            n += 1
    return n

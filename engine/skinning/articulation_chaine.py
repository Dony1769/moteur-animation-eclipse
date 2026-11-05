"""Articulation en charnière par chaîne de nœuds coaxiaux, générique (genou, coude, cheville).

Entrées : rest (N,3) ; dom (N,) os dominant de repos ; os parent et enfant (indices) ; M (B,4,4) pose
de l'enfant à l'angle θ (matrice du segment enfant, repère armature) ; sous-arbre de l'enfant (indices).
Sortie : poids (N,K+1) pour K+1 nœuds de jonction (nœud j tourne de j·φ/K) ; pivot ; axe ; matrices.
Le pivot et l'axe sont mesurés depuis la matrice de pose (pas choisis).
"""
import numpy as np
from scipy.spatial.transform import Rotation as Rot


def pivot_axe(M):
    R = M[:3, :3]; t = M[:3, 3]
    c = np.linalg.lstsq(np.eye(3) - R, t, rcond=None)[0]
    rv = Rot.from_matrix(R).as_rotvec()
    phi = np.linalg.norm(rv)
    axe = rv / phi if phi > 0 else np.array([1.0, 0, 0])
    return c, axe, phi


def chaine(rest, dom, parent, enfants, M_enfant, K, B, enfant_rigide=False, bissectrice=False, f_custom=None):
    """enfant_rigide=True : tout le sous-arbre enfant tourne d'un bloc (f=1) ; la bande ne s'applique
    qu'au segment parent. Utile quand le segment enfant n'est pas dans l'axe du parent (cheville)."""
    c0, axe, phi = pivot_axe(M_enfant)
    # l'axe de pivot est une droite : on prend le point de cette droite au niveau de la jointure
    # (milieu des centroïdes parent / enfant), sinon la bande tombe hors du maillage
    mp = dom == parent
    me = np.isin(dom, enfants)
    m = 0.5 * (rest[mp].mean(0) + rest[me].mean(0))
    c = c0 + ((m - c0) @ axe) * axe
    dp = rest[mp].mean(0) - c
    dp = dp - (dp @ axe) * axe          # direction du segment parent, dans le plan ⊥ axe
    dp = dp / np.linalg.norm(dp)
    s = (rest - c) @ dp               # >0 côté parent, <0 côté enfant
    if bissectrice:
        # normale du plan de jointure : bissectrice des deux segments (dp et direction de l'enfant)
        me_ = rest[np.isin(dom, enfants)].mean(0) - c
        q = me_ - (me_ @ axe) * axe
        q = q / np.linalg.norm(q)
        m = dp - q
        m = m - (m @ axe) * axe
        m = m / np.linalg.norm(m)
        s = (rest - c) @ m            # >0 côté parent du plan de jointure, <0 côté enfant
    f = np.clip((B - s) / (2 * B), 0, 1)
    if f_custom is not None:
        f = f_custom
    if enfant_rigide:
        f = np.where(np.isin(dom, list(enfants)), 1.0, f)
    sel = np.isin(dom, [parent] + list(enfants))
    W = np.zeros((len(rest), K + 1))
    W[~sel, 0] = 1.0
    x = f[sel] * K
    j0 = np.clip(np.floor(x).astype(int), 0, K - 1)
    a = np.clip(x - j0, 0, 1)
    idx = np.where(sel)[0]
    W[idx, j0] += 1 - a
    W[idx, j0 + 1] += a
    Ms = []
    for j in range(K + 1):
        Rj = Rot.from_rotvec(axe * phi * j / K).as_matrix()
        Mj = np.eye(4); Mj[:3, :3] = Rj; Mj[:3, 3] = c - Rj @ c
        Ms.append(Mj)
    return W, np.array(Ms), dict(pivot=c, axe=axe, phi=phi, dp=dp)


def deformer(rest, W, Ms):
    R4 = np.concatenate([rest, np.ones((len(rest), 1))], 1)
    return np.einsum("ib,bjk,ik->ij", W, Ms, R4)[:, :3]

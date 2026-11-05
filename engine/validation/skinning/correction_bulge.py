"""Variante anti-gonflement pour le DQS : Kim & Han, « Bulging-free dual quaternion skinning », Comput. Anim. Virtual
Worlds 2014 (méthode décrite dans l'implémentation de R. Vaillant, rodolphe-vaillant.fr/entry/72, source NON officielle).

Pour chaque sommet : os dominant j ; d_repos = distance du sommet de repos au segment de j au repos ;
d_pose = distance du sommet posé (DQS) au segment de j posé. Si d_pose > d_repos, le décalage est ramené à
d_repos : p' = proj + (d_repos / d_pose) * (p - proj).

Segment : tête de l'os -> tête de l'os suivant de la chaîne (Mixamo), sinon 0,10 m selon l'axe Y de l'os.
Approximation déclarée : les longueurs réelles d'os ne sont pas dans les données.
"""
import numpy as np

SUIVANT = {
    "mixamorig:Hips": "mixamorig:Spine", "mixamorig:Spine": "mixamorig:Spine1", "mixamorig:Spine1": "mixamorig:Neck",
    "mixamorig:Neck": "mixamorig:Head",
    "mixamorig:LeftUpLeg": "mixamorig:LeftLeg", "mixamorig:LeftLeg": "mixamorig:LeftFoot",
    "mixamorig:RightUpLeg": "mixamorig:RightLeg", "mixamorig:RightLeg": "mixamorig:RightFoot",
    "mixamorig:LeftArm": "mixamorig:LeftForeArm", "mixamorig:LeftForeArm": "mixamorig:LeftHand",
    "mixamorig:RightArm": "mixamorig:RightForeArm", "mixamorig:RightForeArm": "mixamorig:RightHand",
}
LONGUEUR_DEFAUT = 0.10


def segments(B, noms, pose_T=None):
    """Retourne (A, Bp) (J,3) extrémités du segment de chaque os, au repos ou posé (pose_T : (J,4,4))."""
    J = len(noms)
    A = np.zeros((J, 3)); Bp = np.zeros((J, 3))
    for j, n in enumerate(noms):
        h = B[j][:3, 3]
        if n in SUIVANT and SUIVANT[n] in noms:
            t = B[noms.index(SUIVANT[n])][:3, 3]
        else:
            t = h + LONGUEUR_DEFAUT * B[j][:3, 1]
        A[j], Bp[j] = h, t
    if pose_T is not None:
        A2 = np.einsum("jab,jb->ja", pose_T[:, :3, :3], A) + pose_T[:, :3, 3]
        B2 = np.einsum("jab,jb->ja", pose_T[:, :3, :3], Bp) + pose_T[:, :3, 3]
        return A2, B2
    return A, Bp


def dist_point_segment(P, A, Bp):
    AB = Bp - A
    t = np.clip(np.einsum("nj,nj->n", P - A, AB) / np.maximum(np.einsum("nj,nj->n", AB, AB), 1e-18), 0, 1)
    proj = A + t[:, None] * AB
    return np.linalg.norm(P - proj, axis=1), proj


def corriger(pos_dqs, rest, Wi, Ww, B, pose_T, noms):
    dom = np.take_along_axis(Wi, np.argmax(np.where(Wi >= 0, Ww, -1.0), axis=1)[:, None], axis=1)[:, 0]
    dom = np.where(dom >= 0, dom, 0)
    Ar, Br = segments(B, noms)
    Ap, Bq = segments(B, noms, pose_T)
    d_rep, _ = dist_point_segment(rest, Ar[dom], Br[dom])
    d_pos, proj = dist_point_segment(pos_dqs, Ap[dom], Bq[dom])
    gonfle = d_pos > d_rep
    fac = np.where(gonfle, d_rep / np.maximum(d_pos, 1e-18), 1.0)
    out = proj + fac[:, None] * (pos_dqs - proj)
    out = np.where(gonfle[:, None], out, pos_dqs)
    return out, {"sommets_corriges": int(gonfle.sum()), "part_corriges": float(gonfle.mean())}

"""Décomposition torsion/flexion d'un os auxiliaire de torsion (phase 4, erreur 68).

Un auxiliaire de torsion ne doit tourner qu'autour de l'axe de l'os (torsion pure) ; sa flexion
(swing) est physiquement incorrecte et produit les plis du bras supérieur à grand angle.
Méthode : décomposition swing-twist (Dobrowolski, 2015 ; Jacobson et al., SIGGRAPH Asia 2011, décrit
la séparation torsion/flexion des os élastiques) appliquée à la rotation de l'auxiliaire dans le repère armature.

- pivot : point fixe de la transformation de l'épaule (LeftArm), résolu par moindres carrés (I - R) p = t ;
- axe : axe principal des sommets de repos dominés par le bras et son auxiliaire (ACP) ;
- torsion : composante de la rotation autour de cet axe ; on remplace M_aux par la torsion seule, pivotée
  sur p.
"""
import numpy as np


def pivot_fixe(M):
    """Point fixe d'une transformation affine 4x4 (rotation autour d'un pivot) : moindres carrés."""
    R, t = M[:3, :3], M[:3, 3]
    A = np.eye(3) - R
    p, *_ = np.linalg.lstsq(A, t, rcond=None)
    return p


def axe_os(rest, poids_bras):
    """Axe principal (ACP) des sommets de repos pondérés par leur appartenance au bras."""
    c = np.average(rest, axis=0, weights=poids_bras)
    X = (rest - c) * np.sqrt(poids_bras)[:, None]
    _, _, Vt = np.linalg.svd(X, full_matrices=False)
    a = Vt[0]
    return a / np.linalg.norm(a)


def swing_twist(R, a):
    """Décompose une rotation R (3x3) en (swing 3x3, angle de torsion en radians) autour de l'axe a.

    q = swing * twist, twist = rotation pure autour de a (projection du quaternion sur a).
    """
    from scipy.spatial.transform import Rotation
    q = Rotation.from_matrix(R).as_quat()          # (x, y, z, w)
    v, w = q[:3], q[3]
    proj = np.dot(v, a) * a
    tw = np.array([*proj, w])
    if np.linalg.norm(tw) < 1e-9:                  # rotation de 180° hors de l'axe : torsion indéfinie
        return Rotation.from_quat(q).as_matrix(), 0.0
    tw = tw / np.linalg.norm(tw)
    angle = 2 * np.arctan2(np.dot(tw[:3], a), tw[3])
    sw = Rotation.from_quat(q) * Rotation.from_quat(tw).inv()
    return sw.as_matrix(), float(angle)


def epaule_sur_axe(rest, poids_bras, a):
    """Articulation de l'épaule : extrémité haute de l'axe du bras (sommets du bras projetés sur a).

    Un point fixe de rotation n'est pas unique (toute la droite de l'axe de rotation est fixe) : le pivot
    doit être pris sur l'axe de l'os, à l'extrémité du bras côté épaule (2e percentile des projections).
    """
    c = np.average(rest, axis=0, weights=poids_bras)
    s = (rest - c) @ a
    w = poids_bras > 0.5
    s_haut = np.percentile(s[w], 2)
    return c + a * s_haut


def aux_torsion_seule(M_aux, rest, poids_bras):
    """Remplace la matrice d'un auxiliaire par sa seule torsion autour de l'axe du bras, pivotée à l'épaule."""
    from scipy.spatial.transform import Rotation
    a = axe_os(rest, poids_bras)
    p = epaule_sur_axe(rest, poids_bras, a)
    _, angle = swing_twist(M_aux[:3, :3], a)
    Rt = Rotation.from_rotvec(a * angle).as_matrix()
    out = np.eye(4)
    out[:3, :3] = Rt
    out[:3, 3] = p - Rt @ p
    return out, angle

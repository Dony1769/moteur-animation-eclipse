"""Critères mécaniques d'une articulation (charnière) à partir de positions Blender.

- écart Blender / numpy de la LBS de chaîne ;
- plis (règle de Newell, mêmes conventions que plis_numpy) ;
- rigidité : écart de distances entre paires de sommets d'un même segment (parent, enfant) ;
- section au joint : aire de la coupe ⊥ à l'axe moyen (rest et pose), rapport pose/repos.
"""
import sys, numpy as np
from scipy.spatial import ConvexHull
from scipy.spatial.transform import Rotation as Rot
sys.path.insert(0, "/home/claude/moteur_3_0/engine/skinning")
from articulation_chaine import chaine, deformer
from plis_numpy import plis_positions


def aire(P, axe, m):
    a = axe / np.linalg.norm(axe)
    t = np.array([1.0, 0, 0]) if abs(a[0]) < 0.9 else np.array([0, 1.0, 0])
    u = np.cross(a, t); u /= np.linalg.norm(u); v = np.cross(a, u)
    return ConvexHull(np.stack([P[m] @ u, P[m] @ v], 1)).volume


def evaluer(rest, faces, dom_parent, dom_enfants, Wc, Ms, pts, th, info, B, rng):
    # dom_parent / dom_enfants : masques des sommets du segment parent / enfant (et de leur sous-arbre)
    # rigidité : segments parent et enfant (hors bande)
    dp = info["dp"]
    s = (rest - info["pivot"]) @ dp
    parent_rigide = (dom_parent) & (s > B + 0.03)
    # direction propre du segment enfant (le pied est horizontal, pas « sous » le genou)
    q = rest[dom_enfants].mean(0) - info["pivot"]
    q = q - (q @ info["axe"]) * info["axe"]
    q = q / np.linalg.norm(q)
    s_enf = (rest - info["pivot"]) @ q
    enfant_rigide = (dom_enfants) & (s_enf > B + 0.03)
    def rig(mask):
        idx = np.where(mask)[0]
        if len(idx) < 10:
            return None  # segment trop court hors bande pour mesurer la rigidité
        a = rng.choice(idx, 4000); b = rng.choice(idx, 4000)
        return float(np.abs(np.linalg.norm(pts[a] - pts[b], axis=1) - np.linalg.norm(rest[a] - rest[b], axis=1)).max() * 1000)
    # plis : dominant = nœud de la chaîne
    pl = plis_positions(rest, pts, np.eye(len(Ms))[Wc.argmax(1)], Ms, faces)
    # section au joint
    R = Rot.from_rotvec(info["axe"] * np.radians(th)).as_matrix()
    q_rest = -dp
    q_pose = R @ q_rest
    axe_rest = dp
    axe_pose = dp - q_pose
    m = (np.abs(s) < 0.01) & (dom_parent | dom_enfants)   # tranche des seuls sommets du membre
    sec = aire(pts, axe_pose, m) / aire(rest, axe_rest, m)
    return dict(plis=int(pl), rigidite_parent_mm=(None if rig(parent_rigide) is None else round(rig(parent_rigide), 3)),
                rigidite_enfant_mm=(None if rig(enfant_rigide) is None else round(rig(enfant_rigide), 3)), section=round(float(sec), 3))

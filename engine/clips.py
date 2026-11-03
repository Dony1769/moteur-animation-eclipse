"""Clips procéduraux sur le squelette Mixamo : un seul FBX suffit.

Fonctions :
- clip_pose(arm, nom, n, poses) : crée une action en posant les os image par image (rotations XYZ).
- marche(t) / victoire(t) : fonctions de pose, t dans [0, 1) sur un cycle.
Les os sont nommés « mixamorig:<nom> » (import FBX Mixamo, orientation automatique).
"""
import math
import bpy
from mathutils import Euler

PREFIXE = "mixamorig:"


def _os(arm, nom):
    return arm.pose.bones.get(PREFIXE + nom)


def clip_pose(arm, nom, n, poses):
    """Crée une action de n images (quaternions). poses(t) renvoie {os: (x, y, z)} en radians, t = image / n."""
    ad = arm.animation_data_create()
    action = bpy.data.actions.new(nom)
    ad.action = action
    for pb in arm.pose.bones:
        pb.rotation_mode = "QUATERNION"
    for f in range(n):
        for nom_os, angles in poses(f / n).items():
            pb = _os(arm, nom_os)
            if pb is None:
                continue
            # quaternions : même mode que les clips Mixamo, sinon l'action serait ignorée
            pb.rotation_quaternion = Euler(angles, "XYZ").to_quaternion()
            pb.keyframe_insert("rotation_quaternion", frame=f + 1)
    if action.slots:
        ad.action_slot = action.slots[0]
    ad.action = None
    return action


def marche(t):
    """Cycle de marche : jambes et bras en opposition, genoux qui se plient à la phase de balancement."""
    a = 2 * math.pi * t
    pose = {}
    for cote, dec in (("LeftUpLeg", 0.0), ("RightUpLeg", math.pi)):
        p = a + dec
        pose[cote] = (0.42 * math.sin(p), 0.0, 0.0)
    for cote, dec in (("LeftLeg", 0.0), ("RightLeg", math.pi)):
        p = a + dec
        pose[cote] = (-0.25 - 0.25 * math.cos(p), 0.0, 0.0)
    for cote, dec in (("LeftArm", math.pi), ("RightArm", 0.0)):
        p = a + dec
        pose[cote] = (-0.35 * math.sin(p), 0.0, 0.0)
    for cote in ("LeftForeArm", "RightForeArm"):
        pose[cote] = (-0.3, 0.0, 0.0)
    pose["Spine"] = (0.03 * math.sin(2 * a), 0.0, 0.0)
    return pose


def victoire(t):
    """Pose de victoire : bras levé avec l'épée, légère respiration."""
    souffle = 0.03 * math.sin(2 * math.pi * t)
    return {
        "LeftArm": (-2.4 + souffle, 0.0, -0.2),
        "LeftForeArm": (-0.3, 0.0, 0.0),
        "RightArm": (0.2, 0.0, 0.2),
        "RightForeArm": (-0.5, 0.0, 0.0),
        "Spine": (-0.05 + souffle, 0.0, 0.0),
    }

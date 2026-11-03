"""Retargeting CMU -> rig Rigify (base Vitruvian, CC0). Exécuté dans Blender.

Même méthode que moteur/mocap.py (delta de rotation monde par rapport à une pose neutre de la source,
composé avec le repos de la cible), mais avec les noms d'os Rigify. Les contraintes des os DEF (qui les
collent aux os de contrôle) sont retirées : la pose est posée directement sur les os déformants.
"""
import math

import bpy
from mathutils import Matrix, Vector

DOSSIER = "/home/claude/moteur3d/mocap"

# os CMU -> os DEF Rigify
CARTE = {
    "Hips": "DEF-spine", "LowerBack": "DEF-spine.001", "Spine": "DEF-spine.002",
    "Spine1": "DEF-spine.003", "Neck": "DEF-spine.004", "Head": "DEF-spine.005",
    "LeftArm": "DEF-upper_arm.L", "LeftForeArm": "DEF-forearm.L", "LeftHand": "DEF-hand.L",
    "RightArm": "DEF-upper_arm.R", "RightForeArm": "DEF-forearm.R", "RightHand": "DEF-hand.R",
    "LeftUpLeg": "DEF-thigh.L", "LeftLeg": "DEF-shin.L", "LeftFoot": "DEF-foot.L", "LeftToeBase": "DEF-toe.L",
    "RightUpLeg": "DEF-thigh.R", "RightLeg": "DEF-shin.R", "RightFoot": "DEF-foot.R", "RightToeBase": "DEF-toe.R",
}
DST2SRC = {v: k for k, v in CARTE.items()}

# ordre parent -> enfant
ORDRE = [
    "DEF-spine", "DEF-spine.001", "DEF-spine.002", "DEF-spine.003", "DEF-spine.004", "DEF-spine.005",
    "DEF-upper_arm.L", "DEF-forearm.L", "DEF-hand.L",
    "DEF-upper_arm.R", "DEF-forearm.R", "DEF-hand.R",
    "DEF-thigh.L", "DEF-shin.L", "DEF-foot.L", "DEF-toe.L",
    "DEF-thigh.R", "DEF-shin.R", "DEF-foot.R", "DEF-toe.R",
]
BRAS = ("DEF-upper_arm.L", "DEF-forearm.L", "DEF-hand.L", "DEF-upper_arm.R", "DEF-forearm.R", "DEF-hand.R")
DOIGTS_NOMS = [f"DEF-f_{d}.0{i}.{c}" for d in ("index", "middle", "ring", "pinky") for i in (1, 2, 3) for c in ("L", "R")]
DOIGTS_NOMS += [f"DEF-thumb.0{i}.{c}" for i in (1, 2, 3) for c in ("L", "R")]


def retirer_contraintes(arm):
    """Retire les contraintes des os DEF et des doigts (ce sont elles qui les suivent sinon)."""
    for pb in arm.pose.bones:
        if pb.name.startswith("DEF-"):
            for c in list(pb.constraints):
                pb.constraints.remove(c)


def _importer(fichier):
    avant = set(bpy.data.objects)
    bpy.ops.import_anim.bvh(
        filepath=f"{DOSSIER}/{fichier}", axis_forward="-Z", axis_up="Y", global_scale=1.0,
        frame_start=1, use_fps_scale=False, update_scene_fps=False, update_scene_duration=False,
        use_cyclic=False, rotate_mode="NATIVE",
    )
    return [o for o in bpy.data.objects if o not in avant and o.type == "ARMATURE"][0]


def _alignement(cmu):
    b = cmu.data.bones
    avant = b["LeftToeBase"].head_local - b["LeftFoot"].head_local
    avant.z = 0.0
    A = avant.normalized().rotation_difference(Vector((0.0, -1.0, 0.0))).to_matrix()
    lateral = A @ (b["LeftUpLeg"].head_local - b["RightUpLeg"].head_local)
    return A, lateral


def _angle_bas(d):
    return math.atan2(d.x, -d.z)


def pendre_bras(arm):
    """Rotations de repos : bras le long du corps et léger écart vers l'extérieur (0,2 rad)."""
    rep = {}
    for cote in ("L", "R"):
        os_ = arm.data.bones[f"DEF-upper_arm.{cote}"]
        d = (os_.tail_local - os_.head_local).normalized()
        meilleur = None
        for signe in (1.0, -1.0):
            C = Matrix.Rotation(signe * _angle_bas(d), 3, "Y")
            err = (C @ d - Vector((0.0, 0.0, -1.0))).length
            if meilleur is None or err < meilleur[0]:
                meilleur = (err, C)
        exterieur = -1.0 if cote == "R" else 1.0
        meilleur_ecart = None
        for signe in (1.0, -1.0):
            E = Matrix.Rotation(signe * 0.2, 3, "Y") @ meilleur[1]
            score = (E @ d).x * exterieur
            if meilleur_ecart is None or score > meilleur_ecart[0]:
                meilleur_ecart = (score, E)
        for nom in (f"DEF-upper_arm.{cote}", f"DEF-forearm.{cote}", f"DEF-hand.{cote}"):
            rep[nom] = meilleur_ecart[1]
        print("BRAS", cote, "erreur", round(meilleur[0], 3))
    return rep


def _pose(cmu, arm, A, Ai, echelle, image, ref, rep, bassin_neutre):
    bpy.context.scene.frame_set(image)
    vl = bpy.context.view_layer
    vl.update()
    res = {}
    dz = (A @ (cmu.pose.bones["Hips"].matrix.translation - bassin_neutre)).z * echelle
    for dst in ORDRE:
        src = DST2SRC.get(dst)
        if src is None:
            continue
        pb = arm.pose.bones[dst]
        pb.rotation_mode = "QUATERNION"
        P = cmu.pose.bones[src].matrix.to_3x3()
        D = A @ P @ ref[src].inverted() @ Ai
        Rd = arm.data.bones[dst].matrix_local.to_3x3()
        if dst in rep:
            Rd = rep[dst] @ Rd
        M = D @ Rd
        if dst == "DEF-spine":
            tete = arm.data.bones["DEF-spine"].head_local + Vector((0.0, 0.0, dz))
        else:
            tete = pb.matrix.translation.copy()
        pb.matrix = Matrix.Translation(tete) @ M.to_4x4()
        vl.update()
        res[dst] = (pb.rotation_quaternion.copy(), pb.location.copy())
    return res


def tout_poser(arm, segments, rep, nb_images_defaut=149):
    """Calcule la pose de chaque image de la scène. segments : (debut, fin, fichier, image CMU, pas)."""
    resultats = {}
    for debut, fin, fichier, image0, pas in segments:
        cmu = _importer(fichier)
        A, lateral = _alignement(cmu)
        if lateral.x < 0:
            raise RuntimeError(f"{fichier}: gauche et droite inversées ({lateral})")
        Ai = A.inverted()
        echelle = arm.data.bones["DEF-thigh.L"].length / cmu.data.bones["LeftUpLeg"].length
        nb = int(cmu.animation_data.action.frame_range[1]) if cmu.animation_data else nb_images_defaut
        bpy.context.scene.frame_set(1)
        bpy.context.view_layer.update()
        ref = {src: cmu.pose.bones[src].matrix.to_3x3().copy() for src in CARTE}
        bassin = cmu.pose.bones["Hips"].matrix.translation.copy()
        for f in range(debut, fin + 1):
            image = image0 + ((f - debut) * pas) % nb
            resultats[f] = _pose(cmu, arm, A, Ai, echelle, image, ref, rep, bassin)
        bpy.data.objects.remove(cmu, do_unlink=True)
        print("CLIP", fichier, "echelle", round(echelle, 3))
    return resultats

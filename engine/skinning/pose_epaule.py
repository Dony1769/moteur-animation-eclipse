"""Pose réaliste de l'épaule : rotation répartie entre l'os d'épaule (1/3) et le bras (2/3).

Exporte, pour chaque angle total, les positions déformées (armature) et les matrices de skinning M,
pour comparer aux poses où le seul humérus tourne (erreur 61 : protocole).
Usage : blender -b --factory-startup --disable-autoexec -P engine/skinning/pose_epaule.py -- SOURCE.blend SORTIE.npz
"""
import sys
import bpy
import numpy as np
sys.path.insert(0, "/home/claude/moteur_3_0/engine/skinning")
import mesure_lbs as m

argv = sys.argv[sys.argv.index("--") + 1:]
src, sortie = argv[0], argv[1]
bpy.ops.wm.open_mainfile(filepath=src)
corps = max([o for o in bpy.data.objects if o.type == "MESH"], key=lambda o: len(o.data.vertices))
arm = [o for o in bpy.data.objects if o.type == "ARMATURE"][0]
for mod in corps.modifiers:
    if mod.type != "ARMATURE":
        mod.show_viewport = False
        mod.show_render = False
AXE = (0, 1, 0)
ANGLES = [0, 60, 75, 90, 105, 120]
dg = bpy.context.evaluated_depsgraph_get
inv = arm.matrix_world.inverted()
out = {}
for a in ANGLES:
    # rotation totale a : 1/3 sur l'épaule, 2/3 sur le bras
    r_epaule = m.poser(arm, "mixamorig:LeftShoulder", AXE, a / 3.0)
    r_bras = m.poser(arm, "mixamorig:LeftArm", AXE, 2.0 * a / 3.0)
    bpy.context.view_layer.update()
    ev = corps.evaluated_get(dg())
    me = ev.to_mesh()
    pts = np.array([list(inv @ (corps.matrix_world @ v.co)) for v in me.vertices])
    ev.to_mesh_clear()
    # matrices de skinning M_b = pose_b * repos_b^-1 (repère armature), mêmes définitions que exporter_poids.py
    noms = [b.name for b in arm.data.bones]
    M = np.zeros((len(noms), 4, 4))
    for ib, n in enumerate(noms):
        rep = arm.matrix_world @ arm.pose.bones[n].bone.matrix_local
        rep_inv = (rep).inverted()
        M[ib] = np.array(inv @ (arm.matrix_world @ arm.pose.bones[n].matrix) @ rep_inv)
    out[f"pts_{a}"] = pts
    out[f"M_{a}"] = M
    out["noms"] = np.array(noms)
    # restaure la pose
    arm.pose.bones["mixamorig:LeftArm"].matrix = r_bras
    arm.pose.bones["mixamorig:LeftShoulder"].matrix = r_epaule
    bpy.context.view_layer.update()
    print("EPAULE", a, len(pts), flush=True)
np.savez(sortie, **out)
print("EPAULE_OK", sortie)

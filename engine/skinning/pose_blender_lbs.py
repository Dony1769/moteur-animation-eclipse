import sys, math, bpy, numpy as np
from mathutils import Matrix, Vector
sys.path.insert(0, "/home/claude/moteur_3_0/engine/skinning")
import mesure_lbs as m
argv = sys.argv[sys.argv.index("--") + 1:]
sortie = argv[0]
corps = max([o for o in bpy.data.objects if o.type == "MESH"], key=lambda o: len(o.data.vertices))
arm = [o for o in bpy.data.objects if o.type == "ARMATURE"][0]
for mod in corps.modifiers:
    if mod.type != "ARMATURE":
        mod.show_viewport = False
        mod.show_render = False
CH = [("mixamorig:LeftArm", (0, 1, 0)), ("mixamorig:LeftForeArm", (0, 1, 0)), ("mixamorig:LeftLeg", (1, 0, 0))]
ANG = [0, 60, 75, 90, 105, 120]
dg = bpy.context.evaluated_depsgraph_get
out = {}
inv = arm.matrix_world.inverted()
for nom, axe in CH:
    for a in ANG:
        repos = m.poser(arm, nom, axe, a)
        bpy.context.view_layer.update()
        ev = corps.evaluated_get(dg())
        me = ev.to_mesh()
        pts = np.array([list(inv @ (corps.matrix_world @ v.co)) for v in me.vertices])
        ev.to_mesh_clear()
        out[f"{nom}_{a}"] = pts
        arm.pose.bones[nom].matrix = repos
        bpy.context.view_layer.update()
        print("POSE", nom, a, len(pts), flush=True)
np.savez(sortie, **out)
print("POSE_OK", sortie)

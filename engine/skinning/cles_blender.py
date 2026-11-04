import sys, numpy as np, bpy
from mathutils import Vector
sys.path.insert(0, "/home/claude/moteur_3_0/engine/skinning")
import mesure_lbs as m
argv = sys.argv[sys.argv.index("--") + 1:]
cles_npz, sortie = argv[0], argv[1]
corps = max([o for o in bpy.data.objects if o.type == "MESH"], key=lambda o: len(o.data.vertices))
arm = [o for o in bpy.data.objects if o.type == "ARMATURE"][0]
for mod in corps.modifiers:
    if mod.type != "ARMATURE":
        mod.show_viewport = False; mod.show_render = False
print("SHAPE_KEYS_AVANT", [k.name for k in corps.data.shape_keys.key_blocks] if corps.data.shape_keys else None)
if corps.data.shape_keys is None:
    corps.shape_key_add(name="Basis", from_mix=False)
cw, aw = corps.matrix_world.copy(), arm.matrix_world.copy()
inv_c = cw.inverted(); inv_a = aw.inverted()
C = np.load(cles_npz)
CH = ["mixamorig:LeftArm", "mixamorig:LeftForeArm", "mixamorig:LeftLeg"]
basis = corps.data.shape_keys.key_blocks["Basis"]
for kb0 in corps.data.shape_keys.key_blocks:
    if kb0.name != "Basis":
        kb0.value = 0.0; kb0.mute = True   # clés de référence désactivées : mesure LBS + nos clés seulement
verts = corps.data.vertices
x_arm = [inv_a @ (cw @ v.co) for v in verts]          # repos, espace armature
keys = {}
for nom in CH:
    for a in (60, 90, 120):
        kb = corps.shape_key_add(name=f"ARAP_{nom[10:]}_{a}", from_mix=False)
        d = C[f"{nom}_{a}"]
        for i, v in enumerate(verts):
            tgt = aw @ (x_arm[i] + Vector(d[i]))
            kb.data[i].co = inv_c @ tgt
        kb.relative_key = basis
        kb.value = 0.0
        keys[(nom, a)] = kb
dg = bpy.context.evaluated_depsgraph_get
ANG = [0, 60, 75, 90, 105, 120]
out = {}
for nom, axe in [(n, ax) for n, ax in [("mixamorig:LeftArm", (0,1,0)), ("mixamorig:LeftForeArm", (0,1,0)), ("mixamorig:LeftLeg", (1,0,0))]]:
    for T in ANG:
        for (n2, a), kb in keys.items():
            kb.value = 0.0
        if T in (60, 90, 120) and T != 0:
            keys[(nom, T)].value = 1.0
        elif T == 75:
            keys[(nom, 60)].value = 0.5; keys[(nom, 90)].value = 0.5
        elif T == 105:
            keys[(nom, 90)].value = 0.5; keys[(nom, 120)].value = 0.5
        repos = m.poser(arm, nom, axe, T)
        bpy.context.view_layer.update()
        ev = corps.evaluated_get(dg()); me = ev.to_mesh()
        out[f"{nom}_{T}"] = np.array([list(inv_a @ (cw @ v.co)) for v in me.vertices])
        ev.to_mesh_clear()
        arm.pose.bones[nom].matrix = repos
        bpy.context.view_layer.update()
        print("CLE_POSE", nom, T, flush=True)
for kb in keys.values(): kb.value = 0.0
np.savez(sortie, **out)
print("CLES_BLENDER_OK", sortie)

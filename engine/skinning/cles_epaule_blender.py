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
if corps.data.shape_keys is None:
    corps.shape_key_add(name="Basis", from_mix=False)
basis = corps.data.shape_keys.key_blocks["Basis"]
for kb0 in corps.data.shape_keys.key_blocks:
    if kb0.name != "Basis":
        kb0.value = 0.0; kb0.mute = True
cw, aw = corps.matrix_world.copy(), arm.matrix_world.copy()
inv_c = cw.inverted(); inv_a = aw.inverted()
C = np.load(cles_npz)
verts = corps.data.vertices
x_arm = [inv_a @ (cw @ v.co) for v in verts]
keys = {}
for a in (60, 90, 120):
    kb = corps.shape_key_add(name=f"EPAULE_{a}", from_mix=False)
    d = C[f"epaule_{a}"]
    for i in range(len(verts)):
        kb.data[i].co = inv_c @ (aw @ (x_arm[i] + Vector(d[i])))
    kb.relative_key = basis
    kb.value = 0.0
    keys[a] = kb
dg = bpy.context.evaluated_depsgraph_get
out = {}
AXE = (0, 1, 0)
for T in (60, 75, 90, 105, 120):
    for kb in keys.values(): kb.value = 0.0
    if T in (60, 90, 120):
        keys[T].value = 1.0
    elif T == 75:
        keys[60].value = 0.5; keys[90].value = 0.5
    elif T == 105:
        keys[90].value = 0.5; keys[120].value = 0.5
    r_e = m.poser(arm, "mixamorig:LeftShoulder", AXE, T / 3.0)
    r_b = m.poser(arm, "mixamorig:LeftArm", AXE, 2.0 * T / 3.0)
    bpy.context.view_layer.update()
    ev = corps.evaluated_get(dg()); me = ev.to_mesh()
    out[f"pts_{T}"] = np.array([list(inv_a @ (cw @ v.co)) for v in me.vertices])
    ev.to_mesh_clear()
    arm.pose.bones["mixamorig:LeftArm"].matrix = r_b
    arm.pose.bones["mixamorig:LeftShoulder"].matrix = r_e
    bpy.context.view_layer.update()
    print("EPAULE_CLE", T, flush=True)
for kb in keys.values(): kb.value = 0.0
np.savez(sortie, **out)
print("EPAULE_CLES_BLENDER_OK", sortie)

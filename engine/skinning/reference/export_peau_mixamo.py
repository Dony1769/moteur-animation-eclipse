import bpy, sys, json
import numpy as np
argv = sys.argv[sys.argv.index("--")+1:]
fichier, sortie = argv[0], argv[1]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=fichier, automatic_bone_orientation=False)
arm = max([o for o in bpy.data.objects if o.type == 'ARMATURE'], key=lambda a: len(a.pose.bones))
corps = max([o for o in bpy.data.objects if o.type == 'MESH'], key=lambda o: len(o.data.vertices))
for mod in corps.modifiers:
    if mod.type != 'ARMATURE': mod.show_viewport = False; mod.show_render = False
scn = bpy.context.scene
depsgraph = bpy.context.evaluated_depsgraph_get
noms = ["LeftUpLeg", "LeftLeg", "LeftFoot", "Hips", "LeftArm", "LeftForeArm", "LeftHand"]
def os_(n):
    for pb in arm.pose.bones:
        if pb.name.split(":")[-1] == n: return pb
frames = list(range(scn.frame_start, scn.frame_end + 1, 5))
out = {"frames": np.array(frames), "faces": None}
V = []; H = []
inv = np.array(arm.matrix_world.inverted())
for f in frames:
    scn.frame_set(f)
    ev = corps.evaluated_get(depsgraph()); me = ev.to_mesh()
    V.append(np.array([list(corps.matrix_world @ v.co) for v in me.vertices]))
    ev.to_mesh_clear()
    H.append(np.array([list(arm.matrix_world @ os_(n).head) for n in noms]))
faces = [list(p.vertices) for p in corps.data.polygons]
out["V"] = np.array(V); out["H"] = np.array(H); out["noms"] = np.array(noms)
out["faces"] = np.array([f for f in faces if len(f) == 3]) if all(len(f) == 3 for f in faces) else np.array([f[:3] for f in faces])
np.savez(sortie, **out)
print("EXPORT_OK", len(frames), out["V"].shape, out["faces"].shape, flush=True)

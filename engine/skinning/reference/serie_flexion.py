import bpy, sys, json, math
argv = sys.argv[sys.argv.index("--")+1:]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=argv[0], automatic_bone_orientation=False)
A = max([o for o in bpy.data.objects if o.type == 'ARMATURE'], key=lambda a: len(a.pose.bones))
def os_(n): return [pb for pb in A.pose.bones if pb.name.split(":")[-1] == n][0]
def flex(p, d):
    h = A.matrix_world @ os_(p).head; j = A.matrix_world @ os_(d).head; t = A.matrix_world @ os_(d).tail
    u = (j-h).normalized(); v = (t-j).normalized()
    return 180.0 - math.degrees(math.acos(max(-1,min(1,-u.dot(v)))))
scn = bpy.context.scene; out = {"frames": [], "coude_gauche": [], "coude_droit": [], "genou_gauche": [], "genou_droit": []}
for f in range(scn.frame_start, scn.frame_end+1):
    scn.frame_set(f); bpy.context.view_layer.update()
    out["frames"].append(f)
    out["coude_gauche"].append(round(flex("LeftArm","LeftForeArm"),2))
    out["coude_droit"].append(round(flex("RightArm","RightForeArm"),2))
    out["genou_gauche"].append(round(flex("LeftUpLeg","LeftLeg"),2))
    out["genou_droit"].append(round(flex("RightUpLeg","RightLeg"),2))
json.dump(out, open(argv[1], "w"))
print("OK")

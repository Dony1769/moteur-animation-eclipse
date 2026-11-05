import bpy, sys, json, math
from mathutils import Vector
argv = sys.argv[sys.argv.index("--")+1:]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=argv[0], automatic_bone_orientation=False)
A = max([o for o in bpy.data.objects if o.type == 'ARMATURE'], key=lambda a: len(a.pose.bones))
def os_(n): return [pb for pb in A.pose.bones if pb.name.split(":")[-1] == n][0]
scn = bpy.context.scene
Z = Vector((0,0,1))
res = {"hanche_gauche_cuisse_depuis_verticale_deg": [], "epaule_gauche_bras_depuis_verticale_deg": [],
       "epaule_droite_bras_depuis_verticale_deg": [], "bras_gauche_depuis_axe_tronc_deg": []}
for f in range(scn.frame_start, scn.frame_end+1):
    scn.frame_set(f); bpy.context.view_layer.update()
    W = lambda pb, t="head": A.matrix_world @ getattr(pb, t)
    hanche = W(os_("LeftUpLeg")); genou = W(os_("LeftLeg"))
    cuisse = (genou - hanche).normalized()
    res["hanche_gauche_cuisse_depuis_verticale_deg"].append(math.degrees(math.acos(max(-1,min(1,cuisse.dot(-Z))))))
    ep_g = W(os_("LeftArm")); ep_d = W(os_("RightArm"))
    coude_g = W(os_("LeftForeArm")); coude_d = W(os_("RightForeArm"))
    bg = (coude_g - ep_g).normalized(); bd = (coude_d - ep_d).normalized()
    res["epaule_gauche_bras_depuis_verticale_deg"].append(math.degrees(math.acos(max(-1,min(1,bg.dot(-Z))))))
    res["epaule_droite_bras_depuis_verticale_deg"].append(math.degrees(math.acos(max(-1,min(1,bd.dot(-Z))))))
    tronc = (W(os_("Neck")) - W(os_("Hips"))).normalized()
    res["bras_gauche_depuis_axe_tronc_deg"].append(math.degrees(math.acos(max(-1,min(1,bg.dot(-tronc))))))
out = {k: ([round(min(v),1), round(max(v),1)] if v else None) for k, v in res.items()}
json.dump(out, open(argv[1], "w"), indent=1)
print("OK", out)

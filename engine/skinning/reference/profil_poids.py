import bpy, sys, json
from mathutils import Vector
argv = sys.argv[sys.argv.index("--")+1:]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=argv[0], automatic_bone_orientation=False)
A = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
M = [o for o in bpy.data.objects if o.type == 'MESH'][0]
def os_(n):
    return [pb for pb in A.pose.bones if pb.name.split(":")[-1] == n][0]
bpy.context.scene.frame_set(bpy.context.scene.frame_start)
bpy.context.view_layer.update()
coude = A.matrix_world @ os_("LeftForeArm").head
epaule = A.matrix_world @ os_("LeftArm").head
poignet = A.matrix_world @ os_("LeftHand").head
info = {"echelle_armature": list(A.matrix_world.to_scale()), "echelle_mesh": list(M.matrix_world.to_scale()),
        "coude": list(coude), "epaule": list(epaule), "poignet": list(poignet),
        "longueur_bras_m": round((coude-epaule).length,4), "longueur_avant_bras_m": round((poignet-coude).length,4)}
gi = {g.index: g.name.split(":")[-1] for g in M.vertex_groups}
# profil : distance non signée au coude, par tranches de 1 cm, poids moyens bras / avant-bras
bins = {}
for v in M.data.vertices:
    p = M.matrix_world @ v.co
    d = (p - coude).length
    if d > 0.25: continue
    wa = sum(g.weight for g in v.groups if gi.get(g.group) == "LeftArm")
    wf = sum(g.weight for g in v.groups if gi.get(g.group) == "LeftForeArm")
    k = int(d*100)  # cm
    bins.setdefault(k, []).append((wa, wf))
profil = []
for k in sorted(bins):
    L = bins[k]; n = len(L)
    profil.append([k, n, round(sum(a for a,_ in L)/n,3), round(sum(b for _,b in L)/n,3)])
info["profil_cm_n_wa_wf"] = profil
# largeur de mélange : plage de distance où wa et wf sont tous deux > 0,05 sur au moins un sommet
mix = [k for k, n, wa, wf in profil if 0.05 < wa < 0.95 or 0.05 < wf < 0.95]
info["zone_melange_cm"] = [min(mix), max(mix)] if mix else None
json.dump(info, open(argv[1], "w"), indent=1)
print("OK")

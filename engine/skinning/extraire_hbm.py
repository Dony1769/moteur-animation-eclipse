"""Extrait le corps complet HBM (test B) : mesh seul, sans armature ni poids."""
import bpy, sys, json
argv = sys.argv[sys.argv.index("--")+1:]
sortie_blend, sortie_json = argv[0], argv[1]
src = "/home/claude/moteur3d/assets/hbm/human-base-meshes-bundle-v1.4.1/human_base_meshes_bundle.blend"
with bpy.data.libraries.load(src, link=False) as (data_from, data_to):
    data_to.objects = [n for n in data_from.objects if n.startswith("GEO-body_male_realistic")]
objs = [o for o in data_to.objects if o is not None]
for o in list(bpy.data.objects):
    if o not in objs:
        bpy.data.objects.remove(o, do_unlink=True)
rapport = {}
for o in objs:
    bpy.context.scene.collection.objects.link(o)
    me = o.data
    rapport[o.name] = {"sommets": len(me.vertices), "faces": len(me.polygons),
        "dimensions": [round(v,4) for v in o.dimensions], "groupes": len(o.vertex_groups),
        "armature": o.parent is not None, "materiaux": len(me.materials),
        "uv": [u.name for u in me.uv_layers]}
bpy.ops.wm.save_as_mainfile(filepath=sortie_blend)
json.dump(rapport, open(sortie_json, "w"), indent=2, ensure_ascii=False)
print("OK", rapport)

"""Morphologie féminine (axe 4) : corps féminin HBM skinné sur le squelette masculin par poids AUTOMATIQUES de Blender.

Ce ne sont pas des poids faits à la main : Bone Heat (ARMATURE_AUTO). La différence de source de poids est
donc une variable du test ; elle est signalée dans le rapport.

Entrées : corps_skin.blend (squelette + corps masculin), corps_hbm.blend (corps féminin, sans armature).
Sortie : .blend contenant les deux corps et le corps féminin lié à l'armature.

Usage : blender -b --factory-startup --disable-autoexec corps_skin.blend -P engine/validation/skinning/preparer_femme.py -- corps_hbm.blend SORTIE.blend
"""
import bpy
import sys

argv = sys.argv[sys.argv.index("--") + 1:]
source_hbm, sortie = argv[0], argv[1]

arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
male = bpy.data.objects["GEO-body_male_realistic"]

with bpy.data.libraries.load(source_hbm, link=False) as (data_from, data_to):
    data_to.objects = [n for n in data_from.objects if n == "GEO-body_female_realistic"]
fem = data_to.objects[0]
bpy.context.scene.collection.objects.link(fem)
fem.matrix_world = male.matrix_world.copy()
for mo in list(fem.modifiers):
    if mo.type == "ARMATURE":
        fem.modifiers.remove(mo)
for g in list(fem.vertex_groups):
    fem.vertex_groups.remove(g)

bpy.ops.object.select_all(action="DESELECT")
fem.select_set(True)
arm.select_set(True)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.parent_set(type="ARMATURE_AUTO")
bpy.context.view_layer.update()

groupes = [g.name for g in fem.vertex_groups]
sans_poids = sum(1 for v in fem.data.vertices if not v.groups)
print("FEMME groupes", len(groupes), "sommets sans poids", sans_poids, "sommets", len(fem.data.vertices))
bpy.ops.wm.save_as_mainfile(filepath=sortie)
print("PREPARE_FEMME_OK", sortie)

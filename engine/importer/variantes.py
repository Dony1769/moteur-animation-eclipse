"""Fabrique des variantes de test à partir d'un FBX source (copies, jamais l'original).

Variantes produites :
  A_sans_armature   : armature supprimée, groupes de poids conservés
  B_poids_partiels  : 30 % des sommets sans aucun poids (skinning incomplet)
  C_sans_poids      : armature présente, aucun groupe de poids
Usage : blender -b --factory-startup --disable-autoexec -P engine/importer/variantes.py -- SOURCE.fbx DOSSIER_SORTIE
"""
import os
import sys

import bpy


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    source, sortie = argv[0], argv[1]
    os.makedirs(sortie, exist_ok=True)

    def charger():
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.fbx(filepath=source, automatic_bone_orientation=True)
        return [o for o in bpy.data.objects if o.type == "MESH"], [o for o in bpy.data.objects if o.type == "ARMATURE"]

    # A : sans armature
    meshes, arms = charger()
    for m in meshes:
        for mod in [x for x in m.modifiers if x.type == "ARMATURE"]:
            m.modifiers.remove(mod)
    for a in arms:
        bpy.data.objects.remove(a, do_unlink=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(sortie, "A_sans_armature.blend"))

    # B : poids partiels (30 % des sommets sans poids)
    meshes, arms = charger()
    for m in meshes:
        for i, v in enumerate(m.data.vertices):
            if i % 10 < 3:
                for g in list(v.groups):
                    m.vertex_groups[g.group].remove([i])
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(sortie, "B_poids_partiels.blend"))

    # C : armature sans poids
    meshes, arms = charger()
    for m in meshes:
        m.vertex_groups.clear()
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(sortie, "C_sans_poids.blend"))
    print("VARIANTES_OK", sortie)


main()

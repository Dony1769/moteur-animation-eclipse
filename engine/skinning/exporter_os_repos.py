"""Exporte les segments des os au repos (tête, queue, repère armature) pour la pondération par distance.

Usage : blender -b --factory-startup --disable-autoexec FICHIER.blend -P engine/skinning/exporter_os_repos.py -- SORTIE.json
Les noms sont ceux de l'armature (préfixe mixamorig: conservé).
"""
import bpy, sys, json
argv = sys.argv[sys.argv.index("--") + 1:]
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
M = arm.matrix_world
out = {}
for b in arm.data.bones:
    out[b.name] = {"tete": list((M @ b.head_local)[:]), "queue": list((M @ b.tail_local)[:])}
json.dump({"armature": arm.name, "os": out}, open(argv[0], "w"), indent=1)
print("OS", len(out))

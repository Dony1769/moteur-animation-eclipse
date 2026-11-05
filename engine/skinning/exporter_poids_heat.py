"""Poids Blender « heat » (ARMATURE_AUTO) pour le maillage du bras, exportés dans l'ordre des os donnees.

Usage : blender -b --factory-startup --disable-autoexec FICHIER.blend -P engine/skinning/exporter_poids_heat.py -- SORTIE.npz ORDRE.json
Travaille sur une COPIE du maillage (la source n'est pas modifiée). Les poids sont exportés dans le même
ordre de sommets que le maillage source (ce qui doit correspondre à donnees.rest).
"""
import bpy, sys, json
import numpy as np
argv = sys.argv[sys.argv.index("--") + 1:]
sortie, ordre_json = argv[0], argv[1]
ordre = json.load(open(ordre_json))            # liste des noms d'os dans l'ordre donnees7
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
src = next(o for o in bpy.data.objects if o.type == "MESH" and len(o.data.vertices) == 10582) if any(
    o.type == "MESH" and len(o.data.vertices) == 10582 for o in bpy.data.objects) else None
if src is None:
    raise SystemExit("maillage de 10582 sommets introuvable")
bpy.ops.object.select_all(action="DESELECT")
cop = src.copy(); cop.data = src.data.copy()
bpy.context.collection.objects.link(cop)
for g in list(cop.vertex_groups): cop.vertex_groups.remove(g)
for m in list(cop.modifiers): cop.modifiers.remove(m)
bpy.ops.object.select_all(action="DESELECT")
arm.select_set(True); cop.select_set(True); bpy.context.view_layer.objects.active = arm
bpy.ops.object.parent_set(type="ARMATURE_AUTO")
W = np.zeros((len(cop.data.vertices), len(ordre)))
for i, nom in enumerate(ordre):
    g = cop.vertex_groups.get(nom)
    if g is None: continue
    for v in cop.data.vertices:
        for ge in v.groups:
            if ge.group == g.index: W[v.index, i] = ge.weight
np.savez(sortie, W=W, nombre_sommets=len(W))
print("HEAT sommets", len(W), "sans poids", int((W.sum(1) == 0).sum()), "somme moyenne", round(float(W.sum(1).mean()), 3))

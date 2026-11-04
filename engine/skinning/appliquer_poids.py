"""Réécrit des poids optimisés (npy : N×B, ordre des os de exporter_poids.py) dans un .blend, sans toucher à l'original.
Usage : blender -b --factory-startup --disable-autoexec -P engine/skinning/appliquer_poids.py -- SOURCE.blend POIDS.npy SORTIE.blend
"""
import bpy, sys, numpy as np
sys.path.insert(0, "/home/claude/moteur_3_0/engine/skinning")
import auto_skin as ak
argv = sys.argv[sys.argv.index("--") + 1:]
src, npy, sortie = argv[0], argv[1], argv[2]
W = np.load(npy)
bpy.ops.wm.open_mainfile(filepath=src)
corps = bpy.data.objects[ak.ENTREE_NOM]
arm = [m.object for m in corps.modifiers if m.type == "ARMATURE"][0]
noms = [b.name for b in arm.data.bones]
groupes = {n: (corps.vertex_groups.get(n) or corps.vertex_groups.new(name=n)) for n in noms}
for i in range(W.shape[0]):
    for b, n in enumerate(noms):
        w = float(W[i, b])
        if w > 1e-6: groupes[n].add([i], w, "REPLACE")
        else:
            try: groupes[n].remove([i])
            except RuntimeError: pass
bpy.ops.wm.save_as_mainfile(filepath=sortie)
print("APPLIQUE_OK", sortie)

"""Version normalisée d'un personnage : transformations appliquées aux maillages (copie, jamais l'original).

Pour chaque maillage : détache du parent en conservant sa transformation monde, puis applique
position, rotation et échelle aux sommets. Les armatures sont conservées telles quelles.
Usage : blender -b --factory-startup --disable-autoexec -P engine/importer/normaliser.py -- ENTREE.blend SORTIE.blend [FACTEUR] [AXE_HAUT]
"""
import sys

import bpy


def normaliser(entree, sortie, facteur=1.0, axe_haut="z"):
    """facteur : échelle uniforme (ex. 0.01) ; axe_haut : axe vertical actuel (« y » => rotation vers Z)."""
    import math
    bpy.ops.wm.open_mainfile(filepath=entree)
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    for o in meshes:
        bpy.ops.object.select_all(action="DESELECT")
        o.select_set(True)
        bpy.context.view_layer.objects.active = o
        if o.parent is not None:
            bpy.ops.object.parent_clear(type="CLEAR_KEEP_TRANSFORM")
        if facteur != 1.0:
            o.scale = (o.scale[0] * facteur, o.scale[1] * facteur, o.scale[2] * facteur)
        if axe_haut == "y":
            o.rotation_euler = (math.radians(90), 0.0, 0.0)  # Y vers Z (rotation autour de X)
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    bpy.ops.wm.save_as_mainfile(filepath=sortie)
    return len(meshes)


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:]
    fac = float(argv[2]) if len(argv) > 2 else 1.0
    axe = argv[3] if len(argv) > 3 else "z"
    n = normaliser(argv[0], argv[1], fac, axe)
    print("NORMALISE_OK", n, "maillages")

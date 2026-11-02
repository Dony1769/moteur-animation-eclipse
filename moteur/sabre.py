"""Épée de Kaël (exécutée dans Blender). Jalon 4 : tenue par la main droite pendant le coup.

Maillages simples : lame effilée, garde, poignée. Ce sont des formes de travail : à l'écran, seuls leurs
contours tracés (Freestyle) apparaissent.
"""
import bmesh
import bpy
import math

from mathutils import Vector

from moteur import costume


def _lame(longueur=0.85, largeur=0.035, epaisseur=0.012):
    """Lame effilée : un prisme dont la pointe est fine."""
    bm = bmesh.new()
    bases = [
        Vector((-largeur, 0.0, 0.0)), Vector((largeur, 0.0, 0.0)),
        Vector((largeur, 0.0, epaisseur)), Vector((-largeur, 0.0, epaisseur)),
    ]
    pointe = [Vector((-largeur * 0.1, 0.0, 0.0)), Vector((largeur * 0.1, 0.0, 0.0)),
              Vector((largeur * 0.1, 0.0, epaisseur)), Vector((-largeur * 0.1, 0.0, epaisseur))]
    bas = [bm.verts.new(v) for v in bases]
    haut = [bm.verts.new(v + Vector((0.0, longueur * 0.85, 0.0))) for v in bases]
    fin = [bm.verts.new(v + Vector((0.0, longueur, 0.0))) for v in pointe]
    bm.verts.ensure_lookup_table()
    for i in range(4):
        j = (i + 1) % 4
        bm.faces.new((bas[i], bas[j], haut[j], haut[i]))
        bm.faces.new((haut[i], haut[j], fin[j], fin[i]))
    bm.faces.new(bas)
    bm.faces.new(fin)
    mesh = bpy.data.meshes.new("LameMaillage")
    bm.to_mesh(mesh)
    bm.free()
    return mesh


def creer(arm, cote="R"):
    """Crée l'épée et la rattache à la main (os hand_R). Renvoie l'objet."""
    lame = bpy.data.objects.new("Lame", _lame())
    lame.data.materials.append(costume._mat("AcierClair", (0.80, 0.84, 0.90), (0.40, 0.44, 0.52)))
    bpy.context.scene.collection.objects.link(lame)
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0.0, 0.0, 0.0))
    garde = bpy.context.active_object
    garde.name = "Garde"
    garde.scale = (0.14, 0.03, 0.025)
    garde.data.materials.append(costume._mat("OrGarde", (0.85, 0.70, 0.30), (0.45, 0.35, 0.12)))
    bpy.ops.mesh.primitive_cylinder_add(radius=0.016, depth=0.16, location=(0.0, 0.0, 0.0))
    poignee = bpy.context.active_object
    poignee.name = "Poignee"
    poignee.data.materials.append(costume._mat("CuirBrun", (0.36, 0.22, 0.12), (0.16, 0.09, 0.05)))
    for objet in (lame, garde, poignee):
        objet.parent = arm
        objet.parent_type = "BONE"
        objet.parent_bone = f"hand_{cote}"
    # position dans la main : poignée axée sur l'os de la main (Y), au centre de la paume ; lame dans le
    # prolongement des doigts. Réglages mesurés sur le rendu de contrôle (smoke/out/main).
    poignee.rotation_euler = (math.radians(90), 0.0, 0.0)
    garde.rotation_euler = (0.0, 0.0, 0.0)
    poignee.location = Vector((0.0, 0.02, 0.0))
    garde.location = Vector((0.0, 0.10, 0.0))
    lame.location = Vector((0.0, 0.11, 0.0))
    lame.rotation_euler = (0.0, 0.0, 0.0)
    return lame, garde, poignee

"""Mesures dans le monde 3D : hauteurs, positions à l'image, quel que soit l'angle de la caméra.

Règles apprises (voir APPRENTISSAGE.md, section Mesure) :
- Ne jamais mesurer avec obj.bound_box pour un objet déformé par une armature : la boîte peut être périmée.
  Mesurer les sommets évalués (depsgraph), transformés par la matrice monde.
- Pour une position à l'image : bpy_extras.object_utils.world_to_camera_view donne (x, y, distance) ;
  x et y sont entre 0 et 1 dans le cadre, distance > 0 si le point est devant la caméra.
"""
import bpy
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view


def sommets_monde(obj):
    """Sommets d'un maillage évalué (après armature et modificateurs), en coordonnées monde."""
    dg = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(dg)
    maillage = ev.to_mesh()
    try:
        return [ev.matrix_world @ v.co for v in maillage.vertices]
    finally:
        ev.to_mesh_clear()


def maillages_de(arm):
    """Maillages dont l'armature est le parent ou le modificateur."""
    return [o for o in bpy.data.objects if o.type == "MESH" and o.find_armature() is arm]


def z_min(arm):
    """Point le plus bas du personnage, en mètres, dans le monde."""
    bpy.context.view_layer.update()
    return min(p.z for m in maillages_de(arm) for p in sommets_monde(m))


def position_image(scene, cam, point):
    """Position d'un point monde dans le cadre : (x, y) de 0 à 1, et distance (> 0 = devant la caméra)."""
    co = world_to_camera_view(scene, cam, Vector(point))
    return co.x, co.y, co.z

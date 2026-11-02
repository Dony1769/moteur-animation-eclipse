"""Costume et traits de Kaël (exécuté dans Blender). Jalon 3.

Le corps MB-Lab est un seul maillage : on attribue un matériau par face selon sa position (hauteur, largeur),
sans ajouter de couleur au-delà de celles des matériaux définis ici. Les cheveux et les yeux sont des
maillages séparés, rattachés à l'os de la tête.

Limites : la cape n'est pas encore simulée ; les vêtements sont des zones du corps, pas des habits modélisés.
"""
import math

import bmesh
import bpy
from mathutils import Vector

from moteur import scene4s


def _mat(nom, clair, ombre):
    return scene4s._mat_deux_tons(nom, clair, ombre)


MATERIAUX = {
    "peau": ("PeauKael", (0.93, 0.78, 0.66), (0.42, 0.30, 0.26)),
    "chemise": ("ChemiseCreme", (0.95, 0.90, 0.76), (0.55, 0.50, 0.40)),
    "pantalon": ("PantalonSombre", (0.16, 0.18, 0.26), (0.05, 0.06, 0.09)),
    "ceinture": ("CeintureBrune", (0.42, 0.26, 0.14), (0.20, 0.12, 0.06)),
    "bottes": ("BottesMarron", (0.36, 0.20, 0.10), (0.16, 0.08, 0.04)),
    "cheveux": ("CheveuxNoirBleu", (0.12, 0.14, 0.24), (0.04, 0.05, 0.10)),
    "pointes": ("PointesBleues", (0.25, 0.50, 0.95), (0.10, 0.20, 0.45)),
    "yeux": ("YeuxBleus", (0.30, 0.60, 1.00), (0.12, 0.25, 0.50)),
}


def _classer(z, x):
    """Renvoie le nom du matériau pour une face de centre (x, z)."""
    ax = abs(x)
    if z < 0.16:
        return "bottes"
    if 0.96 < z < 1.04 and ax < 0.24:
        return "ceinture"
    if z >= 1.5:
        return "peau"
    if 1.02 <= z < 1.44 and ax < 0.24:
        return "chemise"
    if z < 1.0 and ax < 0.30:
        return "pantalon"
    return "peau"


def appliquer_costume(corps):
    """Remplace les matériaux du corps par zones (un matériau par zone, couleur fixe)."""
    ordre = list(MATERIAUX.keys())[:6]
    corps.data.materials.clear()
    index = {}
    for cle in ordre:
        nom, clair, ombre = MATERIAUX[cle]
        corps.data.materials.append(_mat(nom, clair, ombre))
        index[cle] = len(corps.data.materials) - 1
    bm = bmesh.new()
    bm.from_mesh(corps.data)
    for f in bm.faces:
        c = f.calc_center_median()
        f.material_index = index[_classer(c.z, c.x)]
    bm.to_mesh(corps.data)
    bm.free()


def _lier_tete(objet, arm, offset=(0.0, 0.0, 0.0), echelle=(1.0, 1.0, 1.0)):
    """Rattache un objet à l'os de la tête (suit les mouvements de la tête)."""
    objet.parent = arm
    objet.parent_type = "BONE"
    objet.parent_bone = "head"
    objet.location = Vector(offset)
    objet.scale = echelle


def ajouter_cheveux(arm):
    """Cheveux noir-bleu en calotte, avec des pointes bleues. Maillages rattachés à l'os de la tête."""
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=0.125, location=(0.0, 0.0, 0.0))
    calotte = bpy.context.active_object
    calotte.name = "CheveuxCalotte"
    calotte.data.materials.append(_mat(*MATERIAUX["cheveux"]))
    # on ne garde que la moitié supérieure : la calotte couvre le haut du crâne
    bm = bmesh.new()
    bm.from_mesh(calotte.data)
    coupe = [v for v in bm.verts if v.co.z < -0.02]
    bmesh.ops.delete(bm, geom=coupe, context="VERTS")
    bm.to_mesh(calotte.data)
    bm.free()
    _lier_tete(calotte, arm, offset=(0.0, -0.01, -0.02), echelle=(1.12, 1.18, 1.0))
    pointes = []
    for i, (x, z, rx) in enumerate([(-0.07, 0.05, 0.6), (0.0, 0.10, 0.0), (0.07, 0.05, -0.6)]):
        bpy.ops.mesh.primitive_cone_add(vertices=6, radius1=0.035, depth=0.11, location=(x, 0.02, 0.15 + z))
        cone = bpy.context.active_object
        cone.name = f"PointeCheveu{i}"
        cone.rotation_euler = (0.0, rx, 0.0)
        cone.data.materials.append(_mat(*MATERIAUX["pointes"]))
        _lier_tete(cone, arm)
        pointes.append(cone)
    return calotte, pointes


def ajouter_yeux(arm):
    """Yeux bleus : deux petites sphères sur la face (côté -Y, face de Kaël)."""
    yeux = []
    for i, x in enumerate((-0.035, 0.035)):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=6, radius=0.012, location=(x, -0.095, 0.075))
        oeil = bpy.context.active_object
        oeil.name = f"OeilBleu{i}"
        oeil.data.materials.append(_mat(*MATERIAUX["yeux"]))
        _lier_tete(oeil, arm)
        yeux.append(oeil)
    return yeux

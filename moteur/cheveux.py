"""Chevelure réelle de Kaël : système de particules « cheveux » émis du cuir chevelu du corps MB-Lab.

Remplace la calotte en sphère de costume.py. Les cheveux suivent la déformation du corps (ils sont
attachés à la peau par l'armature), et leur matériau est le même deux tons que le reste du costume.
"""
import bpy

from moteur import costume


def ajouter(corps, nb_cheveux=260, longueur=0.10):
    """Cheveux émis du sommet du crâne : peu de mèches courtes, sans enfants (style de la série : formes nettes)."""
    zmax = max(v.co.z for v in corps.data.vertices)
    groupe = corps.vertex_groups.new(name="Cuir")
    sommets = [v.index for v in corps.data.vertices if v.co.z > zmax - 0.06]
    groupe.add(sommets, 1.0, "REPLACE")

    corps.data.materials.append(costume._mat(*costume.MATERIAUX["cheveux"]))
    indice = len(corps.data.materials)                       # index 1-basé pour les particules

    bpy.context.view_layer.objects.active = corps
    bpy.ops.object.particle_system_add()
    psys = corps.particle_systems[-1]
    psys.vertex_group_density = "Cuir"
    ps = psys.settings
    ps.type = "HAIR"
    ps.use_advanced_hair = True
    ps.count = nb_cheveux
    ps.hair_length = longueur
    ps.hair_step = 5
    ps.emit_from = "FACE"
    ps.child_type = "NONE"
    ps.material = indice
    ps.material_slot = corps.data.materials[indice - 1].name
    psys.name = "Cheveux"
    return psys

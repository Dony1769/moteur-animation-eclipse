"""Pose hiérarchique (cinématique directe) : chaque os tourne autour de son articulation,
après que ses parents ont été posés. Corrige la limite des tests « os isolé » : un avant-bras suit le bras.

Règle : poser les os PARENTS d'abord ; mettre la couche de vue à jour après chaque os.
Axes en monde ; l'armature doit être à l'identité (vérifié : Squelette_HBM).
"""
import bpy, math
from mathutils import Matrix, Vector

def poser_chaine(arm, etapes):
    """etapes : liste ordonnée de (nom_os, axe_monde, angle_deg). Renvoie l'état d'origine des matrices."""
    # Sauvegarde des transformations LOCALES (matrix_basis) : indépendantes de l'ordre des os.
    sauve = {pb.name: pb.matrix_basis.copy() for pb in arm.pose.bones}
    for nom, axe, ang in etapes:
        pb = arm.pose.bones[nom]
        t = pb.matrix.translation.copy()          # articulation dans la pose courante (déjà suivie du parent)
        rot = Matrix.Rotation(math.radians(ang), 4, Vector(axe).normalized())
        pb.matrix = Matrix.Translation(t) @ rot @ Matrix.Translation(-t) @ pb.matrix
        bpy.context.view_layer.update()
    return sauve

def restaurer(arm, sauve):
    for nom, m in sauve.items():
        arm.pose.bones[nom].matrix_basis = m
    bpy.context.view_layer.update()

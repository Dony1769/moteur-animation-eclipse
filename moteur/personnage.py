"""Personnage MB-Lab (exécuté dans Blender). Jalon 3 : corps masculin, rig avec doigts.

Choix :
- Préréglage « m_an01 » (MB-Lab, style anime masculin) : le seul préréglage masculin au style
  proche des dessins de référence. Les préréglages « anime_*_base » n'existent pas dans cette version.
- Les traits de Kaël (cheveux noir-bleu, yeux bleus, cape, broche, ceinture) ne sont PAS encore appliqués.
  Ils viennent des jalons suivants (cheveux : particules MB-Lab ; cape : simulation de tissu).
"""
import sys

import addon_utils
import bpy

PRESET = "m_an01"
NOM_ADDON = "mblab"
CHAINES_DOIGTS = ("index", "middle", "ring", "pinky", "thumb")


def activer_mblab():
    """Active l'addon MB-Lab et renvoie son module."""
    addon_utils.enable(NOM_ADDON, default_set=True, persistent=True)
    return sys.modules[NOM_ADDON]


def creer(preset=PRESET):
    """Crée le personnage à partir du préréglage et renvoie (corps, armature)."""
    mod = activer_mblab()
    bpy.context.scene.mblab_character_name = preset
    mod.start_lab_session()
    bpy.ops.mbast.character_generator()
    arm = next(o for o in bpy.data.objects if o.type == "ARMATURE" and o.name.endswith("_skeleton"))
    corps = next(o for o in bpy.data.objects if o.type == "MESH" and o.parent is arm or
                 (o.type == "MESH" and o.modifiers and any(m.type == "ARMATURE" for m in o.modifiers)))
    return corps, arm


def doigts_complets(arm, cote="R"):
    """True si les cinq doigts de la main ont leurs trois phalanges."""
    return all(f"{d}{i:02d}_{cote}" in arm.data.bones for d in CHAINES_DOIGTS for i in (1, 2, 3))


def plier_doigts(arm, angle, cote="R"):
    """Plie les phalanges des doigts d'une main (rotation autour de X, en radians)."""
    for d in CHAINES_DOIGTS:
        for i in (1, 2, 3):
            nom = f"{d}{i:02d}_{cote}"
            if nom in arm.pose.bones:
                pb = arm.pose.bones[nom]
                pb.rotation_mode = "XYZ"
                pb.rotation_euler = (angle, 0.0, 0.0)

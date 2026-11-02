"""Test Blender (à lancer dans Blender) : le personnage a des doigts complets et une pose les plie.

    tools/tester_blender.sh tests/blender_personnage.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import bpy  # noqa: E402
from moteur import personnage  # noqa: E402


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    corps, arm = personnage.creer()
    assert personnage.doigts_complets(arm, "R"), "doigts incomplets"
    assert personnage.doigts_complets(arm, "L"), "doigts incomplets (gauche)"
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="POSE")
    personnage.plier_doigts(arm, 1.1, "R")
    bpy.ops.object.mode_set(mode="OBJECT")
    assert abs(arm.pose.bones["index02_R"].rotation_euler.x - 1.1) < 1e-6, "pose non appliquée"
    print("TEST_PERSONNAGE_OK")


if __name__ == "__main__":
    main()

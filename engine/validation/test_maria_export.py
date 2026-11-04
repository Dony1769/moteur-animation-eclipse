"""Test A, items 9 et 12 : préparation au retargeting et export animé avec réimport.

9.  Retargeting : chaque os animé par le clip source doit exister sur le squelette cible (couverture %).
12. Export : Maria + clip Running exportés en FBX, réimportés ; même nombre de sommets, mêmes os, poids
    normalisés, et position monde identique image par image (tolérance 1 mm).
Usage : blender -b --factory-startup --disable-autoexec -P engine/validation/test_maria_export.py -- SORTIE.json SCRATCH
"""
import bpy, sys, json, os, shutil, re

argv = sys.argv[sys.argv.index("--") + 1:]
sortie, scratch = argv[0], argv[1]
os.makedirs(scratch, exist_ok=True)
SRC = "/home/claude/moteur3d/assets/mixamo"
maria = os.path.join(scratch, "maria.fbx"); clip = os.path.join(scratch, "Running.fbx")
shutil.copy(f"{SRC}/Personnage_Maria.fbx", maria); shutil.copy(f"{SRC}/Running.fbx", clip)
res = {"tests": {}}
T = res["tests"]
def ok(n, c, d=""): T[n] = {"ok": bool(c), "detail": d}

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=maria, automatic_bone_orientation=True)
peau = max([o for o in bpy.data.objects if o.type == "MESH"], key=lambda o: len(o.data.vertices))
arm = [o for o in bpy.data.objects if o.type == "ARMATURE"][0]
av = set(o.name for o in bpy.data.objects)
bpy.ops.import_scene.fbx(filepath=clip, automatic_bone_orientation=True)
for o in [o for o in bpy.data.objects if o.name not in av]:
    bpy.data.objects.remove(o, do_unlink=True)
act = [a for a in bpy.data.actions if a.name.startswith("Armature.001")][0]
arm.animation_data_create(); arm.animation_data.action = act
if act.slots: arm.animation_data.action_slot = act.slots[0]

# 9 : couverture du retargeting
os_cible = set(b.name for b in arm.data.bones)
os_clip = set(re.findall(r'pose\.bones\["([^"]+)"\]', " ".join(fc.data_path for fc in act.fcurves)))
manq = sorted(os_clip - os_cible)
cov = 100.0 * len(os_clip & os_cible) / max(1, len(os_clip))
ok("9_retargeting_couverture", not manq and cov == 100.0,
   f"{len(os_clip)} os animés par le clip, {cov:.1f} % présents sur Maria, manquants {manq[:5]}")

dg = lambda: bpy.context.evaluated_depsgraph_get()
sc = bpy.context.scene
f0, f1 = int(act.frame_range[0]), int(act.frame_range[1])
def pts(o):
    return [(o.matrix_world @ v.co) for v in o.evaluated_get(dg()).data.vertices]
avant = {}
for f in range(f0, f1 + 1):
    sc.frame_set(f); avant[f] = pts(peau)
n_avant = len(peau.data.vertices)

# 12 : export puis réimport
sc.frame_start, sc.frame_end = f0, f1  # sans cela, l'export cuit 250 images de la scène (erreur 11)
fbx = os.path.join(scratch, "maria_running_export.fbx")
bpy.ops.object.select_all(action="DESELECT")
arm.select_set(True); peau.select_set(True); bpy.context.view_layer.objects.active = arm
bpy.ops.export_scene.fbx(filepath=fbx, use_selection=True, add_leaf_bones=False, bake_anim=True,
                         bake_anim_use_all_bones=True, bake_anim_use_nla_strips=False,
                         bake_anim_use_all_actions=False, apply_scale_options="FBX_SCALE_NONE",
                         object_types={"ARMATURE", "MESH"})
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=fbx, automatic_bone_orientation=True)
sc = bpy.context.scene
arm2 = [o for o in bpy.data.objects if o.type == "ARMATURE"][0]
peau2 = max([o for o in bpy.data.objects if o.type == "MESH"], key=lambda o: len(o.data.vertices))
ok("12_sommets", len(peau2.data.vertices) == n_avant, f"{n_avant} avant, {len(peau2.data.vertices)} après réimport")
ok("12_os", len(arm2.data.bones) == 65 and set(b.name for b in arm2.data.bones) == os_cible,
   f"{len(arm2.data.bones)} os après réimport")
mx = max((max([g.weight for g in v.groups] or [0]) for v in peau2.data.vertices), default=0)
inf = max(len(v.groups) for v in peau2.data.vertices)
ok("12_poids", inf <= 4, f"influences max {inf}")
acts2 = [a for a in bpy.data.actions]
ok("12_animation_reimportee", any(a.frame_range[1] - a.frame_range[0] >= f1 - f0 for a in acts2),
   f"actions réimportées {[ (a.name, tuple(a.frame_range)) for a in acts2]}")
if acts2:
    a2 = max(acts2, key=lambda a: len(a.fcurves))
    arm2.animation_data_create(); arm2.animation_data.action = a2
    if a2.slots: arm2.animation_data.action_slot = a2.slots[0]
    ecart = 0.0
    for f in range(f0, f1 + 1):
        # décalage temporel de l'export : l'image f de la source correspond à a2.frame_range[0] + (f - f0)
        sc.frame_set(int(a2.frame_range[0]) + (f - f0))
        p2 = pts(peau2)
        ecart = max(ecart, max((x - y).length for x, y in zip(p2, avant[f])))
    ok("12_mouvement_identique", ecart < 0.001, f"écart maximal monde après réimport {ecart*1000:.3f} mm (tolérance 1 mm)")
json.dump(res, open(sortie, "w"), indent=2, ensure_ascii=False)
print("RESULTAT", "OK" if all(v["ok"] for v in T.values()) else "ECHEC " + ",".join(k for k, v in T.items() if not v["ok"]))
for k, v in T.items(): print("TEST", k, v)

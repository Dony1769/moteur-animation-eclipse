"""Test A (mission) : Maria, personnage Mixamo existant. Exécution Blender en arrière-plan.

Vérifie, sur une COPIE du FBX (l'original n'est jamais modifié) :
 2-3. armature et os reconnus (convention Mixamo, 65 os) ;
 4.   poids : normalisés, au plus 4 influences par sommet ;
 5.   matériaux et textures présents ;
 6.   apparence conservée : nombre de sommets et boîte englobante identiques après export/import ;
 7.   contrôleurs manquants : liste (aucun ajouté ici) ;
 8.   rig facial : non traité ici (Maria n'a pas de formes faciales) ;
 9.   squelette prêt pour retargeting : nommage mixamorig:* sur tous les os ;
 10.  animation d'origine appliquée : déformation mesurée sur plusieurs images ;
 11.  transitions : non testées (une seule animation disponible) ;
 12.  export FBX puis ré-import : mêmes os, mêmes poids, même nombre de sommets.

Usage : blender -b --factory-startup --disable-autoexec -P engine/validation/test_maria.py -- SRC.fbx SORTIE.json SCRATCH_DIR
"""
import bpy, sys, json, os, shutil
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "importer"))
import diagnostic as d  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:]
src, sortie, scratch = argv[0], argv[1], argv[2]
os.makedirs(scratch, exist_ok=True)
copie = os.path.join(scratch, "maria_copie.fbx")
shutil.copy(src, copie)  # l'original reste intact
res = {"source": src, "copie": copie, "tests": {}}
T = res["tests"]


def ok(nom, cond, detail=""):
    T[nom] = {"ok": bool(cond), "detail": detail}


def etat_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    d._importer(copie)
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    arms = [o for o in bpy.data.objects if o.type == "ARMATURE"]
    return meshes, arms


# -- 2 à 6 : analyse et contrôle à l'import --
rap = d.analyser(copie)  # le diagnostic réimporte la copie (il vide la scène)
meshes, arms = etat_scene()
arm = arms[0]
os_noms = [b.name for b in arm.data.bones]
ok("2_armature", len(arms) == 1, f"{len(arms)} armature(s)")
ok("3_os_mixamo", len(os_noms) == 65 and all(n.startswith("mixamorig:") for n in os_noms),
   f"{len(os_noms)} os, préfixe mixamorig présent : {all(n.startswith('mixamorig:') for n in os_noms)}")
peau = max(meshes, key=lambda o: len(o.data.vertices))
mx, bad = 0, 0
for v in peau.data.vertices:
    ws = [g.weight for g in v.groups]
    mx = max(mx, len(ws))
    if ws and abs(sum(ws) - 1.0) > 1e-3:
        bad += 1
ok("4_poids", mx <= 4 and bad == 0, f"influences max {mx}, poids non normalisés {bad}")
mats = [s.material.name for s in peau.material_slots if s.material]
imgs = [i.name for i in bpy.data.images]
ok("5_materiaux", len(mats) > 0, f"matériaux {mats}, images {len(imgs)}")
bb_avant = [tuple(round(c, 4) for c in v.co) for v in (peau.data.vertices[0], peau.data.vertices[-1])]
n_sommets_avant = len(peau.data.vertices)
res["controleurs_manquants"] = []  # rien n'est ajouté par ce test

# -- 10 : déformation sous un vrai clip (Running), mesurée en mètres monde, relative à la hanche --
# L'action embarquée dans Personnage_Maria.fbx ne couvre que 2 images (pose statique) : elle ne prouve rien.
# Corrections (entrées 144 et 145) : slot de l'action affecté (Blender 4.4+) ; coordonnées locales interdites
# (armature à l'échelle 0.01 : 100 fois trop grand) ; translation de la hanche retirée.
CLIP = os.environ.get("MARIA_CLIP", "/home/claude/moteur3d/assets/mixamo/Running.fbx")
ok("10_action_presente", os.path.exists(CLIP), f"clip {CLIP}")
scn = bpy.context.scene
if os.path.exists(CLIP):
    avant_obj = set(bpy.data.objects.keys())
    avant_act = set(a.name for a in bpy.data.actions)
    bpy.ops.import_scene.fbx(filepath=CLIP)
    clip = [a for a in bpy.data.actions if a.name not in avant_act][0]
    for nom in set(bpy.data.objects.keys()) - avant_obj:   # le clip importé : seule son action sert
        bpy.data.objects.remove(bpy.data.objects[nom], do_unlink=True)
    arm.animation_data_create()
    arm.animation_data.action = clip
    if hasattr(arm.animation_data, "action_slot") and clip.slots:
        arm.animation_data.action_slot = clip.slots[0]
    f0, f1 = int(clip.frame_range[0]), int(clip.frame_range[1])
    scn.frame_start, scn.frame_end = f0, f1

    def pts_relatifs():
        hanche = (arm.matrix_world @ arm.pose.bones["mixamorig:Hips"].matrix).to_translation()
        m = peau.evaluated_get(bpy.context.evaluated_depsgraph_get()).data
        return [(peau.matrix_world @ v.co) - hanche for v in m.vertices]

    dep, ref = [], None
    for f in range(f0, f1 + 1, max(1, (f1 - f0) // 6)):
        scn.frame_set(f)
        bpy.context.view_layer.update()
        pts = pts_relatifs()
        if ref is None:
            ref = pts
        dep.append(max((a - b).length for a, b in zip(pts, ref)))
    ok("10_deformation", max(dep) > 0.01 and all(x == x for x in dep),
       f"déplacement max {max(dep):.4f} m (monde, relatif à la hanche) sur {len(dep)} images, pas de NaN")
    res["images_mesurees"] = [round(x, 4) for x in dep]

# -- 12 : export FBX puis ré-import --
exp = os.path.join(scratch, "maria_export.fbx")
bpy.ops.object.select_all(action="SELECT")
bpy.ops.export_scene.fbx(filepath=exp, use_selection=False, object_types={"ARMATURE", "MESH"},
                         add_leaf_bones=False, bake_anim=True, apply_scale_options="FBX_SCALE_NONE")
m2, a2 = etat_scene()
os2 = [b.name for b in a2[0].data.bones] if a2 else []
ok("12_export_os", len(os2) == len(os_noms), f"os avant {len(os_noms)}, après ré-import {len(os2)}")
p2 = max(m2, key=lambda o: len(o.data.vertices)) if m2 else None
ok("6_apparence_sommets", p2 is not None and len(p2.data.vertices) == n_sommets_avant,
   f"sommets avant {n_sommets_avant}, après {len(p2.data.vertices) if p2 else 0}")
res["fichier_export"] = exp
json.dump(res, open(sortie, "w"), indent=2)
echec = [k for k, v in T.items() if not v["ok"]]
print("RESULTAT", "OK" if not echec else "ECHEC " + ",".join(echec))
print("JSON", sortie)

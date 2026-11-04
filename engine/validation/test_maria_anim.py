"""Test A, partie animation : clips Mixamo appliqués au rig de Maria, puis transition Idle -> Running.

Corrections par rapport à la première version (erreurs documentées dans docs/erreurs_apprises.md) :
 - distances mesurées en MÈTRES MONDE (matrix_world), et non en coordonnées locales du maillage
   (l'armature est à l'échelle 0.01 : les valeurs locales étaient 100 fois trop grandes) ;
 - déformation mesurée RELATIVEMENT À LA HANCHE : le clip Running contient un déplacement racine
   (le personnage avance) ; sans cette correction, la translation du corps serait comptée comme déformation ;
 - slot de l'action affecté explicitement (Blender 4.5) : sans cela l'action n'agit pas sur l'armature.

Mesures :
 - déformation par image dans Running : médiane et maximum du déplacement relatif à la hanche ;
 - transition Idle -> Running : saut à la jonction (relatif à la hanche) comparé au déplacement médian
   par image dans Running. Seuil 3 : valeur choisie a priori, à confirmer sur d'autres clips.

Usage : blender -b --factory-startup --disable-autoexec -P engine/validation/test_maria_anim.py -- SORTIE.json SCRATCH
"""
import bpy, sys, json, os, shutil, statistics

argv = sys.argv[sys.argv.index("--") + 1:]
sortie, scratch = argv[0], argv[1]
os.makedirs(scratch, exist_ok=True)
SRC = "/home/claude/moteur3d/assets/mixamo"
MARIA = os.path.join(scratch, "maria.fbx")
shutil.copy(os.path.join(SRC, "Personnage_Maria.fbx"), MARIA)
clips = {}
for nom in ("Idle", "Running"):
    c = os.path.join(scratch, nom + ".fbx")
    shutil.copy(os.path.join(SRC, nom + ".fbx"), c)
    clips[nom] = c

res = {"tests": {}, "unites": "metres monde, relatif a la hanche"}
T = res["tests"]


def ok(nom, cond, detail=""):
    T[nom] = {"ok": bool(cond), "detail": detail}


bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=MARIA, automatic_bone_orientation=True)
peau = max([o for o in bpy.data.objects if o.type == "MESH"], key=lambda o: len(o.data.vertices))
arm = [o for o in bpy.data.objects if o.type == "ARMATURE"][0]
ANIM = {}
for nom, chemin in clips.items():
    avant_act = set(a.name for a in bpy.data.actions)
    avant_obj = set(o.name for o in bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=chemin, automatic_bone_orientation=True)
    nouvelles = [a for a in bpy.data.actions if a.name not in avant_act]
    for o in [o for o in bpy.data.objects if o.name not in avant_obj]:
        bpy.data.objects.remove(o, do_unlink=True)
    ANIM[nom] = nouvelles[0] if nouvelles else None
    ok(f"clip_{nom}_importe", ANIM[nom] is not None, f"action {ANIM[nom].name if ANIM[nom] else 'absente'}")

scn = bpy.context.scene
dg = lambda: bpy.context.evaluated_depsgraph_get()


def affecter(act):
    arm.animation_data_create()
    arm.animation_data.action = act
    if hasattr(arm.animation_data, "action_slot") and act.slots:
        arm.animation_data.action_slot = act.slots[0]
    bpy.context.view_layer.update()


def points_relatifs():
    """Sommets en mètres monde, moins la position monde de la hanche (retire la translation du corps)."""
    hanche = (arm.matrix_world @ arm.pose.bones["mixamorig:Hips"].matrix).to_translation()
    m = peau.evaluated_get(dg()).data
    return [(peau.matrix_world @ v.co) - hanche for v in m.vertices]


def ecart_max_moy(a, b):
    d = [(x - y).length for x, y in zip(a, b)]
    return max(d), statistics.mean(d)


# -- Running : déformation par image, relative à la hanche --
if ANIM.get("Running"):
    affecter(ANIM["Running"])
    f0, f1 = int(ANIM["Running"].frame_range[0]), int(ANIM["Running"].frame_range[1])
    images = {}
    for f in range(f0, f1 + 1):
        scn.frame_set(f)
        images[f] = points_relatifs()
    nan = any(v.x != v.x for p in images.values() for v in p)
    pas_max, pas_moy = [], []
    for f in range(f0 + 1, f1 + 1):
        mx, mo = ecart_max_moy(images[f], images[f - 1])
        pas_max.append(mx)
        pas_moy.append(mo)
    mediane_pas = statistics.median(pas_moy)
    res["running_pas_median_m"] = round(mediane_pas, 5)
    res["running_pas_max_m"] = round(max(pas_max), 5)
    ok("running_deformation",
       (not nan) and 0.0 < mediane_pas < 0.2,
       f"images {f0}-{f1} : pas moyen médian {mediane_pas:.4f} m, pas maximal {max(pas_max):.4f} m, NaN {nan}")
else:
    mediane_pas = 0.0
    ok("running_deformation", False, "clip Running absent")

# -- Transition Idle -> Running (bandes NLA) --
if ANIM.get("Idle") and ANIM.get("Running"):
    arm.animation_data.action = None
    trk = arm.animation_data.nla_tracks.new()
    i0, i1 = int(ANIM["Idle"].frame_range[0]), int(ANIM["Idle"].frame_range[1])
    fin_idle = i0 + (i1 - i0)
    # Fondu enchaîné : Running commence FONDU_IMAGES images avant la fin d'Idle (chevauchement NLA)
    FONDU_IMAGES = int(os.environ.get("FONDU", "12"))
    s1 = trk.strips.new("Idle", i0, ANIM["Idle"])
    trk2 = arm.animation_data.nla_tracks.new()  # piste supérieure : les bandes ne peuvent pas se chevaucher sur une même piste
    s2 = trk2.strips.new("Running", fin_idle + 1 - FONDU_IMAGES, ANIM["Running"])
    s2.blend_in = FONDU_IMAGES
    res["fondu_images"] = FONDU_IMAGES
    # mesure du saut au point de passage (fin d'Idle -> image suivante), toujours dans le fondu
    scn.frame_set(fin_idle)
    avant = points_relatifs()
    scn.frame_set(fin_idle + 1)
    apres = points_relatifs()
    saut_max, saut_moy = ecart_max_moy(avant, apres)
    ratio = saut_moy / mediane_pas if mediane_pas > 0 else float("inf")
    res["transition_saut_moy_m"] = round(saut_moy, 5)
    res["transition_ratio"] = round(ratio, 3)
    ok("transition_idle_running", ratio < 3.0,
       f"saut moyen à la jonction {saut_moy:.4f} m (max {saut_max:.4f} m), pas médian Running {mediane_pas:.4f} m, ratio {ratio:.2f} (seuil 3)")
else:
    ok("transition_idle_running", False, "clips manquants")

json.dump(res, open(sortie, "w"), indent=2)
print("RESULTAT", "OK" if all(v["ok"] for v in T.values()) else "ECHEC " + ",".join(k for k, v in T.items() if not v["ok"]))
for k, v in T.items():
    print("TEST", k, v)
